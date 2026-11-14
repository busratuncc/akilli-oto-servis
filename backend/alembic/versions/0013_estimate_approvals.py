"""Add estimates and privacy-conscious customer approvals.

Revision ID: 0013_estimates
Revises: 0012_inspections
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0013_estimates"
down_revision: Union[str, None] = "0012_inspections"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "estimates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("work_order_id", sa.Uuid(), sa.ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("converted_invoice_id", sa.Uuid(), sa.ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True),
        sa.Column("estimate_number", sa.String(length=40), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="draft"),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="TRY"),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("tax_rate", sa.Numeric(5, 2), nullable=False, server_default="20"),
        sa.Column("tax_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=False),
        sa.Column("approval_token_hash", sa.String(length=64), nullable=True),
        sa.Column("approval_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("response_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("estimate_number", name="uq_estimates_estimate_number"),
        sa.UniqueConstraint("approval_token_hash", name="uq_estimates_approval_token_hash"),
        sa.UniqueConstraint("converted_invoice_id", name="uq_estimates_converted_invoice_id"),
        sa.UniqueConstraint("work_order_id", "version", name="uq_estimates_work_order_version"),
        sa.CheckConstraint("version > 0", name="ck_estimates_version_positive"),
    )
    op.create_index("ix_estimates_owner_id", "estimates", ["owner_id"])
    op.create_index("ix_estimates_work_order_id", "estimates", ["work_order_id"])
    op.create_index("ix_estimates_estimate_number", "estimates", ["estimate_number"])
    op.create_index("ix_estimates_status", "estimates", ["status"])
    op.create_index("ix_estimates_valid_until", "estimates", ["valid_until"])

    op.create_table(
        "estimate_line_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("estimate_id", sa.Uuid(), sa.ForeignKey("estimates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("inventory_part_id", sa.Uuid(), sa.ForeignKey("inventory_parts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("item_type", sa.String(length=20), nullable=False),
        sa.Column("description", sa.String(length=240), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
    )
    op.create_index("ix_estimate_line_items_estimate_id", "estimate_line_items", ["estimate_id"])
    op.create_index("ix_estimate_line_items_inventory_part_id", "estimate_line_items", ["inventory_part_id"])


def downgrade() -> None:
    op.drop_index("ix_estimate_line_items_inventory_part_id", table_name="estimate_line_items")
    op.drop_index("ix_estimate_line_items_estimate_id", table_name="estimate_line_items")
    op.drop_table("estimate_line_items")
    op.drop_index("ix_estimates_valid_until", table_name="estimates")
    op.drop_index("ix_estimates_status", table_name="estimates")
    op.drop_index("ix_estimates_estimate_number", table_name="estimates")
    op.drop_index("ix_estimates_work_order_id", table_name="estimates")
    op.drop_index("ix_estimates_owner_id", table_name="estimates")
    op.drop_table("estimates")
