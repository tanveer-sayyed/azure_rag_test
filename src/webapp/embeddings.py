"""Contextual retrieval: situate each chunk in its document before embedding."""
import os
import ollama
from sentence_transformers import SentenceTransformer

_OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
_CHUNK_SIZE = 300

_CONTEXT_PROMPT = """\
<document>
{document}
</document>
Here is the chunk we want to situate within the whole document:
<chunk>
{chunk}
</chunk>
Please give a short succinct context to situate this chunk within the overall \
document for the purposes of improving search retrieval of the chunk. \
Answer only with the succinct context and nothing else."""

_encoder: SentenceTransformer | None = None


def _get_encoder() -> SentenceTransformer:
    """Return a cached sentence-transformer encoder."""
    global _encoder
    if _encoder is None:
        _encoder = SentenceTransformer(_EMBEDDING_MODEL)
    return _encoder


def split_chunks(text: str, size: int = _CHUNK_SIZE) -> list[str]:
    """Split text into ~size-char chunks on paragraph boundaries."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, current, current_len = [], [], 0
    for para in paragraphs:
        if current and current_len + len(para) > size:
            chunks.append("\n\n".join(current))
            current, current_len = [], 0
        current.append(para)
        current_len += len(para)
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def contextualize_chunk(document: str, chunk: str) -> str:
    """Prepend an Ollama-generated situating context to the chunk."""
    response = ollama.chat(
        model=_OLLAMA_MODEL,
        messages=[{"role": "user", "content": _CONTEXT_PROMPT.format(document=document, chunk=chunk)}],
    )
    context = response.message.content.strip()
    return f"{context}\n\n{chunk}"


def embed(texts: list[str]) -> list[list[float]]:
    """Return sentence-transformer embeddings for a batch of texts."""
    return _get_encoder().encode(texts).tolist()
