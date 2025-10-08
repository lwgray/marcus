"""Initial database schema with User, Project, Task, and Comment models

Revision ID: 8f03f242faea
Revises:
Create Date: 2025-10-08 06:56:23.576602

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8f03f242faea"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema.

    Creates tables for:
    - users: User authentication and profiles
    - projects: Project management
    - tasks: Task tracking and assignments
    - comments: Task discussions
    """
    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("email", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("username", name="uq_users_username"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_username", "users", ["username"])
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_username_email", "users", ["username", "email"])

    # Create projects table
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_projects_created_by_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_projects"),
    )
    op.create_index("ix_projects_name", "projects", ["name"])
    op.create_index("ix_projects_created_by", "projects", ["created_by"])
    op.create_index("ix_projects_created_by_name", "projects", ["created_by", "name"])
    op.create_index("ix_projects_dates", "projects", ["start_date", "end_date"])

    # Create tasks table
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="todo"
        ),
        sa.Column(
            "priority", sa.String(length=20), nullable=False, server_default="medium"
        ),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("assigned_to", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_tasks_project_id_projects",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_to"],
            ["users.id"],
            name="fk_tasks_assigned_to_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_tasks_created_by_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tasks"),
    )
    op.create_index("ix_tasks_title", "tasks", ["title"])
    op.create_index("ix_tasks_due_date", "tasks", ["due_date"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_priority", "tasks", ["priority"])
    op.create_index("ix_tasks_project_id", "tasks", ["project_id"])
    op.create_index("ix_tasks_assigned_to", "tasks", ["assigned_to"])
    op.create_index("ix_tasks_created_by", "tasks", ["created_by"])
    op.create_index("ix_tasks_project_status", "tasks", ["project_id", "status"])
    op.create_index("ix_tasks_assigned_status", "tasks", ["assigned_to", "status"])
    op.create_index("ix_tasks_priority_status", "tasks", ["priority", "status"])
    op.create_index("ix_tasks_due_date_status", "tasks", ["due_date", "status"])

    # Create comments table
    op.create_table(
        "comments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_comments_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
            name="fk_comments_task_id_tasks",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_comments"),
    )
    op.create_index("ix_comments_user_id", "comments", ["user_id"])
    op.create_index("ix_comments_task_id", "comments", ["task_id"])
    op.create_index("ix_comments_task_created", "comments", ["task_id", "created_at"])
    op.create_index("ix_comments_user_created", "comments", ["user_id", "created_at"])


def downgrade() -> None:
    """
    Downgrade schema.

    Drops all tables in reverse dependency order:
    comments → tasks → projects → users
    """
    # Drop tables in reverse order
    op.drop_index("ix_comments_user_created", table_name="comments")
    op.drop_index("ix_comments_task_created", table_name="comments")
    op.drop_index("ix_comments_task_id", table_name="comments")
    op.drop_index("ix_comments_user_id", table_name="comments")
    op.drop_table("comments")

    op.drop_index("ix_tasks_due_date_status", table_name="tasks")
    op.drop_index("ix_tasks_priority_status", table_name="tasks")
    op.drop_index("ix_tasks_assigned_status", table_name="tasks")
    op.drop_index("ix_tasks_project_status", table_name="tasks")
    op.drop_index("ix_tasks_created_by", table_name="tasks")
    op.drop_index("ix_tasks_assigned_to", table_name="tasks")
    op.drop_index("ix_tasks_project_id", table_name="tasks")
    op.drop_index("ix_tasks_priority", table_name="tasks")
    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_index("ix_tasks_due_date", table_name="tasks")
    op.drop_index("ix_tasks_title", table_name="tasks")
    op.drop_table("tasks")

    op.drop_index("ix_projects_dates", table_name="projects")
    op.drop_index("ix_projects_created_by_name", table_name="projects")
    op.drop_index("ix_projects_created_by", table_name="projects")
    op.drop_index("ix_projects_name", table_name="projects")
    op.drop_table("projects")

    op.drop_index("ix_users_username_email", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
