"""add short_code to items

Revision ID: b2c3d4e5f6a7
Revises: 6a46111dc73e
Create Date: 2026-08-26 10:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "6a46111dc73e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ALPHABET = "0123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz"


def _uuid_to_short_code(raw_bytes: bytes) -> str:
    import base64
    return base64.urlsafe_b64encode(raw_bytes[:4]).rstrip(b"=").decode("ascii")


def upgrade() -> None:
    op.add_column("items", sa.Column("short_code", sa.String(8), nullable=True))

    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT id FROM items"))
    for row in result:
        item_id = row[0]
        raw = item_id.bytes if hasattr(item_id, "bytes") else item_id.hex
        if hasattr(item_id, "bytes"):
            code = _uuid_to_short_code(item_id.bytes)
        else:
            import base64
            raw_bytes = bytes.fromhex(str(item_id).replace("-", ""))
            code = base64.urlsafe_b64encode(raw_bytes[:4]).rstrip(b"=").decode("ascii")
        conn.execute(
            sa.text("UPDATE items SET short_code = :code WHERE id = :id"),
            {"code": code, "id": item_id},
        )

    op.alter_column("items", "short_code", nullable=False)
    op.create_unique_constraint("uq_items_short_code", "items", ["short_code"])
    op.create_index("ix_items_short_code", "items", ["short_code"])


def downgrade() -> None:
    op.drop_index("ix_items_short_code", table_name="items")
    op.drop_constraint("uq_items_short_code", "items", type_="unique")
    op.drop_column("items", "short_code")
