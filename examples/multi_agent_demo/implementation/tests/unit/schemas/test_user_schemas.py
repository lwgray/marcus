"""
Unit tests for user management schemas.

Tests Pydantic validation for user CRUD, password changes, role management.
"""

from datetime import datetime

import pytest
from app.schemas.user import (
    ErrorResponse,
    PasswordChange,
    RoleAssignment,
    RoleResponse,
    SuccessResponse,
    UserCreate,
    UserListResponse,
    UserResponse,
    UserSearchParams,
    UserUpdate,
)
from pydantic import ValidationError


class TestUserCreateSchema:
    """Test suite for UserCreate schema validation."""

    def test_valid_user_create(self) -> None:
        """Test valid user creation data."""
        # Act
        user = UserCreate(
            email="test@example.com",
            username="testuser",
            password="SecureP@ssw0rd123",  # pragma: allowlist secret
        )

        # Assert
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.password == "SecureP@ssw0rd123"  # pragma: allowlist secret

    def test_invalid_email(self) -> None:
        """Test creation with invalid email format."""
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="invalid-email",
                username="testuser",
                password="SecureP@ssw0rd123",  # pragma: allowlist secret
            )

        assert "email" in str(exc_info.value).lower()

    def test_username_too_short(self) -> None:
        """Test username shorter than 3 characters."""
        # Act & Assert
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                username="ab",
                password="SecureP@ssw0rd123",  # pragma: allowlist secret
            )

    def test_username_invalid_characters(self) -> None:
        """Test username with invalid characters."""
        # Act & Assert
        with pytest.raises(ValidationError, match="letters, numbers, and underscores"):
            UserCreate(
                email="test@example.com",
                username="test-user!",
                password="SecureP@ssw0rd123",  # pragma: allowlist secret
            )

    def test_password_too_short(self) -> None:
        """Test password shorter than 8 characters."""
        # Act & Assert
        with pytest.raises(ValidationError, match="8 characters"):
            UserCreate(
                email="test@example.com",
                username="testuser",
                password="Short1!",  # pragma: allowlist secret
            )

    def test_password_missing_uppercase(self) -> None:
        """Test password without uppercase letter."""
        # Act & Assert
        with pytest.raises(ValidationError, match="uppercase"):
            UserCreate(
                email="test@example.com",
                username="testuser",
                password="securep@ssw0rd123",  # pragma: allowlist secret
            )

    def test_password_missing_lowercase(self) -> None:
        """Test password without lowercase letter."""
        # Act & Assert
        with pytest.raises(ValidationError, match="lowercase"):
            UserCreate(
                email="test@example.com",
                username="testuser",
                password="SECUREP@SSW0RD123",  # pragma: allowlist secret
            )

    def test_password_missing_digit(self) -> None:
        """Test password without digit."""
        # Act & Assert
        with pytest.raises(ValidationError, match="digit"):
            UserCreate(
                email="test@example.com",
                username="testuser",
                password="SecureP@ssword",  # pragma: allowlist secret
            )

    def test_password_missing_special(self) -> None:
        """Test password without special character."""
        # Act & Assert
        with pytest.raises(ValidationError, match="special"):
            UserCreate(
                email="test@example.com",
                username="testuser",
                password="SecurePassword123",  # pragma: allowlist secret
            )


class TestUserUpdateSchema:
    """Test suite for UserUpdate schema validation."""

    def test_update_email_only(self) -> None:
        """Test updating only email."""
        # Act
        update = UserUpdate(email="new@example.com")

        # Assert
        assert update.email == "new@example.com"
        assert update.username is None

    def test_update_username_only(self) -> None:
        """Test updating only username."""
        # Act
        update = UserUpdate(username="newusername")

        # Assert
        assert update.username == "newusername"
        assert update.email is None

    def test_update_both_fields(self) -> None:
        """Test updating both email and username."""
        # Act
        update = UserUpdate(email="new@example.com", username="newusername")

        # Assert
        assert update.email == "new@example.com"
        assert update.username == "newusername"

    def test_update_invalid_username(self) -> None:
        """Test update with invalid username characters."""
        # Act & Assert
        with pytest.raises(ValidationError, match="letters, numbers, and underscores"):
            UserUpdate(username="test-user!")


class TestPasswordChangeSchema:
    """Test suite for PasswordChange schema validation."""

    def test_valid_password_change(self) -> None:
        """Test valid password change data."""
        # Act
        change = PasswordChange(
            current_password="OldPass123!",  # pragma: allowlist secret
            new_password="NewPass456@",  # pragma: allowlist secret
        )

        # Assert
        assert change.current_password == "OldPass123!"  # pragma: allowlist secret
        assert change.new_password == "NewPass456@"  # pragma: allowlist secret

    def test_new_password_too_weak(self) -> None:
        """Test password change with weak new password."""
        # Act & Assert
        with pytest.raises(ValidationError):
            PasswordChange(
                current_password="OldPass123!",  # pragma: allowlist secret
                new_password="weak",  # pragma: allowlist secret
            )

    def test_missing_current_password(self) -> None:
        """Test password change without current password."""
        # Act & Assert
        with pytest.raises(ValidationError):
            PasswordChange(new_password="NewPass456@")  # pragma: allowlist secret


class TestUserResponseSchema:
    """Test suite for UserResponse schema."""

    def test_valid_user_response(self) -> None:
        """Test valid user response data."""
        # Arrange
        now = datetime.now()

        # Act
        response = UserResponse(
            id=1,
            email="test@example.com",
            username="testuser",
            is_active=True,
            is_verified=False,
            created_at=now,
            updated_at=now,
            last_login=None,
            roles=["user"],
        )

        # Assert
        assert response.id == 1
        assert response.email == "test@example.com"
        assert response.username == "testuser"
        assert response.is_active is True
        assert response.is_verified is False
        assert response.roles == ["user"]

    def test_user_response_multiple_roles(self) -> None:
        """Test user response with multiple roles."""
        # Act
        response = UserResponse(
            id=1,
            email="admin@example.com",
            username="adminuser",
            is_active=True,
            is_verified=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_login=datetime.now(),
            roles=["user", "admin", "moderator"],
        )

        # Assert
        assert len(response.roles) == 3
        assert "admin" in response.roles


class TestUserListResponseSchema:
    """Test suite for UserListResponse schema."""

    def test_valid_user_list(self) -> None:
        """Test valid user list response."""
        # Arrange
        user = UserResponse(
            id=1,
            email="test@example.com",
            username="testuser",
            is_active=True,
            is_verified=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            roles=[],
        )

        # Act
        response = UserListResponse(
            users=[user], total=1, page=1, page_size=20, total_pages=1
        )

        # Assert
        assert len(response.users) == 1
        assert response.total == 1
        assert response.page == 1
        assert response.total_pages == 1

    def test_empty_user_list(self) -> None:
        """Test empty user list response."""
        # Act
        response = UserListResponse(
            users=[], total=0, page=1, page_size=20, total_pages=0
        )

        # Assert
        assert len(response.users) == 0
        assert response.total == 0


class TestUserSearchParamsSchema:
    """Test suite for UserSearchParams schema."""

    def test_default_search_params(self) -> None:
        """Test search params with defaults."""
        # Act
        params = UserSearchParams()

        # Assert
        assert params.page == 1
        assert params.page_size == 20
        assert params.sort_by == "created_at"
        assert params.sort_order == "desc"

    def test_custom_search_params(self) -> None:
        """Test search params with custom values."""
        # Act
        params = UserSearchParams(
            email="test@example.com",
            username="testuser",
            role="admin",
            is_active=True,
            is_verified=True,
            page=2,
            page_size=50,
            sort_by="username",
            sort_order="asc",
        )

        # Assert
        assert params.email == "test@example.com"
        assert params.username == "testuser"
        assert params.role == "admin"
        assert params.is_active is True
        assert params.is_verified is True
        assert params.page == 2
        assert params.page_size == 50
        assert params.sort_by == "username"
        assert params.sort_order == "asc"

    def test_invalid_page_size(self) -> None:
        """Test page size validation."""
        # Act & Assert - page_size > 100
        with pytest.raises(ValidationError):
            UserSearchParams(page_size=101)

        # page_size < 1
        with pytest.raises(ValidationError):
            UserSearchParams(page_size=0)

    def test_invalid_sort_by(self) -> None:
        """Test invalid sort_by field."""
        # Act & Assert
        with pytest.raises(ValidationError):
            UserSearchParams(sort_by="invalid_field")

    def test_invalid_sort_order(self) -> None:
        """Test invalid sort_order value."""
        # Act & Assert
        with pytest.raises(ValidationError):
            UserSearchParams(sort_order="invalid")


class TestRoleAssignmentSchema:
    """Test suite for RoleAssignment schema."""

    def test_valid_role_assignment(self) -> None:
        """Test valid role assignment."""
        # Act
        assignment = RoleAssignment(user_id=1, role="admin")

        # Assert
        assert assignment.user_id == 1
        assert assignment.role == "admin"

    def test_all_valid_roles(self) -> None:
        """Test all valid role values."""
        valid_roles = ["user", "admin", "moderator", "super_admin"]

        for role in valid_roles:
            assignment = RoleAssignment(user_id=1, role=role)
            assert assignment.role == role

    def test_invalid_role(self) -> None:
        """Test invalid role value."""
        # Act & Assert
        with pytest.raises(ValidationError):
            RoleAssignment(user_id=1, role="invalid_role")


class TestRoleResponseSchema:
    """Test suite for RoleResponse schema."""

    def test_valid_role_response(self) -> None:
        """Test valid role response."""
        # Arrange
        now = datetime.now()

        # Act
        response = RoleResponse(
            id=1, user_id=2, role="admin", granted_at=now, granted_by=1
        )

        # Assert
        assert response.id == 1
        assert response.user_id == 2
        assert response.role == "admin"
        assert response.granted_by == 1

    def test_role_response_without_granter(self) -> None:
        """Test role response without granted_by."""
        # Act
        response = RoleResponse(
            id=1, user_id=2, role="admin", granted_at=datetime.now(), granted_by=None
        )

        # Assert
        assert response.granted_by is None


class TestErrorResponseSchema:
    """Test suite for ErrorResponse schema."""

    def test_basic_error_response(self) -> None:
        """Test basic error response."""
        # Act
        error = ErrorResponse(success=False, error="Something went wrong")

        # Assert
        assert error.success is False
        assert error.error == "Something went wrong"
        assert error.details is None

    def test_error_response_with_details(self) -> None:
        """Test error response with details."""
        # Act
        error = ErrorResponse(
            success=False,
            error="Validation error",
            details={"field": "email", "issue": "invalid"},
        )

        # Assert
        assert error.details is not None
        assert error.details["field"] == "email"


class TestSuccessResponseSchema:
    """Test suite for SuccessResponse schema."""

    def test_basic_success_response(self) -> None:
        """Test basic success response."""
        # Act
        success = SuccessResponse(success=True, message="Operation successful")

        # Assert
        assert success.success is True
        assert success.message == "Operation successful"
        assert success.data is None

    def test_success_response_with_data(self) -> None:
        """Test success response with data."""
        # Act
        success = SuccessResponse(
            success=True, message="User created", data={"user_id": 1}
        )

        # Assert
        assert success.data is not None
        assert success.data["user_id"] == 1
