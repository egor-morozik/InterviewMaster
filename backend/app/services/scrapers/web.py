import re
import httpx
from bs4 import BeautifulSoup, Comment
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.source import Source
from app.services.scrapers.base import BaseScraper, ScrapedContent


class WebScraper(BaseScraper):
    """
    Unicersal web scraper.
    """

    def __init__(
        self,
        session: AsyncSession,
        source: Source,
        timeout: int = 30,
        min_content_length: int = 200,
    ):
        super().__init__(session, source)
        self.timeout = timeout
        self.min_content_length = min_content_length
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    async def fetch(self) -> list[ScrapedContent]:
        """
        Get data from source.
        """
        url = self.source.url
        async with httpx.AsyncClient(
            headers=self.headers,
            timeout=self.timeout,
            follow_redirects=True,
        ) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                content = self._extract_main_content(response.text, url)
                if content and len(content) >= self.min_content_length:
                    return [
                        ScrapedContent(
                            title=self._extract_title(response.text, url),
                            text=content,
                            url=url,
                        )
                    ]
            except httpx.HTTPError as e:
                print(f"Error fetching {url}: {e}")
        return []

    def _extract_title(self, html: str, fallback: str) -> str:
        """
        Get page headers.
        """
        soup = BeautifulSoup(html, "html.parser")
        for selector in [
            "h1",
            "title",
            "meta[property='og:title']",
            "meta[name='title']",
        ]:
            elem = soup.select_one(selector)
            if elem:
                text = (
                    elem.get("content")
                    if elem.name == "meta"
                    else elem.get_text(strip=True)
                )
                if text:
                    return text
        return fallback

    def _extract_main_content(self, html: str, url: str) -> str:
        """
        Get main text from HTML.
        """
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(
            [
                "script",
                "style",
                "iframe",
                "noscript",
                "svg",
                "nav",
                "footer",
                "header",
                "aside",
                "form",
            ]
        ):
            tag.decompose()
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        spam_patterns = ["ad", "banner", "promo", "widget", "sidebar", "cookie"]
        for tag in soup.find_all(
            class_=lambda c: c and any(p in str(c).lower() for p in spam_patterns)
        ):
            tag.decompose()
        for tag in soup.find_all(
            id=lambda i: i and any(p in str(i).lower() for p in spam_patterns)
        ):
            tag.decompose()

        for main_selector in [
            "article",
            "main",
            "[role='main']",
            ".content",
            ".post",
            ".entry",
        ]:
            candidate = soup.select_one(main_selector)
            if candidate:
                text = self._clean_text(candidate)
                if len(text) >= self.min_content_length:
                    return text

        body = soup.find("body")
        if body:
            text = self._clean_text(body)
            if len(text) >= self.min_content_length:
                return text
        return ""

    def _clean_text(self, element) -> str:
        """
        Clean element and return text.
        """
        for tag in element.find_all(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = element.get_text(separator="\n", strip=True)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()

    async def get_already_processed(self) -> set[str]:
        """
        Get all proccesed URL.
        """
        return set(self.source.config.get("processed_urls", []))
