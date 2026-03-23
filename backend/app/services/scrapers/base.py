from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.source import Source


@dataclass
class ScrapedContent:
    """
    Content from source.
    """

    title: str
    text: str
    url: str
    published_at: Optional[datetime] = None
    author: Optional[str] = None


class BaseScraper(ABC):
    """
    Base class for scrapers.
    """

    def __init__(self, session: AsyncSession, source: Source):
        self.db = session
        self.source = source

    @abstractmethod
    async def fetch(self) -> list[ScrapedContent]:
        """
        Get content from source.
        """
        pass

    @abstractmethod
    async def get_already_processed(self) -> set[str]:
        """
        Get all procesed URL/ID.
        """
        pass

    async def update_source_state(
        self,
        processed_items: set[str],
        questions_count: int,
    ) -> None:
        """
        Update source status after proccesing.
        """
        from app.services.model_loader.source_loader import SourceService

        source_service = SourceService(self.db)
        config_update = {
            "processed_urls": list(
                set(self.source.config.get("processed_urls", [])) | processed_items
            )
        }
        await source_service.update_scraped_state(
            source_id=self.source.id,
            config=config_update,
        )
        self.source.total_scraped += len(processed_items)
        self.source.total_questions_extracted += questions_count
