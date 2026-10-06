# payload-cache-service

A FastAPI microservice that generates payloads from two lists of strings and caches the results of an
expensive "transformer" call in PostgreSQL. It comes with `cache-cli`, a command-line client for
exercising the service.

> Work in progress. Setup, usage, design decisions, and assumptions will be documented here as the
> implementation lands.

## Stack

Python 3.14 · uv · FastAPI · SQLModel · Alembic · PostgreSQL · pydantic-settings · httpx2 · pytest ·
ruff · ty · Docker
