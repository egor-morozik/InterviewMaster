import hashlib


def get_text_hash(text: str) -> str:
    """
    Generate SHA256 hash from normilize text.
    """
    normalized = text.lower().strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
