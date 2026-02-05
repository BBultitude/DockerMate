"""Add network model for Sprint 4

Revision ID: d4e5f6a7b8c9
Revises: c7d8e9f0a1b2
Create Date: 2026-02-03 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c7d8e9f0a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Guard: table may already exist if init_db() created it before migrations ran
    conn = op.get_bind()
    existing = conn.execute(sa.text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='networks'"
    )).fetchone()
    if existing:
        return

    op.create_table('networks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('network_id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('driver', sa.String(length=50), nullable=False, server_default='bridge'),
        sa.Column('subnet', sa.String(length=45), nullable=True),
        sa.Column('gateway', sa.String(length=45), nullable=True),
        sa.Column('ip_range', sa.String(length=45), nullable=True),
        sa.Column('purpose', sa.String(length=255), nullable=True),
        sa.Column('managed', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_networks_network_id'), 'networks', ['network_id'], unique=True)
    op.create_index(op.f('ix_networks_name'), 'networks', ['name'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_networks_name'), table_name='networks')
    op.drop_index(op.f('ix_networks_network_id'), table_name='networks')
    op.drop_table('networks')
