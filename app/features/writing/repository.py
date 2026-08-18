"""Persistence operations for writings and prompts."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.features.writing.models import Prompt, Writing


async def get_prompt(session: AsyncSession, prompt_id: str):
    result = await session.execute(select(Prompt).where(Prompt.id == prompt_id))
    return result.scalar_one_or_none()


async def add_writing(
    session: AsyncSession,
    *,
    writing_id: str,
    title: str,
    full_text: str,
    prompt_id: str,
    author_id: str,
):
    writing = Writing(
        id=writing_id,
        title=title,
        full_text=full_text,
        prompt_id=prompt_id,
        author_id=author_id,
    )
    session.add(writing)

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    return writing


async def list_writings(session: AsyncSession):
    result = await session.execute(
        select(Writing).options(selectinload(Writing.prompt))
    )
    return list(result.scalars().all())


async def get_writing(session: AsyncSession, writing_id: str):
    result = await session.execute(
        select(Writing)
        .where(Writing.id == writing_id)
        .options(selectinload(Writing.prompt))
    )
    return result.scalar_one_or_none()
