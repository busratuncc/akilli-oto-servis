"""Track work-order updates and completion times for operational analytics.

Revision ID: 0014_order_times
Revises: 0013_estimates
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0014_order_times"
down_revision: Union[str, None] = "0013_estimates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "work_orders",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
    )
    op.add_column(
        "work_orders",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("UPDATE work_orders SET updated_at = created_at")
    op.alter_column("work_orders", "updated_at", nullable=False)
    op.create_index("ix_work_orders_completed_at", "work_orders", ["completed_at"])


def downgrade() -> None:
    op.drop_index("ix_work_orders_completed_at", table_name="work_orders")
    op.drop_column("work_orders", "completed_at")
    op.drop_column("work_orders", "updated_at")
