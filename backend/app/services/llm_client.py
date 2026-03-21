import httpx

import json

from typing import Optional

from app.core.config import settings


class OllamaClient:
    """
    Client to work with local Ollama model.
    """

    def __init__(self):
        self.host = settings.OLLAMA_HOST
        self.model = settings.OLLAMA_MODEL
        self.timeout = 60.0

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.1,
    ) -> Optional[str]:
        """
        Generate text from model.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.host}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "num_predict": max_tokens,
                            "temperature": temperature,
                        },
                    },
                )
                response.raise_for_status()
                return response.json().get("response", "")
            except Exception as e:
                print(f"Ollama error: {e}")
                return None

    async def extract_questions(self, text: str) -> list[str]:
        """
        Get questions from text (vacancy, post).
        """
        prompt = f"""
        Ты — ассистент для подготовки к собеседованиям по Python Backend.
        Извлеки из текста ниже ТОЛЬКО технические вопросы в формате JSON-списка.
        Игнорируй описания, требования, бонусы.

        Текст:
        {text}

        Ответь ТОЛЬКО в формате:
        ["Вопрос 1?", "Вопрос 2?", ...]
        """
        response = await self.generate(prompt, max_tokens=512)

        try:
            start = response.find("[")
            end = response.rfind("]") + 1
            if start >= 0 and end > start:
                questions = json.loads(response[start:end])
                return questions if isinstance(questions, list) else []
            return []
        except json.JSONDecodeError:
            print(f"Failed to parse JSON from: {response[:100]}")
            return []

    async def classify_question(self, question: str, categories: list[str]) -> str:
        """
        Question classification from DB categories.
        """
        prompt = f"""
        Ты — классификатор вопросов для собеседований Python Backend.

        Доступные категории: {", ".join(categories)}

        Определи, к какой ОДНОЙ категории относится вопрос.
        Если не подходит ни к одной — верни "python".

        Вопрос: {question}

        Ответь ТОЛЬКО slug категории (одним словом, без кавычек).
        Пример: redis
        """

        response = await self.generate(prompt, max_tokens=20)
        slug = response.strip().lower()
        return slug if slug in categories else "python"
