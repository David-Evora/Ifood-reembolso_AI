"""Interface web. Uso: uvicorn agente.ui:app --app-dir src --port 8080

Fluxo: navegador -> esta UI -> webhook do n8n -> agente. O WEBHOOK_TOKEN fica só aqui no servidor.
Login (HTTP Basic): usuário = e-mail, senha = UI_SENHA. O n8n confere se o e-mail está em
USUARIOS_PERMITIDOS, então a lista de pessoas continua sendo decidida num lugar só.

shortcut: senha única compartilhada, sem limite de tentativas. Para mais de uma equipe,
trocar por SSO/OIDC num proxy na frente e confiar na identidade que ele repassar.
"""
import hmac
import json
from contextlib import asynccontextmanager
from pathlib import Path
from urllib import request
from urllib.error import HTTPError, URLError

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field

from . import config

ESTATICOS = Path(__file__).parent / "ui_static"
LIMITE_RESPOSTA = 1_000_000  # bytes lidos do n8n

_CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
        "img-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")

_ERROS_N8N = {
    403: "Acesso negado pelo n8n: confira se o seu e-mail está em USUARIOS_PERMITIDOS e se o WEBHOOK_TOKEN é o mesmo nos dois lados.",
    404: "O n8n não encontrou o webhook. Importe o workflow e ative-o (chave no canto superior direito).",
}


@asynccontextmanager
async def _ciclo_de_vida(app: FastAPI):
    if len(config.UI_SENHA) < config.UI_SENHA_TAMANHO_MINIMO:
        raise RuntimeError(f"UI_SENHA ausente ou curta (mínimo {config.UI_SENHA_TAMANHO_MINIMO} caracteres). Defina no .env.")
    if len(config.WEBHOOK_TOKEN) < config.WEBHOOK_TOKEN_TAMANHO_MINIMO:
        raise RuntimeError(f"WEBHOOK_TOKEN ausente ou curto (mínimo {config.WEBHOOK_TOKEN_TAMANHO_MINIMO} caracteres). Defina no .env.")
    yield


app = FastAPI(title="Interface do Agente de Reembolsos", version="0.3.0", lifespan=_ciclo_de_vida,
              docs_url=None, redoc_url=None, openapi_url=None)
_basic = HTTPBasic(realm="Agente de Reembolsos")


@app.middleware("http")
async def _cabecalhos_de_seguranca(request: Request, call_next):
    resposta = await call_next(request)
    resposta.headers["Content-Security-Policy"] = _CSP
    resposta.headers["X-Content-Type-Options"] = "nosniff"
    resposta.headers["Referrer-Policy"] = "no-referrer"
    resposta.headers["Cache-Control"] = "no-store"
    return resposta


def _usuario(cred: HTTPBasicCredentials = Depends(_basic)) -> str:
    # bytes: compare_digest levanta TypeError com texto não ASCII
    senha_ok = hmac.compare_digest(cred.password.encode(), config.UI_SENHA.encode())
    if not config.UI_SENHA or not senha_ok or not cred.username.strip():
        raise HTTPException(status_code=401, detail="credenciais inválidas", headers={"WWW-Authenticate": 'Basic realm="Agente de Reembolsos"'})
    return cred.username.strip()


class Pergunta(BaseModel):
    pergunta: str = Field(min_length=3, max_length=2000)
    pedido_id: str | None = Field(default=None, pattern=r"^\d{3,20}$")


def _chamar_n8n(usuario: str, p: Pergunta) -> JSONResponse:
    corpo = json.dumps({"usuario": usuario, "pergunta": p.pergunta, "pedido_id": p.pedido_id}).encode()
    req = request.Request(config.UI_WEBHOOK_URL, data=corpo, method="POST", headers={
        "Content-Type": "application/json", "X-Webhook-Token": config.WEBHOOK_TOKEN})
    try:
        with request.urlopen(req, timeout=20) as r:
            return JSONResponse(json.loads(r.read(LIMITE_RESPOSTA)))
    except HTTPError as e:
        try:
            dados = json.loads(e.read(LIMITE_RESPOSTA))
        except ValueError:
            dados = {}
        if isinstance(dados, dict) and "decisao" in dados:  # o n8n devolve um fallback com 503 quando o agente está fora
            return JSONResponse(dados, status_code=e.code)
        return JSONResponse({"erro": _ERROS_N8N.get(e.code, f"O n8n respondeu com erro {e.code}.")}, status_code=502)
    except (URLError, TimeoutError, ValueError):
        return JSONResponse({"erro": "Não consegui falar com o n8n. Confira se ele está de pé (docker compose ps)."}, status_code=502)


@app.get("/saude")
def saude() -> dict:
    return {"status": "ok"}  # sem login, de propósito: é o healthcheck do Docker


@app.post("/api/perguntar")
def perguntar(p: Pergunta, usuario: str = Depends(_usuario)) -> JSONResponse:
    return _chamar_n8n(usuario, p)


def _estatico(nome: str, tipo: str):
    return FileResponse(ESTATICOS / nome, media_type=tipo)


@app.get("/", dependencies=[Depends(_usuario)])
def pagina():
    return _estatico("index.html", "text/html; charset=utf-8")


@app.get("/app.js", dependencies=[Depends(_usuario)])
def script():
    return _estatico("app.js", "text/javascript; charset=utf-8")


@app.get("/style.css", dependencies=[Depends(_usuario)])
def estilo():
    return _estatico("style.css", "text/css; charset=utf-8")
