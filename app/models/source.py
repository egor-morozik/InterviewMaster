import enum
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, JSON, Enum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from typing import TYPE_CHECKING

from app.core.database import Base


if TYPE_CHECKING:
    from app.models.question import Question


class SourceType(str, enum.Enum):
    """
    Source types for question collection.
    """
    TELEGRAM = "telegram"
    WEB = "web"
    API = "api"
    MANUAL = "manual"


class Source(Base):
    """
    Source for question collection.
    Хранит состояние скрейпинга для защиты от повторного чтения.
    """
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    url: Mapped[str] = mapped_column(
        String(511),
        nullable=False,
        unique=True,
    )

    type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, name="sourcetype"),
        nullable=False,
        default=SourceType.WEB,
    )

    config: Mapped[dict] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
    )

    last_scraped_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    questions: Mapped[list["Question"]] = relationship(
        "Question",
        back_populates="source",
        cascade="all, delete-orphan",
        lazy="select",
    )

    __table_args__ = (
        Index("index_sources_url", "url"),
        Index("index_sources_type", "type"),
    )

    def __repr__(self) -> str:
        return f"Source(id={self.id}, name='{self.name}', type={self.type.value})"
    