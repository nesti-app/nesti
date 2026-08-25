from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin


class Tag(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    items = relationship("Item", secondary="item_tags", back_populates="tags", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Tag {self.name}>"


class ItemTag(Base):
    __tablename__ = "item_tags"
    __table_args__ = (
        Index("ix_item_tags_item_id", "item_id"),
        Index("ix_item_tags_tag_id", "tag_id"),
    )

    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )
