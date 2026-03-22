"""fix blueprint schema: add idempotency_key, coach_reasoning, storage_path, universal_prompts table

Revision ID: g5h6i7j8k9l0
Revises: f3g4h5i6j7k8
Create Date: 2026-03-21 02:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "g5h6i7j8k9l0"
down_revision: Union[str, None] = "f3g4h5i6j7k8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add idempotency_key to profile_blueprints
    op.add_column(
        "profile_blueprints",
        sa.Column("idempotency_key", sa.String(64), nullable=True),
    )
    op.create_unique_constraint(
        "uq_profile_blueprints_idempotency_key",
        "profile_blueprints",
        ["idempotency_key"],
    )
    op.create_index(
        "ix_profile_blueprints_idempotency_key",
        "profile_blueprints",
        ["idempotency_key"],
    )

    # Add coach_reasoning and storage_path to blueprint_slots
    op.add_column(
        "blueprint_slots",
        sa.Column("coach_reasoning", sa.Text, nullable=False, server_default=""),
    )
    op.add_column(
        "blueprint_slots",
        sa.Column("storage_path", sa.String(500), nullable=True),
    )

    # Create blueprint_universal_prompts table
    op.create_table(
        "blueprint_universal_prompts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "blueprint_id",
            sa.String(36),
            sa.ForeignKey("profile_blueprints.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("category", sa.String(200), nullable=False),
        sa.Column("suggested_text", sa.Text, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("blueprint_universal_prompts")
    op.drop_column("blueprint_slots", "storage_path")
    op.drop_column("blueprint_slots", "coach_reasoning")
    op.drop_index("ix_profile_blueprints_idempotency_key", table_name="profile_blueprints")
    op.drop_constraint(
        "uq_profile_blueprints_idempotency_key", "profile_blueprints", type_="unique"
    )
    op.drop_column("profile_blueprints", "idempotency_key")
