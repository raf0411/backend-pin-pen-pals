"""Validated API contracts for the writing feature."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PromptSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verb: str
    full_text: str
    emotions: list[str] = Field(min_length=1)

    @field_validator("verb", "full_text")
    @classmethod
    def normalize_required_text(cls, value: str):
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be blank")
        return normalized

    @field_validator("emotions")
    @classmethod
    def normalize_emotions(cls, values: list[str]):
        normalized: list[str] = []
        seen: set[str] = set()
        for value in values:
            emotion = value.strip().lower()
            if not emotion:
                raise ValueError("emotion values must not be blank")
            if emotion not in seen:
                seen.add(emotion)
                normalized.append(emotion)
        return normalized


class CreateWritingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_writing_id: UUID
    title: str | None = Field(default=None, max_length=256)
    full_text: str = Field(max_length=50_000)
    prompt: PromptSnapshot

    @field_validator("title", mode="before")
    @classmethod
    def normalize_title(cls, value: str | None):
        if value is None or not isinstance(value, str):
            return value
        normalized = value.strip()
        return normalized or None

    @field_validator("full_text")
    @classmethod
    def validate_full_text(cls, value: str):
        if not value.strip():
            raise ValueError("full_text must not be blank")
        return value


class WritingDetailResponse(BaseModel):
    id: str
    client_writing_id: UUID
    title: str
    full_text: str
    author_id: str
    prompt: PromptSnapshot
    status: Literal["published"]
    created_at: datetime
    published_at: datetime


class WritingPreviewResponse(BaseModel):
    id: str
    client_writing_id: UUID
    title: str
    preview_text: str
    author_id: str
    prompt: PromptSnapshot
    status: Literal["published"]
    created_at: datetime
    published_at: datetime


class CensorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(max_length=50_000)

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, value: str):
        if not value.strip():
            raise ValueError("text must not be blank")
        return value


class CensorResponse(BaseModel):
    text: str
    was_censored: bool


class ErrorResponse(BaseModel):
    detail: str
    errors: list[dict[str, Any]] | None = None
