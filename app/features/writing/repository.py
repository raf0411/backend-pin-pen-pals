"""Persistence operations for writings."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.writing.models import Writing


class DuplicateWritingError(Exception):
    pass


async def add_writing(session: AsyncSession, writing: Writing):
    session.add(writing)
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise DuplicateWritingError from error
    except Exception:
        await session.rollback()
        raise
    return writing


async def get_by_client_id(
    session: AsyncSession,
    *,
    author_id: str,
    client_writing_id: UUID,
):
    result = await session.execute(
        select(Writing).where(
            Writing.author_id == author_id,
            Writing.client_writing_id == client_writing_id,
        )
    )
    return result.scalar_one_or_none()


async def list_writings(session: AsyncSession):
    result = await session.execute(select(Writing))
    return list(result.scalars().all())


async def get_writing(session: AsyncSession, writing_id: str):
    result = await session.execute(select(Writing).where(Writing.id == writing_id))
    return result.scalar_one_or_none()
