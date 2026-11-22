"""API HTTP que o n8n chama. Uso: uvicorn agente.api:app --app-dir src --port 8000

Segurança:
- A chave AGENTE_API_KEY é obrigatória: sem ela (ou com menos de 32 caracteres) a API não sobe.
- Toda rota de consulta exige o cabeçalho X-API-Key; sem chave configurada nada passa (falha fechada).
- Documentação interativa desligada: a API não anuncia o próprio esquema.
A autenticação do usuário final (Slack/portal) e as permissões ficam no n8n.
"""
import hmac
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from . import config
from .orchestrator import criar_agente


@asynccontextmanager
async def _ciclo_de_vida(app: FastAPI):
    if len(config.API_KEY) < config.API_KEY_TAMANHO_MINIMO:
        raise RuntimeError(
            f"AGENTE_API_KEY ausente ou curta (mínimo {config.API_KEY_TAMANHO_MINIMO} caracteres). "
            "Defina AGENTE_API_KEY no .env (veja .env.example)."
        )
    app.state.agente = criar_agente()  # indexa a base uma vez, na subida
    yield


app = FastAPI(title="Agente de Reembolsos e Cancelamentos", version="0.2.0", lifespan=_ciclo_de_vida,
              docs_url=None, redoc_url=None, openapi_url=None)


class Consulta(BaseModel):
    pergunta: str = Field(min_length=3, max_length=2000)
    pedido_id: str | None = Field(default=None, pattern=r"^\d{3,20}$")
    usuario: str | None = Field(default=None, max_length=100)  # só para o log do n8n; não afeta a decisão


def _exigir_chave(x_api_key: str | None = Header(default=None)) -> None:
    # bytes: compare_digest levanta TypeError com texto não ASCII, o que viraria um erro 500
    esperada = config.API_KEY.encode()
    if not esperada or not hmac.compare_digest((x_api_key or "").encode(), esperada):
        raise HTTPException(status_code=401, detail="chave de API inválida")


@app.get("/saude")
def saude() -> dict:
    return {"status": "ok"}  # sem autenticação, de propósito: é o healthcheck do Docker; não expõe dados


@app.post("/consultar", dependencies=[Depends(_exigir_chave)])
def consultar(c: Consulta) -> dict:
    return app.state.agente.responder(c.pergunta, c.pedido_id).to_dict()
