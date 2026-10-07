import os
from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from cache_service import models  # noqa: F401  (registers the tables)
from cache_service.services import transformer

# The app reads DATABASE_URL at import. Tests replace the session, so the URL is never used.
os.environ.setdefault("DATABASE_URL", "sqlite://")


@pytest.fixture
def session() -> Iterator[Session]:
    """Yield a session on a fresh in-memory SQLite database with all tables created."""
    # StaticPool shares one connection, so the in-memory database outlives each session.
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def transform_spy() -> Iterator[MagicMock]:
    """Wrap the real transformer so tests can count its calls."""
    with patch.object(transformer, "transform", wraps=transformer.transform) as spy:
        yield spy


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    """Yield a test client whose requests use the in-memory SQLite session."""
    # Imported here so DATABASE_URL is already set when the app reads its settings.
    from cache_service.db import get_session
    from cache_service.main import app

    app.dependency_overrides[get_session] = lambda: session
    # Rate-limit counters live in memory for the whole test run; start each test at zero.
    app.state.limiter.reset()
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
