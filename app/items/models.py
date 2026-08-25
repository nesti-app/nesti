from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Item(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "items"
    __table_args__ = (
        Index("ix_items_name", "name"),
        Index("ix_items_category_id", "category_id"),
        Index("ix_items_location_id", "location_id"),
        Index("ix_items_parent_item_id", "parent_item_id"),
        Index("ix_items_sku", "sku"),
        Index("ix_items_serial_number", "serial_number"),
    )

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True
    )
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id"), nullable=True
    )
    parent_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id"), nullable=True
    )

    manufacturer: Mapped[str | None] = mapped_column(String, nullable=True)
    model: Mapped[str | None] = mapped_column(String, nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String, nullable=True)
    sku: Mapped[str | None] = mapped_column(String, nullable=True)

    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    category = relationship("Category", back_populates="items", lazy="selectin")
    location = relationship("Location", back_populates="items", lazy="selectin")
    parent_item = relationship(
        "Item", remote_side="Item.id", back_populates="child_items", lazy="selectin"
    )
    child_items = relationship("Item", back_populates="parent_item", lazy="selectin")
    tags = relationship("Tag", secondary="item_tags", back_populates="items", lazy="selectin")
    attributes = relationship(
        "ItemAttribute",
        back_populates="item",
        lazy="selectin",
        order_by="ItemAttribute.sort_order",
    )
    images = relationship(
        "ItemImage",
        back_populates="item",
        lazy="selectin",
        order_by="ItemImage.sort_order",
    )
    movements = relationship(
        "ItemMovement",
        back_populates="item",
        lazy="selectin",
        order_by="ItemMovement.moved_at.desc()",
    )

    def __repr__(self) -> str:
        return f"<Item {self.name}>"


class ItemAttribute(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "item_attributes"
    __table_args__ = (Index("ix_item_attributes_item_id", "item_id"),)

    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[str] = mapped_column(String, nullable=False)
    unit: Mapped[str | None] = mapped_column(String, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    item = relationship("Item", back_populates="attributes")

    def __repr__(self) -> str:
        return f"<ItemAttribute {self.name}={self.value} {self.unit or ''}>"


class ItemRelationship(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "item_relationships"
    __table_args__ = (
        Index("ix_item_relationships_source", "source_item_id"),
        Index("ix_item_relationships_target", "target_item_id"),
        CheckConstraint("source_item_id != target_item_id", name="ck_no_self_relationship"),
    )

    source_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"), nullable=False
    )
    target_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"), nullable=False
    )
    relationship_type: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    source_item = relationship("Item", foreign_keys=[source_item_id], lazy="selectin")
    target_item = relationship("Item", foreign_keys=[target_item_id], lazy="selectin")

    def __repr__(self) -> str:
        return f"<ItemRelationship {self.relationship_type}>"


class ItemMovement(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "item_movements"
    __table_args__ = (
        Index("ix_item_movements_item_id", "item_id"),
        Index("ix_item_movements_moved_at", "moved_at"),
    )

    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"), nullable=False
    )
    from_location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id"), nullable=True
    )
    to_location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id"), nullable=True
    )
    moved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    moved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    item = relationship("Item", back_populates="movements", lazy="selectin")
    from_location = relationship("Location", foreign_keys=[from_location_id], lazy="selectin")
    to_location = relationship("Location", foreign_keys=[to_location_id], lazy="selectin")
    moved_by_user = relationship("User", foreign_keys=[moved_by], lazy="selectin")

    def __repr__(self) -> str:
        return f"<ItemMovement {self.item_id}>"
