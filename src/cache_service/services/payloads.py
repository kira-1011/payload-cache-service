import hashlib
import json
from collections.abc import Sequence
from itertools import chain


def interleave(list_1: Sequence[str], list_2: Sequence[str]) -> list[str]:
    """Alternate items from both lists: list_1[0], list_2[0], list_1[1], ..."""
    # strict=True: unequal lengths raise instead of silently dropping items.
    return list(chain.from_iterable(zip(list_1, list_2, strict=True)))


def hash_payload_input(list_1: Sequence[str], list_2: Sequence[str]) -> str:
    """Return the SHA-256 hex digest of both lists serialized as nested JSON."""
    # Nested JSON keeps list boundaries and escapes commas, so distinct inputs can't collide.
    serialized = json.dumps([list_1, list_2])
    return hashlib.sha256(serialized.encode()).hexdigest()
