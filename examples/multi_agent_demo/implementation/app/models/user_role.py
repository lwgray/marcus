"""
User role model for role-based access control (RBAC).

Defines user roles and permissions for authorization.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from app.models.base import Base
from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.user import User


class UserRole(Base):
    """
    User role assignment for RBAC.

    Attributes
    ----------
    id : int
        Primary key, auto-incrementing role assignment ID
    user_id : int
        Foreign key to users table
    role : str
        Role name (e.g., 'user', 'admin', 'moderator', 'super_admin')
    granted_at : datetime
        UTC timestamp when role was granted
    granted_by : int, optional
        User ID of the administrator who granted this role
    user : User
        Relationship to User model

    Notes
    -----
    - Each user can have multiple roles
    - (user_id, role) combination must be unique
    - Roles are: 'user' (default), 'admin', 'moderator', 'super_admin'
    """

    __tablename__ = "user_roles"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, doc="Unique role assignment identifier"
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="User ID this role is assigned to",
    )

    role: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, doc="Role name"
    )

    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        doc="Timestamp when role was granted",
    )

    granted_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
        doc="Admin user who granted this role",
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User", back_populates="roles", foreign_keys=[user_id]
    )

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint("user_id", "role", name="uq_user_role"),
        Index("ix_user_roles_user_id_role", "user_id", "role"),
    )

    def __repr__(self) -> str:
        """Return string representation of UserRole."""
        return f"<UserRole(user_id={self.user_id}, role='{self.role}')>"


# Role constants
class Role:
    """Standard role definitions."""

    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"
    SUPER_ADMIN = "super_admin"

    @classmethod
    def all_roles(cls) -> list[str]:
        """Get list of all available roles."""
        return [cls.USER, cls.ADMIN, cls.MODERATOR, cls.SUPER_ADMIN]

    @classmethod
    def is_valid_role(cls, role: str) -> bool:
        """Check if role is valid."""
        return role in cls.all_roles()
