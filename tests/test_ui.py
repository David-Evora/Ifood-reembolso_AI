import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from fastapi.testclient import TestClient

from agente import config
from agente.ui import app

USUARIO = "foodlover@exemplo.com"
LOGIN = (USUARIO, "senha-de-teste-ui")
CORPO = {"pergunta": "Pedido 1001 já saiu para entrega, quer reembolso", "pedido_id": "1001"}
DECISAO = {"decisao": "ELEGIVEL", "resumo": "ok", "passos": [], "fontes": ["Política 3.2"],
           "evidencias": [], "confianca": 1.0, "precisa_humano": False, "suporte_url": None,
           "motivos_baixa_confianca": [], "faltando": [], "trace": {}}


@pytest.fixture
def n8n_falso(monkeypatch):
    """Servidor local que imita o webhook do n8n e guarda o que recebeu."""
    estado = {"status": 200, "corpo": DECISAO, "recebido": []}

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            n = int(self.headers["Content-Length"])
            estado["recebido"].append({"token": self.headers.get("X-Webhook-Token"), "json": json.loads(self.rfile.read(n))})
            dados = json.dumps(estado["corpo"]).encode()
            self.send_response(estado["status"])
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(dados)))
            self.end_headers()
            self.wfile.write(dados)

        def log_message(self, *_):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setattr(config, "UI_WEBHOOK_URL", f"http://127.0.0.1:{srv.server_port}/webhook/reembolso-agente")
    yield estado
    srv.shutdown()


@pytest.fixture
def cliente():
    with TestClient(app) as c:
        yield c


def test_saude_sem_login(cliente):
    assert cliente.get("/saude").json() == {"status": "ok"}


@pytest.mark.parametrize("rota", ["/", "/app.js", "/style.css"])
def test_paginas_exigem_login(cliente, rota):
    r = cliente.get(rota)
    assert r.status_code == 401 and "Basic" in r.headers["www-authenticate"]
    assert cliente.get(rota, auth=LOGIN).status_code == 200


def test_senha_errada_ou_usuario_vazio_e_401(cliente, n8n_falso):
    assert cliente.post("/api/perguntar", json=CORPO, auth=(USUARIO, "errada")).status_code == 401
    assert cliente.post("/api/perguntar", json=CORPO, auth=("  ", LOGIN[1])).status_code == 401
    assert cliente.post("/api/perguntar", json=CORPO).status_code == 401
    assert n8n_falso["recebido"] == []  # nada chegou ao n8n


def test_senha_nao_ascii_nao_derruba(cliente):
    r = cliente.post("/api/perguntar", json=CORPO, headers={"Authorization": "Basic " + __import__("base64").b64encode("a@b.c:sénha".encode("utf-8")).decode()})
    assert r.status_code == 401


def test_encaminha_ao_n8n_com_token_e_usuario_do_login(cliente, n8n_falso):
    r = cliente.post("/api/perguntar", json=CORPO, auth=LOGIN)
    assert r.status_code == 200 and r.json()["decisao"] == "ELEGIVEL"
    chamada = n8n_falso["recebido"][0]
    assert chamada["token"] == config.WEBHOOK_TOKEN
    assert chamada["json"] == {"usuario": USUARIO, **CORPO}


def test_usuario_nao_pode_ser_forjado_no_corpo(cliente, n8n_falso):
    cliente.post("/api/perguntar", json={**CORPO, "usuario": "intruso@x.com"}, auth=LOGIN)
    assert n8n_falso["recebido"][0]["json"]["usuario"] == USUARIO


def test_fallback_503_do_n8n_e_repassado(cliente, n8n_falso):
    n8n_falso.update(status=503, corpo={**DECISAO, "decisao": "FALLBACK", "precisa_humano": True})
    r = cliente.post("/api/perguntar", json=CORPO, auth=LOGIN)
    assert r.status_code == 503 and r.json()["decisao"] == "FALLBACK"


@pytest.mark.parametrize("status,trecho", [(403, "USUARIOS_PERMITIDOS"), (404, "ative"), (500, "500")])
def test_erros_do_n8n_viram_mensagem_amigavel(cliente, n8n_falso, status, trecho):
    n8n_falso.update(status=status, corpo={"erro": "interno"})
    r = cliente.post("/api/perguntar", json=CORPO, auth=LOGIN)
    assert r.status_code == 502 and trecho in r.json()["erro"]


def test_n8n_fora_do_ar(cliente, monkeypatch):
    monkeypatch.setattr(config, "UI_WEBHOOK_URL", "http://127.0.0.1:9/x")
    r = cliente.post("/api/perguntar", json=CORPO, auth=LOGIN)
    assert r.status_code == 502 and "n8n" in r.json()["erro"]


def test_validacao_da_entrada(cliente, n8n_falso):
    for corpo in ({"pergunta": "ok"}, {"pergunta": "reembolso", "pedido_id": "abc"}, {"pergunta": "x" * 2001}):
        assert cliente.post("/api/perguntar", json=corpo, auth=LOGIN).status_code == 422
    assert n8n_falso["recebido"] == []


def test_cabecalhos_de_seguranca(cliente):
    h = cliente.get("/", auth=LOGIN).headers
    assert "script-src 'self'" in h["content-security-policy"] and "frame-ancestors 'none'" in h["content-security-policy"]
    assert h["x-content-type-options"] == "nosniff" and h["cache-control"] == "no-store"


def test_docs_desligados(cliente):
    assert cliente.get("/docs", auth=LOGIN).status_code == 404


@pytest.mark.parametrize("campo,valor", [("UI_SENHA", "curta"), ("WEBHOOK_TOKEN", ""), ("UI_SENHA", "")])
def test_nao_sobe_com_segredos_fracos(monkeypatch, campo, valor):
    monkeypatch.setattr(config, campo, valor)
    with pytest.raises(RuntimeError, match=campo):
        with TestClient(app):
            pass
