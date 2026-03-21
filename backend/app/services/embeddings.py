from sentence_transformers import SentenceTransformer


_model: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    """
    Return model to generate embeddings.
    """
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def get_embedding(text: str) -> list[float]:
    """
    Generate vector from text.
    """
    model = get_embedding_model()
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()
