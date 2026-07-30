"""create chat_sessions, artifacts, messages tables

Revision ID: f144a33b5570
Revises:
Create Date: 2026-07-30 13:59:19.648843

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f144a33b5570'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('chat_sessions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('title', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('artifacts',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('session_id', sa.Uuid(), nullable=False),
    sa.Column('type', sa.Enum('markdown', 'html', name='artifacttype'), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('messages',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('session_id', sa.Uuid(), nullable=False),
    sa.Column('role', sa.Enum('user', 'assistant', name='messagerole'), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('artifact_id', sa.Uuid(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['artifact_id'], ['artifacts.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('messages')
    op.drop_table('artifacts')
    op.drop_table('chat_sessions')
    sa.Enum(name='messagerole').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='artifacttype').drop(op.get_bind(), checkfirst=True)
