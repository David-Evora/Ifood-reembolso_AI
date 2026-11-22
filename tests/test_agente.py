"""Cenários de decisão. O central é o da atividade final: pedido já saiu para entrega."""
import pytest

from agente.models import Decisao


def D(agente, pergunta, pedido=None):
    return agente.responder(pergunta, pedido)


# --- cenário da atividade, por causa (sem API: a causa vem da descrição) ---
@pytest.mark.parametrize("texto,fonte", [
    ("O pedido já saiu para entrega, mas foi erro do restaurante. O cliente quer reembolso.", "Política 2.1"),
    ("O pedido já saiu para entrega e houve erro do app. Cliente pede reembolso.", "Política 2.1"),
    ("O pedido já saiu para entrega e o entregador extraviou. Reembolso?", "Política 2.2"),
])
def test_saiu_para_entrega_com_falha_da_empresa_e_elegivel(agente, texto, fonte):
    r = D(agente, texto)
    assert r.decisao is Decisao.ELEGIVEL
    assert "Política 3.2" in r.fontes and fonte in r.fontes
    assert any("não foi confirmada" in p for p in r.passos)  # causa só da descrição: ressalva


def test_saiu_para_entrega_com_desistencia_nao_promete_reembolso(agente):
    r = D(agente, "O pedido já saiu para entrega e o cliente desistiu. Ainda tem reembolso?")
    assert r.decisao is Decisao.PODE_NAO_ELEGIVEL
    assert "Política 4.1" in r.fontes
    assert any("Não confirmar reembolso" in p for p in r.passos)


def test_saiu_para_entrega_sem_causa_vai_para_fallback_e_pergunta_a_causa(agente):
    r = D(agente, "O cliente quer reembolso, mas o pedido já saiu para entrega. Ainda é permitido?")
    assert r.decisao is Decisao.FALLBACK and r.precisa_humano
    assert r.suporte_url and r.faltando
    assert r.confianca < 0.70


# --- API de pedidos confirma a causa ---
def test_causa_confirmada_pela_api_elimina_a_ressalva(agente):
    r = D(agente, "Reembolso do pedido já despachado", "1001")
    assert r.decisao is Decisao.ELEGIVEL and r.confianca == 1.0
    assert not any("não foi confirmada" in p for p in r.passos)


def test_api_diz_cliente(agente):
    assert D(agente, "Cliente quer reembolso, pedido saiu para entrega", "1002").decisao is Decisao.PODE_NAO_ELEGIVEL


def test_api_sem_causa_registrada_cai_no_fallback(agente):
    assert D(agente, "Cliente quer reembolso, pedido saiu para entrega", "1003").decisao is Decisao.FALLBACK


def test_id_do_pedido_e_detectado_no_texto(agente):
    assert D(agente, "Pedido 1004 saiu para entrega, quer reembolso").decisao is Decisao.ELEGIVEL


# --- conflitos bloqueiam a resposta ---
def test_descricao_contradiz_api_bloqueia(agente):
    r = D(agente, "O cliente desistiu, pedido saiu para entrega", "1001")  # API diz restaurante
    assert r.decisao is Decisao.FALLBACK
    assert any("API registra" in m for m in r.motivos_baixa_confianca)


def test_duas_causas_na_descricao_bloqueia(agente):
    r = D(agente, "Saiu para entrega, erro do restaurante e o cliente desistiu")
    assert r.decisao is Decisao.FALLBACK


def test_pedido_inexistente_bloqueia(agente):
    r = D(agente, "Pedido 9999 saiu para entrega, erro do restaurante")
    assert r.decisao is Decisao.FALLBACK
    assert any("não encontrado" in m for m in r.motivos_baixa_confianca)


def test_status_financeiro_diverge_do_pedido(agente):
    assert D(agente, "Reembolso do pedido 1008", None).decisao is Decisao.FALLBACK


# --- demais casos da base ---
def test_falta_de_ingrediente_e_automatico(agente):
    r = D(agente, "O restaurante cancelou por falta de ingrediente. O reembolso é automático?")
    assert r.decisao is Decisao.ELEGIVEL and r.fontes == ["Política 2.3"]


def test_cobrado_apos_cancelamento_orienta_validar_estorno(agente):
    r = D(agente, "O cliente foi cobrado após o cancelamento. O que fazer?")
    assert r.decisao is Decisao.ORIENTACAO and "Fluxo Financeiro" in r.fontes
    assert any("14 dias" in p for p in r.passos)


def test_cobranca_duplicada_abre_ticket(agente):
    r = D(agente, "O cliente foi cobrado duas vezes pelo mesmo pedido")
    assert r.decisao is Decisao.ORIENTACAO and any("ticket" in p for p in r.passos)


def test_cobranca_apos_cancelamento_detectada_pela_api(agente):
    assert D(agente, "Cliente reclama do pedido 1006").decisao is Decisao.ORIENTACAO


def test_cliente_nao_autorizou_vai_para_manual(agente):
    r = D(agente, "Pedido saiu para entrega, mas o cliente afirma que não autorizou")
    assert r.decisao is Decisao.VALIDACAO_MANUAL and r.precisa_humano and "Política 4.4" in r.fontes


def test_consta_entregue_mas_nao_chegou(agente):
    r = D(agente, "O pedido não chegou, mas consta como entregue")
    assert r.decisao is Decisao.VALIDACAO_MANUAL and "Fluxo de Entrega" in r.fontes


def test_suspeita_de_fraude(agente):
    r = D(agente, "Suspeita de fraude no cartão do pedido, cliente quer reembolso")
    assert r.decisao is Decisao.ANTIFRAUDE and "Fluxo Segurança" in r.fontes


def test_multiplos_reembolsos_sinalizam_antifraude(agente):
    assert D(agente, "O cliente fez vários reembolsos seguidos esta semana").decisao is Decisao.ANTIFRAUDE


def test_fraude_tem_prioridade_sobre_causa_elegivel(agente):
    assert D(agente, "Saiu para entrega, erro do restaurante, mas há suspeita de fraude").decisao is Decisao.ANTIFRAUDE


# --- negações e fora de escopo ---
def test_negacao_nao_foi_erro_do_restaurante(agente):
    assert D(agente, "Saiu para entrega e não foi erro do restaurante").decisao is Decisao.FALLBACK


def test_cliente_nao_desistiu_nao_vira_desistencia(agente):
    assert D(agente, "Saiu para entrega, o cliente não desistiu, quer reembolso").decisao is Decisao.FALLBACK


def test_pergunta_fora_do_escopo_vai_para_fallback(agente):
    assert D(agente, "Qual a previsão do tempo para amanhã em Vitória?").decisao is Decisao.FALLBACK


def test_resposta_sempre_traz_trace_e_fontes_oficiais(agente):
    r = D(agente, "Pedido 1001 já saiu para entrega e o cliente quer reembolso")
    assert r.trace["recuperados"] and r.trace["fatos"]["etapa"] == "saiu_para_entrega"
    assert all(e["fonte"] in r.fontes for e in r.evidencias)
