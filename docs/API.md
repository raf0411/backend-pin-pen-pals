# WritingsReader API

Base URL for local development:

```text
http://localhost:8000
```

The machine-readable OpenAPI specification lives at [`openapi.json`](./openapi.json). Import it into Postman, Insomnia, Swagger Editor, or another OpenAPI-compatible client.

## Start the API

```bash
python main.py
```

Configure the database and browser origins with environment variables:

```bash
export DATABASE_URL="postgresql+asyncpg://raffi@localhost/writingsreader"
export ALLOWED_ORIGINS="http://localhost:3000,http://localhost:5173"
python main.py
```

## Authentication header

Writing endpoints require an `X-Device-ID` header. The value must contain 1 to 128 characters after whitespace is removed.

```http
X-Device-ID: device-123
```

A missing or blank header returns `400 Bad Request`:

```json
{
  "detail": "Missing required header: X-Device-ID"
}
```

## Endpoints

### Create a writing

```http
POST /api/writings
```

Seeded prompt IDs:

- `prompt-angry`
- `prompt-joy`
- `prompt-sad`

Request constraints:

| Field | Required | Constraints |
| --- | --- | --- |
| `title` | Yes | 1–256 characters |
| `full_text` | Yes | 1–50,000 characters |
| `prompt_id` | Yes | 1–64 characters; must reference an existing prompt |

#### cURL

```bash
curl -X POST "http://localhost:8000/api/writings" \
  -H "Content-Type: application/json" \
  -H "X-Device-ID: device-123" \
  -d '{
    "title": "A New Beginning",
    "full_text": "The morning started quietly.\nThen everything changed.",
    "prompt_id": "prompt-joy"
  }'
```

#### Response: `201 Created`

```json
{
  "id": "writing-a1b2c3d4",
  "title": "A New Beginning",
  "full_text": "The morning started quietly.\nThen everything changed.",
  "author_id": "device-123",
  "prompt_theme": "Found a Letter",
  "prompt_emotion": "joy"
}
```

The server generates the writing ID.

#### Unknown prompt: `400 Bad Request`

```json
{
  "detail": "Prompt 'prompt-unknown' not found"
}
```

FastAPI returns `422 Unprocessable Entity` when the request body fails validation.

### List writings

```http
GET /api/writings
```

The endpoint returns the first three lines of each writing in `preview_text`.

#### cURL

```bash
curl "http://localhost:8000/api/writings" \
  -H "X-Device-ID: device-123"
```

#### Response: `200 OK`

```json
[
  {
    "id": "writing-1",
    "title": "The Quiet Room",
    "preview_text": "There is a room in my grandmother's house that no one uses anymore.\nIt sits at the end of a narrow hallway, behind a door that swells shut in the summer heat.\nThe wallpaper is the color of old tea, peeling at the seams like a secret losing its grip.",
    "author_id": "seed-author-device-001",
    "prompt_theme": "Lost a Friend",
    "prompt_emotion": "sad"
  }
]
```

The API returns an empty array when the database contains no writings:

```json
[]
```

### Get a writing

```http
GET /api/writings/{writing_id}
```

`writing_id` must contain 1 to 64 characters.

#### cURL

```bash
curl "http://localhost:8000/api/writings/writing-1" \
  -H "X-Device-ID: device-123"
```

#### Response: `200 OK`

```json
{
  "id": "writing-1",
  "title": "The Quiet Room",
  "full_text": "There is a room in my grandmother's house that no one uses anymore.\nIt sits at the end of a narrow hallway...",
  "author_id": "seed-author-device-001",
  "prompt_theme": "Lost a Friend",
  "prompt_emotion": "sad"
}
```

#### Unknown writing: `404 Not Found`

```json
{
  "detail": "Writing 'writing-unknown' not found"
}
```

### Censor text

```http
POST /api/censor
```

This endpoint does not require `X-Device-ID`. The `text` field must contain non-whitespace text and cannot exceed 50,000 characters.

#### cURL

```bash
curl -X POST "http://localhost:8000/api/censor" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "This is a damn test."
  }'
```

#### Response with profanity: `200 OK`

```json
{
  "text": "This is a **** test.",
  "was_censored": true
}
```

#### Response without profanity: `200 OK`

```json
{
  "text": "This is clean.",
  "was_censored": false
}
```

## Interactive documentation

FastAPI serves documentation while the application runs:

| Path | Format |
| --- | --- |
| `/docs` | Swagger UI |
| `/redoc` | ReDoc |
| `/openapi.json` | Generated OpenAPI JSON |

The project does not define a `/` endpoint or a prompt-listing endpoint.
