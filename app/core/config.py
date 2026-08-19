"""Application configuration loaded from environment variables."""

from dataclasses import dataclass
from functools import lru_cache
from os import getenv

_DEFAULT_DATABASE_URL = "postgresql+asyncpg://raffi@localhost/writingsreader"
_DEFAULT_ORIGINS = ("http://localhost:3000", "http://localhost:5173")


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    allowed_origins: tuple[str, ...]


@lru_cache
def get_settings():
    origins_value = getenv("ALLOWED_ORIGINS")
    origins = (
        tuple(origin.strip() for origin in origins_value.split(",") if origin.strip())
        if origins_value is not None
        else _DEFAULT_ORIGINS
    )

    if "*" in origins:
        raise ValueError(
            "ALLOWED_ORIGINS cannot contain '*' when credentialed CORS is enabled"
        )

    return Settings(
        database_url=getenv("DATABASE_URL", _DEFAULT_DATABASE_URL),
        allowed_origins=origins,
    )
