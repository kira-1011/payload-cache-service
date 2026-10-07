import pytest
from pydantic import ValidationError

from cache_service.config import Settings


def test_invalid_rate_limit_is_rejected_at_startup() -> None:
    with pytest.raises(ValidationError):
        Settings(database_url="sqlite://", rate_limit="lots/minute")
