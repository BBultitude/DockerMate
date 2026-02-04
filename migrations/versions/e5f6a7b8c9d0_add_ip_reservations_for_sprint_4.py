"""Add ip_reservations table for Sprint 4 Task 4

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-02-04 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Guard: table may already exist if init_db() created it before migrations ran
    conn = op.get_bind()
    existing = conn.execute(sa.text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='ip_reservations'"
    )).fetchone()
    if existing:
        return

    op.create_table('ip_reservations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('network_id', sa.Integer(), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=False),
        sa.Column('container_id', sa.Integer(), nullable=True),
        sa.Column('range_name', sa.String(length=255), nullable=True),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['network_id'], ['networks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['container_id'], ['containers.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('network_id', 'ip_address', name='uq_reservation_network_ip'),
    )
    op.create_index(op.f('ix_ip_reservations_network_id'), 'ip_reservations', ['network_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_ip_reservations_network_id'), table_name='ip_reservations')
    op.drop_table('ip_reservations')
