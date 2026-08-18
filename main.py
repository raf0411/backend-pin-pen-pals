"""
WritingsReader — FastAPI Backend (PostgreSQL)
=============================================
Run with:  python main.py
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from better_profanity import profanity

from database import create_tables, seed_db
# from features.user.router import router as user_router
from features.writing.router import router as writing_router

# ──────────────────────────────────────────────
# App lifecycle
# ──────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables and seed data on startup."""
    print("✦  Starting WritingsReader API…")
    await create_tables()
    await seed_db()
    profanity.load_censor_words()
    print("   ↳ Profanity filter loaded.")
    yield


app = FastAPI(title="WritingsReader API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
# Routers
# ──────────────────────────────────────────────

# app.include_router(user_router)
app.include_router(writing_router)

# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    print("\n✦  WritingsReader API starting on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
