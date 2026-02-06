"""add stack model for sprint 5 task 3

Revision ID: 47b1efcfdb62
Revises: 7cc7d289bcfc
Create Date: 2026-02-06 10:15:30.769402

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '47b1efcfdb62'
down_revision: Union[str, None] = '7cc7d289bcfc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Guard against double-creation (like Volume/Network migrations)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'stacks' in inspector.get_table_names():
        print("Table 'stacks' already exists, skipping creation")
        return

    # Create stacks table
    op.create_table(
        'stacks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('compose_yaml', sa.Text(), nullable=False),
        sa.Column('compose_version', sa.String(10)),
        sa.Column('status', sa.String(20), server_default='stopped', nullable=False),
        sa.Column('file_path', sa.String(500)),
        sa.Column('services_json', sa.Text()),
        sa.Column('container_ids_json', sa.Text()),
        sa.Column('network_names_json', sa.Text()),
        sa.Column('volume_names_json', sa.Text()),
        sa.Column('managed', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('auto_start', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('env_vars_json', sa.Text()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('deployed_at', sa.DateTime()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Create indexes
    op.create_index(op.f('ix_stacks_name'), 'stacks', ['name'])
    op.create_index(op.f('ix_stacks_status'), 'stacks', ['status'])
    op.create_index(op.f('ix_stacks_managed'), 'stacks', ['managed'])


def downgrade() -> None:
    op.drop_index(op.f('ix_stacks_managed'), 'stacks')
    op.drop_index(op.f('ix_stacks_status'), 'stacks')
    op.drop_index(op.f('ix_stacks_name'), 'stacks')
    op.drop_table('stacks')
