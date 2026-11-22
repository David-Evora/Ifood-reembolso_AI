from agente import config
from agente.rag.embeddings import TfidfEmbedder
from agente.rag.ingest import carregar_base
from agente.rag.retriever import Recuperador
from agente.rag.store import IndiceVetorial


def _recuperador():
    indice = IndiceVetorial(TfidfEmbedder())
    indice.construir(carregar_base(config.CSV_BASE))
    return Recuperador(indice)


def test_ingestao_carrega_as_20_linhas():
    assert len(carregar_base(config.CSV_BASE)) == 20


def test_busca_traz_politica_de_reembolso_apos_entrega():
    fontes = [r.trecho.fonte for r in _recuperador().buscar("reembolso após o pedido sair para entrega")]
    assert "Política 3.2" in fontes[:2]


def test_busca_traz_fluxo_financeiro_para_cobranca_apos_cancelamento():
    fontes = [r.trecho.fonte for r in _recuperador().buscar("cliente foi cobrado após cancelamento")]
    assert fontes[0] == "Fluxo Financeiro"


def test_busca_sem_relacao_nao_traz_nada():
    assert _recuperador().buscar("receita de bolo de cenoura com cobertura de chocolate") == []
