"""FastAPI dependencies shared across features."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session


async def get_device_id(
    x_device_id: Annotated[str | None, Header()] = None,
):
    if x_device_id is None or not x_device_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required header: X-Device-ID",
        )

    device_id = x_device_id.strip()
    if len(device_id) > 128:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Device-ID must not exceed 128 characters",
        )

    return device_id


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session() as session:
        yield session
