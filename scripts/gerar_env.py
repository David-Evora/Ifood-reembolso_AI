"""Cria o .env a partir do .env.example, gerando só os segredos DO SISTEMA que estiverem vazios.

Uso: python scripts/gerar_env.py [--saida CAMINHO] [--force]

- Gera: AGENTE_API_KEY, N8N_ENCRYPTION_KEY, WEBHOOK_TOKEN, UI_SENHA.
- Não toca nas variáveis LLM_* (provedor, chave e modelo): ficam em branco para você preencher.
- Não sobrescreve um .env existente (use --force). Não imprime os valores gerados.
"""
import argparse
import os
import re
import secrets
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
# chave -> bytes aleatórios (o texto gerado é ~1,3x maior); UI_SENHA é digitada no login, então é mais curta
SEGREDOS = {"AGENTE_API_KEY": 32, "N8N_ENCRYPTION_KEY": 32, "WEBHOOK_TOKEN": 32, "UI_SENHA": 18}


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
    for chave, n in SEGREDOS.items():
        texto, achou = re.subn(rf"^{chave}=\s*$", lambda _m, c=chave, n=n: f"{c}={secrets.token_urlsafe(n)}", texto, flags=re.M)
        if achou:
            gerados.append(chave)

    a.saida.write_text(texto, encoding="utf-8")
    try:
        os.chmod(a.saida, 0o600)  # só o dono lê; no Windows o chmod é ignorado
    except OSError:
        pass
    print(f"{a.saida} criado. Segredos gerados: {', '.join(gerados)}.")
    print("Falta você: editar USUARIOS_PERMITIDOS e, se for usar LLM, preencher LLM_PROVEDOR, LLM_API_KEY e LLM_MODELO.")
    print("A senha de login da interface é o valor de UI_SENHA no .env (pode trocar por outra de 12+ caracteres).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
