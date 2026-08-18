from pydantic import BaseModel

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

class CensorRequest(BaseModel):
    text: str

class CensorResponse(BaseModel):
    text: str
    was_censored: bool
