import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from cache_service.models import Payload


def test_payload_input_hash_is_unique(session: Session) -> None:
    session.add(Payload(input_hash="a" * 64, output="A"))
    session.commit()

    session.add(Payload(input_hash="a" * 64, output="A"))
    with pytest.raises(IntegrityError):
        session.commit()


def test_created_at_is_set_by_the_database(session: Session) -> None:
    payload = Payload(input_hash="a" * 64, output="A")
    session.add(payload)
    session.commit()
    session.refresh(payload)

    assert payload.created_at is not None
