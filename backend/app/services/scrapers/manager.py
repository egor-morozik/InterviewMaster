from sqlalchemy.ext.asyncio import AsyncSession

from app.models.source import Source, SourceType
from app.services.scrapers.base import BaseScraper
from app.services.scrapers.web import WebScraper
from app.services.scrapers.discovery import SourceDiscoveryService
from app.services.model_loader.question_loader import QuestionService
from app.services.ai.llm_client import OllamaClient


class ScraperManager:
    """
    Manager for scraping and source discovery.
    """

    def __init__(self, session: AsyncSession):
        """
        Init scraper manager.
        """
        self.db = session
        self.question_service = QuestionService(session)
        self.llm_client = OllamaClient()

    def get_scraper(self, source: Source) -> BaseScraper:
        """
        Return scraper instance for given source type.
        """
        if source.type == SourceType.WEB:
            return WebScraper(self.db, source)
        raise ValueError(f"Unknown source type: {source.type}")

    async def scrape_source(self, source: Source) -> int:
        """
        Scrape single source and return questions count.
        """
        scraper = self.get_scraper(source)
        already_processed = await scraper.get_already_processed()
        contents = await scraper.fetch()

        if not contents:
            return 0

        questions_count = 0
        for content in contents:
            if content.url in already_processed:
                continue

            questions = await self.llm_client.extract_questions(content.text)
            if not questions:
                continue

            for question_text in questions:
                _, is_duplicate = await self.question_service.create_question(
                    text=question_text,
                    source_id=source.id,
                )
                if not is_duplicate:
                    questions_count += 1

            already_processed.add(content.url)

        await scraper.update_source_state(already_processed, questions_count)
        return questions_count

    async def scrape_all(self) -> dict[int, int]:
        """
        Scrape all known sources and return results dict.
        """
        from app.services.model_loader.source_loader import SourceService

        source_service = SourceService(self.db)
        sources = await source_service.get_all()

        results = {}
        for source in sources:
            count = await self.scrape_source(source)
            results[source.id] = count
        return results

    async def discover_new_sources(
        self,
        categories: list[str],
        max_new: int = 10,
    ) -> list[Source]:
        """
        Discover and add new sources via auto-search.
        """
        from app.services.model_loader.source_loader import SourceService

        source_service = SourceService(self.db)
        discovery = SourceDiscoveryService(self.db)

        existing_urls = set(s.url for s in await source_service.get_all())
        candidates = await discovery.discover_and_validate(
            categories=categories,
            max_results=max_new * 2,
        )

        added = []
        for candidate in candidates:
            url = candidate["url"]
            if url in existing_urls:
                continue

            source = await source_service.create_or_get(
                name=candidate.get("title", url),
                url=url,
                source_type=SourceType.WEB,
            )
            existing_urls.add(url)
            added.append(source)

            if len(added) >= max_new:
                break

        return added
