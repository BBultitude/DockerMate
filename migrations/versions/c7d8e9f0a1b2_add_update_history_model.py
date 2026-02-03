"""Add update_history model for Sprint 3

Revision ID: c7d8e9f0a1b2
Revises: a163efae8eca
Create Date: 2026-02-03 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7d8e9f0a1b2'
down_revision: Union[str, None] = 'a163efae8eca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Guard: table may already exist if init_db() created it before migrations ran
    conn = op.get_bind()
    existing = conn.execute(sa.text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='update_history'"
    )).fetchone()
    if existing:
        return

    op.create_table('update_history',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('container_id', sa.String(length=64), nullable=False),
    sa.Column('container_name', sa.String(length=255), nullable=False),
    sa.Column('old_image', sa.String(length=512), nullable=False),
    sa.Column('new_image', sa.String(length=512), nullable=False),
    sa.Column('old_digest', sa.String(length=255), nullable=True),
    sa.Column('new_digest', sa.String(length=255), nullable=True),
    sa.Column('status', sa.String(length=32), nullable=False, server_default='success'),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_update_history_container_id'), 'update_history', ['container_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_update_history_container_id'), table_name='update_history')
    op.drop_table('update_history')
