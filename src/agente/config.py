"""Configuração central do agente. Cada valor pode ser sobrescrito por variável de ambiente."""
import os
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

CSV_BASE = Path(os.getenv("AGENTE_BASE_CSV", RAIZ / "data" / "base_conhecimento.csv"))
PEDIDOS_MOCK = Path(os.getenv("AGENTE_PEDIDOS_MOCK", RAIZ / "data" / "pedidos_mock.json"))

# --- Recuperação (RAG) ---
TOP_K = int(os.getenv("AGENTE_TOP_K", "5"))
SCORE_MINIMO = float(os.getenv("AGENTE_SCORE_MINIMO", "0.10"))  # trechos abaixo disso são descartados da recuperação
SCORE_FORTE = float(os.getenv("AGENTE_SCORE_FORTE", "0.25"))    # o trecho que sustenta a decisão deve ter pelo menos isso

# --- Verificação de confiança ---
LIMIAR_CONFIANCA = float(os.getenv("AGENTE_LIMIAR_CONFIANCA", "0.70"))
PESOS_VERIFICACAO = {
    "fontes_oficiais": 0.15,
    "fundamentada": 0.25,
    "recuperacao_forte": 0.15,
    "fatos_suficientes": 0.20,
    "sem_conflito": 0.15,
    "causa_confirmada": 0.10,
}
# Falhar em qualquer um destes bloqueia a resposta, mesmo com a nota acima do limiar.
VERIFICACOES_ELIMINATORIAS = ("fontes_oficiais", "fundamentada", "fatos_suficientes", "sem_conflito")

# shortcut: a base não tem coluna de vigência; "oficial" é só o padrão do nome da fonte.
# Quando a base ganhar datas de vigência, validar aqui também.
FONTES_OFICIAIS = re.compile(r"^(Política \d+\.\d+|Política Financeira|Fluxo [\w ]+|Integração API)$")

# --- Escalonamento ---
SUPORTE_URL = os.getenv("AGENTE_SUPORTE_URL", "https://suporte.interno.exemplo/reembolsos")  # placeholder
API_KEY = os.getenv("AGENTE_API_KEY", "")  # obrigatória: a API não sobe sem ela e exige o cabeçalho X-API-Key
API_KEY_TAMANHO_MINIMO = 32

# --- Interface web (ui.py) ---
UI_SENHA = os.getenv("UI_SENHA", "")  # senha do login; o usuário do login é o e-mail, validado pelo n8n
UI_SENHA_TAMANHO_MINIMO = 12
WEBHOOK_TOKEN = os.getenv("WEBHOOK_TOKEN", "")  # o mesmo token que o workflow do n8n confere
WEBHOOK_TOKEN_TAMANHO_MINIMO = 16
UI_WEBHOOK_URL = os.getenv("UI_WEBHOOK_URL", "http://n8n:5678/webhook/reembolso-agente")
