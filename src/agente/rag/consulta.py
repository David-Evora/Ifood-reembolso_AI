"""Monta a consulta de busca: pergunta original mais os termos da base que cada fato detectado pede.

Sem isso, "o pedido já saiu para entrega" não casaria com a Política 3.2, que fala em
"após saída para entrega" e "após despacho".
"""
from ..models import Causa, Etapa, Fatos

_POR_ETAPA = {
    Etapa.SAIU_PARA_ENTREGA: "reembolso após o pedido sair para entrega cancelamento solicitado após despacho",
    Etapa.ANTES_DO_PREPARO: "estorno automático cancelamento antes da preparação do pedido",
}
_POR_CAUSA = {
    Causa.RESTAURANTE: "erro do restaurante garante reembolso total",
    Causa.APP: "cancelamento por erro do app reembolso total salvo fraude",
    Causa.ENTREGADOR: "falha do entregador entrega incorreta ou extravio reembolso",
    Causa.CLIENTE: "desistência do cliente após saída para entrega pode não haver reembolso",
}
_POR_FLAG = {
    "falta_item": "restaurante não tiver o item pedido cancelamento por falta de ingrediente reembolso automático",
    "nao_autorizou": "cliente afirma que não autorizou avaliação manual ticket interno",
    "fraude": "suspeita de fraude no método de pagamento avaliação manual bloqueio preventivo",
    "multiplos_reembolsos": "tentativa de múltiplos reembolsos seguidos antifraude",
    "cobrado_apos_cancelamento": "cliente foi cobrado após cancelamento validar status do estorno",
    "cobranca_duplicada": "cliente cobrado duas vezes ticket validação financeira",
    "consta_entregue_nao_chegou": "pedido não chegou mas consta como entregue validação manual",
}


def montar_consulta(pergunta: str, fatos: Fatos) -> str:
    partes = [pergunta]
    if fatos.etapa in _POR_ETAPA:
        partes.append(_POR_ETAPA[fatos.etapa])
    partes += [_POR_CAUSA[c] for c in sorted(fatos.causas, key=lambda c: c.value)]
    partes += [texto for flag, texto in _POR_FLAG.items() if getattr(fatos, flag)]
    return " ".join(partes)
