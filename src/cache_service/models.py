from datetime import UTC, datetime
from uuid import UUID, uuid7

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(UTC)


class TransformResult(SQLModel, table=True):
    """Cached transformer output, keyed by the SHA-256 of its input string."""

    __tablename__ = "transform_result"

    input_hash: str = Field(primary_key=True, max_length=64)
    output_text: str
    created_at: datetime = Field(default_factory=utc_now)


class Payload(SQLModel, table=True):
    """Generated payload output, stored once per distinct input."""

    id: UUID = Field(default_factory=uuid7, primary_key=True)
    input_hash: str = Field(unique=True, max_length=64)
    output: str
    created_at: datetime = Field(default_factory=utc_now)
