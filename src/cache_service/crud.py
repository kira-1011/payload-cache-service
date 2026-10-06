from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.dialects import postgresql, sqlite
from sqlmodel import Session, SQLModel, col, select

from cache_service.models import Payload, TransformResult


def get_payload_by_id(session: Session, payload_id: UUID) -> Payload | None:
    """Return the payload with this id, or None if it doesn't exist."""
    return session.get(Payload, payload_id)


def get_payload_by_input_hash(session: Session, input_hash: str) -> Payload | None:
    """Return the payload generated from the input with this hash, or None."""
    return session.exec(
        select(Payload).where(col(Payload.input_hash) == input_hash)
    ).first()


def get_transform_results(
    session: Session, input_hashes: Sequence[str]
) -> Sequence[TransformResult]:
    """Return the cached transform results for these input hashes in a single query."""
    return session.exec(
        select(TransformResult).where(col(TransformResult.input_hash).in_(input_hashes))
    ).all()


def insert_transform_results(
    session: Session, results: Sequence[TransformResult]
) -> None:
    """Insert the results, skipping any input hash a concurrent request inserted first."""
    if not results:
        return
    # Sorted, so concurrent transactions lock the same keys in the same order (no deadlock).
    rows = [
        result.model_dump() for result in sorted(results, key=lambda r: r.input_hash)
    ]
    session.exec(
        insert_for(session, TransformResult)
        .values(rows)
        .on_conflict_do_nothing(index_elements=["input_hash"])
    )


def insert_payload(session: Session, payload: Payload) -> tuple[Payload, bool]:
    """Insert the payload unless one with its input hash exists; return the stored one.

    The flag is True when this call inserted it, False when a concurrent request did.
    """
    inserted = session.exec(
        insert_for(session, Payload)
        .values(payload.model_dump())
        .on_conflict_do_nothing(index_elements=["input_hash"])
        .returning(col(Payload.id))
    ).first()
    stored = session.exec(
        select(Payload).where(col(Payload.input_hash) == payload.input_hash)
    ).one()
    return stored, inserted is not None


def insert_for(
    session: Session, model: type[SQLModel]
) -> postgresql.Insert | sqlite.Insert:
    """Return an INSERT for the session's database, which supports ON CONFLICT."""
    # Production runs on Postgres, tests on SQLite; both support ON CONFLICT DO NOTHING.
    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        return postgresql.insert(model)
    if dialect == "sqlite":
        return sqlite.insert(model)
    raise NotImplementedError(f"ON CONFLICT inserts are not implemented for {dialect}")
