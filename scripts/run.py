import asyncio

import json

import logging

import signal

import sys

import time

from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from app.core.config import settings
from app.services.scrapers.manager import ScraperManager
from app.services.model_loader.category_loader import CategoryLoader
from app.exporters.obsidian import ObsidianExporter


DISCOVER_INTERVAL = 600
SCRAPE_INTERVAL = 120
MAX_NEW_SOURCES_PER_CYCLE = 5
MAX_CONCURRENT_SCRAPES = 4
REQUEST_DELAY = 1.0
EXPORT_PATH = Path(settings.CONFIG_DIR).parent / "obsidian_output"

shutdown_requested = False


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(Path(__file__).parent / "run.log"),
            logging.StreamHandler(),
        ],
    )


def load_categories() -> list[str]:
    config_path = Path(settings.CONFIG_DIR) / settings.TOPICS_FILE
    with open(config_path, "r", encoding="utf-8") as f:
        return [c["slug"] for c in json.load(f).get("categories", [])]


def handle_shutdown(signum, frame):
    global shutdown_requested
    logging.info("Shutdown requested, finishing current cycle...")
    shutdown_requested = True


async def ensure_categories_loaded(session: AsyncSession):
    loader = CategoryLoader(session)
    count = await loader.load()
    if count > 0:
        logging.info(f"Loaded {count} categories")


async def export_to_obsidian(session: AsyncSession):
    exporter = ObsidianExporter(session, EXPORT_PATH)
    count = await exporter.export_all()
    if count > 0:
        logging.info(f"Exported {count} questions to Obsidian format")


async def scrape_source_with_semaphore(
    session: AsyncSession,
    source_id: int,
    semaphore: asyncio.Semaphore,
) -> tuple[int, int]:
    async with semaphore:
        from app.services.scrapers.manager import ScraperManager
        manager = ScraperManager(session)
        from app.services.model_loader.source_loader import SourceService
        source_service = SourceService(session)
        source = await source_service.get_by_id(source_id)
        if not source:
            return 0, 0
        count = await manager.scrape_source(source)
        return source.id, count


async def run_cycle(session: AsyncSession, categories: list[str]):
    from app.services.scrapers.manager import ScraperManager
    manager = ScraperManager(session)

    logging.info("Discovering new sources...")
    new_sources = await manager.discover_new_sources(
        categories=categories,
        max_new=MAX_NEW_SOURCES_PER_CYCLE,
    )
    if new_sources:
        logging.info(f"Added {len(new_sources)} new sources")

    logging.info("Scraping known sources...")
    from app.services.model_loader.source_loader import SourceService
    source_service = SourceService(session)
    all_sources = await source_service.get_all()
    source_ids = [s.id for s in all_sources]

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_SCRAPES)
    tasks = [
        scrape_source_with_semaphore(session, sid, semaphore)
        for sid in source_ids
    ]
    results = await asyncio.gather(*tasks)

    total = sum(count for _, count in results if count > 0)
    if total > 0:
        logging.info(f"Saved {total} new questions")

    logging.info("Exporting to Obsidian...")
    await export_to_obsidian(session)

    await asyncio.sleep(REQUEST_DELAY)


async def main_loop():
    setup_logging()
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    logging.info("Starting autonomous scraping loop")

    engine = create_async_engine(settings.POSTGRES_URL)
    categories = load_categories()

    EXPORT_PATH.mkdir(parents=True, exist_ok=True)

    async with AsyncSession(engine) as session:
        await ensure_categories_loaded(session)

    last_discover = 0

    try:
        while not shutdown_requested:
            async with AsyncSession(engine) as session:
                now = time.time()

                if now - last_discover >= DISCOVER_INTERVAL:
                    await run_cycle(session, categories)
                    last_discover = now
                else:
                    from app.services.scrapers.manager import ScraperManager
                    manager = ScraperManager(session)
                    
                    from app.services.model_loader.source_loader import SourceService
                    source_service = SourceService(session)
                    all_sources = await source_service.get_all()
                    source_ids = [s.id for s in all_sources]

                    semaphore = asyncio.Semaphore(MAX_CONCURRENT_SCRAPES)
                    tasks = [
                        scrape_source_with_semaphore(session, sid, semaphore)
                        for sid in source_ids
                    ]
                    results = await asyncio.gather(*tasks)

                    total = sum(count for _, count in results if count > 0)
                    if total > 0:
                        logging.info(f"Saved {total} new questions")

                    logging.info("Exporting to Obsidian...")
                    await export_to_obsidian(session)

                    await asyncio.sleep(REQUEST_DELAY)

                elapsed = now - last_discover
                next_discover_in = max(0, DISCOVER_INTERVAL - elapsed)
                logging.info(f"Next discovery in {next_discover_in/60:.1f} min")

            await asyncio.sleep(SCRAPE_INTERVAL)

    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        raise
    finally:
        await engine.dispose()
        logging.info("Loop stopped")


if __name__ == "__main__":
    asyncio.run(main_loop())
