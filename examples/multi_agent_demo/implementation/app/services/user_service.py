"""
User service layer for business logic.

This module provides functions for user management operations including
creation, retrieval, updates, and authentication.

Author: Foundation Agent
Task: Implement User Management (task_user_management_implement)
"""

from datetime import datetime

from app.exceptions import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.models import User
from app.schemas.user import UserCreate, UserUpdate
from app.utils.security import hash_password, verify_password
from sqlalchemy.orm import Session


def create_user(db: Session, user_data: UserCreate) -> User:
    """
    Create a new user.

    Parameters
    ----------
    db : Session
        Database session
    user_data : UserCreate
        User registration data

    Returns
    -------
    User
        Created user model

    Raises
    ------
    UserAlreadyExistsError
        If user with email or username already exists
    """
    # Check if user with email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise UserAlreadyExistsError(
            f"User with email {user_data.email} already exists",
            details={"field": "email"},
        )

    # Check if username is taken
    existing_username = (
        db.query(User).filter(User.username == user_data.username).first()
    )
    if existing_username:
        raise UserAlreadyExistsError(
            f"Username {user_data.username} is already taken",
            details={"field": "username"},
        )

    # Hash password
    hashed_password = hash_password(user_data.password)

    # Create user
    db_user = User(
        email=user_data.email,
        username=user_data.username,
        password_hash=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


def get_user_by_email(db: Session, email: str) -> User | None:
    """
    Get user by email address.

    Parameters
    ----------
    db : Session
        Database session
    email : str
        User email address

    Returns
    -------
    User | None
        User model if found, None otherwise
    """
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """
    Get user by ID.

    Parameters
    ----------
    db : Session
        Database session
    user_id : int
        User ID

    Returns
    -------
    User | None
        User model if found, None otherwise
    """
    return db.query(User).filter(User.id == user_id).first()


def update_user(db: Session, user_id: int, user_data: UserUpdate) -> User:
    """
    Update user information.

    Parameters
    ----------
    db : Session
        Database session
    user_id : int
        User ID to update
    user_data : UserUpdate
        Updated user data

    Returns
    -------
    User
        Updated user model

    Raises
    ------
    UserNotFoundError
        If user with given ID doesn't exist
    UserAlreadyExistsError
        If new email is already taken by another user
    """
    # Get user
    user = get_user_by_id(db, user_id)
    if user is None:
        raise UserNotFoundError(f"User with ID {user_id} not found")

    # Check if email is being changed and if it's already taken
    if user_data.email and user_data.email != user.email:
        existing_user = get_user_by_email(db, user_data.email)
        if existing_user and existing_user.id != user_id:
            raise UserAlreadyExistsError(
                f"Email {user_data.email} is already taken", details={"field": "email"}
            )

    # Update fields
    if user_data.first_name is not None:
        user.first_name = user_data.first_name
    if user_data.last_name is not None:
        user.last_name = user_data.last_name
    if user_data.email is not None:
        user.email = user_data.email

    db.commit()
    db.refresh(user)

    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    """
    Authenticate user with email and password.

    Parameters
    ----------
    db : Session
        Database session
    email : str
        User email
    password : str
        User password

    Returns
    -------
    User
        Authenticated user model

    Raises
    ------
    InvalidCredentialsError
        If email or password is incorrect
    """
    # Get user by email
    user = get_user_by_email(db, email)
    if user is None:
        raise InvalidCredentialsError("Invalid email or password")

    # Verify password
    if not verify_password(password, user.password_hash):
        raise InvalidCredentialsError("Invalid email or password")

    # Check if account is active
    if not user.is_active:
        raise InvalidCredentialsError("User account is inactive")

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    db.refresh(user)

    return user
