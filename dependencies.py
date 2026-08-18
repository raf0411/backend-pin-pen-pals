from typing import Annotated
from fastapi import Header, HTTPException, status
from database import async_session

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
