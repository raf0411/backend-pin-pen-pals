"""Database models owned by the writing feature."""

from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
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

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    prompt_id: Mapped[str] = mapped_column(ForeignKey("prompts.id"), nullable=False)
    author_id: Mapped[str] = mapped_column(String(128), nullable=False)
    full_text: Mapped[str] = mapped_column(Text, nullable=False)

    prompt: Mapped[Prompt] = relationship(back_populates="writings")
