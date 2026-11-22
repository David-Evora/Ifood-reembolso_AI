"""Redator com LLM: reescreve em linguagem natural uma decisão que o motor de regras já tomou.

O LLM não decide. Ele recebe só o parecer e os trechos da base, nunca o texto digitado pelo
usuário, então não há como uma pergunta maliciosa injetar instruções aqui. Se a saída vier vazia,
longa demais ou sem citar todas as fontes, vale o texto do template.
"""
import json
import logging

from ..generation.redator import Redator, RedatorTemplate
from ..models import Fatos, Parecer, Resultado
from .cliente import ClienteLLM, LLMErro

log = logging.getLogger(__name__)

MAX_CARACTERES = 700
SISTEMA = (
    "Você escreve, em português claro e objetivo, a resposta de um agente interno de reembolsos para um atendente. "
    "Use SOMENTE os dados fornecidos em JSON. Não mude a decisão e não invente prazos, valores, políticas ou exceções. "
    "Escreva de 2 a 3 frases e cite as fontes entre parênteses, exatamente como fornecidas."
)


class RedatorLLM:
    def __init__(self, cliente: ClienteLLM, reserva: Redator | None = None) -> None:
        self.cliente = cliente
        self.reserva = reserva or RedatorTemplate()

    def redigir(self, parecer: Parecer, fatos: Fatos, evidencias: list[Resultado]) -> str:
        fontes = sorted({e.trecho.fonte for e in evidencias})
        dados = {
            "decisao": parecer.decisao.value,
            "motivo": parecer.motivo,
            "passos": parecer.passos,
            "evidencias": [{"fonte": e.trecho.fonte, "regra": e.trecho.resposta} for e in evidencias],
        }
        try:
            texto = self.cliente.completar(SISTEMA, json.dumps(dados, ensure_ascii=False)).strip()
        except LLMErro as e:
            log.warning("redator LLM indisponível (%s); usando o template", e)
            return self.reserva.redigir(parecer, fatos, evidencias)
        if not texto or len(texto) > MAX_CARACTERES or any(f not in texto for f in fontes):
            log.warning("saída do redator LLM reprovada (vazia, longa ou sem todas as fontes); usando o template")
            return self.reserva.redigir(parecer, fatos, evidencias)
        return texto
