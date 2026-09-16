"""drop supabase_id from users

Revision ID: 47f1e2c6d9a5
Revises: 36a81a10cf7a639c
Create Date: 2026-09-16 15:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '47f1e2c6d9a5'
down_revision: str | None = '36a81a10cf7a639c'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('supabase_id')


def downgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(
            sa.Column('supabase_id', sa.String(), nullable=False)
        )
        batch_op.create_unique_constraint(
            'users_supabase_id_key', ['supabase_id']
        )