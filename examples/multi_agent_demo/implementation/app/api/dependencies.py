"""
FastAPI dependencies for authentication and authorization.

Provides dependency injection for:
- Database sessions
- Current user authentication
- Role-based access control (RBAC)
"""

from typing import Annotated, Callable, Generator

from app.models import Role, User, UserRole
from app.security.jwt_handler import TokenExpiredError, TokenInvalidError, verify_token
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

# Security scheme for Bearer token
security = HTTPBearer()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get database session.

    Yields
    ------
    Session
        SQLAlchemy database session

    Notes
    -----
    This is a placeholder. Actual implementation will use configured database.
    Each request gets its own session that's automatically closed.
    """
    # TODO: Import actual database session from app.database or config
    # For now, this is a placeholder that will be replaced
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """
    Dependency to get current authenticated user from JWT token.

    Parameters
    ----------
    credentials : HTTPAuthorizationCredentials
        Bearer token from Authorization header
    db : Session
        Database session

    Returns
    -------
    User
        Authenticated user object

    Raises
    ------
    HTTPException
        401 if token is invalid, expired, or user not found
        401 if user account is inactive

    Examples
    --------
    @app.get("/api/users/me")
    async def get_me(current_user: Annotated[User, Depends(get_current_user)]):
        return current_user
    """
    token = credentials.credentials

    try:
        # Verify and decode JWT token
        payload = verify_token(token)
        user_id: int = payload.get("user_id")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except TokenInvalidError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch user from database
    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Dependency to get current active user (convenience wrapper).

    Parameters
    ----------
    current_user : User
        User from get_current_user dependency

    Returns
    -------
    User
        Authenticated and active user

    Notes
    -----
    This is a convenience dependency. The get_current_user already checks
    if the user is active, so this just passes through.
    """
    return current_user


def require_roles(*required_roles: str) -> Callable[..., User]:
    """
    Dependency factory for role-based access control.

    Parameters
    ----------
    *required_roles : str
        One or more roles required to access the endpoint

    Returns
    -------
    callable
        FastAPI dependency function that checks user roles

    Examples
    --------
    @app.delete("/api/users/{user_id}")
    async def delete_user(
        user_id: int,
        current_user: Annotated[User, Depends(require_roles(Role.ADMIN))],
    ):
        # Only admins can access this endpoint
        ...

    @app.get("/api/admin/dashboard")
    async def admin_dashboard(
        current_user: Annotated[
            User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))
        ],
    ):
        # Admins and super_admins can access
        ...
    """

    async def check_roles(
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_db)],
    ) -> User:
        """
        Check if current user has required roles.

        Parameters
        ----------
        current_user : User
            Authenticated user
        db : Session
            Database session

        Returns
        -------
        User
            User with required roles

        Raises
        ------
        HTTPException
            403 if user doesn't have required roles
        """
        # Fetch user's roles from database
        user_role_records = (
            db.query(UserRole).filter(UserRole.user_id == current_user.id).all()
        )

        user_roles = {record.role for record in user_role_records}

        # Check if user has any of the required roles
        if not any(role in user_roles for role in required_roles):
            roles_str = ", ".join(required_roles)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {roles_str}",
            )

        return current_user

    return check_roles


# Type aliases for common dependencies
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]
DatabaseSession = Annotated[Session, Depends(get_db)]


# Pre-configured role dependencies
def require_admin() -> Callable[..., User]:
    """Require admin role."""
    return require_roles(Role.ADMIN, Role.SUPER_ADMIN)


def require_super_admin() -> Callable[..., User]:
    """Require super admin role."""
    return require_roles(Role.SUPER_ADMIN)


def require_moderator() -> Callable[..., User]:
    """Require moderator role or higher."""
    return require_roles(Role.MODERATOR, Role.ADMIN, Role.SUPER_ADMIN)


# Type aliases for role-based dependencies
AdminUser = Annotated[User, Depends(require_admin())]
SuperAdminUser = Annotated[User, Depends(require_super_admin())]
ModeratorUser = Annotated[User, Depends(require_moderator())]
