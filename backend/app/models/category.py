from sqlalchemy import String, Text, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from typing import TYPE_CHECKING

from app.core.database import Base


if TYPE_CHECKING:
    from app.models.question import Question


class Category(Base):
    """
    Question category (Python, SQL, Redis...).
    """

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(127),
        nullable=False,
        unique=True,
    )

    slug: Mapped[str] = mapped_column(
        String(63),
        nullable=False,
        unique=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    questions: Mapped[list["Question"]] = relationship(
        "Question",
        back_populates="category",
        cascade="all, delete-orphan",
        lazy="select",
    )

    __table_args__ = (
        Index("index_categories_name", "name"),
        Index("index_categories_slug", "slug"),
    )

    def __repr__(self) -> str:
        return f"Category(id={self.id}, name='{self.name}', slug='{self.slug}')"
