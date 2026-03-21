"""add pending_resolutions and person_aliases tables for industry-grade stitch

Revision ID: e1f2g3h4i5j6
Revises: d1e2f3g4h5i6
Create Date: 2026-03-21 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e1f2g3h4i5j6"
down_revision: Union[str, None] = "d1e2f3g4h5i6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- pending_resolutions: DB-backed replacement for in-memory dict ---
    op.create_table(
        "pending_resolutions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("suggested_conversation_id", sa.String(36), nullable=False),
        sa.Column("images", sa.Text, nullable=False),
        sa.Column("direction", sa.String(30), nullable=False),
        sa.Column("custom_hint", sa.String(200), nullable=True),
        sa.Column("extracted_person_name", sa.String(100), nullable=False),
        sa.Column("conflict_reason", sa.String(255), nullable=True),
        sa.Column("conflict_detail", sa.Text, nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", sa.String(30), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_pending_res_user_conv",
        "pending_resolutions",
        ["user_id", "suggested_conversation_id"],
    )
    op.create_index(
        "ix_pending_resolutions_user_id",
        "pending_resolutions",
        ["user_id"],
    )

    # --- person_aliases: identity resolution / alias mapping ---
    op.create_table(
        "person_aliases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("alias_name", sa.String(100), nullable=False),
        sa.Column(
            "conversation_id",
            sa.String(36),
            sa.ForeignKey("conversations.id"),
            nullable=False,
        ),
        sa.Column("source", sa.String(30), nullable=False, server_default="auto_stitch"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_person_alias_user_alias",
        "person_aliases",
        ["user_id", "alias_name"],
    )
    op.create_unique_constraint(
        "uq_person_alias_user_name",
        "person_aliases",
        ["user_id", "alias_name"],
    )


def downgrade() -> None:
    op.drop_table("person_aliases")
    op.drop_table("pending_resolutions")
