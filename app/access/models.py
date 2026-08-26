from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AccessScope(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "access_scopes"

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    rules = relationship(
        "AccessScopeRule", back_populates="scope", lazy="selectin",
        cascade="all, delete-orphan",
    )
    permissions = relationship(
        "AccessScopePermission", back_populates="scope", lazy="selectin",
        cascade="all, delete-orphan",
    )
    users = relationship(
        "AccessScopeUser", back_populates="scope", lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<AccessScope {self.name}>"


class AccessScopeRule(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "access_scope_rules"
    __table_args__ = (Index("ix_access_scope_rules_scope_id", "scope_id"),)

    scope_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("access_scopes.id", ondelete="CASCADE"), nullable=False
    )
    rule_type: Mapped[str] = mapped_column(String, nullable=False)
    rule_value: Mapped[str] = mapped_column(String, nullable=False)

    scope = relationship("AccessScope", back_populates="rules")

    def __repr__(self) -> str:
        return f"<AccessScopeRule {self.rule_type}={self.rule_value}>"


class AccessScopePermission(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "access_scope_permissions"
    __table_args__ = (Index("ix_access_scope_permissions_scope_id", "scope_id"),)

    scope_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("access_scopes.id", ondelete="CASCADE"), nullable=False
    )
    permission: Mapped[str] = mapped_column(String, nullable=False)

    scope = relationship("AccessScope", back_populates="permissions")

    def __repr__(self) -> str:
        return f"<AccessScopePermission {self.permission}>"


class AccessScopeUser(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "access_scope_users"
    __table_args__ = (
        Index("ix_access_scope_users_scope_id", "scope_id"),
        Index("ix_access_scope_users_user_id", "user_id"),
    )

    scope_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("access_scopes.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    scope = relationship("AccessScope", back_populates="users")
    user = relationship("User", lazy="selectin")

    def __repr__(self) -> str:
        return f"<AccessScopeUser scope={self.scope_id} user={self.user_id}>"
