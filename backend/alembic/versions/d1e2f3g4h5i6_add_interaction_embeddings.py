"""add pgvector extension and interaction embeddings

Revision ID: d1e2f3g4h5i6
Revises: c3d4e5f6g7h8
Create Date: 2026-03-17 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = "d1e2f3g4h5i6"
down_revision: Union[str, None] = "c3d4e5f6g7h8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure the pgvector extension is available
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # Add embedding column to interactions (768-dim, gemini-embedding-001)
    op.add_column(
        "interactions",
        sa.Column("embedding", Vector(768), nullable=True),
    )

    # HNSW index for fast vector similarity search using cosine distance
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_interactions_embedding_hnsw
        ON interactions
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP INDEX IF EXISTS ix_interactions_embedding_hnsw;"
    )
    op.drop_column("interactions", "embedding")

