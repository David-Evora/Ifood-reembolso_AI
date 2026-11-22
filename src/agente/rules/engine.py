"""Motor de regras: transforma fatos em um parecer, aplicando o que a base de conhecimento diz.

Só decide. Não consulta a base nem fala com o usuário. A regra é determinística: o LLM nunca
decide se há reembolso. A verificação (verification/) checa depois se o RAG realmente
recuperou as fontes de que cada regra depende.

A ordem importa: segurança (fraude) primeiro, depois exceções, depois a regra geral.
"""
from ..models import Causa, Decisao, Etapa, Fatos, Parecer

_ELEGIVEL_POR_CAUSA = {
    Causa.RESTAURANTE: ("falha do restaurante gera reembolso total", ["Política 3.2", "Política 2.1"]),
    Causa.APP: ("erro do app gera reembolso total, salvo fraude", ["Política 3.2", "Política 2.1"]),
    Causa.ENTREGADOR: ("falha do entregador (entrega incorreta ou extravio) é elegível a reembolso", ["Política 3.2", "Política 2.2"]),
}


def _fallback(motivo: str, faltando: list[str]) -> Parecer:
    return Parecer(Decisao.FALLBACK, motivo, [], faltando=faltando)


def decidir(f: Fatos) -> Parecer:
    # 1. Segurança
    if f.fraude:
        return Parecer(
            Decisao.ANTIFRAUDE,
            "Há suspeita de fraude no pagamento: a base manda encaminhar para avaliação manual e bloqueio preventivo.",
            ["Fluxo Segurança"],
            ["Não aprovar nem negar o reembolso.", "Encaminhar para avaliação manual e bloqueio preventivo."],
        )
    if f.multiplos_reembolsos:
        return Parecer(
            Decisao.ANTIFRAUDE,
            "Há tentativas de múltiplos reembolsos seguidos: a base manda sinalizar a equipe antifraude.",
            ["Fluxo Segurança"],
            ["Não aprovar o reembolso automaticamente.", "Sinalizar a equipe antifraude."],
        )

    # 2. Exceções e casos financeiros
    if f.nao_autorizou:
        return Parecer(
            Decisao.VALIDACAO_MANUAL,
            "O cliente diz que não autorizou o pedido: a base manda encaminhar para avaliação manual.",
            ["Política 4.4"],
            ["Encaminhar para avaliação manual.", "Abrir ticket interno se necessário."],
        )
    if f.consta_entregue_nao_chegou:
        return Parecer(
            Decisao.VALIDACAO_MANUAL,
            "O pedido consta como entregue, mas o cliente diz que não chegou: exige validação manual; o reembolso só é decidido após a análise.",
            ["Fluxo de Entrega"],
            ["Fazer a validação manual da entrega.", "Reembolso possível após análise."],
        )
    if f.cobranca_duplicada:
        return Parecer(
            Decisao.ORIENTACAO,
            "Cobrança em duplicidade não é esperada: a base manda abrir ticket para validação financeira.",
            ["Fluxo Financeiro"],
            ["Abrir ticket para validação financeira."],
        )
    if f.cobrado_apos_cancelamento:
        return Parecer(
            Decisao.ORIENTACAO,
            "Cobrança após cancelamento: é preciso validar o status do estorno antes de qualquer outra ação.",
            ["Fluxo Financeiro"],
            ["Validar o status do estorno.", "Em alguns meios de pagamento a devolução leva até 14 dias.", "Se persistir ou houver suspeita de erro, abrir ticket."],
        )

    # 3. Falta de item: caso do restaurante, não depende de confirmar a causa
    if f.falta_item:
        return Parecer(
            Decisao.ELEGIVEL,
            "Falta de item ou ingrediente: cancelamento com reembolso automático, salvo exceções operacionais específicas.",
            ["Política 2.3"],
            ["Prosseguir com o reembolso automático.", "Verificar se há exceção operacional específica."],
        )

    # 4. Regra geral por etapa e causa
    causa = f.causa()
    if f.etapa is Etapa.SAIU_PARA_ENTREGA:
        if causa in _ELEGIVEL_POR_CAUSA:
            texto, fontes = _ELEGIVEL_POR_CAUSA[causa]
            return Parecer(
                Decisao.ELEGIVEL,
                f"O pedido já saiu para entrega, mas a causa é {causa.value}: {texto}.",
                fontes, ["Prosseguir com o reembolso conforme a política."],
                depende_de_causa=True,
            )
        if causa is Causa.CLIENTE:
            return Parecer(
                Decisao.PODE_NAO_ELEGIVEL,
                "Desistência do cliente após a saída para entrega: pode não haver reembolso. Não prometer o reembolso.",
                ["Política 3.2", "Política 4.1"],
                ["Não confirmar reembolso ao cliente.", "Se o cliente contestar (falha da operação, não autorização), encaminhar para avaliação manual."],
                depende_de_causa=True,
            )
        return _fallback(
            "O pedido já saiu para entrega, mas a causa não foi identificada. A elegibilidade depende de quem errou, e a causa não está clara.",
            ["causa do problema (erro do restaurante, erro do app, falha do entregador ou desistência do cliente)"],
        )

    if f.etapa is Etapa.ANTES_DO_PREPARO:
        return Parecer(
            Decisao.ELEGIVEL,
            "Cancelamento antes da preparação: o estorno é automático.",
            ["Política 3.5"],
            ["Prosseguir com o estorno automático."],
        )

    if causa in _ELEGIVEL_POR_CAUSA:
        texto, fontes = _ELEGIVEL_POR_CAUSA[causa]
        return Parecer(
            Decisao.ELEGIVEL, f"{texto[0].upper()}{texto[1:]}.", [fontes[1]],
            ["Prosseguir com o reembolso conforme a política."], depende_de_causa=True,
        )

    return _fallback(
        "A base de conhecimento não cobre este caso com clareza.",
        ["etapa do pedido e causa do problema"],
    )
