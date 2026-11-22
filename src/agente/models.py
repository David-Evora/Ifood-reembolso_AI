"""Tipos compartilhados entre os módulos."""
from dataclasses import dataclass, field
from enum import Enum


class Causa(str, Enum):
    RESTAURANTE = "restaurante"
    APP = "app"
    ENTREGADOR = "entregador"
    CLIENTE = "cliente"


class Etapa(str, Enum):
    ANTES_DO_PREPARO = "antes_do_preparo"
    EM_PREPARO = "em_preparo"
    SAIU_PARA_ENTREGA = "saiu_para_entrega"
    ENTREGUE = "entregue"


class Decisao(str, Enum):
    ELEGIVEL = "ELEGIVEL"
    PODE_NAO_ELEGIVEL = "PODE_NAO_ELEGIVEL"  # a base diz "pode não haver reembolso": nunca prometer
    VALIDACAO_MANUAL = "VALIDACAO_MANUAL"
    ANTIFRAUDE = "ANTIFRAUDE"
    ORIENTACAO = "ORIENTACAO"  # casos financeiros: validar estorno, abrir ticket
    FALLBACK = "FALLBACK"  # sem confiança suficiente para decidir


@dataclass(frozen=True)
class Trecho:
    """Uma linha da base de conhecimento (pergunta e resposta formam um trecho)."""
    id: int
    categoria: str
    pergunta: str
    resposta: str
    fonte: str

    @property
    def texto_indexado(self) -> str:
        # shortcut: pergunta repetida = peso dobrado, para a resposta longa não diluir o casamento
        # com a pergunta; trocar por índice separado da pergunta se a base crescer.
        return f"{self.categoria} {self.pergunta} {self.pergunta} {self.resposta}"


@dataclass
class Resultado:
    trecho: Trecho
    score: float


@dataclass
class Fatos:
    """O que se sabe sobre o caso, vindo do texto da pergunta e da API de pedidos."""
    etapa: Etapa | None = None
    causas: set[Causa] = field(default_factory=set)
    falta_item: bool = False
    nao_autorizou: bool = False
    fraude: bool = False
    multiplos_reembolsos: bool = False
    cobrado_apos_cancelamento: bool = False
    cobranca_duplicada: bool = False
    consta_entregue_nao_chegou: bool = False
    causa_confirmada: bool = False  # True quando a API de pedidos confirma o motivo
    conflitos: list[str] = field(default_factory=list)

    def causa(self) -> Causa | None:
        """A causa só vale se for única; duas causas diferentes significam conflito."""
        return next(iter(self.causas)) if len(self.causas) == 1 else None

    def to_dict(self) -> dict:
        return {
            "etapa": self.etapa.value if self.etapa else None,
            "causas": sorted(c.value for c in self.causas),
            "falta_item": self.falta_item,
            "nao_autorizou": self.nao_autorizou,
            "fraude": self.fraude,
            "multiplos_reembolsos": self.multiplos_reembolsos,
            "cobrado_apos_cancelamento": self.cobrado_apos_cancelamento,
            "cobranca_duplicada": self.cobranca_duplicada,
            "consta_entregue_nao_chegou": self.consta_entregue_nao_chegou,
            "causa_confirmada": self.causa_confirmada,
            "conflitos": list(self.conflitos),
        }


@dataclass
class Parecer:
    """Saída do motor de regras, antes da verificação de confiança."""
    decisao: Decisao
    motivo: str
    fontes_necessarias: list[str]
    passos: list[str] = field(default_factory=list)
    faltando: list[str] = field(default_factory=list)
    depende_de_causa: bool = False


@dataclass
class Verificacao:
    confianca: float
    checks: dict[str, bool]
    motivos: list[str]
    aprovado: bool


@dataclass
class Resposta:
    decisao: Decisao
    resumo: str
    passos: list[str]
    fontes: list[str]
    evidencias: list[dict]
    confianca: float
    precisa_humano: bool
    suporte_url: str | None
    motivos_baixa_confianca: list[str]
    trace: dict
    faltando: list[str] = field(default_factory=list)  # o que perguntar ao atendente para destravar o caso

    def to_dict(self) -> dict:
        return {
            "faltando": self.faltando,
            "decisao": self.decisao.value,
            "resumo": self.resumo,
            "passos": self.passos,
            "fontes": self.fontes,
            "evidencias": self.evidencias,
            "confianca": self.confianca,
            "precisa_humano": self.precisa_humano,
            "suporte_url": self.suporte_url,
            "motivos_baixa_confianca": self.motivos_baixa_confianca,
            "trace": self.trace,
        }
