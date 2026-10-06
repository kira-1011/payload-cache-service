from unittest.mock import MagicMock
from uuid import uuid7

from sqlmodel import Session

from cache_service.services.payloads import get_or_create_payload, get_payload


def test_spec_example_creates_payload_with_expected_output(
    session: Session, transform_spy: MagicMock
) -> None:
    payload, created = get_or_create_payload(
        session,
        ["first string", "second string", "third string"],
        ["other string", "another string", "last string"],
    )

    assert created
    assert payload.output == (
        "FIRST STRING, OTHER STRING, SECOND STRING, ANOTHER STRING, THIRD STRING, LAST STRING"
    )


def test_transformer_is_called_once_per_unique_string(
    session: Session, transform_spy: MagicMock
) -> None:
    get_or_create_payload(session, ["a", "b", "a"], ["b", "c", "a"])

    assert transform_spy.call_count == 3


def test_repeated_input_reuses_payload_without_transforming(
    session: Session, transform_spy: MagicMock
) -> None:
    first, _ = get_or_create_payload(session, ["a"], ["b"])
    transform_spy.reset_mock()

    second, created = get_or_create_payload(session, ["a"], ["b"])

    assert second.id == first.id
    assert not created
    transform_spy.assert_not_called()


def test_overlapping_input_transforms_only_new_strings(
    session: Session, transform_spy: MagicMock
) -> None:
    get_or_create_payload(session, ["a", "b"], ["c", "d"])
    transform_spy.reset_mock()

    payload, created = get_or_create_payload(session, ["a", "b"], ["c", "new"])

    assert created
    assert payload.output == "A, C, B, NEW"
    transform_spy.assert_called_once_with("new")


def test_get_payload_returns_stored_payload(session: Session) -> None:
    payload, _ = get_or_create_payload(session, ["a"], ["b"])

    assert get_payload(session, payload.id) == payload


def test_get_payload_returns_none_for_unknown_id(session: Session) -> None:
    assert get_payload(session, uuid7()) is None
