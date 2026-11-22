"""Normalização de texto compartilhada pela busca (RAG) e pelo classificador de fatos."""
import re
import unicodedata

STOPWORDS = {
    "a", "o", "as", "os", "de", "da", "do", "das", "dos", "e", "em", "no", "na", "nos", "nas",
    "um", "uma", "para", "pra", "por", "com", "que", "se", "ao", "aos", "ou", "mas", "ja",
    "foi", "sao", "ser", "qual", "quais", "quando", "como", "ainda", "tem",
}


def normalizar(texto: str) -> str:
    """Minúsculas e sem acentos: 'Política' vira 'politica'."""
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()


def tokens(texto: str) -> list[str]:
    # shortcut: stemming por prefixo de 6 letras ("entregador", "entregue" -> "entreg");
    # trocar por um stemmer real (ou embeddings densos) se a base crescer.
    return [t[:6] for t in re.findall(r"[a-z0-9]+", normalizar(texto)) if t not in STOPWORDS]
