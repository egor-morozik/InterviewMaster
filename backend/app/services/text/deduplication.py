from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.question import Question
from app.models.category import Category
from backend.app.services.text.embeddings import get_embedding_async
from app.utils.hash import get_text_hash
from app.utils.normalization import normalize_text


class DedupService:
    """
    Service to check questions duplicate at DB.

    2 Level check:
    1. Exact match by hash (fast)
    2. Semantic find by embeddings
    """

    SEMANTIC_THRESHOLD: float = 0.12

    def __init__(self, session: AsyncSession):
        self.db = session

    async def is_duplicate_by_hash(self, text: str) -> bool:
        """
        Fast check by hash.
        """
        normalized = normalize_text(text)
        text_hash = get_text_hash(normalized)

        result = await self.db.execute(
            select(Question.id).filter(Question.text_hash == text_hash)
        )
        return result.scalar_one_or_none() is not None

    async def find_similar(
        self,
        text: str,
        limit: int = 5,
        category_slug: str | None = None,
        threshold: float | None = None,
    ) -> list[tuple[Question, float]]:
        """
        Semantic check via pgvector.
        """
        embedding = await get_embedding_async(text)
        threshold = threshold or self.SEMANTIC_THRESHOLD

        stmt = (
            select(Question, text("(embedding <=> :embedding) AS distance"))
            .filter(
                Question.embedding.is_not(None),
                text("(embedding <=> :embedding) <= :threshold"),
            )
            .order_by(text("distance ASC"))
            .limit(limit)
        )

        if category_slug:
            stmt = stmt.join(Category).filter(Category.slug == category_slug)

        result = await self.db.execute(
            stmt,
            {
                "embedding": embedding,
                "threshold": threshold,
            },
        )

        return [(row[0], float(row[1])) for row in result.all()]

    async def check_duplicate(
        self, text: str
    ) -> tuple[bool, Question | None, float | None]:
        """
        Full check to find duplicates.
        """
        normalized = normalize_text(text)
        text_hash = get_text_hash(normalized)

        if await self.is_duplicate_by_hash(text):
            result = await self.db.execute(
                select(Question).filter(Question.text_hash == text_hash)
            )
            existing = result.scalar_one_or_none()
            return True, existing, 1.0

        similar = await self.find_similar(text, limit=1)

        if similar:
            question, distance = similar[0]
            similarity = 1 - distance
            return True, question, similarity

        return False, None, None
