"""
WritingsReader — FastAPI Backend (PostgreSQL)
=============================================
Run with:  python main.py
"""

from __future__ import annotations

import uuid

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from better_profanity import profanity
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import Bookmark, DevicePreference, Prompt, Writing, async_session, create_tables, seed_db

# ──────────────────────────────────────────────
# App lifecycle
# ──────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables and seed data on startup."""
    print("✦  Starting WritingsReader API…")
    await create_tables()
    await seed_db()
    profanity.load_censor_words()
    print("   ↳ Profanity filter loaded.")
    yield


app = FastAPI(title="WritingsReader API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────
# Dependencies
# ──────────────────────────────────────────────


async def get_device_id(
    x_device_id: Annotated[str | None, Header()] = None,
) -> str:
    """Extract and validate the X-Device-ID header."""
    if not x_device_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required header: X-Device-ID",
        )
    return x_device_id


async def get_session():
    """Yield an async SQLAlchemy session."""
    async with async_session() as session:
        yield session


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _preview(text: str, lines: int = 3) -> str:
    """Return the first *lines* lines of *text*."""
    return "\n".join(text.splitlines()[:lines])


# ──────────────────────────────────────────────
# Response models
# ──────────────────────────────────────────────


class WritingPreviewResponse(BaseModel):
    id: str
    title: str
    preview_text: str
    author_id: str
    prompt_theme: str
    prompt_emotion: str
    is_bookmarked: bool


class WritingDetailResponse(BaseModel):
    id: str
    title: str
    full_text: str
    author_id: str
    prompt_theme: str
    prompt_emotion: str
    is_bookmarked: bool


class BookmarkToggleResponse(BaseModel):
    writing_id: str
    is_bookmarked: bool


class CreateWritingRequest(BaseModel):
    title: str
    full_text: str
    prompt_id: str


class PreferenceRequest(BaseModel):
    is_adult: bool


class PreferenceResponse(BaseModel):
    device_id: str
    is_adult: bool


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────


@app.post("/api/writings", response_model=WritingDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_writing(
    body: CreateWritingRequest,
    device_id: str = Depends(get_device_id),
    session: AsyncSession = Depends(get_session),
):
    """Create a new writing from OCR-scanned text."""
    # Verify the prompt exists.
    prompt_result = await session.execute(
        select(Prompt).where(Prompt.id == body.prompt_id)
    )
    prompt = prompt_result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Prompt '{body.prompt_id}' not found",
        )

    # Check device age preference.
    pref_result = await session.execute(
        select(DevicePreference).where(DevicePreference.device_id == device_id)
    )
    pref = pref_result.scalar_one_or_none()
    is_adult = pref.is_adult if pref else False

    # Profanity handling.
    title_text = body.title
    full_text = body.full_text
    has_profanity = profanity.contains_profanity(title_text) or profanity.contains_profanity(full_text)
    is_mature = False

    if has_profanity:
        if is_adult:
            # 18+ users: allow exact text, mark as mature.
            is_mature = True
        else:
            # Under 18: censor the bad words.
            title_text = profanity.censor(title_text)
            full_text = profanity.censor(full_text)
            is_mature = False  # censored, so it's clean now

    writing = Writing(
        id=f"writing-{uuid.uuid4().hex[:8]}",
        title=title_text,
        full_text=full_text,
        prompt_id=body.prompt_id,
        author_id=device_id,
        is_mature=is_mature,
    )
    session.add(writing)
    await session.commit()

    return WritingDetailResponse(
        id=writing.id,
        title=writing.title,
        full_text=writing.full_text,
        author_id=writing.author_id,
        prompt_theme=prompt.theme,
        prompt_emotion=prompt.emotion,
        is_bookmarked=False,
    )


@app.post("/api/preferences", response_model=PreferenceResponse)
async def set_preference(
    body: PreferenceRequest,
    device_id: str = Depends(get_device_id),
    session: AsyncSession = Depends(get_session),
):
    """Set or update the age preference for a device."""
    result = await session.execute(
        select(DevicePreference).where(DevicePreference.device_id == device_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.is_adult = body.is_adult
    else:
        session.add(DevicePreference(device_id=device_id, is_adult=body.is_adult))

    await session.commit()
    return PreferenceResponse(device_id=device_id, is_adult=body.is_adult)


class CensorRequest(BaseModel):
    text: str


class CensorResponse(BaseModel):
    text: str
    was_censored: bool


@app.post("/api/censor", response_model=CensorResponse)
async def censor_text(body: CensorRequest):
    """Censor profanity in the given text."""
    has_profanity = profanity.contains_profanity(body.text)
    censored = profanity.censor(body.text) if has_profanity else body.text
    return CensorResponse(text=censored, was_censored=has_profanity)

@app.get("/api/writings", response_model=list[WritingPreviewResponse])
async def list_writings(
    device_id: str = Depends(get_device_id),
    session: AsyncSession = Depends(get_session),
):
    """Return all writings with a 3-line preview."""
    # Check if device is adult.
    pref_result = await session.execute(
        select(DevicePreference).where(DevicePreference.device_id == device_id)
    )
    pref = pref_result.scalar_one_or_none()
    is_adult = pref.is_adult if pref else False

    # Fetch writings, filtering mature content for non-adults.
    query = select(Writing).options(selectinload(Writing.prompt))
    if not is_adult:
        query = query.where(Writing.is_mature == False)  # noqa: E712
    result = await session.execute(query)
    writings = result.scalars().all()

    # Fetch this device's bookmarked writing IDs in one query.
    bm_result = await session.execute(
        select(Bookmark.writing_id).where(Bookmark.device_id == device_id)
    )
    bookmarked_ids = set(bm_result.scalars().all())

    return [
        WritingPreviewResponse(
            id=w.id,
            title=w.title,
            preview_text=_preview(w.full_text),
            author_id=w.author_id,
            prompt_theme=w.prompt.theme if w.prompt else "Unknown",
            prompt_emotion=w.prompt.emotion if w.prompt else "unknown",
            is_bookmarked=w.id in bookmarked_ids,
        )
        for w in writings
    ]


@app.get("/api/bookmarks", response_model=list[WritingPreviewResponse])
async def list_bookmarks(
    device_id: str = Depends(get_device_id),
    session: AsyncSession = Depends(get_session),
):
    """Return all bookmarked writings for the requesting device."""
    # Check if device is adult.
    pref_result = await session.execute(
        select(DevicePreference).where(DevicePreference.device_id == device_id)
    )
    pref = pref_result.scalar_one_or_none()
    is_adult = pref.is_adult if pref else False

    # Join bookmarks → writings → prompts for this device.
    query = (
        select(Writing)
        .join(Bookmark, Bookmark.writing_id == Writing.id)
        .where(Bookmark.device_id == device_id)
        .options(selectinload(Writing.prompt))
    )
    if not is_adult:
        query = query.where(Writing.is_mature == False)  # noqa: E712
    result = await session.execute(query)
    writings = result.scalars().all()

    return [
        WritingPreviewResponse(
            id=w.id,
            title=w.title,
            preview_text=_preview(w.full_text),
            author_id=w.author_id,
            prompt_theme=w.prompt.theme if w.prompt else "Unknown",
            prompt_emotion=w.prompt.emotion if w.prompt else "unknown",
            is_bookmarked=True,  # they're all bookmarked by definition
        )
        for w in writings
    ]



@app.get("/api/writings/{writing_id}", response_model=WritingDetailResponse)
async def get_writing(
    writing_id: str,
    device_id: str = Depends(get_device_id),
    session: AsyncSession = Depends(get_session),
):
    """Return the full detail of a single writing."""
    result = await session.execute(
        select(Writing)
        .where(Writing.id == writing_id)
        .options(selectinload(Writing.prompt))
    )
    w = result.scalar_one_or_none()
    if not w:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Writing '{writing_id}' not found",
        )

    # Check bookmark status.
    bm_result = await session.execute(
        select(Bookmark)
        .where(Bookmark.device_id == device_id, Bookmark.writing_id == writing_id)
    )
    is_bookmarked = bm_result.scalar_one_or_none() is not None

    return WritingDetailResponse(
        id=w.id,
        title=w.title,
        full_text=w.full_text,
        author_id=w.author_id,
        prompt_theme=w.prompt.theme if w.prompt else "Unknown",
        prompt_emotion=w.prompt.emotion if w.prompt else "unknown",
        is_bookmarked=is_bookmarked,
    )


@app.post("/api/bookmarks/{writing_id}", response_model=BookmarkToggleResponse)
async def toggle_bookmark(
    writing_id: str,
    device_id: str = Depends(get_device_id),
    session: AsyncSession = Depends(get_session),
):
    """Toggle the bookmark state for the requesting device."""
    # Verify the writing exists.
    w_result = await session.execute(
        select(Writing).where(Writing.id == writing_id)
    )
    if not w_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Writing '{writing_id}' not found",
        )

    # Check if bookmark already exists.
    bm_result = await session.execute(
        select(Bookmark)
        .where(Bookmark.device_id == device_id, Bookmark.writing_id == writing_id)
    )
    existing = bm_result.scalar_one_or_none()

    if existing:
        await session.delete(existing)
        await session.commit()
        return BookmarkToggleResponse(writing_id=writing_id, is_bookmarked=False)
    else:
        session.add(Bookmark(device_id=device_id, writing_id=writing_id))
        await session.commit()
        return BookmarkToggleResponse(writing_id=writing_id, is_bookmarked=True)


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    print("\n✦  WritingsReader API starting on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
