from agente.models import Decisao, Fatos, Parecer, Resultado, Trecho
from agente.verification.verificador import Verificador


def _res(fonte, score=0.5):
    return Resultado(Trecho(0, "reembolso", "p", "r", fonte), score)


def _parecer(**kw):
    base = dict(decisao=Decisao.ELEGIVEL, motivo="m", fontes_necessarias=["Política 3.2"])
    return Parecer(**{**base, **kw})


def test_aprova_quando_tudo_confere():
    v = Verificador().verificar("q", _parecer(), Fatos(), [_res("Política 3.2")])
    assert v.aprovado and v.confianca == 1.0


def test_fonte_necessaria_nao_recuperada_bloqueia():
    v = Verificador().verificar("q", _parecer(), Fatos(), [])
    assert not v.aprovado and not v.checks["fundamentada"] and v.confianca < 0.70


def test_fonte_nao_oficial_bloqueia():
    v = Verificador().verificar("q", _parecer(fontes_necessarias=["Blog X"]), Fatos(), [_res("Blog X")])
    assert not v.aprovado and not v.checks["fontes_oficiais"]


def test_conflito_bloqueia_mesmo_com_nota_alta():
    f = Fatos(conflitos=["x"])
    v = Verificador().verificar("q", _parecer(), f, [_res("Política 3.2")])
    assert not v.aprovado and v.confianca <= 0.69


def test_causa_nao_confirmada_reduz_nota_mas_nao_bloqueia():
    v = Verificador().verificar("q", _parecer(depende_de_causa=True), Fatos(), [_res("Política 3.2")])
    assert v.aprovado and v.confianca == 0.90


def test_juiz_pode_vetar():
    class JuizVeta:
        def avaliar(self, *_):
            return False, "inconsistente"
    v = Verificador(juiz=JuizVeta()).verificar("q", _parecer(), Fatos(), [_res("Política 3.2")])
    assert not v.aprovado and "inconsistente" in v.motivos[-1]
