"""Uso: python -m agente.cli "pergunta" [--pedido 1001] [--json]"""
import argparse
import json

from .orchestrator import criar_agente


def main() -> None:
    ap = argparse.ArgumentParser(description="Consulta o agente de reembolsos e cancelamentos")
    ap.add_argument("pergunta")
    ap.add_argument("--pedido", help="id do pedido na API (opcional; também é detectado no texto)")
    ap.add_argument("--json", action="store_true", help="imprime a resposta completa, com trace")
    a = ap.parse_args()

    r = criar_agente().responder(a.pergunta, a.pedido)
    if a.json:
        print(json.dumps(r.to_dict(), ensure_ascii=False, indent=2))
        return
    print(f"[{r.decisao.value}] confiança {r.confianca:.2f}\n{r.resumo}")
    for p in r.passos:
        print(f"  - {p}")
    if r.motivos_baixa_confianca:
        print("Motivos da baixa confiança: " + "; ".join(r.motivos_baixa_confianca))
    if r.suporte_url:
        print(f"Suporte: {r.suporte_url}")


if __name__ == "__main__":
    main()
