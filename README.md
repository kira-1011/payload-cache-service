# payload-cache-service

A FastAPI microservice that generates payloads from two lists of strings and caches the results of an
expensive "transformer" call in PostgreSQL. It comes with `cache-cli`, a command-line client for
exercising the service.

> Work in progress. Setup, usage, design decisions, and assumptions will be documented here as the
> implementation lands.

## Run locally

Requires [uv](https://docs.astral.sh/uv/).

```sh
uv sync
cp .env.example .env            # DATABASE_URL for the local Postgres
docker compose up -d db         # Postgres only
uv run alembic upgrade head
uv run fastapi dev
```

The API docs are served at http://localhost:8000/docs.

## Run with Docker

```sh
docker compose up --build
```

This starts Postgres, applies the migrations once, and then starts the API.

## API

| Method | Path | Success | Errors |
|---|---|---|---|
| `POST` | `/payload` | `201` new payload (with `Location` header), `200` payload already existed | `422` invalid input |
| `GET` | `/payload/{id}` | `200` `{"output": "..."}` | `404` unknown id, `422` malformed id |

```sh
curl -X POST localhost:8000/payload -H "content-type: application/json" \
  -d '{"list_1": ["first string", "second string"], "list_2": ["other string", "another string"]}'
# {"id": "<uuid>", "message": "Payload created"}

curl localhost:8000/payload/<uuid>
# {"output": "FIRST STRING, OTHER STRING, SECOND STRING, ANOTHER STRING"}
```

Both lists must be non-empty and the same length, with at most 1,000 items of at most 1,000
characters each.

## Stack

Python 3.14 · uv · FastAPI · SQLModel · Alembic · PostgreSQL · pydantic-settings · httpx2 · pytest ·
ruff · ty · Docker
