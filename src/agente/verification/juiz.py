"""Ponto de extensão para a 'segunda avaliação do modelo' (LLM-as-judge).

Sem juiz configurado, a verificação roda só com os controles determinísticos.
Um juiz recebe a pergunta, o parecer e as evidências e devolve (aprovado, motivo).
Veto do juiz bloqueia a resposta e aciona o fallback.
"""
from typing import Protocol

from ..models import Parecer, Resultado


class Juiz(Protocol):
    def avaliar(self, pergunta: str, parecer: Parecer, evidencias: list[Resultado]) -> tuple[bool, str]: ...
