from uuid import uuid7

import limits
from fastapi.testclient import TestClient

from cache_service.config import settings


def test_requests_over_the_limit_get_429(client: TestClient) -> None:
    allowed = limits.parse(settings.rate_limit).amount
    url = f"/payload/{uuid7()}"

    statuses = {client.get(url).status_code for _ in range(allowed)}
    over_limit = client.get(url)

    assert statuses == {404}
    assert over_limit.status_code == 429
    assert "retry-after" in over_limit.headers
