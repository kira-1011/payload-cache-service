import pytest

from cache_service.services.payloads import interleave
from cache_service.services.transformer import transform


def test_spec_example_produces_expected_output() -> None:
    list_1 = ["first string", "second string", "third string"]
    list_2 = ["other string", "another string", "last string"]

    output = ", ".join(
        interleave([transform(s) for s in list_1], [transform(s) for s in list_2])
    )

    assert output == (
        "FIRST STRING, OTHER STRING, SECOND STRING, ANOTHER STRING, THIRD STRING, LAST STRING"
    )


def test_interleave_alternates_items() -> None:
    assert interleave(["a1", "a2"], ["b1", "b2"]) == ["a1", "b1", "a2", "b2"]


def test_interleave_rejects_unequal_lengths() -> None:
    with pytest.raises(ValueError):
        interleave(["a1", "a2"], ["b1"])
