"""Normalize legacy work order status values.

Revision ID: 0002_normalize_status
Revises: 0001_initial
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0002_normalize_status"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE work_orders SET status = 'completed' WHERE status = 'confirmed'")


def downgrade() -> None:
    # Normalized values are kept because old and newly completed records cannot
    # be distinguished safely after the migration.
    pass
