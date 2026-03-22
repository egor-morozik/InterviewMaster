import re

import string


def get_text_normalize(text: str) -> str:
    """
    Нормализует текст для сравнения на дубликаты.

    Что делает:
    • Приводит к нижнему регистру
    • Удаляет пунктуацию
    • Заменяет множественные пробелы на один
    • Trim
    """
    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = re.sub(r"\s+", " ", text)
    return text.strip()
