"""Orquestrador do agente: liga os módulos na ordem do fluxo.

fatos -> (API de pedidos) -> consulta RAG -> regras -> verificação -> resposta ou fallback
"""
import time

from . import config
from .generation.redator import Redator, RedatorTemplate, montar_resposta
from .integrations.pedidos import MockPedidosClient, PedidosClient, aplicar_pedido
from .models import Resposta
from .rag.consulta import montar_consulta
from .rag.embeddings import TfidfEmbedder
from .rag.ingest import carregar_base
from .rag.retriever import Recuperador
from .rag.store import IndiceVetorial
from .rules.engine import decidir
from .rules.facts import extrair_fatos, extrair_pedido_id
from .verification.verificador import Verificador


class Agente:
    def __init__(self, recuperador: Recuperador, pedidos: PedidosClient | None = None,
                 verificador: Verificador | None = None, redator: Redator | None = None) -> None:
        self.recuperador = recuperador
        self.pedidos = pedidos
        self.verificador = verificador or Verificador()
        self.redator = redator or RedatorTemplate()

    def responder(self, pergunta: str, pedido_id: str | None = None) -> Resposta:
        inicio = time.perf_counter()
        fatos = extrair_fatos(pergunta)

        pedido_id = pedido_id or extrair_pedido_id(pergunta)
        if pedido_id and self.pedidos:
            aplicar_pedido(fatos, pedido_id, self.pedidos.obter(pedido_id))

        consulta = montar_consulta(pergunta, fatos)
        recuperados = self.recuperador.buscar(consulta)
        parecer = decidir(fatos)

        # evidência = melhor trecho recuperado de cada fonte de que a regra depende
        melhores = {}
        for r in recuperados:
            if r.trecho.fonte in parecer.fontes_necessarias and r.trecho.fonte not in melhores:
                melhores[r.trecho.fonte] = r
        evidencias = list(melhores.values())

        verificacao = self.verificador.verificar(pergunta, parecer, fatos, evidencias)
        trace = {
            "pedido_id": pedido_id,
            "fatos": fatos.to_dict(),
            "consulta": consulta,
            "recuperados": [{"fonte": r.trecho.fonte, "pergunta": r.trecho.pergunta, "score": round(r.score, 3)}
                            for r in recuperados],
            "decisao_preliminar": parecer.decisao.value,
            "checks": verificacao.checks,
            "latencia_ms": round((time.perf_counter() - inicio) * 1000, 1),
        }
        return montar_resposta(parecer, fatos, verificacao, evidencias, trace, self.redator)


def criar_agente() -> Agente:
    """Monta o agente com os padrões: base em CSV, TF-IDF em memória e API de pedidos mock."""
    indice = IndiceVetorial(TfidfEmbedder())
    indice.construir(carregar_base(config.CSV_BASE))
    return Agente(Recuperador(indice), pedidos=MockPedidosClient(config.PEDIDOS_MOCK))
