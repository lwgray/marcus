"""
Refresh Token model for JWT token management.

Handles refresh token storage, validation, and revocation.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from app.models.base import Base
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.user import User


class RefreshToken(Base):
    """
    Refresh Token entity for token management.

    Stores refresh tokens with metadata for security and audit purposes.
    Supports token revocation and cleanup of expired tokens.

    Attributes
    ----------
    id : int
        Primary key, auto-incrementing token ID
    user_id : int
        Foreign key to users table
    token_hash : str
        SHA-256 hash of the refresh token
    expires_at : datetime
        UTC timestamp when token expires
    is_revoked : bool
        Whether token has been revoked (default: False)
    created_at : datetime
        UTC timestamp when token was created
    revoked_at : datetime, optional
        UTC timestamp when token was revoked
    ip_address : str, optional
        IP address where token was issued (max 45 chars for IPv6)
    user_agent : str, optional
        User agent string from token request
    user : User
        Related user object

    Notes
    -----
    - Token hashes are stored for security (never store raw tokens)
    - Expired tokens should be cleaned up periodically
    - Revoked tokens cannot be used for refresh operations
    - CASCADE delete when user is deleted
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, doc="Unique token identifier"
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="User who owns this token",
    )

    token_hash: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="SHA-256 hash of refresh token",
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        doc="Token expiration timestamp (UTC)",
    )

    is_revoked: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, doc="Token revocation status"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        doc="Token creation timestamp (UTC)",
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, doc="Token revocation timestamp (UTC)"
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(45), nullable=True, doc="IP address where token was issued"
    )

    user_agent: Mapped[str | None] = mapped_column(
        Text, nullable=True, doc="User agent from token request"
    )

    # Relationship
    user: Mapped["User"] = relationship(
        "User", back_populates="refresh_tokens", doc="User who owns this token"
    )

    def __repr__(self) -> str:
        """Return string representation of RefreshToken."""
        return (
            f"<RefreshToken(id={self.id}, user_id={self.user_id}, "
            f"expires={self.expires_at}, revoked={self.is_revoked})>"
        )

    def is_valid(self) -> bool:
        """
        Check if token is valid (not expired and not revoked).

        Returns
        -------
        bool
            True if token is valid, False otherwise
        """
        return not self.is_revoked and self.expires_at > datetime.utcnow()

    def revoke(self) -> None:
        """
        Revoke the refresh token.

        Sets is_revoked=True and records revocation timestamp.
        """
        self.is_revoked = True
        self.revoked_at = datetime.utcnow()
