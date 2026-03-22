"""add idempotency_key column to audited_photos

Revision ID: e2f3g4h5i6j7
Revises: d1e2f3g4h5i6
Create Date: 2026-03-21 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e2f3g4h5i6j7"
down_revision: Union[str, None] = "d1e2f3g4h5i6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "audited_photos",
        sa.Column("idempotency_key", sa.String(64), nullable=True),
    )
    op.create_index(
        "ix_audited_photos_idempotency_key",
        "audited_photos",
        ["idempotency_key"],
    )


def downgrade() -> None:
    op.drop_index("ix_audited_photos_idempotency_key", table_name="audited_photos")
    op.drop_column("audited_photos", "idempotency_key")
