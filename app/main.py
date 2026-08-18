"""FastAPI application assembly."""

from contextlib import asynccontextmanager

from better_profanity import profanity
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import create_tables, dispose_database
from app.features.writing.router import router as writing_router
from app.features.writing.seed import seed_database


@asynccontextmanager
async def lifespan(_app: FastAPI):
    print("✦  Starting WritingsReader API…")
    await create_tables()
    await seed_database()
    profanity.load_censor_words()
    print("   ↳ Profanity filter loaded.")

    try:
        yield
    finally:
        await dispose_database()


settings = get_settings()
app = FastAPI(title="WritingsReader API", version="0.3.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(writing_router)
