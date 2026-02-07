"""add previous_tag to images

Revision ID: 6d7e8f9a0b1c
Revises: 5c8b90979ce6
Create Date: 2026-02-07 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6d7e8f9a0b1c'
down_revision: Union[str, None] = '5c8b90979ce6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add previous_tag column to images table for dangling image tracking."""
    # Add previous_tag column
    op.add_column('images',
        sa.Column('previous_tag', sa.String(length=255), nullable=True,
                  comment='Tag before becoming dangling (<none>)')
    )


def downgrade() -> None:
    """Remove previous_tag column from images table."""
    op.drop_column('images', 'previous_tag')
