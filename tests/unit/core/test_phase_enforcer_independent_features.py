"""
Unit tests for phase dependency enforcer with independent features.

Tests that the enforcer correctly handles independent features without
creating unnecessary cross-feature dependencies.
"""

from datetime import datetime

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.core.phase_dependency_enforcer import PhaseDependencyEnforcer


@pytest.fixture
def enforcer():
    """Create phase dependency enforcer instance."""
    return PhaseDependencyEnforcer()


@pytest.fixture
def independent_api_tasks():
    """
    Create tasks for two independent API endpoints.

    Feature 1: List Users (GET /users)
    Feature 2: Get User by ID (GET /users/{id})

    These should NOT depend on each other.
    """
    now = datetime.now()

    return [
        # Feature 1: List Users
        Task(
            id="design-list",
            name="Design List Users",
            description="Design GET /users endpoint",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=now,
            updated_at=now,
            due_date=None,
            estimated_hours=4.0,
            dependencies=[],
            labels=[],
        ),
        Task(
            id="impl-list",
            name="Implement List Users",
            description="Implement GET /users endpoint",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=now,
            updated_at=now,
            due_date=None,
            estimated_hours=8.0,
            dependencies=[],
            labels=[],
        ),
        Task(
            id="test-list",
            name="Test List Users",
            description="Test GET /users endpoint",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=now,
            updated_at=now,
            due_date=None,
            estimated_hours=4.0,
            dependencies=[],
            labels=[],
        ),
        # Feature 2: Get User by ID
        Task(
            id="design-get",
            name="Design Get User by ID",
            description="Design GET /users/{id} endpoint",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=now,
            updated_at=now,
            due_date=None,
            estimated_hours=4.0,
            dependencies=[],
            labels=[],
        ),
        Task(
            id="impl-get",
            name="Implement Get User by ID",
            description="Implement GET /users/{id} endpoint",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=now,
            updated_at=now,
            due_date=None,
            estimated_hours=8.0,
            dependencies=[],
            labels=[],
        ),
        Task(
            id="test-get",
            name="Test Get User by ID",
            description="Test GET /users/{id} endpoint",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=now,
            updated_at=now,
            due_date=None,
            estimated_hours=4.0,
            dependencies=[],
            labels=[],
        ),
    ]


def test_independent_features_no_cross_dependencies(enforcer, independent_api_tasks):
    """
    Test that independent features don't create cross-dependencies.

    Feature 1 (List Users) and Feature 2 (Get User by ID) are independent.
    After phase enforcement:
    - "Implement List Users" should depend ONLY on "Design List Users"
    - "Implement Get User by ID" should depend ONLY on "Design Get User by ID"
    - NO cross-feature dependencies
    """
    result = enforcer.enforce_phase_dependencies(independent_api_tasks)

    # Find tasks
    impl_list = next(t for t in result if t.id == "impl-list")
    impl_get = next(t for t in result if t.id == "impl-get")
    test_list = next(t for t in result if t.id == "test-list")
    test_get = next(t for t in result if t.id == "test-get")

    # Feature 1: Implement List Users
    assert (
        "design-list" in impl_list.dependencies
    ), "Implement List Users should depend on Design List Users"
    assert "design-get" not in impl_list.dependencies, (
        "Implement List Users should NOT depend on Design Get User by ID "
        "(different feature!)"
    )

    # Feature 2: Implement Get User by ID
    assert (
        "design-get" in impl_get.dependencies
    ), "Implement Get User by ID should depend on Design Get User by ID"
    assert "design-list" not in impl_get.dependencies, (
        "Implement Get User by ID should NOT depend on Design List Users "
        "(different feature!)"
    )

    # Feature 1: Test List Users
    assert (
        "impl-list" in test_list.dependencies
    ), "Test List Users should depend on Implement List Users"
    assert "impl-get" not in test_list.dependencies, (
        "Test List Users should NOT depend on Implement Get User by ID "
        "(different feature!)"
    )

    # Feature 2: Test Get User by ID
    assert (
        "impl-get" in test_get.dependencies
    ), "Test Get User by ID should depend on Implement Get User by ID"
    assert "impl-list" not in test_get.dependencies, (
        "Test Get User by ID should NOT depend on Implement List Users "
        "(different feature!)"
    )


def test_feature_detection_fine_grained(enforcer, independent_api_tasks):
    """
    Test that feature detection is fine-grained enough to separate
    "List Users" from "Get User by ID".
    """
    # Get feature IDs
    design_list = independent_api_tasks[0]
    design_get = independent_api_tasks[3]

    feature_list = enforcer._identify_task_feature(design_list)
    feature_get = enforcer._identify_task_feature(design_get)

    # They should be DIFFERENT features
    assert feature_list != feature_get, (
        f"'List Users' ({feature_list}) and 'Get User by ID' ({feature_get}) "
        "should be identified as different features"
    )

    # Check specific names
    assert (
        "list" in feature_list.lower()
    ), f"List Users feature should contain 'list', got: {feature_list}"
    assert (
        "get" in feature_get.lower() or "id" in feature_get.lower()
    ), f"Get User by ID feature should contain 'get' or 'id', got: {feature_get}"


def test_explicit_feature_labels_respected(enforcer):
    """Test that explicit feature: labels are respected and prevent grouping."""
    now = datetime.now()

    tasks = [
        Task(
            id="1",
            name="Design User Authentication",
            description="",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=now,
            updated_at=now,
            due_date=None,
            estimated_hours=4.0,
            labels=["feature:auth"],
        ),
        Task(
            id="2",
            name="Implement User Authentication",
            description="",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=now,
            updated_at=now,
            due_date=None,
            estimated_hours=8.0,
            labels=["feature:auth"],
        ),
        Task(
            id="3",
            name="Design User Profile Management",
            description="",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=now,
            updated_at=now,
            due_date=None,
            estimated_hours=4.0,
            labels=["feature:profile"],
        ),
        Task(
            id="4",
            name="Implement User Profile Management",
            description="",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=now,
            updated_at=now,
            due_date=None,
            estimated_hours=8.0,
            labels=["feature:profile"],
        ),
    ]

    result = enforcer.enforce_phase_dependencies(tasks)

    impl_auth = next(t for t in result if t.id == "2")
    impl_profile = next(t for t in result if t.id == "4")

    # Auth implementation should depend on auth design
    assert "1" in impl_auth.dependencies

    # Auth implementation should NOT depend on profile design
    assert "3" not in impl_auth.dependencies

    # Profile implementation should depend on profile design
    assert "3" in impl_profile.dependencies

    # Profile implementation should NOT depend on auth design
    assert "1" not in impl_profile.dependencies
