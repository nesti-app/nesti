"""add local auth fields to users

Revision ID: 36a81a10cf7a639c
Revises: 8d0e3f2a1b4c
Create Date: 2026-09-16 12:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '36a81a10cf7a639c'
down_revision: str | None = '8d0e3f2a1b4c'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('users', sa.Column('password_hash', sa.String(), nullable=True))
    op.add_column('users', sa.Column('totp_secret', sa.String(), nullable=True))
    op.add_column(
        'users', sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0')
    )
    op.add_column(
        'users', sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'failed_login_attempts')
    op.drop_column('users', 'totp_secret')
    op.drop_column('users', 'password_hash')