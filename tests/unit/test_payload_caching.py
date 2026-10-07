from unittest.mock import MagicMock
from uuid import uuid7

import pytest
from sqlmodel import Session, func, select

from cache_service import crud
from cache_service.models import Payload, TransformResult
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


def test_payload_stored_concurrently_is_returned_instead_of_failing(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    winner, _ = get_or_create_payload(session, ["a"], ["b"])
    # Race: our lookup ran before the concurrent request committed the same payload.
    monkeypatch.setattr(crud, "get_payload_by_input_hash", lambda *_: None)

    payload, created = get_or_create_payload(session, ["a"], ["b"])

    assert payload.id == winner.id
    assert not created
    assert session.exec(select(func.count()).select_from(Payload)).one() == 1


def test_transform_stored_concurrently_is_skipped_instead_of_failing(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    get_or_create_payload(session, ["a"], ["b"])
    # Race: our cache read ran before a concurrent request committed "a".
    monkeypatch.setattr(crud, "get_transform_results", lambda *_: [])

    payload, created = get_or_create_payload(session, ["a"], ["c"])

    assert created
    assert payload.output == "A, C"
    assert session.exec(select(func.count()).select_from(TransformResult)).one() == 3
