from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.question import Question
from app.models.category import Category
from app.models.source import Source


class ObsidianExporter:
    """
    Export questions to Obsidian-compatible Markdown files.
    """

    def __init__(self, session: AsyncSession, output_dir: Path):
        """
        Init exporter with session and output directory.
        """
        self.db = session
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _slugify(self, text: str) -> str:
        """
        Convert text to safe filename.
        """
        import re

        text = text.lower().strip()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[\s_-]+", "-", text)
        return text[:100]

    def _generate_frontmatter(
        self,
        question: Question,
        category: Category | None,
        source: Source | None,
    ) -> str:
        """
        Generate YAML frontmatter for Obsidian.
        """
        tags = [f"interview", f"python-backend"]
        if category:
            tags.append(category.slug)
        if source:
            tags.append(source.type.value)

        fm = [
            "---",
            f"created: {question.created_at.strftime('%Y-%m-%d')}",
            f"tags: [{', '.join(tags)}]",
        ]
        if category:
            fm.append(f"category: {category.name}")
        if source:
            fm.append(f"source: {source.name}")
            fm.append(f"source_url: {source.url}")
        fm.append("---")
        return "\n".join(fm)

    def _generate_content(
        self,
        question: Question,
        category: Category | None,
        source: Source | None,
    ) -> str:
        """
        Generate full Markdown content.
        """
        frontmatter = self._generate_frontmatter(question, category, source)
        content = [
            frontmatter,
            "",
            f"# {question.text}",
            "",
            "> [!question] Answer",
            "> ",
            "> [Add your answer here]",
            "",
            f"## Metadata",
            f"- **ID**: {question.id}",
            f"- **Added**: {question.created_at.strftime('%Y-%m-%d %H:%M')}",
        ]
        if category:
            content.append(f"- **Category**: [[{category.slug}]]")
        if source:
            content.append(f"- **Source**: [{source.name}]({source.url})")
        return "\n".join(content)

    async def export_question(self, question: Question) -> Path:
        """
        Export single question to Markdown file.
        """
        category = None
        if question.category_id:
            result = await self.db.execute(
                select(Category).filter(Category.id == question.category_id)
            )
            category = result.scalar_one_or_none()

        source = None
        if question.source_id:
            result = await self.db.execute(
                select(Source).filter(Source.id == question.source_id)
            )
            source = result.scalar_one_or_none()

        filename = f"{self._slugify(question.text[:50])}-{question.id}.md"
        filepath = self.output_dir / filename

        content = self._generate_content(question, category, source)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return filepath

    async def export_all(self) -> int:
        """
        Export all questions and return count.
        """
        result = await self.db.execute(
            select(Question).order_by(Question.created_at.desc())
        )
        questions = result.scalars().all()

        exported = 0
        for question in questions:
            await self.export_question(question)
            exported += 1

        return exported
