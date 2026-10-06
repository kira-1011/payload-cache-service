from typing import Any

import pytest
from pydantic import ValidationError

from cache_service.schemas import MAX_ITEMS, MAX_STRING_LENGTH, PayloadCreate


def test_payload_create_accepts_equal_length_lists() -> None:
    body = PayloadCreate(list_1=["a", "b"], list_2=["c", "d"])

    assert body.list_1 == ["a", "b"]


@pytest.mark.parametrize(
    "body",
    [
        {"list_1": ["a", "b"], "list_2": ["c"]},  # unequal lengths
        {"list_1": [], "list_2": []},  # empty lists
        {"list_1": ["a"]},  # missing field
        {"list_1": [1], "list_2": [2]},  # not strings
        {
            "list_1": ["a"] * (MAX_ITEMS + 1),
            "list_2": ["b"] * (MAX_ITEMS + 1),
        },  # too many
        {"list_1": ["a" * (MAX_STRING_LENGTH + 1)], "list_2": ["b"]},  # string too long
    ],
)
def test_payload_create_rejects_invalid_input(body: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        PayloadCreate.model_validate(body)
