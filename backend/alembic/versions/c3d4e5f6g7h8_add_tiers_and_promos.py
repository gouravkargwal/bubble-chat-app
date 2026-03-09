"""add tier fields and promo tables

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-03-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6g7h8"
down_revision: Union[str, None] = "b2c3d4e5f6g7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Tier columns on users ---
    op.add_column("users", sa.Column("tier", sa.String(20), nullable=False, server_default="free"))
    op.add_column("users", sa.Column("tier_expires_at", sa.DateTime(), nullable=True))

    # --- Promos table ---
    op.create_table(
        "promos",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(30), nullable=False, unique=True),
        sa.Column("tier_grant", sa.String(20), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("max_uses", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("current_uses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("new_users_only", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_promos_code", "promos", ["code"], unique=True)

    # --- Promo redemptions table ---
    op.create_table(
        "promo_redemptions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("promo_id", sa.String(36), sa.ForeignKey("promos.id"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_promo_redemptions_promo_id", "promo_redemptions", ["promo_id"])
    op.create_index("ix_promo_redemptions_user_id", "promo_redemptions", ["user_id"])


def downgrade() -> None:
    op.drop_table("promo_redemptions")
    op.drop_table("promos")
    op.drop_column("users", "tier_expires_at")
    op.drop_column("users", "tier")
