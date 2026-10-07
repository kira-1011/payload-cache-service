from sqlmodel import Session, func, select

from cache_service import crud
from cache_service.models import Payload, TransformResult


def test_insert_payload_reports_creation(session: Session) -> None:
    payload, created = crud.insert_payload(session, Payload(input_hash="h", output="A"))

    assert created
    assert payload.output == "A"


def test_insert_payload_returns_the_stored_row_on_conflict(session: Session) -> None:
    # Another request stored the same input first (e.g. after both missed the lookup).
    winner, _ = crud.insert_payload(session, Payload(input_hash="h", output="A"))
    session.commit()

    payload, created = crud.insert_payload(session, Payload(input_hash="h", output="A"))

    assert payload.id == winner.id
    assert not created
    assert session.exec(select(func.count()).select_from(Payload)).one() == 1


def test_insert_transform_results_skips_rows_that_already_exist(
    session: Session,
) -> None:
    crud.insert_transform_results(
        session, [TransformResult(input_hash="a", output_text="A")]
    )
    session.commit()

    crud.insert_transform_results(
        session,
        [
            TransformResult(input_hash="a", output_text="A"),
            TransformResult(input_hash="b", output_text="B"),
        ],
    )

    stored = session.exec(select(TransformResult)).all()
    assert sorted(row.input_hash for row in stored) == ["a", "b"]
