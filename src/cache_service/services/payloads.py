import hashlib
import json
from collections.abc import Iterable, Sequence
from itertools import chain
from uuid import UUID

from sqlmodel import Session

from cache_service import crud
from cache_service.models import Payload, TransformResult
from cache_service.services import transformer


def interleave(list_1: Sequence[str], list_2: Sequence[str]) -> list[str]:
    """Alternate items from both lists: list_1[0], list_2[0], list_1[1], ..."""
    # strict=True: unequal lengths raise instead of silently dropping items.
    return list(chain.from_iterable(zip(list_1, list_2, strict=True)))


def hash_text(text: str) -> str:
    """Return the SHA-256 hex digest of the text."""
    return hashlib.sha256(text.encode()).hexdigest()


def hash_payload_input(list_1: Sequence[str], list_2: Sequence[str]) -> str:
    """Return the SHA-256 hex digest of both lists serialized as nested JSON."""
    # Nested JSON keeps list boundaries and escapes commas, so distinct inputs can't collide.
    return hash_text(json.dumps([list_1, list_2]))


def transform_with_cache(session: Session, texts: Iterable[str]) -> dict[str, str]:
    """Map each distinct text to its transformed value, transforming only cache misses."""
    texts_by_hash = {hash_text(text): text for text in set(texts)}
    cached = crud.get_transform_results(session, list(texts_by_hash))
    results = {texts_by_hash[row.input_hash]: row.output_text for row in cached}

    for input_hash, text in texts_by_hash.items():
        if text not in results:
            output_text = transformer.transform(text)
            # Added, not committed: the caller commits once for the whole request.
            session.add(TransformResult(input_hash=input_hash, output_text=output_text))
            results[text] = output_text
    return results


def get_or_create_payload(
    session: Session, list_1: Sequence[str], list_2: Sequence[str]
) -> tuple[Payload, bool]:
    """Return the payload for this input and whether it was just created."""
    input_hash = hash_payload_input(list_1, list_2)
    existing = crud.get_payload_by_input_hash(session, input_hash)
    if existing is not None:
        return existing, False

    transformed = transform_with_cache(session, chain(list_1, list_2))
    output = ", ".join(
        interleave(
            [transformed[text] for text in list_1],
            [transformed[text] for text in list_2],
        )
    )
    payload = Payload(input_hash=input_hash, output=output)
    session.add(payload)
    # One commit, so the payload and its new cache rows are saved together or not at all.
    session.commit()
    session.refresh(payload)
    return payload, True


def get_payload(session: Session, payload_id: UUID) -> Payload | None:
    """Return the payload with this id, or None if it doesn't exist."""
    return crud.get_payload_by_id(session, payload_id)
