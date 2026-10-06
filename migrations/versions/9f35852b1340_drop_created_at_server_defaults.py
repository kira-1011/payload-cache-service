"""drop created_at server defaults

Revision ID: 9f35852b1340
Revises: d1884d4c678e
Create Date: 2026-10-07 01:00:09.940902

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9f35852b1340"
down_revision: str | Sequence[str] | None = "d1884d4c678e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TABLES = ("payload", "transform_result")


def upgrade() -> None:
    """Upgrade schema."""
    # created_at is now set by the application (SQLModel's UTC datetime handling).
    for table in TABLES:
        op.alter_column(table, "created_at", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    for table in TABLES:
        op.alter_column(table, "created_at", server_default=sa.text("now()"))
