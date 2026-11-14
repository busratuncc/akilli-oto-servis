"""Add digital vehicle inspection reports.

Revision ID: 0012_inspections
Revises: 0011_appointments
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0012_inspections"
down_revision: Union[str, None] = "0011_appointments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "inspection_reports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("work_order_id", sa.Uuid(), sa.ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="draft"),
        sa.Column("odometer", sa.Integer(), nullable=True),
        sa.Column("technician_name", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("mechanic_approved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("work_order_id", name="uq_inspection_reports_work_order_id"),
        sa.CheckConstraint("odometer IS NULL OR odometer >= 0", name="ck_inspection_odometer_nonnegative"),
    )
    op.create_index("ix_inspection_reports_owner_id", "inspection_reports", ["owner_id"])
    op.create_index("ix_inspection_reports_work_order_id", "inspection_reports", ["work_order_id"])
    op.create_index("ix_inspection_reports_status", "inspection_reports", ["status"])

    op.create_table(
        "inspection_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("report_id", sa.Uuid(), sa.ForeignKey("inspection_reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("item_key", sa.String(length=80), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column("condition", sa.String(length=24), nullable=False, server_default="not_checked"),
        sa.Column("measurement", sa.String(length=80), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.UniqueConstraint("report_id", "item_key", name="uq_inspection_items_report_key"),
    )
    op.create_index("ix_inspection_items_report_id", "inspection_items", ["report_id"])
    op.create_index("ix_inspection_items_category", "inspection_items", ["category"])
    op.create_index("ix_inspection_items_condition", "inspection_items", ["condition"])


def downgrade() -> None:
    op.drop_index("ix_inspection_items_condition", table_name="inspection_items")
    op.drop_index("ix_inspection_items_category", table_name="inspection_items")
    op.drop_index("ix_inspection_items_report_id", table_name="inspection_items")
    op.drop_table("inspection_items")
    op.drop_index("ix_inspection_reports_status", table_name="inspection_reports")
    op.drop_index("ix_inspection_reports_work_order_id", table_name="inspection_reports")
    op.drop_index("ix_inspection_reports_owner_id", table_name="inspection_reports")
    op.drop_table("inspection_reports")
