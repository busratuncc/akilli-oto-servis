"""Add account-scoped inventory and stock movements.

Revision ID: 0008_inventory_module
Revises: 0007_finance_module
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0008_inventory_module"
down_revision: Union[str, None] = "0007_finance_module"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "inventory_parts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sku", sa.String(length=48), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("brand", sa.String(length=100), nullable=True),
        sa.Column("category", sa.String(length=80), nullable=True),
        sa.Column("unit", sa.String(length=20), nullable=False, server_default="piece"),
        sa.Column("stock_quantity", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("low_stock_threshold", sa.Numeric(12, 2), nullable=False, server_default="1"),
        sa.Column("purchase_price", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("sale_price", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("owner_id", "sku", name="uq_inventory_parts_owner_sku"),
    )
    op.create_index("ix_inventory_parts_owner_id", "inventory_parts", ["owner_id"])
    op.create_index("ix_inventory_parts_active", "inventory_parts", ["active"])

    op.create_table(
        "stock_movements",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("part_id", sa.Uuid(), sa.ForeignKey("inventory_parts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("movement_type", sa.String(length=24), nullable=False),
        sa.Column("quantity_delta", sa.Numeric(12, 2), nullable=False),
        sa.Column("balance_after", sa.Numeric(12, 2), nullable=False),
        sa.Column("reference_type", sa.String(length=32), nullable=True),
        sa.Column("reference_id", sa.Uuid(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_stock_movements_part_id", "stock_movements", ["part_id"])
    op.create_index("ix_stock_movements_movement_type", "stock_movements", ["movement_type"])
    op.create_index("ix_stock_movements_created_at", "stock_movements", ["created_at"])

    op.add_column("invoice_line_items", sa.Column("inventory_part_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_invoice_line_items_inventory_part",
        "invoice_line_items",
        "inventory_parts",
        ["inventory_part_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_invoice_line_items_inventory_part_id", "invoice_line_items", ["inventory_part_id"])


def downgrade() -> None:
    op.drop_index("ix_invoice_line_items_inventory_part_id", table_name="invoice_line_items")
    op.drop_constraint("fk_invoice_line_items_inventory_part", "invoice_line_items", type_="foreignkey")
    op.drop_column("invoice_line_items", "inventory_part_id")
    op.drop_index("ix_stock_movements_created_at", table_name="stock_movements")
    op.drop_index("ix_stock_movements_movement_type", table_name="stock_movements")
    op.drop_index("ix_stock_movements_part_id", table_name="stock_movements")
    op.drop_table("stock_movements")
    op.drop_index("ix_inventory_parts_active", table_name="inventory_parts")
    op.drop_index("ix_inventory_parts_owner_id", table_name="inventory_parts")
    op.drop_table("inventory_parts")
