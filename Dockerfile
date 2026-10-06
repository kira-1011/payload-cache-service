# syntax=docker/dockerfile:1

# Both stages share a base image so the copied .venv finds the same interpreter path.
FROM python:3.14-slim-trixie AS builder
COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Dependencies get their own layer, so code changes don't reinstall them.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked


FROM python:3.14-slim-trixie

RUN groupadd --system --gid 999 app \
 && useradd --system --gid 999 --uid 999 --create-home app

# Owned by root: the app user can run the code but not modify it.
COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

USER app
WORKDIR /app
EXPOSE 8000

# Exec form so shutdown signals reach the app.
CMD ["fastapi", "run", "--port", "8000"]
