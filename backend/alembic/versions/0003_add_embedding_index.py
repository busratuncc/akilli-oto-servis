"""Add a cosine HNSW index for semantic case search.

Revision ID: 0003_embedding_index
Revises: 0002_normalize_status
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0003_embedding_index"
down_revision: Union[str, None] = "0002_normalize_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_work_orders_embedding_hnsw "
        "ON work_orders USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_work_orders_embedding_hnsw")
