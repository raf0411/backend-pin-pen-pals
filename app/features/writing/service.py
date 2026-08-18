"""Business logic for the writing feature."""

import uuid

from better_profanity import profanity
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.writing import repository
from app.features.writing.models import Prompt, Writing
from app.features.writing.schemas import (
    CensorResponse,
    CreateWritingRequest,
    WritingDetailResponse,
    WritingPreviewResponse,
)


class PromptNotFoundError(Exception):
    def __init__(self, prompt_id: str):
        self.prompt_id = prompt_id
        super().__init__(prompt_id)


class WritingNotFoundError(Exception):
    def __init__(self, writing_id: str):
        self.writing_id = writing_id
        super().__init__(writing_id)


def _preview(text: str, lines: int = 3):
    return "\n".join(text.splitlines()[:lines])


def _to_detail(writing: Writing, prompt: Prompt):
    return WritingDetailResponse(
        id=writing.id,
        title=writing.title,
        full_text=writing.full_text,
        author_id=writing.author_id,
        prompt_theme=prompt.theme,
        prompt_emotion=prompt.emotion,
    )


async def create_writing(
    session: AsyncSession,
    body: CreateWritingRequest,
    author_id: str,
):
    prompt = await repository.get_prompt(session, body.prompt_id)
    if prompt is None:
        raise PromptNotFoundError(body.prompt_id)

    writing = await repository.add_writing(
        session,
        writing_id=f"writing-{uuid.uuid4().hex[:8]}",
        title=body.title,
        full_text=body.full_text,
        prompt_id=body.prompt_id,
        author_id=author_id,
    )
    return _to_detail(writing, prompt)


async def list_writings(session: AsyncSession):
    writings = await repository.list_writings(session)
    return [
        WritingPreviewResponse(
            id=writing.id,
            title=writing.title,
            preview_text=_preview(writing.full_text),
            author_id=writing.author_id,
            prompt_theme=writing.prompt.theme,
            prompt_emotion=writing.prompt.emotion,
        )
        for writing in writings
    ]


async def get_writing(session: AsyncSession, writing_id: str):
    writing = await repository.get_writing(session, writing_id)
    if writing is None:
        raise WritingNotFoundError(writing_id)
    return _to_detail(writing, writing.prompt)


def censor_text(text: str):
    was_censored = profanity.contains_profanity(text)
    return CensorResponse(
        text=profanity.censor(text) if was_censored else text,
        was_censored=was_censored,
    )
