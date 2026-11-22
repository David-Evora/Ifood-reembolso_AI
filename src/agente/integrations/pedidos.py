"""Integração com a API interna de pedidos ('Integração API' na base).

`MockPedidosClient` lê data/pedidos_mock.json (dados fictícios). Para produção, implemente
`PedidosClient.obter` chamando a API real; o resto do agente não muda.
"""
import json
from pathlib import Path
from typing import Protocol

from ..models import Causa, Etapa, Fatos

_ETAPA_POR_STATUS = {
    "em_preparo": Etapa.EM_PREPARO,
    "saiu_para_entrega": Etapa.SAIU_PARA_ENTREGA,
    "entregue": Etapa.ENTREGUE,
}


class PedidosClient(Protocol):
    def obter(self, pedido_id: str) -> dict | None: ...


class MockPedidosClient:
    def __init__(self, caminho: Path) -> None:
        self._pedidos: dict[str, dict] = json.loads(caminho.read_text(encoding="utf-8"))

    def obter(self, pedido_id: str) -> dict | None:
        return self._pedidos.get(pedido_id)


def aplicar_pedido(f: Fatos, pedido_id: str, pedido: dict | None) -> None:
    """Enriquece os fatos com o que a API sabe e registra divergências como conflitos."""
    if pedido is None:
        f.conflitos.append(f"pedido {pedido_id} não encontrado na API")
        return

    status = pedido.get("status")
    etapa_api = _ETAPA_POR_STATUS.get(status)
    if etapa_api and f.etapa and f.etapa is not etapa_api:
        f.conflitos.append(f"a descrição diz '{f.etapa.value}', mas a API mostra '{status}'")
    f.etapa = etapa_api or f.etapa

    pagamento = (pedido.get("pagamento") or {}).get("status")
    if status == "cancelado" and pagamento == "capturado":
        f.cobrado_apos_cancelamento = True
    if pagamento == "estornado" and status != "cancelado":
        f.conflitos.append("o pagamento consta estornado, mas o pedido não consta cancelado")

    causa_api = pedido.get("causa_falha")
    if causa_api:
        causa = Causa(causa_api)
        if f.causas and causa not in f.causas:
            f.conflitos.append(
                f"a descrição aponta {sorted(c.value for c in f.causas)}, mas a API registra '{causa.value}'"
            )
        f.causas.add(causa)
        f.causa_confirmada = len(f.causas) == 1
