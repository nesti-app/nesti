"""add label wrap settings

Revision ID: d1e2f3a4b5c6
Revises: c9f1a2b3d4e5
Create Date: 2026-09-17 09:30:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, None] = "c9f1a2b3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "label_settings",
        sa.Column("max_name_lines", sa.Integer(), nullable=False, server_default=sa.text("4")),
    )
    op.add_column(
        "label_settings",
        sa.Column("wrap_by_words", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("label_settings", "wrap_by_words")
    op.drop_column("label_settings", "max_name_lines")
