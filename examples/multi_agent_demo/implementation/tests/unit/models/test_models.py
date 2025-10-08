"""
Unit tests for database models.

Tests model creation, relationships, and cascade behavior using in-memory SQLite.
"""

import pytest
from datetime import date, datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from app.models import Base, User, Project, Task, Comment
from app.models.task import TaskStatus, TaskPriority


@pytest.fixture
def engine():
    """Create in-memory SQLite database engine for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def db_session(engine):
    """Create database session for testing."""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_user(db_session):
    """Create a sample user for testing."""
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash="$2b$12$hashed_password"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_project(db_session, sample_user):
    """Create a sample project for testing."""
    project = Project(
        name="Test Project",
        description="A test project",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        created_by=sample_user.id
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


@pytest.fixture
def sample_task(db_session, sample_project, sample_user):
    """Create a sample task for testing."""
    task = Task(
        title="Test Task",
        description="A test task",
        due_date=date(2025, 6, 1),
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
        project_id=sample_project.id,
        assigned_to=sample_user.id,
        created_by=sample_user.id
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


class TestUserModel:
    """Test suite for User model."""

    def test_create_user_successfully(self, db_session):
        """Test creating a user with valid data."""
        # Arrange & Act
        user = User(
            username="johndoe",
            email="john@example.com",
            password_hash="hashed_password"
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

    def test_user_unique_username_constraint(self, db_session, sample_user):
        """Test that username must be unique."""
        # Arrange
        duplicate_user = User(
            username=sample_user.username,  # Duplicate username
            email="different@example.com",
            password_hash="hash"
        )

        # Act & Assert
        db_session.add(duplicate_user)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_user_unique_email_constraint(self, db_session, sample_user):
        """Test that email must be unique."""
        # Arrange
        duplicate_user = User(
            username="differentuser",
            email=sample_user.email,  # Duplicate email
            password_hash="hash"
        )

        # Act & Assert
        db_session.add(duplicate_user)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_user_to_dict_method(self, sample_user):
        """Test converting user to dictionary."""
        # Act
        user_dict = sample_user.to_dict()

        # Assert
        assert isinstance(user_dict, dict)
        assert user_dict['id'] == sample_user.id
        assert user_dict['username'] == sample_user.username
        assert user_dict['email'] == sample_user.email

    def test_user_repr_method(self, sample_user):
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
            created_by=sample_user.id
        )
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        # Assert
        assert project.id is not None
        assert project.name == "New Project"
        assert project.created_by == sample_user.id
        assert project.created_at is not None

    def test_project_creator_relationship(self, db_session, sample_project, sample_user):
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
        project = Project(
            name="Undated Project",
            created_by=sample_user.id
        )
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
            created_by=sample_user.id
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
            priority=TaskPriority.MEDIUM
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
            status=TaskStatus.TODO
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        # Assert
        assert task.priority == TaskPriority.MEDIUM

    def test_task_relationships(self, db_session, sample_task, sample_project, sample_user):
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
            priority=TaskPriority.LOW
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
            task_id=sample_task.id
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
            text="Test comment",
            user_id=sample_user.id,
            task_id=sample_task.id
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

    def test_deleting_project_cascades_to_tasks(self, db_session, sample_project, sample_task):
        """Test that deleting a project deletes all its tasks."""
        # Arrange
        project_id = sample_project.id
        task_id = sample_task.id

        # Act
        db_session.delete(sample_project)
        db_session.commit()

        # Assert
        assert db_session.query(Project).filter(Project.id == project_id).first() is None
        assert db_session.query(Task).filter(Task.id == task_id).first() is None

    def test_deleting_task_cascades_to_comments(self, db_session, sample_task, sample_user):
        """Test that deleting a task deletes all its comments."""
        # Arrange
        comment = Comment(
            text="Test comment",
            user_id=sample_user.id,
            task_id=sample_task.id
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
        assert db_session.query(Comment).filter(Comment.id == comment_id).first() is None

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
            priority=TaskPriority.MEDIUM
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

    def test_created_at_set_automatically(self, db_session):
        """Test that created_at is set automatically."""
        # Arrange & Act
        user = User(username="user", email="user@example.com", password_hash="hash")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Assert
        assert user.created_at is not None
        assert isinstance(user.created_at, datetime)

    def test_updated_at_set_automatically(self, db_session):
        """Test that updated_at is set automatically."""
        # Arrange & Act
        user = User(username="user", email="user@example.com", password_hash="hash")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Assert
        assert user.updated_at is not None
        assert isinstance(user.updated_at, datetime)
