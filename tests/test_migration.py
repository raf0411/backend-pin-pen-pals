from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings


@pytest.mark.asyncio
async def test_migration_backfills_legacy_writings(tmp_path, monkeypatch):
    database_path = tmp_path / "migration.db"
    database_url = f"sqlite+aiosqlite:///{database_path}"
    engine = create_async_engine(database_url)

    async with engine.begin() as connection:
        await connection.run_sync(_create_legacy_schema)
        await connection.execute(
            sa.text(
                "INSERT INTO prompts (id, emotion, theme) "
                "VALUES ('prompt-joy', 'Joy', 'Found a Letter')"
            )
        )
        await connection.execute(
            sa.text(
                "INSERT INTO writings "
                "(id, title, prompt_id, author_id, full_text) VALUES "
                "('writing-legacy', 'Legacy', 'prompt-joy', 'device-1', 'Body'), "
                "('writing-orphan', 'Orphan', 'missing', 'device-1', 'Body')"
            )
        )
    await engine.dispose()

    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = Config(str(Path("alembic.ini").resolve()))
    await asyncio_to_thread(command.upgrade, config, "head")

    sync_engine = sa.create_engine(f"sqlite:///{database_path}")
    with sync_engine.connect() as connection:
        rows = {
            row["id"]: row
            for row in connection.execute(sa.text("SELECT * FROM writings")).mappings()
        }
        legacy = rows["writing-legacy"]
        assert legacy["client_writing_id"]
        assert legacy["prompt_verb"] == "Write"
        assert legacy["prompt_full_text"] == "Found a Letter"
        assert legacy["prompt_emotions"] == '["joy"]'
        assert legacy["created_at"]
        assert legacy["published_at"]
        assert rows["writing-orphan"]["prompt_emotions"] == '["unknown"]'
        constraints = sa.inspect(connection).get_unique_constraints("writings")
        assert any(
            constraint["name"] == "uq_writings_author_client_id"
            for constraint in constraints
        )
    sync_engine.dispose()


async def asyncio_to_thread(function, *args):
    import asyncio

    return await asyncio.to_thread(function, *args)


def _create_legacy_schema(connection):
    metadata = sa.MetaData()
    sa.Table(
        "prompts",
        metadata,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("emotion", sa.String(32), nullable=False),
        sa.Column("theme", sa.String(128), nullable=False),
    )
    sa.Table(
        "writings",
        metadata,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("prompt_id", sa.ForeignKey("prompts.id"), nullable=False),
        sa.Column("author_id", sa.String(128), nullable=False),
        sa.Column("full_text", sa.Text(), nullable=False),
    )
    metadata.create_all(connection)
