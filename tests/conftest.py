from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from cache_service import models  # noqa: F401  (registers the tables)
from cache_service.services import transformer


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
