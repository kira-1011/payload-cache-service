from uuid import uuid7

import pytest
from fastapi.testclient import TestClient

from cache_service.config import settings

BODY = {"list_1": ["a"], "list_2": ["b"]}


@pytest.fixture
def low_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "rate_limit", "2/minute")


@pytest.mark.usefixtures("low_limit")
def test_get_over_the_limit_gets_429(client: TestClient) -> None:
    url = f"/payload/{uuid7()}"

    statuses = [client.get(url).status_code for _ in range(3)]

    assert statuses == [404, 404, 429]


@pytest.mark.usefixtures("low_limit")
def test_post_over_the_limit_gets_429_with_retry_after(client: TestClient) -> None:
    responses = [client.post("/payload", json=BODY) for _ in range(3)]

    assert [r.status_code for r in responses] == [201, 200, 429]
    assert "retry-after" in responses[-1].headers
