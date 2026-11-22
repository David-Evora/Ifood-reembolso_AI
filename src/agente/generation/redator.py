"""Geração da resposta. O texto vem do parecer já validado, nunca de uma decisão do modelo.

`Redator` é o ponto de extensão para um LLM: ele receberia parecer + evidências e reescreveria
`resumo` em linguagem natural. O padrão (template) é determinístico, não alucina e roda offline.
"""
from typing import Protocol

from ..config import SUPORTE_URL
from ..models import Decisao, Fatos, Parecer, Resposta, Resultado, Verificacao

MENSAGEM_FALLBACK = (
    "Não encontrei informações suficientes na base para responder com segurança. "
    "Sugiro abrir um ticket interno ou consultar a política oficial."
)

_PRECISA_HUMANO = {Decisao.VALIDACAO_MANUAL, Decisao.ANTIFRAUDE, Decisao.FALLBACK}


class Redator(Protocol):
    def redigir(self, parecer: Parecer, fatos: Fatos, evidencias: list[Resultado]) -> str: ...


class RedatorTemplate:
    def redigir(self, parecer: Parecer, fatos: Fatos, evidencias: list[Resultado]) -> str:
        fontes = ", ".join(dict.fromkeys(e.trecho.fonte for e in evidencias))
        return f"{parecer.motivo} (Fonte: {fontes})"


def montar_resposta(parecer: Parecer, fatos: Fatos, verificacao: Verificacao,
                    evidencias: list[Resultado], trace: dict, redator: Redator) -> Resposta:
    ev = [{"fonte": e.trecho.fonte, "categoria": e.trecho.categoria, "pergunta": e.trecho.pergunta,
           "resposta": e.trecho.resposta, "score": round(e.score, 3)} for e in evidencias]

    if not verificacao.aprovado:
        passos = ["Solicitar validação manual do caso.", "Orientar a abertura de um ticket interno."]
        if parecer.faltando:
            passos.insert(0, "Se possível, informar: " + "; ".join(parecer.faltando) + ".")
        return Resposta(Decisao.FALLBACK, MENSAGEM_FALLBACK, passos, [], ev, verificacao.confianca,
                        True, SUPORTE_URL, verificacao.motivos, trace, faltando=parecer.faltando)

    passos = list(parecer.passos)
    if parecer.depende_de_causa and not fatos.causa_confirmada:
        passos.append("Atenção: a causa veio só da descrição e não foi confirmada na API do pedido; confirmar antes de aprovar ou negar.")
    precisa_humano = parecer.decisao in _PRECISA_HUMANO
    return Resposta(parecer.decisao, redator.redigir(parecer, fatos, evidencias), passos,
                    sorted({e.trecho.fonte for e in evidencias}), ev, verificacao.confianca,
                    precisa_humano, SUPORTE_URL if precisa_humano else None, [], trace)
