"""add health monitoring models for sprint 5 tasks 5-7

Revision ID: 5c8b90979ce6
Revises: 47b1efcfdb62
Create Date: 2026-02-06 20:51:02.046018

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c8b90979ce6'
down_revision: Union[str, None] = '47b1efcfdb62'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create health_metrics and container_health tables for Sprint 5 Tasks 5-7.

    Tables:
        - health_metrics: System-wide resource usage over time
        - container_health: Per-container resource metrics

    Both tables indexed by timestamp for efficient time-range queries.
    """
    # Guard against double-creation
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Create health_metrics table
    if 'health_metrics' not in inspector.get_table_names():
        op.create_table(
            'health_metrics',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('timestamp', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('cpu_usage_percent', sa.Float()),
            sa.Column('memory_usage_percent', sa.Float()),
            sa.Column('memory_used_bytes', sa.BigInteger()),
            sa.Column('memory_total_bytes', sa.BigInteger()),
            sa.Column('disk_usage_percent', sa.Float()),
            sa.Column('disk_used_bytes', sa.BigInteger()),
            sa.Column('disk_total_bytes', sa.BigInteger()),
            sa.Column('containers_running', sa.Integer()),
            sa.Column('containers_stopped', sa.Integer()),
            sa.Column('containers_total', sa.Integer()),
            sa.Column('images_total', sa.Integer()),
            sa.Column('networks_total', sa.Integer()),
            sa.Column('volumes_total', sa.Integer()),
            sa.Column('overall_status', sa.String(20)),
            sa.Column('warning_count', sa.Integer(), server_default='0'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_health_metrics_timestamp', 'health_metrics', ['timestamp'])
        print("✓ Created health_metrics table")
    else:
        print("Table 'health_metrics' already exists, skipping creation")

    # Create container_health table
    if 'container_health' not in inspector.get_table_names():
        op.create_table(
            'container_health',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('timestamp', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('container_id', sa.String(64), nullable=False),
            sa.Column('container_name', sa.String(255), nullable=False),
            sa.Column('cpu_usage_percent', sa.Float()),
            sa.Column('memory_usage_bytes', sa.BigInteger()),
            sa.Column('memory_limit_bytes', sa.BigInteger()),
            sa.Column('memory_usage_percent', sa.Float()),
            sa.Column('network_rx_bytes', sa.BigInteger()),
            sa.Column('network_tx_bytes', sa.BigInteger()),
            sa.Column('block_read_bytes', sa.BigInteger()),
            sa.Column('block_write_bytes', sa.BigInteger()),
            sa.Column('status', sa.String(20)),
            sa.Column('health_status', sa.String(20)),
            sa.Column('exit_code', sa.Integer()),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_container_health_container_id', 'container_health', ['container_id'])
        op.create_index('ix_container_health_timestamp', 'container_health', ['timestamp'])
        print("✓ Created container_health table")
    else:
        print("Table 'container_health' already exists, skipping creation")


def downgrade() -> None:
    """Remove health monitoring tables"""
    # Drop container_health table and indexes
    op.drop_index('ix_container_health_timestamp', 'container_health')
    op.drop_index('ix_container_health_container_id', 'container_health')
    op.drop_table('container_health')

    # Drop health_metrics table and indexes
    op.drop_index('ix_health_metrics_timestamp', 'health_metrics')
    op.drop_table('health_metrics')
