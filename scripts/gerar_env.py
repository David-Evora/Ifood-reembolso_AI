"""Cria o .env a partir do .env.example, gerando os segredos que estiverem vazios.

Uso: python scripts/gerar_env.py [--saida CAMINHO] [--force]
Não sobrescreve um .env existente (use --force). Não imprime os valores gerados.
"""
import argparse
import os
import re
import secrets
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SEGREDOS = ("AGENTE_API_KEY", "N8N_ENCRYPTION_KEY", "WEBHOOK_TOKEN")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--saida", type=Path, default=RAIZ / ".env")
    ap.add_argument("--force", action="store_true", help="sobrescreve o .env existente")
    a = ap.parse_args()

    if a.saida.exists() and not a.force:
        print(f"{a.saida} já existe; nada foi alterado (use --force para refazer).", file=sys.stderr)
        return 1

    texto = (RAIZ / ".env.example").read_text(encoding="utf-8")
    gerados = []
    for chave in SEGREDOS:
        texto, n = re.subn(rf"^{chave}=\s*$", lambda _m, c=chave: f"{c}={secrets.token_urlsafe(32)}", texto, flags=re.M)
        if n:
            gerados.append(chave)

    a.saida.write_text(texto, encoding="utf-8")
    try:
        os.chmod(a.saida, 0o600)  # só o dono lê; no Windows o chmod é ignorado
    except OSError:
        pass
    print(f"{a.saida} criado. Segredos gerados: {', '.join(gerados)}.")
    print("Edite USUARIOS_PERMITIDOS com os e-mails que podem usar o agente.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
