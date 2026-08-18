"""HTTP routes for the writing feature."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_device_id, get_session
from app.features.writing import service
from app.features.writing.schemas import (
    CensorRequest,
    CensorResponse,
    CreateWritingRequest,
    WritingDetailResponse,
    WritingPreviewResponse,
)

router = APIRouter(prefix="/api", tags=["Writings"])
DeviceId = Annotated[str, Depends(get_device_id)]
Session = Annotated[AsyncSession, Depends(get_session)]
WritingId = Annotated[str, Path(min_length=1, max_length=64)]


@router.post(
    "/writings",
    response_model=WritingDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_writing(
    body: CreateWritingRequest,
    device_id: DeviceId,
    session: Session,
):
    try:
        return await service.create_writing(session, body, device_id)
    except service.PromptNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Prompt '{error.prompt_id}' not found",
        ) from error


@router.get("/writings", response_model=list[WritingPreviewResponse])
async def list_writings(device_id: DeviceId, session: Session):
    del device_id
    return await service.list_writings(session)


@router.get("/writings/{writing_id}", response_model=WritingDetailResponse)
async def get_writing(writing_id: WritingId, device_id: DeviceId, session: Session):
    del device_id
    try:
        return await service.get_writing(session, writing_id)
    except service.WritingNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Writing '{error.writing_id}' not found",
        ) from error


@router.post("/censor", response_model=CensorResponse)
async def censor_text(body: CensorRequest):
    return service.censor_text(body.text)
