import os

CHAVE_TESTE = "chave-de-teste-" + "x" * 32
os.environ.setdefault("AGENTE_API_KEY", CHAVE_TESTE)  # antes de importar agente.config
os.environ.setdefault("UI_SENHA", "senha-de-teste-ui")
os.environ.setdefault("WEBHOOK_TOKEN", "token-de-teste-webhook")

import pytest  # noqa: E402

from agente.orchestrator import criar_agente  # noqa: E402


@pytest.fixture(scope="session")
def agente():
    return criar_agente()
