"""Add user registration profile and consent fields.

Revision ID: 0005_user_registration
Revises: 0004_email_otp_auth
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005_user_registration"
down_revision: Union[str, None] = "0004_email_otp_auth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("full_name", sa.String(length=120), nullable=True))
    op.add_column("users", sa.Column("workshop_name", sa.String(length=160), nullable=True))
    op.add_column("users", sa.Column("phone_country_code", sa.String(length=6), nullable=True))
    op.add_column("users", sa.Column("phone_number", sa.String(length=15), nullable=True))
    op.add_column("users", sa.Column("privacy_accepted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("terms_accepted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("consent_version", sa.String(length=24), nullable=True))
    op.add_column(
        "users",
        sa.Column("marketing_consent", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_unique_constraint(
        "uq_users_phone", "users", ["phone_country_code", "phone_number"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_users_phone", "users", type_="unique")
    op.drop_column("users", "marketing_consent")
    op.drop_column("users", "consent_version")
    op.drop_column("users", "terms_accepted_at")
    op.drop_column("users", "privacy_accepted_at")
    op.drop_column("users", "phone_number")
    op.drop_column("users", "phone_country_code")
    op.drop_column("users", "workshop_name")
    op.drop_column("users", "full_name")
