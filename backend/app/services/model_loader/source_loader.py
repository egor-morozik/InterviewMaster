from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.source import Source, SourceType


class SourceService:
    """
    Service for source management.
    """

    def __init__(self, session: AsyncSession):
        """
        Init source service.
        """
        self.db = session

    async def create_or_get(
        self,
        name: str,
        url: str,
        source_type: SourceType = SourceType.WEB,
    ) -> Source:
        """
        Create source or return existing by url.
        """
        result = await self.db.execute(select(Source).filter(Source.url == url))
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        source = Source(name=name, url=url, type=source_type)
        self.db.add(source)
        await self.db.commit()
        await self.db.refresh(source)
        return source

    async def update_scraped_state(
        self,
        source_id: int,
        config: dict | None = None,
    ) -> None:
        """
        Update source state after scraping.
        """
        result = await self.db.execute(select(Source).filter(Source.id == source_id))
        source = result.scalar_one_or_none()
        if source:
            source.last_scraped_at = datetime.utcnow()
            if config:
                current_config = source.config or {}
                current_config.update(config)
                source.config = current_config
            await self.db.commit()

    async def get_by_id(self, source_id: int) -> Source | None:
        """
        Get source by id.
        """
        result = await self.db.execute(select(Source).filter(Source.id == source_id))
        return result.scalar_one_or_none()

    async def get_all(self) -> list[Source]:
        """
        Get all sources.
        """
        result = await self.db.execute(select(Source))
        return result.scalars().all()
