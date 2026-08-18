"""Validated API contracts for the writing feature."""

from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, field_validator

StrippedText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class WritingPreviewResponse(BaseModel):
    id: str
    title: str
    preview_text: str
    author_id: str
    prompt_theme: str
    prompt_emotion: str


class WritingDetailResponse(BaseModel):
    id: str
    title: str
    full_text: str
    author_id: str
    prompt_theme: str
    prompt_emotion: str


class CreateWritingRequest(BaseModel):
    title: Annotated[StrippedText, Field(max_length=256)]
    full_text: Annotated[StrippedText, Field(max_length=50_000)]
    prompt_id: Annotated[StrippedText, Field(max_length=64)]


class CensorRequest(BaseModel):
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
