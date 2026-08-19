"""Database models owned by the writing feature."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Prompt(Base):
    __tablename__ = "prompts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    emotion: Mapped[str] = mapped_column(String(32), nullable=False)
    theme: Mapped[str] = mapped_column(String(128), nullable=False)

    writings: Mapped[list[Writing]] = relationship(back_populates="prompt")


class Writing(Base):
    __tablename__ = "writings"
    __table_args__ = (
        UniqueConstraint(
            "author_id",
            "client_writing_id",
            name="uq_writings_author_client_id",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_writing_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    prompt_id: Mapped[str | None] = mapped_column(
        ForeignKey("prompts.id"), nullable=True
    )
    prompt_verb: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_full_text: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_emotions: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    author_id: Mapped[str] = mapped_column(String(128), nullable=False)
    full_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    prompt: Mapped[Prompt | None] = relationship(back_populates="writings")
