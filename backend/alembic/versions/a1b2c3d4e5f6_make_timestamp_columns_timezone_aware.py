"""make timestamp columns timezone-aware

Revision ID: a1b2c3d4e5f6
Revises: 4e2e5b86247b
Create Date: 2026-08-02 20:00:00.000000

Existing columns are TIMESTAMP WITHOUT TIME ZONE, populated exclusively via
_utcnow() (orm_models.py), so every stored value already *is* a UTC wall-clock
reading — it's just missing the marker. Without that marker, FastAPI/Pydantic
serializes it without a timezone offset, and the browser's `new Date(iso)`
then parses it as local time instead of UTC, showing raw UTC clock time
mislabeled as local (e.g. an IST user sees a time ~5:30 behind their clock).

`USING col AT TIME ZONE 'UTC'` tells Postgres to reinterpret the existing
naive values as UTC instants (not the session's local timezone, which is the
default and wrong interpretation here) while converting to timestamptz.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '4e2e5b86247b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COLUMNS = [
    ("chat_sessions", "created_at"),
    ("chat_sessions", "updated_at"),
    ("artifacts", "created_at"),
    ("messages", "created_at"),
]


def upgrade() -> None:
    for table, column in _COLUMNS:
        op.alter_column(
            table,
            column,
            type_=sa.DateTime(timezone=True),
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
            nullable=False,
        )


def downgrade() -> None:
    for table, column in _COLUMNS:
        op.alter_column(
            table,
            column,
            type_=sa.DateTime(timezone=False),
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
            nullable=False,
        )
