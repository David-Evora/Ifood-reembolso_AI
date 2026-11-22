"""Extrai fatos estruturados do texto da pergunta.

shortcut: regex sobre texto normalizado, com tratamento só das negações mais comuns
("não foi erro do restaurante", "cliente não desistiu"). Quando o volume de casos justificar,
trocar por um classificador (LLM com saída estruturada) mantendo a assinatura `extrair_fatos`.
"""
import re

from ..models import Causa, Etapa, Fatos
from ..textos import normalizar

_NEGACAO = re.compile(
    r"\bnao (foi|houve|e|teve)\s+(erro|falha|culpa|problema)\s+(do|da|de|no|na)\s+\w+"
    r"|\bnao (desist\w*|quer\w* cancelar)"
)

_CAUSAS = {
    Causa.RESTAURANTE: re.compile(
        r"(erro|falha|culpa|problema)\s+(do|de|no)\s+restaurante"
        r"|restaurante\s+(errou|cancelou|falhou|esqueceu|nao tinha|nao tem|nao tinha)"
    ),
    Causa.APP: re.compile(
        r"(erro|falha|bug|problema)\s+(do|de|no)\s+(app|aplicativo)"
        r"|(app|aplicativo)\s+(falhou|travou|bugou|cancelou|errou)"
    ),
    Causa.ENTREGADOR: re.compile(
        r"(erro|falha|culpa|problema)\s+(do|no)\s+(entregador|motoboy)"
        r"|(entregador|motoboy)\s+(errou|se perdeu|extraviou|sumiu|nao entregou)"
        r"|extravi|entrega (incorreta|errada)"
    ),
    Causa.CLIENTE: re.compile(
        r"desist|mudou de ideia|mudei de ideia|nao quer mais|nao quero mais"
        r"|se arrependeu|cliente cancelou|pediu sem querer"
    ),
}

_ETAPAS = (
    (Etapa.ANTES_DO_PREPARO, re.compile(r"antes (do|de) (o )?(preparo|preparar|preparacao)|ainda nao (comecou|iniciou) (o )?preparo")),
    (Etapa.SAIU_PARA_ENTREGA, re.compile(r"\bsaiu\b.{0,25}\b(entrega|rota)\b|\bdespach|a caminho|em rota|em transito")),
    (Etapa.EM_PREPARO, re.compile(r"em preparo|sendo preparado")),
)

_FLAGS = {
    "falta_item": re.compile(
        r"falta de (ingrediente|item|produto|estoque)|sem (o )?(item|ingrediente)"
        r"|nao (tinha|tem|havia) (o )?(item|ingrediente|produto)|(item|produto) (indisponivel|esgotado)"
        r"|ingrediente (acabou|esgotou)"
    ),
    "nao_autorizou": re.compile(r"nao autoriz|sem autoriza|nao fez (esse|o) pedido|nao reconhece"),
    "fraude": re.compile(r"fraud|golpe|clonad|pagamento suspeito|chargeback"),
    "multiplos_reembolsos": re.compile(
        r"(varios|multiplos|diversos|muitos|\d+|dois|tres|quatro) reembolsos"
        r"|reembolsos? (seguidos?|repetidos?|em sequencia)|reembolso (de novo|outra vez)"
    ),
    "cobranca_duplicada": re.compile(r"cobrad\w+ (duas|2) vezes|cobranca (dupla|duplicada|em duplicidade)|cobrou (duas|2) vezes|duas cobrancas"),
    "cobrado_apos_cancelamento": re.compile(r"cobr\w+.{0,40}cancel|cancel.{0,40}cobr"),
}

_PEDIDO_ID = re.compile(r"(?:pedido|#)\s*(?:n[o.]?\s*)?#?(\d{3,})")


def extrair_pedido_id(pergunta: str) -> str | None:
    m = _PEDIDO_ID.search(normalizar(pergunta))
    return m.group(1) if m else None


def extrair_fatos(pergunta: str) -> Fatos:
    t = _NEGACAO.sub(" ", normalizar(pergunta))
    f = Fatos()

    f.causas = {c for c, rx in _CAUSAS.items() if rx.search(t)}
    for etapa, rx in _ETAPAS:
        if rx.search(t):
            f.etapa = etapa
            break
    for nome, rx in _FLAGS.items():
        setattr(f, nome, bool(rx.search(t)))

    # "consta como entregue" + "não chegou": duas frases que juntas formam o caso da Fluxo de Entrega
    if re.search(r"nao (chegou|recebeu|recebi|foi recebido)", t) and re.search(r"entregue|consta", t):
        f.consta_entregue_nao_chegou = True
        f.etapa = f.etapa or Etapa.ENTREGUE
    # cobrança duplicada é um caso diferente de "cobrado após cancelamento"
    if f.cobranca_duplicada:
        f.cobrado_apos_cancelamento = False

    if len(f.causas) > 1:
        f.conflitos.append("a descrição aponta mais de uma causa: " + ", ".join(sorted(c.value for c in f.causas)))
    return f
