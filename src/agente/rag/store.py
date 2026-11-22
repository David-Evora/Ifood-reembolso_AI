"""Etapa 3 do RAG: índice vetorial.

Implementação em memória (suficiente para centenas de trechos). Para escalar, troque por
pgvector, Qdrant, OpenSearch etc. mantendo `construir` e `consultar`.
"""
from ..models import Resultado, Trecho
from .embeddings import Embedder, Vetor


class IndiceVetorial:
    def __init__(self, embedder: Embedder) -> None:
        self.embedder = embedder
        self._itens: list[tuple[Trecho, Vetor]] = []

    def construir(self, trechos: list[Trecho]) -> None:
        textos = [t.texto_indexado for t in trechos]
        self.embedder.fit(textos)
        self._itens = [(t, self.embedder.embed(x)) for t, x in zip(trechos, textos)]

    def consultar(self, texto: str, k: int) -> list[Resultado]:
        q = self.embedder.embed(texto)
        resultados = [Resultado(t, self.embedder.similaridade(q, v)) for t, v in self._itens]
        return sorted(resultados, key=lambda r: r.score, reverse=True)[:k]
