"""
Unit tests for database models.

Tests model creation, relationships, and cascade behavior using in-memory SQLite.
"""

from datetime import date, datetime
from typing import Generator

import pytest
import sqlalchemy as sa
from app.models import Base, Comment, Project, Task, User
from app.models.task import TaskPriority, TaskStatus
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture
def engine() -> sa.engine.Engine:
    """Create in-memory SQLite database engine for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)

    # Enable foreign key constraints in SQLite
    from sqlalchemy import event
    from typing import Any

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def db_session(engine: sa.engine.Engine) -> Generator[Session, None, None]:
    """Create database session for testing."""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_user(db_session: Session) -> User:
    """Create a sample user for testing."""
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash="$2b$12$hashed_password",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_project(db_session: Session, sample_user: User) -> Project:
    """Create a sample project for testing."""
    project = Project(
        name="Test Project",
        description="A test project",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        created_by=sample_user.id,
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


@pytest.fixture
def sample_task(
    db_session: Session, sample_project: Project, sample_user: User
) -> Task:
    """Create a sample task for testing."""
    task = Task(
        title="Test Task",
        description="A test task",
        due_date=date(2025, 6, 1),
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
        project_id=sample_project.id,
        assigned_to=sample_user.id,
        created_by=sample_user.id,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


class TestUserModel:
    """Test suite for User model."""

    def test_create_user_successfully(self, db_session: Session) -> None:
        """Test creating a user with valid data."""
        # Arrange & Act
        user = User(
            username="johndoe",
            email="john@example.com",
            password_hash="hashed_password",  # pragma: allowlist secret
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Assert
        assert user.id is not None
        assert user.username == "johndoe"
        assert user.email == "john@example.com"
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_user_unique_username_constraint(
        self, db_session: Session, sample_user: User
    ) -> None:
        """Test that username must be unique."""
        # Arrange
        duplicate_user = User(
            username=sample_user.username,  # Duplicate username
            email="different@example.com",
            password_hash="hash",  # pragma: allowlist secret
        )

        # Act & Assert
        db_session.add(duplicate_user)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_user_unique_email_constraint(
        self, db_session: Session, sample_user: User
    ) -> None:
        """Test that email must be unique."""
        # Arrange
        duplicate_user = User(
            username="differentuser",
            email=sample_user.email,  # Duplicate email
            password_hash="hash",  # pragma: allowlist secret
        )

        # Act & Assert
        db_session.add(duplicate_user)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_user_to_dict_method(self, sample_user: User) -> None:
        """Test converting user to dictionary."""
        # Act
        user_dict = sample_user.to_dict()

        # Assert
        assert isinstance(user_dict, dict)
        assert user_dict["id"] == sample_user.id
        assert user_dict["username"] == sample_user.username
        assert user_dict["email"] == sample_user.email

    def test_user_repr_method(self, sample_user: User) -> None:
        """Test user string representation."""
        # Act
        repr_str = repr(sample_user)

        # Assert
        assert "User" in repr_str
        assert str(sample_user.id) in repr_str
        assert sample_user.username in repr_str


class TestProjectModel:
    """Test suite for Project model."""

    def test_create_project_successfully(self, db_session, sample_user):
        """Test creating a project with valid data."""
        # Arrange & Act
        project = Project(
            name="New Project",
            description="Project description",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 6, 30),
            created_by=sample_user.id,
        )
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        # Assert
        assert project.id is not None
        assert project.name == "New Project"
        assert project.created_by == sample_user.id
        assert project.created_at is not None

    def test_project_creator_relationship(
        self, db_session, sample_project, sample_user
    ):
        """Test project creator relationship."""
        # Act
        creator = sample_project.creator

        # Assert
        assert creator.id == sample_user.id
        assert creator.username == sample_user.username

    def test_project_tasks_relationship(self, db_session, sample_project, sample_task):
        """Test project tasks relationship."""
        # Act
        tasks = sample_project.tasks

        # Assert
        assert len(tasks) == 1
        assert tasks[0].id == sample_task.id

    def test_project_nullable_dates(self, db_session, sample_user):
        """Test that project dates are nullable."""
        # Arrange & Act
        project = Project(name="Undated Project", created_by=sample_user.id)
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        # Assert
        assert project.start_date is None
        assert project.end_date is None


class TestTaskModel:
    """Test suite for Task model."""

    def test_create_task_successfully(self, db_session, sample_project, sample_user):
        """Test creating a task with valid data."""
        # Arrange & Act
        task = Task(
            title="New Task",
            description="Task description",
            due_date=date(2025, 3, 1),
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            project_id=sample_project.id,
            assigned_to=sample_user.id,
            created_by=sample_user.id,
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        # Assert
        assert task.id is not None
        assert task.title == "New Task"
        assert task.status == TaskStatus.TODO
        assert task.priority == TaskPriority.HIGH

    def test_task_default_status(self, db_session, sample_project):
        """Test that task status defaults to TODO."""
        # Arrange & Act
        task = Task(
            title="Task with default status",
            project_id=sample_project.id,
            priority=TaskPriority.MEDIUM,
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        # Assert
        assert task.status == TaskStatus.TODO

    def test_task_default_priority(self, db_session, sample_project):
        """Test that task priority defaults to MEDIUM."""
        # Arrange & Act
        task = Task(
            title="Task with default priority",
            project_id=sample_project.id,
            status=TaskStatus.TODO,
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        # Assert
        assert task.priority == TaskPriority.MEDIUM

    def test_task_relationships(
        self, db_session, sample_task, sample_project, sample_user
    ):
        """Test task relationships with project and users."""
        # Act & Assert - Project relationship
        assert sample_task.project.id == sample_project.id

        # Assert - Assignee relationship
        assert sample_task.assignee.id == sample_user.id

        # Assert - Creator relationship
        assert sample_task.creator.id == sample_user.id

    def test_task_nullable_assigned_to(self, db_session, sample_project, sample_user):
        """Test that assigned_to is nullable for unassigned tasks."""
        # Arrange & Act
        task = Task(
            title="Unassigned Task",
            project_id=sample_project.id,
            created_by=sample_user.id,
            status=TaskStatus.TODO,
            priority=TaskPriority.LOW,
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        # Assert
        assert task.assigned_to is None
        assert task.assignee is None


class TestCommentModel:
    """Test suite for Comment model."""

    def test_create_comment_successfully(self, db_session, sample_task, sample_user):
        """Test creating a comment with valid data."""
        # Arrange & Act
        comment = Comment(
            text="This is a test comment",
            user_id=sample_user.id,
            task_id=sample_task.id,
        )
        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)

        # Assert
        assert comment.id is not None
        assert comment.text == "This is a test comment"
        assert comment.user_id == sample_user.id
        assert comment.task_id == sample_task.id

    def test_comment_relationships(self, db_session, sample_task, sample_user):
        """Test comment relationships with task and author."""
        # Arrange
        comment = Comment(
            text="Test comment", user_id=sample_user.id, task_id=sample_task.id
        )
        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)

        # Act & Assert - Author relationship
        assert comment.author.id == sample_user.id
        assert comment.author.username == sample_user.username

        # Assert - Task relationship
        assert comment.task.id == sample_task.id


class TestCascadeRules:
    """Test suite for cascade delete behavior."""

    def test_deleting_project_cascades_to_tasks(
        self, db_session, sample_project, sample_task
    ):
        """Test that deleting a project deletes all its tasks."""
        # Arrange
        project_id = sample_project.id
        task_id = sample_task.id

        # Act
        db_session.delete(sample_project)
        db_session.commit()

        # Assert
        assert (
            db_session.query(Project).filter(Project.id == project_id).first() is None
        )
        assert db_session.query(Task).filter(Task.id == task_id).first() is None

    def test_deleting_task_cascades_to_comments(
        self, db_session, sample_task, sample_user
    ):
        """Test that deleting a task deletes all its comments."""
        # Arrange
        comment = Comment(
            text="Test comment", user_id=sample_user.id, task_id=sample_task.id
        )
        db_session.add(comment)
        db_session.commit()
        comment_id = comment.id
        task_id = sample_task.id

        # Act
        db_session.delete(sample_task)
        db_session.commit()

        # Assert
        assert db_session.query(Task).filter(Task.id == task_id).first() is None
        assert (
            db_session.query(Comment).filter(Comment.id == comment_id).first() is None
        )

    def test_deleting_user_cascades_to_assigned_tasks(self, db_session, sample_user):
        """Test that deleting a user deletes tasks assigned to them."""
        # Arrange
        project = Project(name="Project", created_by=sample_user.id)
        db_session.add(project)
        db_session.commit()

        task = Task(
            title="Assigned Task",
            project_id=project.id,
            assigned_to=sample_user.id,
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
        )
        db_session.add(task)
        db_session.commit()
        task_id = task.id
        user_id = sample_user.id

        # Act
        db_session.delete(sample_user)
        db_session.commit()

        # Assert
        assert db_session.query(User).filter(User.id == user_id).first() is None
        assert db_session.query(Task).filter(Task.id == task_id).first() is None


class TestTimestamps:
    """Test suite for automatic timestamp behavior."""

    def test_created_at_set_automatically(self, db_session: Session) -> None:
        """Test that created_at is set automatically."""
        # Arrange & Act
        user = User(username="user", email="user@example.com", password_hash="hash")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Assert
        assert user.created_at is not None
        assert isinstance(user.created_at, datetime)

    def test_updated_at_set_automatically(self, db_session: Session) -> None:
        """Test that updated_at is set automatically."""
        # Arrange & Act
        user = User(username="user", email="user@example.com", password_hash="hash")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Assert
        assert user.updated_at is not None
        assert isinstance(user.updated_at, datetime)

    def test_updated_at_changes_on_modification(
        self, db_session: Session, sample_user: User
    ) -> None:
        """Test that updated_at is modified when entity is updated."""
        # Arrange
        original_updated_at = sample_user.updated_at

        # Delay to ensure timestamp difference (SQLite datetime has 1s precision)
        import time

        time.sleep(1.1)

        # Act - Modify user
        sample_user.email = "newemail@example.com"
        db_session.commit()
        db_session.refresh(sample_user)

        # Assert
        assert sample_user.updated_at > original_updated_at


class TestUserRoleModel:
    """Test suite for UserRole model."""

    def test_create_user_role_successfully(
        self, db_session: Session, sample_user: User
    ) -> None:
        """Test creating a user role with valid data."""
        # Arrange & Act
        from app.models.user_role import Role, UserRole

        user_role = UserRole(user_id=sample_user.id, role=Role.ADMIN)
        db_session.add(user_role)
        db_session.commit()
        db_session.refresh(user_role)

        # Assert
        assert user_role.id is not None
        assert user_role.user_id == sample_user.id
        assert user_role.role == Role.ADMIN
        assert user_role.granted_at is not None

    def test_user_role_relationship(
        self, db_session: Session, sample_user: User
    ) -> None:
        """Test user_role to user relationship."""
        # Arrange
        from app.models.user_role import Role, UserRole

        user_role = UserRole(user_id=sample_user.id, role=Role.USER)
        db_session.add(user_role)
        db_session.commit()
        db_session.refresh(user_role)

        # Act & Assert
        assert user_role.user.id == sample_user.id
        assert user_role.user.username == sample_user.username

    def test_user_role_unique_constraint(
        self, db_session: Session, sample_user: User
    ) -> None:
        """Test that (user_id, role) combination must be unique."""
        # Arrange
        from app.models.user_role import Role, UserRole

        user_role1 = UserRole(user_id=sample_user.id, role=Role.ADMIN)
        db_session.add(user_role1)
        db_session.commit()

        # Act & Assert - Try to add duplicate role
        user_role2 = UserRole(user_id=sample_user.id, role=Role.ADMIN)
        db_session.add(user_role2)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_user_role_granted_by_nullable(
        self, db_session: Session, sample_user: User
    ) -> None:
        """Test that granted_by is nullable."""
        # Arrange & Act
        from app.models.user_role import Role, UserRole

        user_role = UserRole(
            user_id=sample_user.id, role=Role.MODERATOR, granted_by=None
        )
        db_session.add(user_role)
        db_session.commit()
        db_session.refresh(user_role)

        # Assert
        assert user_role.granted_by is None

    def test_user_role_repr(self, db_session: Session, sample_user: User) -> None:
        """Test user role string representation."""
        # Arrange
        from app.models.user_role import Role, UserRole

        user_role = UserRole(user_id=sample_user.id, role=Role.ADMIN)
        db_session.add(user_role)
        db_session.commit()

        # Act
        repr_str = repr(user_role)

        # Assert
        assert "UserRole" in repr_str
        assert str(sample_user.id) in repr_str
        assert Role.ADMIN in repr_str

    def test_role_class_all_roles(self) -> None:
        """Test Role.all_roles() returns all available roles."""
        # Arrange
        from app.models.user_role import Role

        # Act
        roles = Role.all_roles()

        # Assert
        assert len(roles) == 4
        assert Role.USER in roles
        assert Role.ADMIN in roles
        assert Role.MODERATOR in roles
        assert Role.SUPER_ADMIN in roles

    def test_role_class_is_valid_role(self) -> None:
        """Test Role.is_valid_role() validates roles correctly."""
        # Arrange
        from app.models.user_role import Role

        # Act & Assert
        assert Role.is_valid_role(Role.USER) is True
        assert Role.is_valid_role(Role.ADMIN) is True
        assert Role.is_valid_role("invalid_role") is False
        assert Role.is_valid_role("") is False


class TestRefreshTokenModel:
    """Test suite for RefreshToken model."""

    def test_create_refresh_token_successfully(
        self, db_session: Session, sample_user: User
    ) -> None:
        """Test creating a refresh token with valid data."""
        # Arrange & Act
        from datetime import timedelta

        from app.models.refresh_token import RefreshToken

        expires = datetime.utcnow() + timedelta(days=7)
        token = RefreshToken(
            user_id=sample_user.id,
            token_hash="abc123hash",
            expires_at=expires,
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0",
        )
        db_session.add(token)
        db_session.commit()
        db_session.refresh(token)

        # Assert
        assert token.id is not None
        assert token.user_id == sample_user.id
        assert token.token_hash == "abc123hash"
        assert token.is_revoked is False
        assert token.created_at is not None
        assert token.revoked_at is None

    def test_refresh_token_user_relationship(
        self, db_session: Session, sample_user: User
    ) -> None:
        """Test refresh token to user relationship."""
        # Arrange
        from datetime import timedelta

        from app.models.refresh_token import RefreshToken

        expires = datetime.utcnow() + timedelta(days=7)
        token = RefreshToken(
            user_id=sample_user.id, token_hash="hash123", expires_at=expires
        )
        db_session.add(token)
        db_session.commit()
        db_session.refresh(token)

        # Act & Assert
        assert token.user.id == sample_user.id
        assert token.user.username == sample_user.username

    def test_refresh_token_unique_hash_constraint(
        self, db_session: Session, sample_user: User
    ) -> None:
        """Test that token_hash must be unique."""
        # Arrange
        from datetime import timedelta

        from app.models.refresh_token import RefreshToken

        expires = datetime.utcnow() + timedelta(days=7)
        token1 = RefreshToken(
            user_id=sample_user.id, token_hash="samehash", expires_at=expires
        )
        db_session.add(token1)
        db_session.commit()

        # Act & Assert - Try to add token with same hash
        token2 = RefreshToken(
            user_id=sample_user.id, token_hash="samehash", expires_at=expires
        )
        db_session.add(token2)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_refresh_token_is_valid_not_expired(
        self, db_session: Session, sample_user: User
    ) -> None:
        """Test is_valid() returns True for valid non-expired token."""
        # Arrange
        from datetime import timedelta

        from app.models.refresh_token import RefreshToken

        expires = datetime.utcnow() + timedelta(days=7)
        token = RefreshToken(
            user_id=sample_user.id,
            token_hash="validtoken",
            expires_at=expires,
            is_revoked=False,
        )
        db_session.add(token)
        db_session.commit()

        # Act
        is_valid = token.is_valid()

        # Assert
        assert is_valid is True

    def test_refresh_token_is_valid_expired(
        self, db_session: Session, sample_user: User
    ) -> None:
        """Test is_valid() returns False for expired token."""
        # Arrange
        from datetime import timedelta

        from app.models.refresh_token import RefreshToken

        expires = datetime.utcnow() - timedelta(days=1)  # Expired yesterday
        token = RefreshToken(
            user_id=sample_user.id,
            token_hash="expiredtoken",
            expires_at=expires,
            is_revoked=False,
        )
        db_session.add(token)
        db_session.commit()

        # Act
        is_valid = token.is_valid()

        # Assert
        assert is_valid is False

    def test_refresh_token_is_valid_revoked(
        self, db_session: Session, sample_user: User
    ) -> None:
        """Test is_valid() returns False for revoked token."""
        # Arrange
        from datetime import timedelta

        from app.models.refresh_token import RefreshToken

        expires = datetime.utcnow() + timedelta(days=7)
        token = RefreshToken(
            user_id=sample_user.id,
            token_hash="revokedtoken",
            expires_at=expires,
            is_revoked=True,
        )
        db_session.add(token)
        db_session.commit()

        # Act
        is_valid = token.is_valid()

        # Assert
        assert is_valid is False

    def test_refresh_token_revoke_method(
        self, db_session: Session, sample_user: User
    ) -> None:
        """Test revoke() method sets revocation flags."""
        # Arrange
        from datetime import timedelta

        from app.models.refresh_token import RefreshToken

        expires = datetime.utcnow() + timedelta(days=7)
        token = RefreshToken(
            user_id=sample_user.id,
            token_hash="torevoke",
            expires_at=expires,
            is_revoked=False,
        )
        db_session.add(token)
        db_session.commit()

        # Act
        token.revoke()
        db_session.commit()

        # Assert
        assert token.is_revoked is True
        assert token.revoked_at is not None
        assert token.is_valid() is False

    def test_refresh_token_repr(self, db_session: Session, sample_user: User) -> None:
        """Test refresh token string representation."""
        # Arrange
        from datetime import timedelta

        from app.models.refresh_token import RefreshToken

        expires = datetime.utcnow() + timedelta(days=7)
        token = RefreshToken(
            user_id=sample_user.id, token_hash="reprhash", expires_at=expires
        )
        db_session.add(token)
        db_session.commit()

        # Act
        repr_str = repr(token)

        # Assert
        assert "RefreshToken" in repr_str
        assert str(sample_user.id) in repr_str
        assert "revoked=False" in repr_str


class TestAdditionalCascadeRules:
    """Test suite for additional cascade delete scenarios."""

    def test_deleting_user_cascades_to_created_projects(
        self, db_session: Session, sample_user: User
    ) -> None:
        """Test that deleting a user deletes projects they created."""
        # Arrange
        project = Project(name="User's Project", created_by=sample_user.id)
        db_session.add(project)
        db_session.commit()
        project_id = project.id
        user_id = sample_user.id

        # Act
        db_session.delete(sample_user)
        db_session.commit()

        # Assert
        assert db_session.query(User).filter(User.id == user_id).first() is None
        assert (
            db_session.query(Project).filter(Project.id == project_id).first() is None
        )

    def test_deleting_user_cascades_to_comments(
        self, db_session: Session, sample_user: User
    ) -> None:
        """Test that deleting a user deletes their comments."""
        # Arrange
        project = Project(name="Project", created_by=sample_user.id)
        db_session.add(project)
        db_session.commit()

        task = Task(
            title="Task",
            project_id=project.id,
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
        )
        db_session.add(task)
        db_session.commit()

        comment = Comment(text="User comment", user_id=sample_user.id, task_id=task.id)
        db_session.add(comment)
        db_session.commit()
        comment_id = comment.id
        user_id = sample_user.id

        # Act
        db_session.delete(sample_user)
        db_session.commit()

        # Assert
        assert db_session.query(User).filter(User.id == user_id).first() is None
        assert (
            db_session.query(Comment).filter(Comment.id == comment_id).first() is None
        )

    def test_deleting_user_cascades_to_roles(
        self, db_session: Session, sample_user: User
    ) -> None:
        """Test that deleting a user deletes their role assignments."""
        # Arrange
        from app.models.user_role import Role, UserRole

        user_role = UserRole(user_id=sample_user.id, role=Role.ADMIN)
        db_session.add(user_role)
        db_session.commit()
        role_id = user_role.id
        user_id = sample_user.id

        # Act
        db_session.delete(sample_user)
        db_session.commit()

        # Assert
        assert db_session.query(User).filter(User.id == user_id).first() is None
        assert db_session.query(UserRole).filter(UserRole.id == role_id).first() is None

    def test_deleting_user_cascades_to_refresh_tokens(
        self, db_session: Session, sample_user: User
    ) -> None:
        """Test that deleting a user deletes their refresh tokens."""
        # Arrange
        from datetime import timedelta

        from app.models.refresh_token import RefreshToken

        expires = datetime.utcnow() + timedelta(days=7)
        token = RefreshToken(
            user_id=sample_user.id, token_hash="usertokenhash", expires_at=expires
        )
        db_session.add(token)
        db_session.commit()
        token_id = token.id
        user_id = sample_user.id

        # Act
        db_session.delete(sample_user)
        db_session.commit()

        # Assert
        assert db_session.query(User).filter(User.id == user_id).first() is None
        assert (
            db_session.query(RefreshToken).filter(RefreshToken.id == token_id).first()
            is None
        )


class TestModelRepresentations:
    """Test suite for model __repr__ methods."""

    def test_project_repr(self, db_session: Session, sample_project: Project) -> None:
        """Test project string representation."""
        # Act
        repr_str = repr(sample_project)

        # Assert
        assert "Project" in repr_str
        assert str(sample_project.id) in repr_str
        assert sample_project.name in repr_str

    def test_task_repr(self, db_session: Session, sample_task: Task) -> None:
        """Test task string representation."""
        # Act
        repr_str = repr(sample_task)

        # Assert
        assert "Task" in repr_str
        assert str(sample_task.id) in repr_str
        assert sample_task.title in repr_str
        assert sample_task.status.value in repr_str
        assert sample_task.priority.value in repr_str

    def test_comment_repr(
        self, db_session: Session, sample_task: Task, sample_user: User
    ) -> None:
        """Test comment string representation."""
        # Arrange
        comment = Comment(
            text="This is a comment for testing repr method",
            user_id=sample_user.id,
            task_id=sample_task.id,
        )
        db_session.add(comment)
        db_session.commit()

        # Act
        repr_str = repr(comment)

        # Assert
        assert "Comment" in repr_str
        assert str(comment.id) in repr_str
        assert str(sample_task.id) in repr_str
        assert str(sample_user.id) in repr_str


class TestForeignKeyConstraints:
    """Test suite for foreign key constraint failures."""

    def test_create_project_with_invalid_user_id_fails(
        self, db_session: Session
    ) -> None:
        """Test that creating a project with invalid user_id fails."""
        # Arrange
        project = Project(name="Invalid Project", created_by=99999)  # Non-existent user

        # Act & Assert
        db_session.add(project)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_create_task_with_invalid_project_id_fails(
        self, db_session: Session
    ) -> None:
        """Test that creating a task with invalid project_id fails."""
        # Arrange
        task = Task(
            title="Invalid Task",
            project_id=99999,  # Non-existent project
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
        )

        # Act & Assert
        db_session.add(task)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_create_comment_with_invalid_task_id_fails(
        self, db_session: Session, sample_user: User
    ) -> None:
        """Test that creating a comment with invalid task_id fails."""
        # Arrange
        comment = Comment(
            text="Invalid comment",
            user_id=sample_user.id,
            task_id=99999,  # Non-existent task
        )

        # Act & Assert
        db_session.add(comment)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_create_comment_with_invalid_user_id_fails(
        self, db_session: Session, sample_task: Task
    ) -> None:
        """Test that creating a comment with invalid user_id fails."""
        # Arrange
        comment = Comment(
            text="Invalid comment",
            user_id=99999,  # Non-existent user
            task_id=sample_task.id,
        )

        # Act & Assert
        db_session.add(comment)
        with pytest.raises(IntegrityError):
            db_session.commit()
