"""Add local test-bank 3D Secure challenges.

Revision ID: 0009_test_bank_3d
Revises: 0008_inventory_module
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0009_test_bank_3d"
down_revision: Union[str, None] = "0008_inventory_module"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "card_payment_challenges",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), sa.ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("card_last4", sa.String(length=4), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_card_payment_challenges_owner_id", "card_payment_challenges", ["owner_id"])
    op.create_index("ix_card_payment_challenges_invoice_id", "card_payment_challenges", ["invoice_id"])
    op.create_index("ix_card_payment_challenges_token_hash", "card_payment_challenges", ["token_hash"], unique=True)
    op.create_index("ix_card_payment_challenges_status", "card_payment_challenges", ["status"])
    op.create_index("ix_card_payment_challenges_expires_at", "card_payment_challenges", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_card_payment_challenges_expires_at", table_name="card_payment_challenges")
    op.drop_index("ix_card_payment_challenges_status", table_name="card_payment_challenges")
    op.drop_index("ix_card_payment_challenges_token_hash", table_name="card_payment_challenges")
    op.drop_index("ix_card_payment_challenges_invoice_id", table_name="card_payment_challenges")
    op.drop_index("ix_card_payment_challenges_owner_id", table_name="card_payment_challenges")
    op.drop_table("card_payment_challenges")
