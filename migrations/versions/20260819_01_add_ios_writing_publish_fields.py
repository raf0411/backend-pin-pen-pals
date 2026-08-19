"""Add iOS writing publish fields and idempotency constraint.

Revision ID: 20260819_01
Revises:
Create Date: 2026-08-19
"""

from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid5

import sqlalchemy as sa
from alembic import op

revision = "20260819_01"
down_revision = None
branch_labels = None
depends_on = None


def _create_prompts_table() -> None:
    op.create_table(
        "prompts",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("emotion", sa.String(length=32), nullable=False),
        sa.Column("theme", sa.String(length=128), nullable=False),
    )


def _create_writings_table() -> None:
    op.create_table(
        "writings",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("client_writing_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("prompt_id", sa.String(length=64), nullable=True),
        sa.Column("prompt_verb", sa.Text(), nullable=False),
        sa.Column("prompt_full_text", sa.Text(), nullable=False),
        sa.Column("prompt_emotions", sa.JSON(), nullable=False),
        sa.Column("author_id", sa.String(length=128), nullable=False),
        sa.Column("full_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["prompt_id"], ["prompts.id"]),
        sa.UniqueConstraint(
            "author_id",
            "client_writing_id",
            name="uq_writings_author_client_id",
        ),
    )


def _backfill_writings() -> None:
    connection = op.get_bind()
    prompts = sa.table(
        "prompts",
        sa.column("id", sa.String()),
        sa.column("emotion", sa.String()),
        sa.column("theme", sa.String()),
    )
    writings = sa.table(
        "writings",
        sa.column("id", sa.String()),
        sa.column("author_id", sa.String()),
        sa.column("prompt_id", sa.String()),
        sa.column("client_writing_id", sa.Uuid()),
        sa.column("prompt_verb", sa.Text()),
        sa.column("prompt_full_text", sa.Text()),
        sa.column("prompt_emotions", sa.JSON()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("published_at", sa.DateTime(timezone=True)),
    )

    prompt_rows = connection.execute(
        sa.select(prompts.c.id, prompts.c.emotion, prompts.c.theme)
    ).mappings()
    prompts_by_id = {row["id"]: row for row in prompt_rows}
    published_at = datetime.now(UTC)

    rows = connection.execute(
        sa.select(writings.c.id, writings.c.author_id, writings.c.prompt_id)
    ).mappings()
    for row in rows:
        prompt = prompts_by_id.get(row["prompt_id"])
        prompt_theme = prompt["theme"].strip() if prompt and prompt["theme"] else ""
        prompt_emotion = (
            prompt["emotion"].strip().lower() if prompt and prompt["emotion"] else ""
        )
        connection.execute(
            writings.update()
            .where(writings.c.id == row["id"])
            .values(
                client_writing_id=uuid5(
                    NAMESPACE_URL,
                    f"writingsreader:{row['author_id']}:{row['id']}",
                ),
                prompt_verb="Write",
                prompt_full_text=prompt_theme or "Legacy prompt unavailable",
                prompt_emotions=[prompt_emotion] if prompt_emotion else ["unknown"],
                created_at=published_at,
                published_at=published_at,
            )
        )


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = set(inspector.get_table_names())

    if "prompts" not in tables:
        _create_prompts_table()
    if "writings" not in tables:
        _create_writings_table()
        return

    columns = {column["name"]: column for column in inspector.get_columns("writings")}
    additions = (
        sa.Column("client_writing_id", sa.Uuid(), nullable=True),
        sa.Column("prompt_verb", sa.Text(), nullable=True),
        sa.Column("prompt_full_text", sa.Text(), nullable=True),
        sa.Column("prompt_emotions", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    for column in additions:
        if column.name not in columns:
            op.add_column("writings", column)

    _backfill_writings()

    unique_names = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("writings")
    }
    with op.batch_alter_table("writings") as batch:
        batch.alter_column("client_writing_id", nullable=False)
        batch.alter_column("prompt_verb", nullable=False)
        batch.alter_column("prompt_full_text", nullable=False)
        batch.alter_column("prompt_emotions", nullable=False)
        batch.alter_column("created_at", nullable=False)
        batch.alter_column("published_at", nullable=False)
        if not columns["prompt_id"]["nullable"]:
            batch.alter_column("prompt_id", nullable=True)
        if "uq_writings_author_client_id" not in unique_names:
            batch.create_unique_constraint(
                "uq_writings_author_client_id",
                ["author_id", "client_writing_id"],
            )


def downgrade() -> None:
    connection = op.get_bind()
    writings = sa.table(
        "writings",
        sa.column("prompt_id", sa.String()),
    )
    missing_prompt_count = connection.scalar(
        sa.select(sa.func.count())
        .select_from(writings)
        .where(writings.c.prompt_id.is_(None))
    )
    if missing_prompt_count:
        raise RuntimeError(
            "Cannot downgrade while writings without legacy prompt_id values exist"
        )

    with op.batch_alter_table("writings") as batch:
        batch.drop_constraint("uq_writings_author_client_id", type_="unique")
        batch.alter_column("prompt_id", nullable=False)
        batch.drop_column("published_at")
        batch.drop_column("created_at")
        batch.drop_column("prompt_emotions")
        batch.drop_column("prompt_full_text")
        batch.drop_column("prompt_verb")
        batch.drop_column("client_writing_id")
