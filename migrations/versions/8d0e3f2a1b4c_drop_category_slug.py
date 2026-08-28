"""drop category slug

Revision ID: 8d0e3f2a1b4c
Revises: 5ddce1d4cc9b
Create Date: 2026-08-28 10:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '8d0e3f2a1b4c'
down_revision: str | None = '5ddce1d4cc9b'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index(op.f('ix_categories_slug'), table_name='categories')
    op.drop_column('categories', 'slug')


def downgrade() -> None:
    op.add_column(
        'categories',
        sa.Column('slug', sa.VARCHAR(), autoincrement=False, nullable=True),
    )
    op.create_index(op.f('ix_categories_slug'), 'categories', ['slug'], unique=True)
