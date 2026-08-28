from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Category(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "categories"
    __table_args__ = (
        Index("ix_categories_parent_category_id", "parent_category_id"),
    )

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True
    )

    parent = relationship(
        "Category", remote_side="Category.id", back_populates="children", lazy="selectin"
    )
    children = relationship("Category", back_populates="parent", lazy="selectin")
    items = relationship("Item", back_populates="category", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Category {self.name}>"
