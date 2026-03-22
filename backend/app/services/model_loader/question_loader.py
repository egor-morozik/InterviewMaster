from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.question import Question
from app.models.category import Category
from backend.app.services.text.deduplication import DedupService
from app.utils.hash import get_text_hash
from app.utils.normalization import normalize_text


class QuestionService:
    """
    Service to work with questions.
    """

    def __init__(self, session: AsyncSession):
        self.db = session
        self.dedup = DedupService(session)

    async def create_question(
        self,
        text: str,
        category_slug: str | None = None,
        source_id: int | None = None,
    ) -> tuple[Question, bool]:
        """
        Add question or return duplicate.
        """
        is_duplicate, existing, _ = await self.dedup.check_duplicate(text)

        if is_duplicate and existing:
            return existing, True

        normalized = normalize_text(text)
        text_hash = get_text_hash(normalized)
        embedding = await self.dedup.get_embedding_async(text)

        category_id = None
        if category_slug:
            result = await self.db.execute(
                select(Category.id).filter(Category.slug == category_slug)
            )
            cat = result.scalar_one_or_none()
            if cat:
                category_id = cat

        question = Question(
            text=text,
            text_hash=text_hash,
            embedding=embedding,
            category_id=category_id,
            source_id=source_id,
        )

        self.db.add(question)
        await self.db.commit()
        await self.db.refresh(question)

        return question, False

    async def search_similar(
        self,
        query: str,
        limit: int = 10,
        category_slug: str | None = None,
        threshold: float = 0.3,
    ) -> list[tuple[Question, float]]:
        """
        Semantic search.
        """
        return await self.dedup.find_similar(
            text=query,
            limit=limit,
            category_slug=category_slug,
            threshold=threshold,
        )

    async def get_by_id(self, question_id: int) -> Question | None:
        """
        Get question by id.
        """
        result = await self.db.execute(
            select(Question).filter(Question.id == question_id)
        )
        return result.scalar_one_or_none()

    async def get_by_category(
        self, category_slug: str, limit: int = 50
    ) -> list[Question]:
        """
        Get questions by category.
        """
        result = await self.db.execute(
            select(Question)
            .join(Category)
            .filter(Category.slug == category_slug)
            .order_by(Question.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_source(self, source_id: int, limit: int = 50) -> list[Question]:
        """
        Get questions by source.
        """
        result = await self.db.execute(
            select(Question)
            .filter(Question.source_id == source_id)
            .order_by(Question.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
