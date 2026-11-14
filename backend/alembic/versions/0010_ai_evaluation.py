"""Add AI retrieval benchmark queries and runs.

Revision ID: 0010_ai_evaluation
Revises: 0009_test_bank_3d
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0010_ai_evaluation"
down_revision: Union[str, None] = "0009_test_bank_3d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "evaluation_queries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expected_work_order_id", sa.Uuid(), sa.ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("dtc_code", sa.String(length=8), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_evaluation_queries_owner_id", "evaluation_queries", ["owner_id"])
    op.create_index("ix_evaluation_queries_expected_work_order_id", "evaluation_queries", ["expected_work_order_id"])
    op.create_index("ix_evaluation_queries_created_at", "evaluation_queries", ["created_at"])

    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("modes", sa.JSON(), nullable=False),
        sa.Column("top_k", sa.Integer(), nullable=False),
        sa.Column("query_count", sa.Integer(), nullable=False),
        sa.Column("metrics_json", sa.JSON(), nullable=False),
        sa.Column("details_json", sa.JSON(), nullable=False),
        sa.Column("best_mode", sa.String(length=24), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_evaluation_runs_owner_id", "evaluation_runs", ["owner_id"])
    op.create_index("ix_evaluation_runs_created_at", "evaluation_runs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_evaluation_runs_created_at", table_name="evaluation_runs")
    op.drop_index("ix_evaluation_runs_owner_id", table_name="evaluation_runs")
    op.drop_table("evaluation_runs")
    op.drop_index("ix_evaluation_queries_created_at", table_name="evaluation_queries")
    op.drop_index("ix_evaluation_queries_expected_work_order_id", table_name="evaluation_queries")
    op.drop_index("ix_evaluation_queries_owner_id", table_name="evaluation_queries")
    op.drop_table("evaluation_queries")
