from collections.abc import Iterator

from sqlmodel import Session, create_engine

from cache_service.config import settings

engine = create_engine(settings.database_url)


def get_session() -> Iterator[Session]:
    """Yield a database session that is closed once the caller is done."""
    with Session(engine) as session:
        yield session
