"""Add account data ownership and audit trail.

Revision ID: 0006_data_ownership_audit
Revises: 0005_user_registration
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006_data_ownership_audit"
down_revision: Union[str, None] = "0005_user_registration"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("vehicles", sa.Column("owner_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_vehicles_owner_id_users",
        "vehicles",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_vehicles_owner_id", "vehicles", ["owner_id"])
    op.drop_constraint("vehicles_anonymous_code_key", "vehicles", type_="unique")
    op.create_index("ix_vehicles_anonymous_code", "vehicles", ["anonymous_code"])
    op.create_unique_constraint(
        "uq_vehicles_owner_code", "vehicles", ["owner_id", "anonymous_code"]
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("entity_type", sa.String(length=40), nullable=True),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("event_data", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_audit_events_user_id", "audit_events", ["user_id"])
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_created_at", table_name="audit_events")
    op.drop_index("ix_audit_events_event_type", table_name="audit_events")
    op.drop_index("ix_audit_events_user_id", table_name="audit_events")
    op.drop_table("audit_events")

    op.drop_constraint("uq_vehicles_owner_code", "vehicles", type_="unique")
    op.drop_index("ix_vehicles_anonymous_code", table_name="vehicles")
    op.create_unique_constraint(
        "vehicles_anonymous_code_key", "vehicles", ["anonymous_code"]
    )
    op.drop_index("ix_vehicles_owner_id", table_name="vehicles")
    op.drop_constraint("fk_vehicles_owner_id_users", "vehicles", type_="foreignkey")
    op.drop_column("vehicles", "owner_id")
