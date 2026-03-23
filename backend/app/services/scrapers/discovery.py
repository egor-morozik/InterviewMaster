import httpx

import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.llm_client import OllamaClient


class SourceDiscoveryService:
    """Service to discover sources with interview questions."""

    SEARCH_TEMPLATES = [
        "python backend interview questions {category}",
        "python interview prep {category}",
        "backend developer interview {category}",
        "programming interview questions {category}",
    ]

    EXCLUDE_PATTERNS = [
        r"job",
        r"vacancy",
        r"salary",
        r"hire",
        r"apply",
        r"buy",
        r"course",
        r"paid",
        r"promo",
        r"advert",
    ]

    def __init__(self, session: AsyncSession):
        """
        Init discovery service.
        """
        self.db = session
        self.llm = OllamaClient()
        self.timeout = 30

    async def discover_from_search(
        self,
        categories: list[str],
        max_results: int = 50,
    ) -> list[dict]:
        """
        Discover potential sources via search queries.
        """
        results = []
        seen_urls = set()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for category in categories:
                queries = [t.format(category=category) for t in self.SEARCH_TEMPLATES]

                for query in queries:
                    search_url = f"https://duckduckgo.com/html?q={httpx.URL(query).quote()}&kl=en-us"

                    try:
                        response = await client.get(
                            search_url, headers={"User-Agent": "Mozilla/5.0"}
                        )
                        if response.status_code != 200:
                            continue

                        urls = self._parse_search_results(response.text)

                        for url_data in urls:
                            url = url_data["url"]
                            if url in seen_urls:
                                continue
                            if not self._is_valid_candidate(
                                url, url_data.get("snippet", "")
                            ):
                                continue

                            seen_urls.add(url)
                            results.append(url_data)

                            if len(results) >= max_results:
                                return results

                    except httpx.HTTPError:
                        continue

        return results

    def _parse_search_results(self, html: str) -> list[dict]:
        """
        Parse search engine HTML results.
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        results = []

        for result in soup.find_all("div", class_="result"):
            link = result.find("a", class_="result__a")
            snippet = result.find("a", class_="result__snippet")

            if link and link.get("href"):
                url = link["href"]
                if url.startswith("/l?kh="):
                    continue

                results.append(
                    {
                        "url": url,
                        "title": link.get_text(strip=True),
                        "snippet": snippet.get_text(strip=True) if snippet else "",
                    }
                )

        return results

    def _is_valid_candidate(self, url: str, snippet: str) -> bool:
        """
        Filter out invalid or irrelevant candidates.
        """
        text = f"{url} {snippet}".lower()
        if any(re.search(p, text, re.I) for p in self.EXCLUDE_PATTERNS):
            return False

        if not url.startswith(("http://", "https://")):
            return False
        if any(ext in url for ext in [".pdf", ".jpg", ".png", ".zip", ".exe"]):
            return False

        return True

    async def validate_with_llm(self, url: str, snippet: str) -> bool:
        """
        Validate candidate via LLM classification.
        """
        prompt = f"""
        You are a classifier for interview question sources.

        Determine if the following page contains technical questions for interview preparation.

        URL: {url}
        Snippet: {snippet}

        Answer ONLY "yes" or "no".
        """
        response = await self.llm.generate(prompt, max_tokens=10)
        return response.strip().lower() == "yes"

    async def discover_and_validate(
        self,
        categories: list[str],
        max_results: int = 20,
    ) -> list[dict]:
        """
        Run full discovery pipeline: search + validate.
        """
        candidates = await self.discover_from_search(
            categories, max_results=max_results * 3
        )
        validated = []

        for candidate in candidates:
            is_valid = await self.validate_with_llm(
                candidate["url"], candidate.get("snippet", "")
            )
            if is_valid:
                validated.append(
                    {
                        **candidate,
                        "validated": True,
                    }
                )
                if len(validated) >= max_results:
                    break

        return validated
