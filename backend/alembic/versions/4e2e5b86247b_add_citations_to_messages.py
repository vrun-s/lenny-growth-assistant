"""add citations to messages

Revision ID: 4e2e5b86247b
Revises: 0365a449c420
Create Date: 2026-08-01 17:25:34.223524

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4e2e5b86247b'
down_revision: Union[str, Sequence[str], None] = '0365a449c420'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# NOTE: autogenerate also proposed dropping/recreating the `documents` table
# here — a false positive. `documents` lives under pgvector_store.py's own
# separate DeclarativeBase (see docs/design.md "Phase 4A: single `documents`
# table, not three"), which this migration's target_metadata (orm_models.Base)
# never sees, so autogenerate treats it as "removed". Stripped manually, same
# as the note left in 0365a449c420 warning about this exact false positive.


def upgrade() -> None:
    """Upgrade schema."""
    # server_default backfills existing rows (nullable=False on a populated
    # table); Message.citations' ORM-level default=list covers new inserts
    # going forward, same as this table's own artifact_id/created_at columns.
    op.add_column(
        "messages", sa.Column("citations", sa.JSON(), nullable=False, server_default="[]")
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("messages", "citations")
