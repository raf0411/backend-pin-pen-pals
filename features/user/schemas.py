from pydantic import BaseModel

class PreferenceRequest(BaseModel):
    is_adult: bool

class PreferenceResponse(BaseModel):
    device_id: str
    is_adult: bool
