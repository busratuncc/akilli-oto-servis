"""Add workshop appointments and maintenance reminders.

Revision ID: 0011_appointments
Revises: 0010_ai_evaluation
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0011_appointments"
down_revision: Union[str, None] = "0010_ai_evaluation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "appointments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vehicle_id", sa.Uuid(), sa.ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("service_type", sa.String(length=120), nullable=False),
        sa.Column("customer_complaint", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="scheduled"),
        sa.Column("assigned_technician", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_appointments_owner_id", "appointments", ["owner_id"])
    op.create_index("ix_appointments_vehicle_id", "appointments", ["vehicle_id"])
    op.create_index("ix_appointments_scheduled_start", "appointments", ["scheduled_start"])
    op.create_index("ix_appointments_status", "appointments", ["status"])

    op.create_table(
        "maintenance_reminders",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vehicle_id", sa.Uuid(), sa.ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("due_mileage", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("due_date IS NOT NULL OR due_mileage IS NOT NULL", name="ck_reminder_has_due_target"),
    )
    op.create_index("ix_maintenance_reminders_owner_id", "maintenance_reminders", ["owner_id"])
    op.create_index("ix_maintenance_reminders_vehicle_id", "maintenance_reminders", ["vehicle_id"])
    op.create_index("ix_maintenance_reminders_due_date", "maintenance_reminders", ["due_date"])
    op.create_index("ix_maintenance_reminders_status", "maintenance_reminders", ["status"])


def downgrade() -> None:
    op.drop_index("ix_maintenance_reminders_status", table_name="maintenance_reminders")
    op.drop_index("ix_maintenance_reminders_due_date", table_name="maintenance_reminders")
    op.drop_index("ix_maintenance_reminders_vehicle_id", table_name="maintenance_reminders")
    op.drop_index("ix_maintenance_reminders_owner_id", table_name="maintenance_reminders")
    op.drop_table("maintenance_reminders")
    op.drop_index("ix_appointments_status", table_name="appointments")
    op.drop_index("ix_appointments_scheduled_start", table_name="appointments")
    op.drop_index("ix_appointments_vehicle_id", table_name="appointments")
    op.drop_index("ix_appointments_owner_id", table_name="appointments")
    op.drop_table("appointments")
