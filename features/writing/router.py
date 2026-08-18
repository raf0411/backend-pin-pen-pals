import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from better_profanity import profanity

from database import Prompt, Writing
from dependencies import get_device_id, get_session
from features.writing.schemas import (
    CensorRequest,
    CensorResponse,
    CreateWritingRequest,
    WritingDetailResponse,
    WritingPreviewResponse,
)

router = APIRouter(prefix="/api", tags=["Writings"])

def _preview(text: str, lines: int = 3) -> str:
    """Return the first *lines* lines of *text*."""
    return "\n".join(text.splitlines()[:lines])

@router.post("/writings", response_model=WritingDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_writing(
    body: CreateWritingRequest,
    device_id: str = Depends(get_device_id),
    session: AsyncSession = Depends(get_session),
):
    """Create a new writing from OCR-scanned text."""
    prompt_result = await session.execute(
        select(Prompt).where(Prompt.id == body.prompt_id)
    )
    prompt = prompt_result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Prompt '{body.prompt_id}' not found",
        )

    # pref_result = await session.execute(
    #     select(DevicePreference).where(DevicePreference.device_id == device_id)
    # )
    # pref = pref_result.scalar_one_or_none()
    # is_adult = pref.is_adult if pref else False
    is_adult = True # Default to true for now since preference is removed

    title_text = body.title
    full_text = body.full_text
    has_profanity = profanity.contains_profanity(title_text) or profanity.contains_profanity(full_text)
    is_mature = False

    if has_profanity:
        if is_adult:
            is_mature = True
        else:
            title_text = profanity.censor(title_text)
            full_text = profanity.censor(full_text)
            is_mature = False

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

@router.get("/writings", response_model=list[WritingPreviewResponse])
async def list_writings(
    device_id: str = Depends(get_device_id),
    session: AsyncSession = Depends(get_session),
):
    """Return all writings with a 3-line preview."""
    # pref_result = await session.execute(
    #     select(DevicePreference).where(DevicePreference.device_id == device_id)
    # )
    # pref = pref_result.scalar_one_or_none()
    # is_adult = pref.is_adult if pref else False
    is_adult = True

    query = select(Writing).options(selectinload(Writing.prompt))
    if not is_adult:
        query = query.where(Writing.is_mature == False)  # noqa: E712
    result = await session.execute(query)
    writings = result.scalars().all()

    # bm_result = await session.execute(
    #     select(Bookmark.writing_id).where(Bookmark.device_id == device_id)
    # )
    # bookmarked_ids = set(bm_result.scalars().all())
    bookmarked_ids = set()

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

@router.get("/writings/{writing_id}", response_model=WritingDetailResponse)
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

    # bm_result = await session.execute(
    #     select(Bookmark)
    #     .where(Bookmark.device_id == device_id, Bookmark.writing_id == writing_id)
    # )
    # is_bookmarked = bm_result.scalar_one_or_none() is not None
    is_bookmarked = False

    return WritingDetailResponse(
        id=w.id,
        title=w.title,
        full_text=w.full_text,
        author_id=w.author_id,
        prompt_theme=w.prompt.theme if w.prompt else "Unknown",
        prompt_emotion=w.prompt.emotion if w.prompt else "unknown",
        is_bookmarked=is_bookmarked,
    )

# @router.get("/bookmarks", response_model=list[WritingPreviewResponse])
# async def list_bookmarks(
#     device_id: str = Depends(get_device_id),
#     session: AsyncSession = Depends(get_session),
# ):
#     """Return all bookmarked writings for the requesting device."""
#     pref_result = await session.execute(
#         select(DevicePreference).where(DevicePreference.device_id == device_id)
#     )
#     pref = pref_result.scalar_one_or_none()
#     is_adult = pref.is_adult if pref else False

#     query = (
#         select(Writing)
#         .join(Bookmark, Bookmark.writing_id == Writing.id)
#         .where(Bookmark.device_id == device_id)
#         .options(selectinload(Writing.prompt))
#     )
#     if not is_adult:
#         query = query.where(Writing.is_mature == False)  # noqa: E712
#     result = await session.execute(query)
#     writings = result.scalars().all()

#     return [
#         WritingPreviewResponse(
#             id=w.id,
#             title=w.title,
#             preview_text=_preview(w.full_text),
#             author_id=w.author_id,
#             prompt_theme=w.prompt.theme if w.prompt else "Unknown",
#             prompt_emotion=w.prompt.emotion if w.prompt else "unknown",
#             is_bookmarked=True,
#         )
#         for w in writings
#     ]

# @router.post("/bookmarks/{writing_id}", response_model=BookmarkToggleResponse)
# async def toggle_bookmark(
#     writing_id: str,
#     device_id: str = Depends(get_device_id),
#     session: AsyncSession = Depends(get_session),
# ):
#     """Toggle the bookmark state for the requesting device."""
#     w_result = await session.execute(
#         select(Writing).where(Writing.id == writing_id)
#     )
#     if not w_result.scalar_one_or_none():
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Writing '{writing_id}' not found",
#         )

#     bm_result = await session.execute(
#         select(Bookmark)
#         .where(Bookmark.device_id == device_id, Bookmark.writing_id == writing_id)
#     )
#     existing = bm_result.scalar_one_or_none()

#     if existing:
#         await session.delete(existing)
#         await session.commit()
#         return BookmarkToggleResponse(writing_id=writing_id, is_bookmarked=False)
#     else:
#         session.add(Bookmark(device_id=device_id, writing_id=writing_id))
#         await session.commit()
#         return BookmarkToggleResponse(writing_id=writing_id, is_bookmarked=True)

@router.post("/censor", response_model=CensorResponse)
async def censor_text(body: CensorRequest):
    """Censor profanity in the given text."""
    has_profanity = profanity.contains_profanity(body.text)
    censored = profanity.censor(body.text) if has_profanity else body.text
    return CensorResponse(text=censored, was_censored=has_profanity)
