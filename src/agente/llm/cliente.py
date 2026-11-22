"""Clientes de LLM. Dois formatos cobrem a maioria dos provedores:

  anthropic  API de mensagens da Anthropic (Claude)
  openai     API de chat completions da OpenAI e compatíveis (Azure, Ollama, vLLM... via LLM_URL_BASE)

Só biblioteca padrão. Qualquer falha vira LLMErro, e quem chama decide o que fazer (fallback).
A chave nunca aparece em mensagens de erro, logs nem no trace da resposta.
"""
import json
from typing import Protocol
from urllib import request
from urllib.error import HTTPError, URLError

from .. import config

LIMITE_RESPOSTA = 1_000_000  # bytes lidos do provedor


class LLMErro(Exception):
    pass


class ClienteLLM(Protocol):
    def completar(self, sistema: str, usuario: str) -> str: ...


class _SemRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, *_a, **_k):
        return None  # um redirecionamento levaria o cabeçalho com a chave para outro host


_abrir = request.build_opener(_SemRedirect).open


def _post(url: str, headers: dict, corpo: dict, timeout: float) -> dict:
    req = request.Request(url, data=json.dumps(corpo).encode(), method="POST",
                          headers={"Content-Type": "application/json", **headers})
    try:
        with _abrir(req, timeout=timeout) as r:
            return json.loads(r.read(LIMITE_RESPOSTA))
    except HTTPError as e:
        raise LLMErro(f"o provedor respondeu {e.code}") from None  # sem o corpo: pode ecoar dados
    except (URLError, TimeoutError, ValueError, OSError) as e:
        raise LLMErro(f"falha ao chamar o provedor ({type(e).__name__})") from None


class ClienteAnthropic:
    def __init__(self, chave: str, modelo: str, url_base: str, timeout: float) -> None:
        self._chave, self._modelo, self._url, self._timeout = chave, modelo, url_base.rstrip("/"), timeout

    def completar(self, sistema: str, usuario: str) -> str:
        d = _post(f"{self._url}/v1/messages",
                  {"x-api-key": self._chave, "anthropic-version": "2023-06-01"},
                  {"model": self._modelo, "max_tokens": 500, "system": sistema,
                   "messages": [{"role": "user", "content": usuario}]}, self._timeout)
        try:
            return "".join(b["text"] for b in d["content"] if b.get("type") == "text")
        except (KeyError, TypeError):
            raise LLMErro("resposta do provedor em formato inesperado") from None


class ClienteOpenAI:
    def __init__(self, chave: str, modelo: str, url_base: str, timeout: float) -> None:
        self._chave, self._modelo, self._url, self._timeout = chave, modelo, url_base.rstrip("/"), timeout

    def completar(self, sistema: str, usuario: str) -> str:
        d = _post(f"{self._url}/chat/completions", {"Authorization": f"Bearer {self._chave}"},
                  {"model": self._modelo,
                   "messages": [{"role": "system", "content": sistema}, {"role": "user", "content": usuario}]},
                  self._timeout)
        try:
            return d["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError):
            raise LLMErro("resposta do provedor em formato inesperado") from None


_PROVEDORES = {
    "anthropic": (ClienteAnthropic, "https://api.anthropic.com"),
    "openai": (ClienteOpenAI, "https://api.openai.com/v1"),
}


def criar_cliente() -> ClienteLLM | None:
    """None quando LLM_PROVEDOR está vazio (LLM desligado). Configuração incompleta impede a subida."""
    nome = config.LLM_PROVEDOR.strip().lower()
    if not nome:
        return None
    if nome not in _PROVEDORES:
        raise RuntimeError(f"LLM_PROVEDOR inválido: '{nome}'. Use {' ou '.join(_PROVEDORES)}, ou deixe vazio para desligar.")
    if not config.LLM_API_KEY or not config.LLM_MODELO:
        raise RuntimeError("LLM_PROVEDOR está definido, mas LLM_API_KEY ou LLM_MODELO estão vazios no .env.")
    classe, url_padrao = _PROVEDORES[nome]
    url = config.LLM_URL_BASE or url_padrao
    if not url.startswith(("http://", "https://")):
        raise RuntimeError("LLM_URL_BASE deve começar com http:// ou https://")
    return classe(config.LLM_API_KEY, config.LLM_MODELO, url, config.LLM_TIMEOUT)
