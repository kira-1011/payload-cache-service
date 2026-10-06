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

## Stack

Python 3.14 · uv · FastAPI · SQLModel · Alembic · PostgreSQL · pydantic-settings · httpx2 · pytest ·
ruff · ty · Docker
