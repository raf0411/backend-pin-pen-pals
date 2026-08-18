from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import DevicePreference
from dependencies import get_device_id, get_session
from features.user.schemas import PreferenceRequest, PreferenceResponse

# router = APIRouter(prefix="/api/preferences", tags=["Preferences"])

# @router.post("", response_model=PreferenceResponse)
# async def set_preference(
#     body: PreferenceRequest,
#     device_id: str = Depends(get_device_id),
#     session: AsyncSession = Depends(get_session),
# ):
#     """Set or update the age preference for a device."""
#     result = await session.execute(
#         select(DevicePreference).where(DevicePreference.device_id == device_id)
#     )
#     existing = result.scalar_one_or_none()

#     if existing:
#         existing.is_adult = body.is_adult
#     else:
#         session.add(DevicePreference(device_id=device_id, is_adult=body.is_adult))

#     await session.commit()
#     return PreferenceResponse(device_id=device_id, is_adult=body.is_adult)
