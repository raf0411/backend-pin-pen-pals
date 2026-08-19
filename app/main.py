"""FastAPI application assembly."""

from contextlib import asynccontextmanager

from better_profanity import profanity
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.database import dispose_database
from app.features.writing.router import router as writing_router
from app.features.writing.seed import seed_database


@asynccontextmanager
async def lifespan(_app: FastAPI):
    print("✦  Starting WritingsReader API…")
    await seed_database()
    profanity.load_censor_words()
    print("   ↳ Profanity filter loaded.")

    try:
        yield
    finally:
        await dispose_database()


settings = get_settings()
app = FastAPI(title="WritingsReader API", version="0.4.0", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, error: RequestValidationError):
    missing_device_id = any(
        item["type"] == "missing" and item["loc"] == ("header", "x-device-id")
        for item in error.errors()
    )
    if missing_device_id:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "Missing required header: X-Device-ID"},
        )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=jsonable_encoder(
            {"detail": "Request validation failed", "errors": error.errors()}
        ),
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(writing_router)
