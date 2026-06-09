"""Local sentence-transformers embedding wrapper."""

from sentence_transformers import SentenceTransformer


VECTOR_SIZE = 384
_MODEL_NAME = "all-MiniLM-L6-v2"
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(_MODEL_NAME)
    return _model


def embed_text(text: str) -> list[float]:
    """Embed a single query string."""
    return _get_model().encode(text, prompt_name="query").tolist()


def embed_documents(texts: list[str], *, batch_size: int = 256, **_: object) -> list[list[float]]:
    """Embed a list of documents. Returns one 384-dim vector per text."""
    vectors = _get_model().encode(texts, batch_size=batch_size, show_progress_bar=True)
    return [v.tolist() for v in vectors]
