"""add_barcode_column_to_order_items

Revision ID: bfcf32ef46ea
Revises: a6df19851eb7
Create Date: 2025-05-17 16:54:44.470727

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bfcf32ef46ea'
down_revision: Union[str, None] = 'a6df19851eb7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('order_items', sa.Column('barcode', sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('order_items', 'barcode')
