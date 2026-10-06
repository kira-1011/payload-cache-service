from unittest.mock import MagicMock
from uuid import uuid7

from fastapi.testclient import TestClient

SPEC_BODY = {
    "list_1": ["first string", "second string", "third string"],
    "list_2": ["other string", "another string", "last string"],
}


def test_create_then_read_returns_spec_output(client: TestClient) -> None:
    created = client.post("/payload", json=SPEC_BODY)

    assert created.status_code == 201
    payload_id = created.json()["id"]
    assert created.headers["location"].endswith(f"/payload/{payload_id}")

    read = client.get(f"/payload/{payload_id}")

    assert read.status_code == 200
    assert read.json() == {
        "output": "FIRST STRING, OTHER STRING, SECOND STRING, ANOTHER STRING, "
        "THIRD STRING, LAST STRING"
    }


def test_repeated_post_reuses_payload_without_transforming(
    client: TestClient, transform_spy: MagicMock
) -> None:
    first = client.post("/payload", json=SPEC_BODY)
    transform_spy.reset_mock()

    second = client.post("/payload", json=SPEC_BODY)

    assert second.status_code == 200
    assert second.json() == {
        "id": first.json()["id"],
        "message": "Payload already exists",
    }
    transform_spy.assert_not_called()


def test_overlapping_post_transforms_only_new_strings(
    client: TestClient, transform_spy: MagicMock
) -> None:
    client.post("/payload", json={"list_1": ["a", "b"], "list_2": ["c", "d"]})
    transform_spy.reset_mock()

    response = client.post(
        "/payload", json={"list_1": ["a", "new"], "list_2": ["c", "d"]}
    )

    assert response.status_code == 201
    transform_spy.assert_called_once_with("new")


def test_invalid_body_returns_422(client: TestClient) -> None:
    response = client.post("/payload", json={"list_1": ["a", "b"], "list_2": ["c"]})

    assert response.status_code == 422


def test_unknown_id_returns_404(client: TestClient) -> None:
    response = client.get(f"/payload/{uuid7()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Payload not found"}


def test_malformed_id_returns_422(client: TestClient) -> None:
    assert client.get("/payload/not-a-uuid").status_code == 422
