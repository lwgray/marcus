"""
User management API endpoints.

Provides REST API for:
- User profile retrieval and updates
- User search and filtering
- Role management (admin only)
- Password changes
"""

from datetime import datetime, timezone
from math import ceil

from app.api.dependencies import (
    AdminUser,
    CurrentUser,
    DatabaseSession,
)
from app.models import Role, User, UserRole
from app.schemas import (
    PasswordChange,
    RoleAssignment,
    RoleResponse,
    SuccessResponse,
    UserListResponse,
    UserResponse,
    UserUpdate,
)
from app.security.password import hash_password, verify_password
from fastapi import APIRouter, HTTPException, Query, status

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)  # type: ignore[misc]
async def get_current_user_profile(
    current_user: CurrentUser,
    db: DatabaseSession,
) -> UserResponse:
    """
    Get current user's profile.

    Returns
    -------
    UserResponse
        Current user's profile information

    Notes
    -----
    Requires valid JWT token in Authorization header.
    """
    # Load user roles
    roles = db.query(UserRole).filter(UserRole.user_id == current_user.id).all()
    role_names = [role.role for role in roles]

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        last_login=current_user.last_login,
        roles=role_names,
    )


@router.put("/me", response_model=UserResponse)  # type: ignore[misc]
async def update_current_user_profile(
    update_data: UserUpdate,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> UserResponse:
    """
    Update current user's profile.

    Parameters
    ----------
    update_data : UserUpdate
        Fields to update (email and/or username)

    Returns
    -------
    UserResponse
        Updated user profile

    Raises
    ------
    HTTPException
        409 if email or username already exists
        400 if validation fails
    """
    # Check if email is being changed and if it's already taken
    if update_data.email and update_data.email != current_user.email:
        existing_user = db.query(User).filter(User.email == update_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        current_user.email = update_data.email

    # Check if username is being changed and if it's already taken
    if update_data.username and update_data.username != current_user.username:
        existing_user = (
            db.query(User).filter(User.username == update_data.username).first()
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken",
            )
        current_user.username = update_data.username

    # Update timestamp
    current_user.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(current_user)

    # Load user roles
    roles = db.query(UserRole).filter(UserRole.user_id == current_user.id).all()
    role_names = [role.role for role in roles]

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        last_login=current_user.last_login,
        roles=role_names,
    )


@router.delete("/me", response_model=SuccessResponse)  # type: ignore[misc]
async def delete_current_user(
    current_user: CurrentUser,
    db: DatabaseSession,
) -> SuccessResponse:
    """
    Deactivate current user's account (soft delete).

    Returns
    -------
    SuccessResponse
        Success message

    Notes
    -----
    This performs a soft delete by setting is_active=False.
    User data is preserved but account is deactivated.
    """
    current_user.is_active = False
    current_user.updated_at = datetime.now(timezone.utc)

    db.commit()

    return SuccessResponse(success=True, message="Account deactivated successfully")


@router.put("/me/password", response_model=SuccessResponse)  # type: ignore[misc]
async def change_password(
    password_change: PasswordChange,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> SuccessResponse:
    """
    Change current user's password.

    Parameters
    ----------
    password_change : PasswordChange
        Current and new password

    Returns
    -------
    SuccessResponse
        Success message

    Raises
    ------
    HTTPException
        401 if current password is incorrect
        400 if new password doesn't meet requirements
    """
    # Verify current password
    if not verify_password(
        password_change.current_password, current_user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    # Hash and update new password
    current_user.password_hash = hash_password(password_change.new_password)
    current_user.updated_at = datetime.now(timezone.utc)

    db.commit()

    # TODO: Revoke all refresh tokens when another agent implements that

    return SuccessResponse(success=True, message="Password changed successfully")


@router.get("", response_model=UserListResponse)  # type: ignore[misc]
async def list_users(
    admin_user: AdminUser,
    db: DatabaseSession,
    email: str = Query(None, description="Filter by email (partial match)"),
    username: str = Query(None, description="Filter by username (partial match)"),
    role: str = Query(None, description="Filter by role"),
    is_active: bool = Query(None, description="Filter by active status"),
    is_verified: bool = Query(None, description="Filter by verified status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    sort_by: str = Query(
        "created_at", pattern="^(created_at|username|email|last_login)$"
    ),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
) -> UserListResponse:
    """
    List and search users (admin only).

    Parameters
    ----------
    Various query parameters for filtering and pagination

    Returns
    -------
    UserListResponse
        Paginated list of users

    Notes
    -----
    Requires admin or super_admin role.
    """
    # Build query
    query = db.query(User)

    # Apply filters
    if email:
        query = query.filter(User.email.ilike(f"%{email}%"))
    if username:
        query = query.filter(User.username.ilike(f"%{username}%"))
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    if is_verified is not None:
        query = query.filter(User.is_verified == is_verified)

    # Role filter (requires join)
    if role:
        query = query.join(UserRole).filter(UserRole.role == role)

    # Get total count before pagination
    total = query.count()

    # Apply sorting
    sort_column = getattr(User, sort_by)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Apply pagination
    offset = (page - 1) * page_size
    users = query.offset(offset).limit(page_size).all()

    # Build response with roles
    user_responses = []
    for user in users:
        roles = db.query(UserRole).filter(UserRole.user_id == user.id).all()
        role_names = [role.role for role in roles]

        user_responses.append(
            UserResponse(
                id=user.id,
                email=user.email,
                username=user.username,
                is_active=user.is_active,
                is_verified=user.is_verified,
                created_at=user.created_at,
                updated_at=user.updated_at,
                last_login=user.last_login,
                roles=role_names,
            )
        )

    total_pages = ceil(total / page_size) if total > 0 else 0

    return UserListResponse(
        users=user_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{user_id}", response_model=UserResponse)  # type: ignore[misc]
async def get_user_by_id(
    user_id: int,
    admin_user: AdminUser,
    db: DatabaseSession,
) -> UserResponse:
    """
    Get user by ID (admin only).

    Parameters
    ----------
    user_id : int
        User ID to retrieve

    Returns
    -------
    UserResponse
        User profile

    Raises
    ------
    HTTPException
        404 if user not found
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Load user roles
    roles = db.query(UserRole).filter(UserRole.user_id == user.id).all()
    role_names = [role.role for role in roles]

    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login=user.last_login,
        roles=role_names,
    )


@router.delete("/{user_id}", response_model=SuccessResponse)  # type: ignore[misc]
async def deactivate_user(
    user_id: int,
    admin_user: AdminUser,
    db: DatabaseSession,
) -> SuccessResponse:
    """
    Deactivate a user account (admin only).

    Parameters
    ----------
    user_id : int
        User ID to deactivate

    Returns
    -------
    SuccessResponse
        Success message

    Raises
    ------
    HTTPException
        404 if user not found
        400 if trying to deactivate self
    """
    if user_id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account",
        )

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.is_active = False
    user.updated_at = datetime.now(timezone.utc)

    db.commit()

    return SuccessResponse(success=True, message="User deactivated successfully")


@router.post("/{user_id}/roles", response_model=RoleResponse)  # type: ignore[misc]
async def assign_role_to_user(
    user_id: int,
    role_assignment: RoleAssignment,
    admin_user: AdminUser,
    db: DatabaseSession,
) -> RoleResponse:
    """
    Assign a role to a user (admin only).

    Parameters
    ----------
    user_id : int
        User ID to assign role to
    role_assignment : RoleAssignment
        Role to assign

    Returns
    -------
    RoleResponse
        Created role assignment

    Raises
    ------
    HTTPException
        404 if user not found
        409 if role already assigned
        400 if invalid role
    """
    # Validate role
    if not Role.is_valid_role(role_assignment.role):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(Role.all_roles())}",
        )

    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Check if role already assigned
    existing_role = (
        db.query(UserRole)
        .filter(UserRole.user_id == user_id, UserRole.role == role_assignment.role)
        .first()
    )

    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Role '{role_assignment.role}' already assigned to user",
        )

    # Create role assignment
    user_role = UserRole(
        user_id=user_id,
        role=role_assignment.role,
        granted_at=datetime.now(timezone.utc),
        granted_by=admin_user.id,
    )

    db.add(user_role)
    db.commit()
    db.refresh(user_role)

    return RoleResponse(
        id=user_role.id,
        user_id=user_role.user_id,
        role=user_role.role,
        granted_at=user_role.granted_at,
        granted_by=user_role.granted_by,
    )


@router.delete(  # type: ignore[misc]
    "/{user_id}/roles/{role}", response_model=SuccessResponse
)
async def remove_role_from_user(
    user_id: int,
    role: str,
    admin_user: AdminUser,
    db: DatabaseSession,
) -> SuccessResponse:
    """
    Remove a role from a user (admin only).

    Parameters
    ----------
    user_id : int
        User ID to remove role from
    role : str
        Role to remove

    Returns
    -------
    SuccessResponse
        Success message

    Raises
    ------
    HTTPException
        404 if user or role assignment not found
    """
    user_role = (
        db.query(UserRole)
        .filter(UserRole.user_id == user_id, UserRole.role == role)
        .first()
    )

    if not user_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role '{role}' not assigned to user",
        )

    db.delete(user_role)
    db.commit()

    return SuccessResponse(success=True, message=f"Role '{role}' removed successfully")
