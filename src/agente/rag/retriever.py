"""Etapa 4 do RAG: recuperação (busca, ranking e seleção dos melhores trechos)."""
from ..config import SCORE_MINIMO, TOP_K
from ..models import Resultado
from .store import IndiceVetorial


class Recuperador:
    def __init__(self, indice: IndiceVetorial, k: int = TOP_K, score_minimo: float = SCORE_MINIMO) -> None:
        self.indice = indice
        self.k = k
        self.score_minimo = score_minimo

    def buscar(self, consulta: str) -> list[Resultado]:
        return [r for r in self.indice.consultar(consulta, self.k) if r.score >= self.score_minimo]
