# Agente de Reembolsos e Cancelamentos (RAG modular)

POC de um agente interno que decide se um pedido é elegível a reembolso com base em uma base de conhecimento. O agente só responde quando tem **fonte** e **confiança** suficientes; senão, pede a informação que falta, validação manual ou ticket.

Cenário central: **"O cliente quer reembolso, mas o pedido já saiu para entrega. Ainda é permitido?"**

![Interface do agente](docs/interface.png)

> A base de conhecimento é uma simulação educacional (material de curso) e **não representa políticas oficiais** de nenhuma empresa. Os pedidos em `data/pedidos_mock.json` são fictícios.

## Como funciona

```
Interface web ─► n8n (token, usuário permitido) ─► API Python ─► fatos ─► API de pedidos
                                                                   │
              resposta fundamentada  ◄─ verificação ◄─ regras ◄─ RAG (políticas)
              ou fallback (manual, ticket, link)
```

- **RAG em módulos** (`rag/`): ingestão, embeddings, índice vetorial e recuperação, cada um atrás de uma interface trocável.
- **Motor de regras** (`rules/`): decide a elegibilidade de forma determinística, por causa (restaurante, app, entregador, cliente) e etapa do pedido. O LLM, quando entrar, só redige.
- **Verificação** (`verification/`): libera a resposta só se a recuperação trouxe as fontes de que a regra depende, sem conflito entre a descrição e a API. Caso contrário, fallback.
- **LLM opcional** (`llm/`): um redator que escreve a resposta em linguagem natural e um juiz que pode vetar. Desligado por padrão; veja a seção abaixo.

Detalhes em [docs/ARQUITETURA.md](docs/ARQUITETURA.md).

## Cenários cobertos (todos com teste automatizado)

| Caso | Decisão |
|---|---|
| Saiu para entrega, erro do restaurante, do app ou falha do entregador | Elegível (Políticas 3.2 e 2.1/2.2) |
| Saiu para entrega, desistência do cliente | Pode não ser elegível; não promete (Política 4.1) |
| Saiu para entrega, causa desconhecida | Fallback: pergunta a causa e dá o link de suporte |
| Descrição contradiz a API, pedido inexistente, status financeiro diverge | Fallback |
| Falta de ingrediente | Reembolso automático (Política 2.3) |
| Cobrado após cancelamento ou em duplicidade | Validar estorno ou abrir ticket (Fluxo Financeiro) |
| Cliente diz que não autorizou; consta entregue mas não chegou | Validação manual (Política 4.4, Fluxo de Entrega) |
| Suspeita de fraude; vários reembolsos seguidos | Antifraude (Fluxo Segurança) |

## LLM (opcional)

Sem configurar nada, o agente roda só com regras + RAG, e a resposta sai de um template. Para ligar um modelo, preencha no `.env` o bloco `LLM_*`:

| Variável | O que é |
|---|---|
| `LLM_PROVEDOR` | `anthropic` ou `openai` (o formato `openai` também serve para Azure, Ollama, vLLM etc.). Vazio = desligado. |
| `LLM_API_KEY` | **Sua chave do provedor do modelo** (a que você cria no site dele). Não é a `AGENTE_API_KEY`, que é a senha entre n8n e a API Python e vem do gerador. |
| `LLM_MODELO` | Nome do modelo, como o provedor o chama. |
| `LLM_URL_BASE` | Opcional; vazio usa o endereço padrão do provedor. |
| `LLM_REDATOR` / `LLM_JUIZ` | Liga o redator (padrão `true`) e o juiz (padrão `false`). |

Com LLM ligado, o agente precisa de internet: ative também `COMPOSE_FILE=docker-compose.yml:docker-compose.llm.yml` no `.env` (no Windows, use `;` no lugar de `:`). Sem isso ele fica isolado e o redator cai no template; com o juiz ligado, tudo iria para o fallback.

Como o LLM é contido:
- **Ele não decide.** A elegibilidade vem do motor de regras; o redator só reescreve uma decisão pronta e o juiz só pode vetar.
- **O texto digitado pelo usuário nunca vai no prompt do redator**, só a decisão e os trechos da base. Se a saída vier vazia, longa ou sem citar todas as fontes, vale o template.
- **O juiz falha fechado:** se o revisor cair ou responder fora do formato, vale o veto.
- A chave fica só no serviço do agente, nunca em log, erro ou resposta. Redirecionamentos do provedor não são seguidos.
- O LLM só é chamado quando a resposta foi aprovada pela verificação; o fallback nunca gasta chamada.

## Subir com Docker

Requisito: Docker com Compose.

1. Rode `python scripts/gerar_env.py`: ele cria o `.env` e gera os segredos do sistema (`AGENTE_API_KEY`, `N8N_ENCRYPTION_KEY`, `WEBHOOK_TOKEN`, `UI_SENHA`). Depois edite `USUARIOS_PERMITIDOS` com o seu e-mail. Sem Python, copie `.env.example` para `.env` e preencha esses campos à mão. As variáveis `LLM_*` o gerador nunca preenche: são suas (veja a seção LLM).
2. `docker compose up -d --build` e confira com `docker compose ps` (agente e interface devem ficar *healthy*).
3. Abra http://localhost:5678, crie a conta do n8n e importe o workflow:
   `docker compose exec n8n n8n import:workflow --input=/workflows/workflow_agente_reembolso.json`
4. Recarregue o n8n, abra "Agente de Reembolsos" e **ative** o workflow.
5. Abra http://localhost:8080. Login: usuário = e-mail de `USUARIOS_PERMITIDOS`, senha = `UI_SENHA`.

Para mudar qualquer configuração, edite o `.env` e rode `docker compose up -d`. Todas as variáveis estão comentadas em `.env.example`.

### Segurança

- Segredos só no `.env` (fora do git e da imagem; o gerador cria o arquivo com permissão só do dono). O compose se recusa a subir com segredo obrigatório vazio.
- O agente fica numa rede Docker interna, sem porta publicada e sem internet; só o n8n o alcança, com `X-API-Key`. Sem a chave configurada a API nem sobe.
- A interface exige login e **não guarda segredos no navegador**: ela repassa a pergunta ao n8n com o `WEBHOOK_TOKEN` no servidor. O n8n confere o token e a lista de e-mails.
- Contêineres sem root, disco somente leitura, sem capabilities. Interface e n8n publicados só em `127.0.0.1`. Cabeçalhos CSP, `nosniff` e `no-store` na interface; texto do servidor nunca entra na página como HTML.
- **Com LLM ligado**, o agente ganha saída para a internet (só ele); o resto continua isolado.
- **Limites:** senha única compartilhada, sem limite de tentativas nem de requisições; HTTP puro (para expor fora da máquina, coloque um proxy HTTPS na frente e ajuste `N8N_PROTOCOL`, `N8N_SECURE_COOKIE` e `N8N_WEBHOOK_URL`); o n8n precisa de `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` para ler o `.env`. Fixe uma versão em `N8N_IMAGE`.

## Rodar sem Docker

```bash
pip install -r requirements-dev.txt
pytest                                   # 98 testes

PYTHONPATH=src python -m agente.cli "O cliente quer reembolso, mas o pedido já saiu para entrega."
PYTHONPATH=src python -m agente.cli "Reembolso do pedido já despachado" --pedido 1001 --json
```

Pedidos de teste (API mock): `1001` falha do restaurante, `1002` desistência do cliente, `1003` sem causa registrada, `1004` entregador, `1005` app, `1006` cancelado com pagamento capturado, `1007` entregue, `1008` estornado mas em preparo (diverge).

## Estrutura

```
src/agente/
  rag/ rules/ integrations/ verification/ generation/   núcleo do agente
  llm/                                                  clientes, redator e juiz com LLM (opcional)
  orchestrator.py  api.py (para o n8n)  ui.py + ui_static/ (interface)  cli.py
data/    base_conhecimento.csv, pedidos_mock.json
n8n/     workflow_agente_reembolso.json
docs/    ARQUITETURA.md, interface.png
tests/   98 testes
```

## Limitações conhecidas

- A extração de fatos usa regex; trata as negações mais comuns, mas não substitui um classificador.
- A base não tem vigência nas fontes, nem define "falha comprovada" ou "exceções operacionais específicas": esses casos vão para validação manual.
- TF-IDF não entende sinônimos; é o primeiro candidato a troca por embeddings densos.
- O workflow do n8n foi montado e validado como JSON, mas depende de você importá-lo na sua instância.
- Os clientes de LLM foram testados contra servidores simulados nos dois formatos de API, não contra um provedor real: valide com a sua chave e o seu modelo.

## Próximos passos

1. Slack como entrada do workflow, no lugar do webhook.
2. Embeddings densos (interface `Embedder`) e medição da recuperação.
3. Medir o redator e o juiz com LLM contra o template em um conjunto de casos reais.
4. Conjunto de avaliação com perguntas reais: acerto de decisão e taxa de fallback.
5. Vigência e versão nas fontes da base.

## Licença

MIT. Veja [LICENSE](LICENSE).
