from datetime import datetime

from sqlalchemy import (
    String,
    Integer,
    DateTime,
    ForeignKey,
    Text,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pgvector.sqlalchemy import Vector

from typing import TYPE_CHECKING

from app.core.database import Base


if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.source import Source


class Question(Base):
    """
    Interview question.
    """

    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    text_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
    )

    embedding: Mapped[list[float]] = mapped_column(
        Vector(384),
        nullable=True,
    )

    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )

    category: Mapped["Category | None"] = relationship(
        "Category",
        back_populates="questions",
    )

    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("sources.id", ondelete="SET NULL"),
        nullable=True,
    )

    source: Mapped["Source | None"] = relationship(
        "Source",
        back_populates="questions",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    __table_args__ = (
        Index("index_questions_text_hash", "text_hash"),
        Index("index_questions_category", "category_id"),
        Index("index_questions_source", "source_id"),
        Index("index_questions_created", "created_at"),
    )

    def __repr__(self) -> str:
        return f"Question(id={self.id}, text='{self.text[:50]}...')"
