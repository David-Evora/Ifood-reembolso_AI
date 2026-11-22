import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "gerar_env.py"
SISTEMA = {"AGENTE_API_KEY": 32, "N8N_ENCRYPTION_KEY": 32, "WEBHOOK_TOKEN": 16, "UI_SENHA": 12}  # tamanhos mínimos


def rodar(saida, *extra):
    return subprocess.run([sys.executable, str(SCRIPT), "--saida", str(saida), *extra], capture_output=True, text=True)


def ler(caminho):
    return dict(l.split("=", 1) for l in caminho.read_text(encoding="utf-8").splitlines() if "=" in l and not l.startswith("#"))


def test_gera_os_segredos_do_sistema_com_tamanho_suficiente(tmp_path):
    saida = tmp_path / ".env"
    r = rodar(saida)
    assert r.returncode == 0
    env = ler(saida)
    for chave, minimo in SISTEMA.items():
        assert len(env[chave]) >= minimo, chave
    assert len({env[c] for c in SISTEMA}) == len(SISTEMA)  # todos diferentes
    assert not any(env[c] in r.stdout for c in SISTEMA)  # não imprime os valores


def test_nao_preenche_nada_do_llm(tmp_path):
    saida = tmp_path / ".env"
    rodar(saida)
    env = ler(saida)
    for chave in ("LLM_PROVEDOR", "LLM_API_KEY", "LLM_MODELO", "LLM_URL_BASE"):
        assert env[chave] == "", chave


def test_preserva_o_restante_do_exemplo(tmp_path):
    saida = tmp_path / ".env"
    rodar(saida)
    assert ler(saida)["USUARIOS_PERMITIDOS"] == "foodlover@exemplo.com"


def test_nao_sobrescreve_sem_force(tmp_path):
    saida = tmp_path / ".env"
    saida.write_text("AGENTE_API_KEY=meu-valor\n", encoding="utf-8")
    r = rodar(saida)
    assert r.returncode == 1 and saida.read_text(encoding="utf-8") == "AGENTE_API_KEY=meu-valor\n"
    assert rodar(saida, "--force").returncode == 0 and len(ler(saida)["AGENTE_API_KEY"]) >= 32


@pytest.mark.skipif(os.name == "nt", reason="chmod não se aplica no Windows")
def test_arquivo_so_o_dono_le(tmp_path):
    saida = tmp_path / ".env"
    rodar(saida)
    assert oct(saida.stat().st_mode & 0o777) == "0o600"
