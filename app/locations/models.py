from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Location(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "locations"
    __table_args__ = (Index("ix_locations_parent_location_id", "parent_location_id"),)

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id"), nullable=True
    )

    parent = relationship(
        "Location", remote_side="Location.id", back_populates="children", lazy="selectin"
    )
    children = relationship("Location", back_populates="parent", lazy="selectin")
    items = relationship("Item", back_populates="location", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Location {self.name}>"
