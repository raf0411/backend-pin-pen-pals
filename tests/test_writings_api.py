import asyncio
from datetime import UTC
from uuid import UUID

import pytest
from sqlalchemy import delete, func, select

from app.features.writing.models import Prompt, Writing

CLIENT_ID = "2d249146-eed2-46e7-91b2-66a8562fc23c"
HEADERS = {"X-Device-ID": "device-123"}


def publish_payload(**overrides):
    payload = {
        "client_writing_id": CLIENT_ID,
        "title": None,
        "full_text": "\n  The first usable line  \nThe writing content",
        "prompt": {
            "verb": " Reflect ",
            "full_text": " Write about a moment when... ",
            "emotions": [" Hope ", "JOY", "hope"],
        },
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_creates_writing_with_normalized_prompt_snapshot(client):
    response = await client.post(
        "/api/writings", headers=HEADERS, json=publish_payload()
    )

    assert response.status_code == 201
    body = response.json()
    assert body["client_writing_id"] == CLIENT_ID
    assert body["title"] == "The first usable line"
    assert body["full_text"] == "\n  The first usable line  \nThe writing content"
    assert body["prompt"] == {
        "verb": "Reflect",
        "full_text": "Write about a moment when...",
        "emotions": ["hope", "joy"],
    }
    assert body["status"] == "published"
    assert body["created_at"].endswith("Z")
    assert body["published_at"].endswith("Z")


@pytest.mark.asyncio
async def test_uses_trimmed_explicit_title(client):
    response = await client.post(
        "/api/writings",
        headers=HEADERS,
        json=publish_payload(title="  Supplied title  "),
    )

    assert response.status_code == 201
    assert response.json()["title"] == "Supplied title"


@pytest.mark.asyncio
async def test_blank_title_uses_truncated_first_nonempty_line(client):
    response = await client.post(
        "/api/writings",
        headers=HEADERS,
        json=publish_payload(title="  ", full_text=f"\n  {'x' * 300}\nsecond"),
    )

    assert response.status_code == 201
    assert response.json()["title"] == "x" * 256


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("full_text", "   \n  "),
        ("client_writing_id", "not-a-uuid"),
        ("title", 123),
    ],
)
async def test_rejects_invalid_top_level_fields(client, field, value):
    response = await client.post(
        "/api/writings",
        headers=HEADERS,
        json=publish_payload(**{field: value}),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Request validation failed"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "prompt",
    [
        {"full_text": "Prompt", "emotions": ["hope"]},
        {"verb": " ", "full_text": "Prompt", "emotions": ["hope"]},
        {"verb": "Reflect", "full_text": " ", "emotions": ["hope"]},
        {"verb": "Reflect", "full_text": "Prompt", "emotions": [" "]},
        {"verb": "Reflect", "full_text": "Prompt", "emotions": []},
    ],
)
async def test_rejects_missing_or_blank_prompt_values(client, prompt):
    response = await client.post(
        "/api/writings",
        headers=HEADERS,
        json=publish_payload(prompt=prompt),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_rejects_unknown_fields(client):
    response = await client.post(
        "/api/writings",
        headers=HEADERS,
        json={**publish_payload(), "unexpected": True},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_identical_retry_returns_existing_writing(client, session_factory):
    first = await client.post("/api/writings", headers=HEADERS, json=publish_payload())
    retry = await client.post("/api/writings", headers=HEADERS, json=publish_payload())

    assert first.status_code == 201
    assert retry.status_code == 200
    assert retry.json() == first.json()
    async with session_factory() as session:
        count = await session.scalar(select(func.count()).select_from(Writing))
    assert count == 1


@pytest.mark.asyncio
async def test_conflicting_retry_returns_409(client):
    await client.post("/api/writings", headers=HEADERS, json=publish_payload())
    response = await client.post(
        "/api/writings",
        headers=HEADERS,
        json=publish_payload(full_text="Different content"),
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            "client_writing_id already exists for this device with different content"
        )
    }


@pytest.mark.asyncio
async def test_different_devices_may_use_same_client_id(client, session_factory):
    first = await client.post("/api/writings", headers=HEADERS, json=publish_payload())
    second = await client.post(
        "/api/writings",
        headers={"X-Device-ID": "device-456"},
        json=publish_payload(),
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]
    async with session_factory() as session:
        count = await session.scalar(select(func.count()).select_from(Writing))
    assert count == 2


@pytest.mark.asyncio
async def test_concurrent_retries_create_one_writing(client, session_factory):
    first, second = await asyncio.gather(
        client.post("/api/writings", headers=HEADERS, json=publish_payload()),
        client.post("/api/writings", headers=HEADERS, json=publish_payload()),
    )

    assert sorted([first.status_code, second.status_code]) == [200, 201]
    assert first.json()["id"] == second.json()["id"]
    async with session_factory() as session:
        count = await session.scalar(select(func.count()).select_from(Writing))
    assert count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "headers",
    [{}, {"X-Device-ID": "   "}, {"X-Device-ID": "x" * 129}],
)
async def test_requires_valid_device_id(client, headers):
    response = await client.post(
        "/api/writings", headers=headers, json=publish_payload()
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_returns_stored_timestamps_and_new_fields(client, session_factory):
    created = await client.post(
        "/api/writings", headers=HEADERS, json=publish_payload()
    )
    body = created.json()

    async with session_factory() as session:
        writing = await session.scalar(select(Writing))

    assert body["client_writing_id"] == str(writing.client_writing_id)
    assert UUID(body["client_writing_id"]) == writing.client_writing_id
    assert body["created_at"] == writing.created_at.replace(
        tzinfo=UTC
    ).isoformat().replace("+00:00", "Z")
    assert body["published_at"] == writing.published_at.replace(
        tzinfo=UTC
    ).isoformat().replace("+00:00", "Z")


@pytest.mark.asyncio
async def test_snapshot_survives_prompt_seed_changes(client, session_factory):
    async with session_factory() as session:
        session.add(Prompt(id="prompt-joy", emotion="joy", theme="Old seed"))
        await session.commit()

    created = await client.post(
        "/api/writings", headers=HEADERS, json=publish_payload()
    )

    async with session_factory() as session:
        await session.execute(delete(Prompt))
        await session.commit()

    response = await client.get(
        f"/api/writings/{created.json()['id']}",
        headers=HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["prompt"] == created.json()["prompt"]


@pytest.mark.asyncio
async def test_list_preserves_three_line_preview_and_snapshot(client):
    payload = publish_payload(full_text="line one\nline two\nline three\nline four")
    await client.post("/api/writings", headers=HEADERS, json=payload)

    response = await client.get("/api/writings", headers=HEADERS)

    assert response.status_code == 200
    assert response.json()[0]["preview_text"] == "line one\nline two\nline three"
    assert response.json()[0]["prompt"]["emotions"] == ["hope", "joy"]


def test_openapi_marks_device_header_required():
    from app.main import app

    parameter = next(
        item
        for item in app.openapi()["paths"]["/api/writings"]["post"]["parameters"]
        if item["name"] == "x-device-id"
    )
    assert parameter["required"] is True
