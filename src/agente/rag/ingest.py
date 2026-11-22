"""Etapa 1 do RAG: leitura da base e divisão em trechos.

Cada linha do CSV já é um par pergunta/resposta completo, então um trecho = uma linha.
Se a base passar a ter documentos longos, o chunking entra aqui sem afetar os outros módulos.
"""
import csv
from pathlib import Path

from ..models import Trecho

COLUNAS = ("categoria", "pergunta", "resposta", "fonte")


def carregar_base(caminho: Path) -> list[Trecho]:
    with open(caminho, encoding="utf-8", newline="") as f:
        leitor = csv.DictReader(f)
        faltando = set(COLUNAS) - set(leitor.fieldnames or [])
        if faltando:
            raise ValueError(f"CSV sem as colunas: {sorted(faltando)}")
        trechos = [
            Trecho(id=i, **{c: (linha[c] or "").strip() for c in COLUNAS})
            for i, linha in enumerate(leitor)
            if (linha["pergunta"] or "").strip() and (linha["resposta"] or "").strip()
        ]
    if not trechos:
        raise ValueError(f"Nenhum trecho válido em {caminho}")
    return trechos
