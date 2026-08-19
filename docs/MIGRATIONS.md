# Database migrations

The project uses Alembic with the async SQLAlchemy database URL from `DATABASE_URL`.

## Install dependencies

```bash
pip install -r requirements.txt
```

## Upgrade

Back up shared or production databases before applying a migration, then run:

```bash
alembic upgrade head
```

Run this command before starting version `0.4.0` of the API. Application startup no longer calls `Base.metadata.create_all()` because that method cannot update existing tables safely.

## Current revision

`20260819_01_add_ios_writing_publish_fields.py` adds:

- `client_writing_id`
- `prompt_verb`
- `prompt_full_text`
- `prompt_emotions` as a native JSON array
- `created_at`
- `published_at`
- Unique constraint `uq_writings_author_client_id` on `(author_id, client_writing_id)`

The migration makes the legacy `prompt_id` nullable so locally generated prompts do not require a row in `prompts`.

## Existing-row backfill

For each existing writing, the migration:

- Generates a deterministic UUID v5 from its author ID and backend writing ID.
- Sets `prompt_verb` to `Write`.
- Copies the related prompt theme into `prompt_full_text` when available.
- Copies and lowercases the related prompt emotion into the JSON emotion array.
- Uses fallback prompt text and an `unknown` emotion when the related prompt no longer exists.
- Stores one migration timestamp in `created_at` and `published_at`.

The migration adds required constraints only after backfilling existing rows.

## Downgrade

```bash
alembic downgrade base
```

Alembic refuses to downgrade while any writing has a null legacy `prompt_id`. New iOS-published writings have no legacy prompt relation, so deleting or explicitly migrating those records requires a deliberate data decision before downgrade. This guard prevents silent data loss.

## Create a future revision

```bash
alembic revision --autogenerate -m "describe the schema change"
alembic upgrade head
```

Review generated revisions before applying them.
