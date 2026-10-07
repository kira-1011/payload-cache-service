import hashlib

import pytest

from cache_service.services.payloads import hash_payload_input, interleave


def test_interleave_alternates_items() -> None:
    assert interleave(["a1", "a2"], ["b1", "b2"]) == ["a1", "b1", "a2", "b2"]


def test_interleave_rejects_unequal_lengths() -> None:
    with pytest.raises(ValueError):
        interleave(["a1", "a2"], ["b1"])


def test_hash_payload_input_is_sha256_of_nested_json() -> None:
    expected = hashlib.sha256(b'[["a", "b"], ["c", "d"]]').hexdigest()

    assert hash_payload_input(["a", "b"], ["c", "d"]) == expected


@pytest.mark.parametrize(
    ("other_list_1", "other_list_2"),
    [
        (["c", "d"], ["a", "b"]),  # lists swapped
        (["b", "a"], ["c", "d"]),  # order within a list
        (["a, b"], ["c, d"]),  # commas inside strings
    ],
)
def test_hash_payload_input_distinguishes_inputs(
    other_list_1: list[str], other_list_2: list[str]
) -> None:
    assert hash_payload_input(["a", "b"], ["c", "d"]) != hash_payload_input(
        other_list_1, other_list_2
    )
