import re

import string


def get_text_normalize(text: str) -> str:
    """
    Normilize to find duplications.
    """
    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = re.sub(r"\s+", " ", text)
    return text.strip()
