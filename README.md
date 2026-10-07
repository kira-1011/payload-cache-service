# payload-cache-service

A FastAPI microservice that builds payloads from two lists of strings. Each string goes through a
"transformer function" (a stand-in for a slow external service), and the results are cached in
PostgreSQL so the transformer is called as rarely as possible. `cache-cli` is a command-line client
for exercising the service.

## Quick start

Requires Docker, and [uv](https://docs.astral.sh/uv/) for the CLI.

```sh
docker compose up --build
```

This starts Postgres, applies the migrations once, then starts the API on http://localhost:8000
(interactive docs at `/docs`). In another terminal:

```sh
uv run cache-cli -j '{"list_1": ["first string", "second string"], "list_2": ["other string", "another string"]}'
# {"id": "<uuid>", "output": "FIRST STRING, OTHER STRING, SECOND STRING, ANOTHER STRING"}
```

## Run locally

Requires [uv](https://docs.astral.sh/uv/) and Docker (for Postgres).

```sh
uv sync
cp .env.example .env            # DATABASE_URL for the local Postgres
docker compose up -d db         # Postgres only
uv run alembic upgrade head
uv run fastapi dev
```

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

## CLI

`cache-cli` posts a payload, reads it back by its id, and writes one JSON line per round trip.

```text
cache-cli [-h|--host URL] [-r|--repeat N] [-i|--input FILE|-] [-j|--json JSON] [-o|--output FILE|-] [--help]
```

```sh
uv run cache-cli -j '{"list_1": ["first string"], "list_2": ["other string"]}' -r 3
uv run cache-cli -i payload.json -o results.jsonl
cat payload.json | uv run cache-cli -i -
```

- Pass exactly one of `--input` and `--json`. Both take the same JSON body as `POST /payload`.
- `-h` is `--host` as in the task spec, so help is `--help` only.
- Exit codes: `0` success, `1` request or input failure, `2` invalid arguments.
- Input files and stdin are read as UTF-8; a byte order mark (as written by Windows PowerShell) is accepted.

Windows PowerShell 5.1 strips double quotes from arguments passed to programs. Escape them,
use `--%` when the JSON contains spaces, or pass a file with `-i`:

```powershell
uv run cache-cli -j '{\"list_1\":[\"a\"],\"list_2\":[\"b\"]}'
uv run cache-cli --% -j "{\"list_1\":[\"first string\"],\"list_2\":[\"other string\"]}"
```

## How it works

One `POST /payload`, from the endpoint to the database and back:

```text
routers/payloads.py     validate the body (schemas.py), call the service, map the result to 201/200
services/payloads.py    get_or_create_payload:
  1. hash the input: SHA-256 of [list_1, list_2] as JSON
  2. payload with that hash exists?           -> return it (200), no transformer calls
  3. deduplicate the strings, read their cached results in one query
  4. call the transformer only for the misses, insert them (ON CONFLICT DO NOTHING)
  5. interleave: transform(list_1[0]), transform(list_2[0]), transform(list_1[1]), ... joined with ", "
  6. insert the payload (ON CONFLICT DO NOTHING ... RETURNING id), commit once -> 201
crud.py                 the SQL: lookups and conflict-tolerant inserts
models.py               tables: transform_result (input_hash -> output_text), payload
```

`GET /payload/{id}` is a primary-key lookup of the stored output. Dependencies point one way:
`routers` → `services` → `crud` → `models`; the services never import FastAPI.

## Design decisions

| Topic | Decision | Why |
|---|---|---|
| Transformer | Works on one string at a time; uppercases it | The cache is per string, so a string seen in any earlier payload is never transformed again. Uppercase is inferred from the spec's sample output. |
| Two levels of reuse | Transform results per string, and payload ids per input | Both are required by the spec. A repeated input skips the transformer entirely. |
| Cache keys | SHA-256 of the string, and of `json.dumps([list_1, list_2])` for payloads | A fixed 64-character key stays under the Postgres index-entry size limit for long inputs. Nested JSON keeps the list boundaries and escapes commas, so `["a, b"]` and `["a", "b"]` don't collide. |
| Payload id | UUIDv7 (`uuid.uuid7()`, Python 3.14) | Time-ordered, so it indexes well, and it doesn't reveal the content |
| Concurrency | `INSERT ... ON CONFLICT DO NOTHING` for both tables, cache rows inserted in sorted order | Parallel requests for the same new input all succeed with the same id, instead of failing on the unique constraint. The sorted order avoids deadlocks. |
| Transactions | One commit per request; the session is passed in, never created by the services | The payload and its new cache rows are saved together or not at all |
| Migrations | Alembic, run by a one-off `migrate` service before the API starts | Migrations run once, even with several API containers |
| Input limits | 1,000 items per list, 1,000 characters per string | OWASP API4 (unrestricted resource consumption) |
| `POST` status codes | `201` with a `Location` header for a new payload, `200` for an existing one | RFC 9110 |
| CLI parsing | pydantic-settings, with a custom argparse parser | The spec requires pydantic-settings. The custom parser lets `-h` mean `--host`, as the spec's usage line does. Environment variables are ignored, so a stray `HOST` can't change the options. |
| Docker | Multi-stage build with uv, non-root user, pinned versions | Small, reproducible image |

## Assumptions

Where the spec is open, I chose the simplest reading:

- **The transformation** is uppercase, taken from the sample output. The spec only says it simulates an external service.
- **"Payloads generated before"** means the same input: the same two lists in the same order. Different inputs that happen to give the same output are different payloads.
- **"Payload files"** are rows in the database, not files on disk.
- **Validation:** both lists must be non-empty and the same length. Empty strings are allowed, and whitespace is kept as given.
- **The CLI** does one round trip per iteration (POST, then GET by the returned id). `--repeat N` runs N round trips. `--input` and `--json` take the same JSON body as the API, and the output is one JSON line per round trip.
- **`-h`** is listed in the spec for both `--host` and `--help`. It means `--host` here, and help is `--help` only.

## Shortcuts and known limitations

- **Tests run on in-memory SQLite**, so they need no Docker. Postgres-specific behavior (migrations, reconnecting after a restart, the concurrency fix) was checked by hand against the Docker stack.
- **Duplicate transformer calls under concurrency:** two simultaneous requests with the same *new* string both call the transformer. The data stays correct; avoiding the extra call would need a per-key lock.
- **The cache never expires**, which is correct while the transformer is deterministic.
- **The transformer is synchronous.** A slow external service would call for async calls and releasing the database connection while waiting.
- **No authentication or request-body size limit (413).** In production these belong to a reverse proxy.
- **A database outage** returns FastAPI's generic `500`.
- **Local credentials** in `compose.yaml` and `.env.example` are plain text, for local use only.

## Testing

```sh
uv run pytest                                        # no Docker needed
uv run ruff check . && uv run ruff format --check .  # lint and format
uv run ty check                                      # types
```

- **Unit** (`tests/unit`):
  - interleaving, hashing and the spec example;
  - schema validation;
  - the caching service, with a spy that counts transformer calls;
  - race tests that simulate a concurrent insert;
  - CLI argument parsing.
- **Integration** (`tests/integration`): the API through FastAPI's `TestClient`, and the CLI driven against the app in-process.
- **CI** (GitHub Actions) runs the tests and the code-quality checks on every push and pull request.

## Project layout

```text
src/cache_service/       FastAPI service
  main.py                app and router wiring
  config.py              settings (DATABASE_URL)
  db.py                  engine and session
  models.py              SQLModel tables
  schemas.py             request and response models
  crud.py                database queries and inserts
  dependencies.py        SessionDep
  routers/payloads.py    POST /payload, GET /payload/{id}
  services/payloads.py   caching and payload generation
  services/transformer.py
src/cache_cli/           cache-cli (settings.py: parsing; main.py: round trips)
migrations/              Alembic
tests/                   unit/ and integration/
```

## Stack

Python 3.14 · uv · FastAPI · SQLModel · Alembic · PostgreSQL 18 · pydantic-settings · httpx2 ·
pytest · ruff · ty · Docker · GitHub Actions
