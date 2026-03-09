"""add referral system and purchases table

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-09 00:00:00.000000

"""
import secrets
import string
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6g7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _generate_code(length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def upgrade() -> None:
    # --- Referral columns on users ---
    op.add_column("users", sa.Column("referral_code", sa.String(8), nullable=True))
    op.add_column("users", sa.Column("bonus_replies", sa.Integer(), nullable=False, server_default="0"))
    op.add_column(
        "users",
        sa.Column("referred_by", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_users_referral_code", "users", ["referral_code"], unique=True)

    # Generate referral codes for existing users
    conn = op.get_bind()
    users = conn.execute(sa.text("SELECT id FROM users")).fetchall()
    for (user_id,) in users:
        code = _generate_code()
        conn.execute(
            sa.text("UPDATE users SET referral_code = :code WHERE id = :uid"),
            {"code": code, "uid": user_id},
        )

    # --- Referrals table ---
    op.create_table(
        "referrals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("referrer_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("referee_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("bonus_granted", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_referrals_referrer_id", "referrals", ["referrer_id"])
    op.create_index("ix_referrals_referee_id", "referrals", ["referee_id"])

    # --- Purchases table ---
    op.create_table(
        "purchases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("product_id", sa.String(100), nullable=False),
        sa.Column("purchase_token", sa.String(500), nullable=False, unique=True),
        sa.Column("order_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="active"),
        sa.Column("started_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("auto_renewing", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_purchases_user_id", "purchases", ["user_id"])


def downgrade() -> None:
    op.drop_table("purchases")
    op.drop_table("referrals")
    op.drop_index("ix_users_referral_code", table_name="users")
    op.drop_column("users", "referred_by")
    op.drop_column("users", "bonus_replies")
    op.drop_column("users", "referral_code")
