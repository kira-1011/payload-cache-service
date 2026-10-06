# [AGENTS.md](http://AGENTS.md)

Instructions for AI coding agents (and humans) working in this repository.
Read this file fully before planning or writing code.

## 1. What this project is

A small **caching microservice** built with FastAPI, plus a **CLI** to exercise it.

The task spec lives in `Test task Python.md`. That file is **local only**: it is gitignored and must never be committed.
If this file and the spec disagree, the spec wins. Raise the conflict instead of silently picking one.

### Core requirements (from the spec)

1. `POST /payload` takes two string lists of equal length and returns the **identifier** of the generated payload.
2. `GET /payload/{id}` returns the generated payload: `{"output": "..."}`.
3. Payload generation has two separate steps:
  - **Transform:** the transformer function (a simulated external service) works on **one string at a time**: `transform("first string") -> "FIRST STRING"`. The spec doesn't define the transformation; uppercase is inferred from its sample output.
  - **Interleave:** our own service code, not the transformer, merges the transformed strings by alternating between the lists: `transform(list_1[0]), transform(list_2[0]), transform(list_1[1]), transform(list_2[1]), ...`, joined with `", "`.
  - The transformer has to work per string because the cache is per string. Then a string seen in any earlier payload is never transformed again. If the transformer took both whole lists, any new combination would be a cache miss, and the transformer cache would be the same thing as payload reuse.
4. Caching is explicitly required at **two** levels:
  - **Transformer results** are cached per input string and reused. The number of transformer calls must be as small as possible.
  - **Payload identifiers** are reused when the same input was generated before.
5. Cached results are stored in **PostgreSQL**.
6. A CLI tool, `cache-cli`, uses **pydantic-settings** for argument parsing and validation.
7. The service runs with **Docker** and docker compose.
8. **Unit and integration tests** are included.



## 2. Working principles

- **Core first, extras later.** Build exactly what the spec asks, end to end, before adding anything.
Concurrency handling, async I/O, retries, timeouts, and LLM-style hardening come only after the core is complete, and only if justified.
- **No over-engineering.** Prefer the simplest design that is correct.
  - Add no abstraction layers, generic repositories, or plugin systems "for later".
  - Write a function before writing a class.
  - Use one module per concern, not one package per concern.
- **Every line must be defensible.** If you can't explain why a line exists, delete it.
- **Questions go at the start.** When the spec is ambiguous:
  - choose the simplest reasonable interpretation;
  - write it down in section 4 and in the README under "Assumptions";
  - move on.
- **Say "this is a bad idea" when it is one,** and give the argument. Don't implement something you believe is wrong without flagging it.
- **Shortcuts are allowed** if they are documented and justified in the README under "Shortcuts".



## 3. Guidelines from the assessment (verbatim, mandatory)

- Thoroughly review the task, make sure the goal and the requirements are clear. Communicate directly any questions and concerns.
- Follow the coding style and conventions when writing your code/scripts. Write clear and concise comments and documentation, focus on the "why" (not on the "how").
- Use *git* for version control. Commit in small and manageable chunks with meaningful commit messages. Review and clean up the code before final submission. Refactor the code as needed.
- Test and debug your code. Add some tests to demonstrate knowledge of unit- and integration-testing. It's ok to make necessary shortcuts as long as they are clearly documented and justified.



## 4. Decisions and assumptions (resolved ambiguities)

Keep this list up to date. Copy it into the README before submission.


| Topic                   | Decision                                                                                                                                                                                                                                       |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Transformer             | A plain function, `transform(text: str) -> str`, that returns `text.upper()`. It has no artificial delay, no configuration, and no dependency injection, because the spec asks for none of these. Tests count its calls by patching it with a spy (section 8). |
| Transformer cache key   | SHA-256 of the input string, with a unique index; the raw input and the output are stored next to it. A hash is used because Postgres B-tree index entries are limited to about 2.7 KB, so long strings could not be indexed directly.         |
| Fewer transformer calls | Deduplicate the strings within a request (`set`), fetch all cached ones in **one** `IN` query, and call the transformer only for the misses.                                                                                                   |
| Payload reuse           | Two payloads are the same when their **input** is identical: same lists, same order. The key is `sha256(json.dumps([list_1, list_2]))`: the two lists **nested, not flattened or zipped**, stored with a unique index. A repeated POST returns the existing id and makes no transformer calls. JSON escapes commas and quotes, so different inputs can't serialize to the same text (a plain `", ".join` would make `["a, b"]` and `["a", "b"]` collide). Zipping into pairs carries the same information but adds a step. The input is hashed because it can be large, and a unique index on the raw text would hit the Postgres index-size limit. Python's built-in `hash()` must never be stored: its value changes between processes. |
| Payload id              | UUIDv7 (`uuid.uuid7()`, new in Python 3.14). It is time-ordered, which suits the index, and can't be guessed from the content.                                                                                                                 |
| Payload storage         | The generated output string is stored in the DB, so `GET` is a plain read. Nothing is written to disk as files.                                                                                                                                |
| Generation mode         | Synchronous: `POST` generates the payload, then returns. No background jobs in the core.                                                                                                                                                       |
| Validation              | The two lists must have equal length and at least one item each; otherwise the API returns 422. Strings are used exactly as given, with no trimming or normalization.                                                                          |
| POST response           | `201 {"id": ..., "message": "Payload created"}` for a new payload. `200` with the same shape for a reused one.                                                                                                                                 |
| GET response            | `200 {"output": "..."}`. `404` if the id is unknown. `422` if the id is not a valid UUID.                                                                                                                                                      |
| CLI behavior            | Each iteration is one round trip: `POST` the input, then `GET` the payload by the returned id, then write one JSON line `{"id": ..., "output": ...}` to the output. `--repeat N` runs N iterations (N ≥ 1, default 1).                         |
| CLI input               | Exactly one of `--input FILE` (use `-` for stdin) or `--json JSON` is required. Both contain the same JSON body as `POST /payload`.                                                                                                            |
| CLI output              | `--output FILE`, where `-` means stdout (the default). Errors go to stderr with a non-zero exit code.                                                                                                                                          |
| CLI `-h` conflict       | The spec uses `-h` for both `--host` and `--help`. Decision: `-h` means `--host`, and help is `--help` only (the same convention as `psql`). Mention this in the README.                                                                       |
| CLI host default        | `http://localhost:8000`                                                                                                                                                                                                                        |
| Test database           | Tests run against in-memory SQLite (a documented shortcut that keeps them fast and needing no extra setup). Production uses Postgres. Queries stay dialect-neutral.                                                                            |




## 5. Tech stack

Use the **latest stable versions**. Pin them with `uv.lock`, and check the official docs before using an API.


| Tool                         | Use                                            | Docs                                                                                                                                                                                                                |
| ---------------------------- | ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Python 3.14                  | language                                       | [https://docs.python.org/3.14/](https://docs.python.org/3.14/)                                                                                                                                                      |
| uv                           | project, dependencies, lockfile, running tools | [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/)                                                                                                                                                            |
| FastAPI                      | HTTP API                                       | [https://fastapi.tiangolo.com/tutorial/](https://fastapi.tiangolo.com/tutorial/)                                                                                                                                    |
| SQLModel                     | ORM and table models (sync `Session`)          | [https://sqlmodel.tiangolo.com/](https://sqlmodel.tiangolo.com/)                                                                                                                                                    |
| psycopg 3                    | Postgres driver (`postgresql+psycopg://`)      | [https://www.psycopg.org/psycopg3/docs/](https://www.psycopg.org/psycopg3/docs/)                                                                                                                                    |
| Alembic                      | schema migrations                              | [https://alembic.sqlalchemy.org/en/latest/](https://alembic.sqlalchemy.org/en/latest/)                                                                                                                              |
| PostgreSQL                   | database, run in docker compose                | [https://docs.docker.com/guides/postgresql/](https://docs.docker.com/guides/postgresql/)                                                                                                                            |
| pydantic / pydantic-settings | validation, service config, CLI parsing        | [https://docs.pydantic.dev/](https://docs.pydantic.dev/)                                                                                                                                                            |
| httpx2                       | HTTP client in the CLI (`import httpx2`)       | [https://pydantic.dev/docs/httpx2/get-started/](https://pydantic.dev/docs/httpx2/get-started/)                                                                                                                      |
| pytest                       | unit and integration tests                     | [https://docs.pytest.org/en/stable/](https://docs.pytest.org/en/stable/)                                                                                                                                            |
| ruff                         | lint and format                                | [https://docs.astral.sh/ruff/](https://docs.astral.sh/ruff/)                                                                                                                                                        |
| ty                           | type checking                                  | [https://docs.astral.sh/ty/](https://docs.astral.sh/ty/)                                                                                                                                                            |
| Docker                       | image built with uv                            | [https://docs.astral.sh/uv/guides/integration/docker/](https://docs.astral.sh/uv/guides/integration/docker/) and [https://fastapi.tiangolo.com/deployment/docker/](https://fastapi.tiangolo.com/deployment/docker/) |


Stack rules:

- Use **sync** SQLModel sessions and `def` endpoints in the core. FastAPI runs them in a threadpool. Async can come later, once the core is complete.
- Declare `[tool.fastapi] entrypoint = "cache_service.main:app"` in `pyproject.toml`. Run with `fastapi dev` locally and `fastapi run` in Docker.
- Do **not** add dependencies beyond this table without stating why in the commit message.
- Dev tools (pytest, ruff, ty) go in the `dev` dependency group (`uv add --dev ...`).



## 6. Project layout

```
.
├── .github/workflows/ci.yml     # CI: test + code-quality jobs (section 10)
├── AGENTS.md
├── README.md
├── .python-version              # 3.14, used by uv locally and in CI
├── pyproject.toml / uv.lock
├── Dockerfile / .dockerignore / compose.yaml
├── alembic.ini
├── migrations/                  # Alembic env + versions
├── src/
│   ├── cache_service/
│   │   ├── main.py              # FastAPI app: creates the app, includes routers
│   │   ├── config.py            # service Settings (pydantic-settings, env vars)
│   │   ├── db.py                # engine + session dependency
│   │   ├── models.py            # SQLModel tables
│   │   ├── schemas.py           # API request/response models
│   │   ├── dependencies.py      # Annotated Depends alias: SessionDep
│   │   ├── routers/             # HTTP layer only
│   │   │   └── payloads.py      # APIRouter(prefix="/payload"): POST, GET
│   │   └── services/            # business logic, no FastAPI imports
│   │       ├── transformer.py   # simulated external service: one string in, one string out
│   │       └── payloads.py      # caching, interleaving, payload get-or-create
│   └── cache_cli/
│       └── main.py              # `cache-cli` entry point
└── tests/
    ├── conftest.py
    ├── unit/                    # services with a transformer spy and SQLite session
    └── integration/             # API through TestClient, CLI end to end
```

Layering rules (dependencies point inward: `routers` → `services` → `models`):

- `routers/` handles HTTP only. A route parses the request, calls one service function, and maps the result or a domain error to a status code and response. It contains no caching or DB logic. Following the FastAPI skill, each router declares its `prefix` and `tags` on the `APIRouter` itself, and `main.py` only calls `include_router`.
- `services/` holds the business logic as **plain module-level functions**, not classes and not a repository layer.
  - It never imports `fastapi`.
  - It receives the DB `Session` as an argument.
  - It calls the transformer as `transformer.transform(...)`, via `from cache_service.services import transformer`. Because the call goes through the module attribute, a test can patch `transformer.transform` in one place.
  - Pure helpers such as `interleave` and `fingerprint` live in `services/payloads.py` and have no I/O at all.
- `services/transformer.py` is a stand-in for an external dependency rather than real business logic.
- `dependencies.py` provides the DB session to routes as `SessionDep = Annotated[Session, Depends(get_session)]`. Tests override it with `app.dependency_overrides` to use SQLite.
- Signal "not found" with a domain exception or a `None` return, never `HTTPException`. Only routers translate errors into HTTP responses.
- `cache_cli` never imports `cache_service`. It talks to the service only over HTTP.
- `cache-cli` is exposed through `[project.scripts]` in `pyproject.toml`.



## 7. Coding conventions

- Format and lint with **ruff**, type-check with **ty**. Code with ruff or ty errors is not finished.
- Type hints on every function signature. No `Any` unless it is justified.
- Comments and docstrings explain **why**, not what. No commented-out code, and no TODOs without a reason.
- Names say what things are, e.g. `transform_cache`, `payload_fingerprint`. Avoid abbreviations.
- Configuration comes from environment variables through pydantic-settings. No hard-coded URLs or credentials.
- Use timezone-aware UTC timestamps (`datetime.now(UTC)`).
- Keep each DB transaction short and explicit. Commit once per request, after all writes.
- Return proper HTTP status codes. Let FastAPI/Pydantic return 422 for invalid input.
- Follow the official **fastapi** and **pydantic** skills for idioms: `Annotated` dependencies, `response_model`, `model_validator`, and so on.



## 8. Testing

- **Unit tests** (`tests/unit/`):
  - the interleaving function;
  - request validation (unequal lists, empty lists);
  - fingerprint stability;
  - the caching logic, counting transformer calls with a spy: `patch("cache_service.services.transformer.transform", wraps=transform)`. The real function still runs, and `spy.call_count` gives the number of calls.
- **Integration tests** (`tests/integration/`): the full API through FastAPI's `TestClient`, with the session dependency overridden to use SQLite and the same transformer spy. Also the CLI: its argument parsing, and a run against the test app.
- These tests are required, because they prove the caching works:
  - The first POST calls the transformer once per **unique** string.
  - A repeated identical POST returns the same id with **0** transformer calls.
  - A POST that partly overlaps with cached strings calls the transformer only for the new strings.
  - GET of an unknown id returns 404.
- Tests must be deterministic and must not need Docker or network access.
- Commands: `uv run pytest`, `uv run ruff check . && uv run ruff format --check .`, `uv run ty check`.

## 9. Docker

Sources:
- the uv Docker guide (how to build the image): https://docs.astral.sh/uv/guides/integration/docker/
- uv's official example repo: https://github.com/astral-sh/uv-docker-example
- the FastAPI Docker guide (how to run the app): https://fastapi.tiangolo.com/deployment/docker/

### Dockerfile rules

- **Multi-stage build.** A `builder` stage installs everything with uv, and the final image contains no uv and no build tooling.
- **Both stages use the same base image, `python:3.14-slim-trixie`.** The copied `.venv` points at the interpreter's exact path, so a different final base breaks it.
- **Install uv by copying a pinned binary:** `COPY --from=ghcr.io/astral-sh/uv:<exact version> /uv /uvx /bin/`. Never use `latest`, so builds stay reproducible. 0.12.23 was the latest release on 2026-10-06.
- **Builder environment:**
  - `UV_COMPILE_BYTECODE=1`: faster startup.
  - `UV_LINK_MODE=copy`: required with a cache mount.
  - `UV_NO_DEV=1`: no pytest, ruff, or ty in the image.
  - `UV_PYTHON_DOWNLOADS=0`: use the image's Python, so both stages match.
- **Dependencies before code.** First run `uv sync --locked --no-install-project`, with only `uv.lock` and `pyproject.toml` bind-mounted and a cache mount on `/root/.cache/uv`. Then `COPY . /app` and run `uv sync --locked`. Code changes then don't reinstall the dependencies.
- **`--locked` is mandatory.** The build fails if `uv.lock` is out of sync with `pyproject.toml`. Always commit `uv.lock`.
- **Final stage:**
  - Create a non-root user (`groupadd`/`useradd`, uid 999) and switch to it with `USER`.
  - `COPY --from=builder /app /app` without `--chown`. The code stays owned by root, so the app can't modify it.
  - Set `ENV PATH="/app/.venv/bin:$PATH"` and `PYTHONUNBUFFERED=1`.
- **Run command:** `CMD ["fastapi", "run", "--port", "8000"]`.
  - Use the **exec form** (a JSON list) so shutdown signals reach the app and lifespan events run.
  - The app's location comes from `[tool.fastapi]` in `pyproject.toml`.
  - `fastapi run` already listens on `0.0.0.0`.
  - Use one process per container: no `--workers`, and no `--proxy-headers`, since there is no TLS proxy.
- **Don't use** `tiangolo/uvicorn-gunicorn-fastapi` (deprecated), shell-form `CMD`, or entrypoint shell scripts. On Windows, CRLF line endings break shell scripts inside a Linux container.

### compose.yaml rules

Postgres sources:
- Docker's PostgreSQL guide: https://docs.docker.com/guides/postgresql/
- the official `postgres` image page: https://hub.docker.com/_/postgres

- **`db`:**
  - Image `postgres:18.x-trixie`, pinned to a minor version.
  - Healthcheck with `pg_isready`. Other services wait on it with `condition: service_healthy`.
  - Named volume mounted at **`/var/lib/postgresql`**. Since Postgres 18, `PGDATA` is version-specific (`/var/lib/postgresql/18/docker`). The old `/var/lib/postgresql/data` mount doesn't persist data, and mounting the parent directory allows `pg_upgrade --link` later.
  - Publish the port as `127.0.0.1:5432:5432`: only this machine can reach it, for local tools such as `fastapi dev` and Alembic, not the whole network.
  - The plain-text `POSTGRES_*` credentials are local-only. In production, use Docker secrets through the `_FILE` variants (e.g. `POSTGRES_PASSWORD_FILE`).
  - `POSTGRES_*` variables and init scripts only take effect when the data directory is empty. After changing them, recreate the volume with `docker compose down -v`.
- **`migrate`:**
  - Same image as `api`, with `command: ["alembic", "upgrade", "head"]`.
  - `depends_on: db: condition: service_healthy`.
  - It runs once and exits. This is FastAPI's "previous steps in a separate container" pattern, so replicas never run migrations in parallel.
- **`api`:**
  - `ports: ["8000:8000"]`.
  - `depends_on: migrate: condition: service_completed_successfully`.
- `build: .` is declared once, and both `migrate` and `api` use `image: payload-cache-service`.
- `DATABASE_URL=postgresql+psycopg://...` is passed through `environment`. The plain-text local credentials are a documented shortcut.

### .dockerignore

It must contain `.venv`, `.git`, `**/__pycache__`, `.pytest_cache`, `.ruff_cache`, `.env`, `tests`, `AGENTS.md`, and `Test task Python.md`.
It must **not** exclude `alembic.ini` or `migrations/`, because the `migrate` service needs them.

### Not in the core

These are left out on purpose: `docker compose watch`, an API container healthcheck, `--workers`, a TLS proxy.

### Local requirement

Docker Desktop must be running. The cache and bind mounts need BuildKit, which Docker Desktop enables by default.

## 10. GitHub CI/CD

Source: the uv GitHub Actions guide, https://docs.astral.sh/uv/guides/integration/github/

The workflow is `.github/workflows/ci.yml`. It runs on every push to `main` and on every pull request, and has exactly **two jobs that run in parallel**:

| Job | Steps |
|---|---|
| `test` | checkout → setup-uv → `uv sync --locked` → `uv run pytest` |
| `code-quality` | checkout → setup-uv → `uv sync --locked` → `uv run ruff format --check .` → `uv run ruff check .` → `uv run ty check` |

Rules:
- **Install uv with the official `astral-sh/setup-uv` action.**
  - Pin uv to an exact version (`version: "0.12.23"`), the **same as in the Dockerfile**. Change both together.
  - `enable-cache: true` keeps uv's cache between runs.
- **Pin every action to a full commit SHA, with the tag in a comment**, e.g. `actions/checkout@<sha> # v7.0.1`. Tags can be moved; SHAs can't. That protects us from a supply-chain attack through a re-tagged action. Before bumping an action, look up its SHA with `git ls-remote --tags <repo> <tag>`.
- **Python comes from the committed `.python-version` (`3.14`).** `uv sync` installs that version. No `setup-python` step and no Python matrix: we support one version.
- **`uv sync --locked` in both jobs.** CI fails if `uv.lock` is out of date. The dev group (pytest, ruff, ty) is installed by default. `code-quality` needs the sync because ty resolves imports against installed packages.
- **Security and hygiene:**
  - `permissions: contents: read` at the top level (least privilege).
  - `persist-credentials: false` on checkout.
  - A `concurrency` group cancels outdated runs.
  - `timeout-minutes: 10` per job.
- **Tests need no services.** They use SQLite (section 8), so the `test` job has no Postgres service container. If tests ever move to Postgres, add a `services: postgres` block to this job.
- CI must pass on the final commit. Run the same commands locally before pushing (section 8).

**CD:** there is no deployment target, so there is no CD job. Deploying is out of scope; the Docker image is built and run locally with compose (section 9). If CD is needed later, the next step is a job that builds the image on `main`, then pushes it to GHCR (`docker/build-push-action`, `permissions: packages: write` on that job only). Don't add it unless asked.

## 11. Git workflow

- Use the **conventional-branch** skill for branch names (`feature/...`, `chore/...`, `bugfix/...`). Do the work on branches and merge them into `main` **without squashing**. Reviewers read the history.
- Use the **conventional-commit** skill for messages, e.g. `feat(api): add payload creation endpoint`.
- Make small commits that each work on their own. Each commit should leave the project passing lint and tests whenever that's feasible.
- Never commit secrets, `.env`, `.venv`, caches, or `Test task Python.md`.
- Keep the hiring company's name out of the code, commits, and repo name. The repository must have a neutral name.
- Commit and push only when the user asks you to.



## 12. Definition of done (core)

- [ ] `POST /payload` and `GET /payload/{id}` behave as described in section 4.
- [ ] Transformer results and payload ids are reused. The tests in section 8 prove it.
- [ ] Alembic migration creates the schema. In compose, the one-off `migrate` service runs it before `api` starts (section 9).
- [ ] `docker compose up --build` starts Postgres, migrates, and serves the API. The README sample request works.
- [ ] `cache-cli` handles all the flags in the spec and is validated with pydantic-settings.
- [ ] Unit and integration tests pass. ruff and ty are clean.
- [ ] Both GitHub Actions jobs (`test`, `code-quality`) are green on the final commit.
- [ ] README covers: how to run it, the API, the CLI, design decisions, assumptions, shortcuts, and next steps.
- [ ] Git history is clean and readable, made of small conventional commits.



## 13. Skills to use


| Skill                                              | When                                                                                                                                                                         |
| -------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `library-skills` (`.agents/skills/library-skills`) | After `uv sync`, run `uvx library-skills` to install the official skills that ship with our dependencies, such as FastAPI's. Use `--claude` to also manage `.claude/skills`. |
| `fastapi`                                          | Any endpoint, dependency, or app wiring.                                                                                                                                     |
| `pydantic`                                         | Request/response models, validators, settings, and the CLI settings model.                                                                                                   |
| `improve-codebase-architecture`                    | Before the final cleanup pass: look for simplification and better module boundaries. Don't add layers.                                                                       |
| `conventional-branch`                              | Creating branches.                                                                                                                                                           |
| `conventional-commit`                              | Writing commit messages.                                                                                                                                                     |
| `uv`, `pytest` (optional)                          | uv commands and Docker integration; pytest fixtures and FastAPI testing patterns.                                                                                            |


