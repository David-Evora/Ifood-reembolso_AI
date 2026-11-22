"""Etapa 2 do RAG: embeddings.

`Embedder` é a interface. O padrão é TF-IDF esparso, que roda offline e sem dependências.
Para trocar por embeddings densos (OpenAI, sentence-transformers, Bedrock...), basta uma classe
com os mesmos três métodos; o resto do sistema não muda.
"""
import math
from collections import Counter
from typing import Protocol

from ..textos import tokens

Vetor = dict[str, float]


class Embedder(Protocol):
    def fit(self, textos: list[str]) -> None: ...
    def embed(self, texto: str) -> Vetor: ...
    def similaridade(self, a: Vetor, b: Vetor) -> float: ...


class TfidfEmbedder:
    def __init__(self) -> None:
        self._idf: dict[str, float] = {}
        self._idf_desconhecido = 1.0

    def fit(self, textos: list[str]) -> None:
        n = len(textos)
        df = Counter(t for x in textos for t in set(tokens(x)))
        self._idf = {t: math.log((1 + n) / (1 + c)) + 1 for t, c in df.items()}
        self._idf_desconhecido = math.log(1 + n) + 1

    def embed(self, texto: str) -> Vetor:
        # Termos fora do vocabulário nunca casam com a base, mas entram na norma:
        # assim uma pergunta cheia de palavras desconhecidas não parece "quase igual" a um trecho.
        v = {t: c * self._idf.get(t, self._idf_desconhecido) for t, c in Counter(tokens(texto)).items()}
        norma = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {t: x / norma for t, x in v.items()}

    def similaridade(self, a: Vetor, b: Vetor) -> float:
        if len(a) > len(b):
            a, b = b, a
        return sum(x * b.get(t, 0.0) for t, x in a.items())
