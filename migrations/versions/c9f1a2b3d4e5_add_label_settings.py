"""add label settings

Revision ID: c9f1a2b3d4e5
Revises: 47f1e2c6d9a5
Create Date: 2026-09-17 08:30:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9f1a2b3d4e5"
down_revision: Union[str, None] = "47f1e2c6d9a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DEFAULTS = {
    "id": "default",
    "label_type": "full",
    "orientation": "horizontal",
    "size": "30x15",
    "custom_width": 30,
    "custom_height": 15,
    "name_font_size": 14,
    "code_font_size": 10,
}


def upgrade() -> None:
    op.create_table(
        "label_settings",
        sa.Column("id", sa.String(length=16), primary_key=True),
        sa.Column("label_type", sa.String(length=16), nullable=False),
        sa.Column("orientation", sa.String(length=16), nullable=False),
        sa.Column("size", sa.String(length=16), nullable=False),
        sa.Column("custom_width", sa.Integer(), nullable=False),
        sa.Column("custom_height", sa.Integer(), nullable=False),
        sa.Column("name_font_size", sa.Integer(), nullable=False),
        sa.Column("code_font_size", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.bulk_insert(
        sa.table(
            "label_settings",
            sa.column("id", sa.String),
            sa.column("label_type", sa.String),
            sa.column("orientation", sa.String),
            sa.column("size", sa.String),
            sa.column("custom_width", sa.Integer),
            sa.column("custom_height", sa.Integer),
            sa.column("name_font_size", sa.Integer),
            sa.column("code_font_size", sa.Integer),
        ),
        [_DEFAULTS],
    )


def downgrade() -> None:
    op.drop_table("label_settings")
