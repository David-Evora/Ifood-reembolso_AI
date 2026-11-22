import pytest
from fastapi.testclient import TestClient

from agente import config
from agente.api import app

CORPO = {"pergunta": "Pedido 1001 já saiu para entrega, quer reembolso"}


@pytest.fixture
def cliente():
    with TestClient(app) as c:  # abre o lifespan: indexa a base
        yield c


@pytest.fixture
def chave():
    return {"X-API-Key": config.API_KEY}


def test_saude_nao_exige_chave_e_nao_vaza_dados(cliente):
    r = cliente.get("/saude")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_consultar(cliente, chave):
    r = cliente.post("/consultar", json=CORPO, headers=chave)
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["decisao"] == "ELEGIVEL" and corpo["fontes"] and "trace" in corpo


def test_sem_chave_ou_chave_errada_e_401(cliente):
    assert cliente.post("/consultar", json=CORPO).status_code == 401
    assert cliente.post("/consultar", json=CORPO, headers={"X-API-Key": "errada"}).status_code == 401


def test_chave_com_caracteres_nao_ascii_nao_derruba_a_api(cliente):
    r = cliente.post("/consultar", json=CORPO, headers={"X-API-Key": "chavé".encode("latin-1")})
    assert r.status_code == 401


def test_validacao_da_entrada(cliente, chave):
    assert cliente.post("/consultar", json={"pergunta": "ok"}, headers=chave).status_code == 422
    assert cliente.post("/consultar", json={"pergunta": "reembolso do pedido", "pedido_id": "abc"}, headers=chave).status_code == 422
    assert cliente.post("/consultar", json={"pergunta": "x" * 2001}, headers=chave).status_code == 422


def test_docs_desligados(cliente):
    for rota in ("/docs", "/redoc", "/openapi.json"):
        assert cliente.get(rota).status_code == 404


@pytest.mark.parametrize("valor", ["", "curta"])
def test_api_nao_sobe_sem_chave_forte(monkeypatch, valor):
    monkeypatch.setattr(config, "API_KEY", valor)
    with pytest.raises(RuntimeError, match="AGENTE_API_KEY"):
        with TestClient(app):
            pass
