from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, col, select

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
