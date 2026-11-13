"""Initial vehicle, work order and AI extraction schema."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "vehicles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("anonymous_code", sa.String(length=32), nullable=False, unique=True),
        sa.Column("brand", sa.String(length=80), nullable=False),
        sa.Column("model", sa.String(length=80), nullable=False),
        sa.Column("model_year", sa.Integer(), nullable=True),
        sa.Column("engine", sa.String(length=120), nullable=True),
        sa.Column("fuel_type", sa.String(length=40), nullable=True),
        sa.Column("mileage", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "work_orders",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("vehicle_id", sa.Uuid(), sa.ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_complaint", sa.Text(), nullable=False),
        sa.Column("symptoms", sa.Text(), nullable=True),
        sa.Column("diagnosis", sa.Text(), nullable=True),
        sa.Column("actions", sa.Text(), nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="draft"),
        sa.Column("approved_by_mechanic", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("voice_transcript", sa.Text(), nullable=True),
        sa.Column("search_text", sa.Text(), nullable=True),
        sa.Column("embedding", Vector(384), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_work_orders_vehicle_id", "work_orders", ["vehicle_id"])
    op.create_index("ix_work_orders_created_at", "work_orders", ["created_at"])

    op.create_table(
        "dtc_codes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("work_order_id", sa.Uuid(), sa.ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(length=8), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.create_index("ix_dtc_codes_code", "dtc_codes", ["code"])

    op.create_table(
        "ai_extractions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("work_order_id", sa.Uuid(), sa.ForeignKey("work_orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("extracted_json", sa.JSON(), nullable=False),
        sa.Column("confirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("ai_extractions")
    op.drop_index("ix_dtc_codes_code", table_name="dtc_codes")
    op.drop_table("dtc_codes")
    op.drop_index("ix_work_orders_created_at", table_name="work_orders")
    op.drop_index("ix_work_orders_vehicle_id", table_name="work_orders")
    op.drop_table("work_orders")
    op.drop_table("vehicles")
    op.execute("DROP EXTENSION IF EXISTS vector")

