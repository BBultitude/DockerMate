"""add volume model for sprint 5 task 1

Revision ID: 7cc7d289bcfc
Revises: e5f6a7b8c9d0
Create Date: 2026-02-06 19:07:15.623793

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7cc7d289bcfc'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Guard: table may already exist if init_db() created it before migrations ran
    conn = op.get_bind()
    existing = conn.execute(sa.text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='volumes'"
    )).fetchone()
    if existing:
        return

    op.create_table('volumes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('volume_id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('driver', sa.String(length=50), nullable=False, server_default='local'),
        sa.Column('mount_point', sa.String(length=500), nullable=True),
        sa.Column('labels_json', sa.Text(), nullable=True),
        sa.Column('options_json', sa.Text(), nullable=True),
        sa.Column('size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('managed', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_volumes_volume_id'), 'volumes', ['volume_id'], unique=True)
    op.create_index(op.f('ix_volumes_name'), 'volumes', ['name'], unique=True)
    op.create_index(op.f('ix_volumes_driver'), 'volumes', ['driver'], unique=False)
    op.create_index(op.f('ix_volumes_managed'), 'volumes', ['managed'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_volumes_managed'), table_name='volumes')
    op.drop_index(op.f('ix_volumes_driver'), table_name='volumes')
    op.drop_index(op.f('ix_volumes_name'), table_name='volumes')
    op.drop_index(op.f('ix_volumes_volume_id'), table_name='volumes')
    op.drop_table('volumes')
