"""Business logic for the writing feature."""

import uuid
from datetime import UTC, datetime

from better_profanity import profanity
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.writing import repository
from app.features.writing.models import Writing
from app.features.writing.schemas import (
    CensorResponse,
    CreateWritingRequest,
    PromptSnapshot,
    WritingDetailResponse,
    WritingPreviewResponse,
)


class WritingConflictError(Exception):
    pass


class WritingNotFoundError(Exception):
    def __init__(self, writing_id: str):
        self.writing_id = writing_id
        super().__init__(writing_id)


class WritingPersistenceError(Exception):
    pass


def generate_title(full_text: str):
    for line in full_text.splitlines():
        title = line.strip()
        if title:
            return title[:256]
    return "Untitled"


def _preview(text: str, lines: int = 3):
    return "\n".join(text.splitlines()[:lines])


def _as_utc(value: datetime):
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _prompt_snapshot(writing: Writing):
    return PromptSnapshot(
        verb=writing.prompt_verb,
        full_text=writing.prompt_full_text,
        emotions=writing.prompt_emotions,
    )


def _to_detail(writing: Writing):
    return WritingDetailResponse(
        id=writing.id,
        client_writing_id=writing.client_writing_id,
        title=writing.title,
        full_text=writing.full_text,
        author_id=writing.author_id,
        prompt=_prompt_snapshot(writing),
        status="published",
        created_at=_as_utc(writing.created_at),
        published_at=_as_utc(writing.published_at),
    )


def _matches_request(
    writing: Writing,
    body: CreateWritingRequest,
    normalized_title: str,
):
    return (
        writing.title == normalized_title
        and writing.full_text == body.full_text
        and writing.prompt_verb == body.prompt.verb
        and writing.prompt_full_text == body.prompt.full_text
        and writing.prompt_emotions == body.prompt.emotions
    )


async def publish_writing(
    session: AsyncSession,
    body: CreateWritingRequest,
    author_id: str,
):
    title = body.title or generate_title(body.full_text)

    try:
        existing = await repository.get_by_client_id(
            session,
            author_id=author_id,
            client_writing_id=body.client_writing_id,
        )
        if existing is not None:
            if not _matches_request(existing, body, title):
                raise WritingConflictError
            return _to_detail(existing), False

        published_at = datetime.now(UTC)
        writing = Writing(
            id=f"writing-{uuid.uuid4().hex}",
            client_writing_id=body.client_writing_id,
            title=title,
            full_text=body.full_text,
            author_id=author_id,
            prompt_verb=body.prompt.verb,
            prompt_full_text=body.prompt.full_text,
            prompt_emotions=body.prompt.emotions,
            created_at=published_at,
            published_at=published_at,
        )

        try:
            writing = await repository.add_writing(session, writing)
        except repository.DuplicateWritingError:
            existing = await repository.get_by_client_id(
                session,
                author_id=author_id,
                client_writing_id=body.client_writing_id,
            )
            if existing is None:
                raise WritingPersistenceError from None
            if not _matches_request(existing, body, title):
                raise WritingConflictError from None
            return _to_detail(existing), False

        return _to_detail(writing), True
    except (WritingConflictError, WritingPersistenceError):
        raise
    except SQLAlchemyError as error:
        raise WritingPersistenceError from error


async def list_writings(session: AsyncSession):
    try:
        writings = await repository.list_writings(session)
    except SQLAlchemyError as error:
        raise WritingPersistenceError from error

    return [
        WritingPreviewResponse(
            id=writing.id,
            client_writing_id=writing.client_writing_id,
            title=writing.title,
            preview_text=_preview(writing.full_text),
            author_id=writing.author_id,
            prompt=_prompt_snapshot(writing),
            status="published",
            created_at=_as_utc(writing.created_at),
            published_at=_as_utc(writing.published_at),
        )
        for writing in writings
    ]


async def get_writing(session: AsyncSession, writing_id: str):
    try:
        writing = await repository.get_writing(session, writing_id)
    except SQLAlchemyError as error:
        raise WritingPersistenceError from error

    if writing is None:
        raise WritingNotFoundError(writing_id)
    return _to_detail(writing)


def censor_text(text: str):
    was_censored = profanity.contains_profanity(text)
    return CensorResponse(
        text=profanity.censor(text) if was_censored else text,
        was_censored=was_censored,
    )
