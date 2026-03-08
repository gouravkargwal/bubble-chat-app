"""add firebase auth columns to users

Revision ID: a1b2c3d4e5f6
Revises: f9542ab4711b
Create Date: 2026-03-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f9542ab4711b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('firebase_uid', sa.String(128), nullable=True))
    op.add_column('users', sa.Column('email', sa.String(320), nullable=True))
    op.add_column('users', sa.Column('display_name', sa.String(255), nullable=True))
    op.create_index('ix_users_firebase_uid', 'users', ['firebase_uid'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_users_firebase_uid', table_name='users')
    op.drop_column('users', 'display_name')
    op.drop_column('users', 'email')
    op.drop_column('users', 'firebase_uid')
