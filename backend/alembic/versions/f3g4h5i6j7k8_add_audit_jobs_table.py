"""add audit_jobs table for async processing

Revision ID: f3g4h5i6j7k8
Revises: e2f3g4h5i6j7
Create Date: 2026-03-21 01:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f3g4h5i6j7k8"
down_revision: Union[str, None] = "e2f3g4h5i6j7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("progress_current", sa.Integer, nullable=False, server_default="0"),
        sa.Column("progress_total", sa.Integer, nullable=False, server_default="0"),
        sa.Column("progress_step", sa.String(50), nullable=False, server_default="uploading"),
        sa.Column("lang", sa.String(30), nullable=False, server_default="English"),
        sa.Column("result_json", sa.Text, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("idempotency_key", sa.String(64), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("audit_jobs")
