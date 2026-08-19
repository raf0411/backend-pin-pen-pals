"""HTTP routes for the writing feature."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_device_id, get_session
from app.features.writing import service
from app.features.writing.schemas import (
    CensorRequest,
    CensorResponse,
    CreateWritingRequest,
    ErrorResponse,
    WritingDetailResponse,
    WritingPreviewResponse,
)

router = APIRouter(prefix="/api", tags=["Writings"])
DeviceId = Annotated[str, Depends(get_device_id)]
Session = Annotated[AsyncSession, Depends(get_session)]
WritingId = Annotated[str, Path(min_length=1, max_length=64)]

_ERROR_RESPONSES = {
    400: {"model": ErrorResponse, "description": "Invalid X-Device-ID"},
    422: {"model": ErrorResponse, "description": "Request validation failed"},
    500: {"model": ErrorResponse, "description": "Writing persistence failed"},
}


@router.post(
    "/writings",
    response_model=WritingDetailResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        200: {
            "model": WritingDetailResponse,
            "description": "An identical publish request already succeeded",
        },
        409: {
            "model": ErrorResponse,
            "description": "The client ID is already used by different content",
        },
        **_ERROR_RESPONSES,
    },
)
async def create_writing(
    body: CreateWritingRequest,
    device_id: DeviceId,
    session: Session,
    response: Response,
):
    try:
        writing, created = await service.publish_writing(session, body, device_id)
    except service.WritingConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "client_writing_id already exists for this device with different "
                "content"
            ),
        ) from error
    except service.WritingPersistenceError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to publish writing",
        ) from error

    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return writing


@router.get(
    "/writings",
    response_model=list[WritingPreviewResponse],
    responses=_ERROR_RESPONSES,
)
async def list_writings(device_id: DeviceId, session: Session):
    del device_id
    try:
        return await service.list_writings(session)
    except service.WritingPersistenceError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to read writings",
        ) from error


@router.get(
    "/writings/{writing_id}",
    response_model=WritingDetailResponse,
    responses={404: {"model": ErrorResponse}, **_ERROR_RESPONSES},
)
async def get_writing(writing_id: WritingId, device_id: DeviceId, session: Session):
    del device_id
    try:
        return await service.get_writing(session, writing_id)
    except service.WritingNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Writing '{error.writing_id}' not found",
        ) from error
    except service.WritingPersistenceError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to read writing",
        ) from error


@router.post("/censor", response_model=CensorResponse)
async def censor_text(body: CensorRequest):
    return service.censor_text(body.text)
