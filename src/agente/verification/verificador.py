"""Verificação de confiabilidade: decide se a resposta pode sair ou se vai para o fallback.

Controles:
  fontes_oficiais    toda fonte citada tem formato de política/fluxo oficial
  fundamentada       o RAG recuperou todas as fontes de que a regra depende
  recuperacao_forte  as evidências têm similaridade suficiente com a consulta
  fatos_suficientes  nada essencial falta para a regra decidir
  sem_conflito       descrição e API não se contradizem
  causa_confirmada   a API confirmou a causa (quando a decisão depende dela)

A nota é a soma dos pesos dos controles aprovados. Os eliminatórios bloqueiam mesmo com nota alta.
"""
from ..config import (FONTES_OFICIAIS, LIMIAR_CONFIANCA, PESOS_VERIFICACAO,
                      SCORE_FORTE, VERIFICACOES_ELIMINATORIAS)
from ..models import Fatos, Parecer, Resultado, Verificacao
from .juiz import Juiz

_MOTIVOS = {
    "fontes_oficiais": "alguma fonte citada não é uma política ou fluxo oficial",
    "fundamentada": "a recuperação não trouxe todas as fontes de que a regra depende",
    "recuperacao_forte": "os trechos recuperados têm pouca semelhança com o caso",
    "fatos_suficientes": "faltam informações para decidir",
    "sem_conflito": "há informações conflitantes",
    "causa_confirmada": "a causa não foi confirmada pela API do pedido",
}


class Verificador:
    def __init__(self, juiz: Juiz | None = None, limiar: float = LIMIAR_CONFIANCA) -> None:
        self.juiz = juiz
        self.limiar = limiar

    def verificar(self, pergunta: str, parecer: Parecer, fatos: Fatos, evidencias: list[Resultado]) -> Verificacao:
        fontes_achadas = {e.trecho.fonte for e in evidencias}
        checks = {
            "fontes_oficiais": all(FONTES_OFICIAIS.match(e.trecho.fonte) for e in evidencias),
            "fundamentada": set(parecer.fontes_necessarias) <= fontes_achadas,
            "recuperacao_forte": all(e.score >= SCORE_FORTE for e in evidencias),
            "fatos_suficientes": not parecer.faltando,
            "sem_conflito": not fatos.conflitos,
            "causa_confirmada": fatos.causa_confirmada or not parecer.depende_de_causa,
        }
        confianca = round(sum(PESOS_VERIFICACAO[k] for k, ok in checks.items() if ok), 2)

        motivos = [_MOTIVOS[k] for k, ok in checks.items() if not ok]
        motivos += [f"faltando: {x}" for x in parecer.faltando]
        motivos += list(fatos.conflitos)

        if not all(checks[k] for k in VERIFICACOES_ELIMINATORIAS):
            confianca = min(confianca, round(self.limiar - 0.01, 2))  # nota nunca contradiz o bloqueio
        aprovado = confianca >= self.limiar
        if self.juiz and aprovado:
            ok, motivo = self.juiz.avaliar(pergunta, parecer, evidencias)
            checks["juiz_modelo"] = ok
            if not ok:
                aprovado = False
                motivos.append(f"segunda avaliação do modelo vetou: {motivo}")
        return Verificacao(confianca, checks, motivos, aprovado)
