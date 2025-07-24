"""
Unit tests for phase dependency enforcer component label fix.

Tests that the phase dependency enforcer correctly handles component: prefixed labels
and only blocks implementation tasks within the same component/feature.
"""

from unittest.mock import Mock

import pytest

from src.core.models import Task, TaskStatus
from src.core.phase_dependency_enforcer import PhaseDependencyEnforcer


class TestPhaseDependencyEnforcerComponentFix:
    """Test phase dependency enforcer with component: prefixed labels."""

    @pytest.fixture
    def enforcer(self):
        """Create a phase dependency enforcer instance."""
        return PhaseDependencyEnforcer()

    def test_component_prefix_labels_grouped_correctly(self, enforcer):
        """Test that tasks with component: prefix are grouped by feature correctly."""
        # Create tasks for authentication component
        auth_design = Mock(spec=Task)
        auth_design.id = "task-1"
        auth_design.name = "Design authentication flow"
        auth_design.description = ""
        auth_design.labels = ["component:authentication", "phase:design"]
        auth_design.development_phase = "design"
        auth_design.status = TaskStatus.TODO
        auth_design.dependencies = []

        auth_impl = Mock(spec=Task)
        auth_impl.id = "task-2"
        auth_impl.name = "Implement login endpoint"
        auth_impl.description = ""
        auth_impl.labels = ["component:authentication", "phase:implementation"]
        auth_impl.development_phase = "implementation"
        auth_impl.status = TaskStatus.TODO
        auth_impl.dependencies = []

        # Create tasks for frontend component
        frontend_design = Mock(spec=Task)
        frontend_design.id = "task-3"
        frontend_design.name = "Design dashboard UI"
        frontend_design.description = ""
        frontend_design.labels = ["component:frontend", "phase:design"]
        frontend_design.development_phase = "design"
        frontend_design.status = TaskStatus.TODO
        frontend_design.dependencies = []

        frontend_impl = Mock(spec=Task)
        frontend_impl.id = "task-4"
        frontend_impl.name = "Implement dashboard components"
        frontend_impl.description = ""
        frontend_impl.labels = ["component:frontend", "phase:implementation"]
        frontend_impl.development_phase = "implementation"
        frontend_impl.status = TaskStatus.TODO
        frontend_impl.dependencies = []

        tasks = [auth_design, auth_impl, frontend_design, frontend_impl]

        # Apply phase dependencies
        enforcer.enforce_phase_dependencies(tasks)

        # Auth implementation should be blocked by auth design
        assert auth_impl.dependencies == ["task-1"]

        # Frontend implementation should be blocked by frontend design
        assert frontend_impl.dependencies == ["task-3"]

        # Cross-component blocking should NOT occur
        # Frontend implementation should NOT be blocked by auth design
        assert "task-1" not in frontend_impl.dependencies

        # Auth implementation should NOT be blocked by frontend design
        assert "task-3" not in auth_impl.dependencies

    def test_mixed_label_formats_handled(self, enforcer):
        """Test that both 'component:frontend' and 'frontend' labels work."""
        # Task with component: prefix
        task1 = Mock(spec=Task)
        task1.id = "task-1"
        task1.name = "Design with prefix"
        task1.description = ""
        task1.labels = ["component:frontend", "phase:design"]
        task1.development_phase = "design"
        task1.status = TaskStatus.TODO
        task1.dependencies = []

        # Task without prefix
        task2 = Mock(spec=Task)
        task2.id = "task-2"
        task2.name = "Design without prefix"
        task2.description = ""
        task2.labels = ["frontend", "phase:design"]
        task2.development_phase = "design"
        task2.status = TaskStatus.TODO
        task2.dependencies = []

        # Implementation task
        impl_task = Mock(spec=Task)
        impl_task.id = "task-3"
        impl_task.name = "Implement frontend"
        impl_task.description = ""
        impl_task.labels = ["component:frontend", "phase:implementation"]
        impl_task.development_phase = "implementation"
        impl_task.status = TaskStatus.TODO
        impl_task.dependencies = []

        tasks = [task1, task2, impl_task]

        # Apply phase dependencies
        enforcer.enforce_phase_dependencies(tasks)

        # Implementation should be blocked by both design tasks
        # (they're in the same feature despite different label formats)
        assert set(impl_task.dependencies) == {"task-1", "task-2"}

    def test_no_cross_feature_blocking(self, enforcer):
        """Test that design tasks in one feature don't block implementation in another."""
        # Multiple features with design tasks
        features = ["authentication", "frontend", "backend", "api"]
        tasks = []

        # Create design task for each feature
        for i, feature in enumerate(features):
            design_task = Mock(spec=Task)
            design_task.id = f"design-{i}"
            design_task.name = f"Design {feature}"
            design_task.description = ""
            design_task.labels = [f"component:{feature}", "phase:design"]
            design_task.development_phase = "design"
            design_task.status = TaskStatus.TODO
            design_task.dependencies = []
            tasks.append(design_task)

        # Create implementation task for just authentication
        auth_impl = Mock(spec=Task)
        auth_impl.id = "auth-impl"
        auth_impl.name = "Implement authentication"
        auth_impl.description = ""
        auth_impl.labels = ["component:authentication", "phase:implementation"]
        auth_impl.development_phase = "implementation"
        auth_impl.status = TaskStatus.TODO
        auth_impl.dependencies = []
        tasks.append(auth_impl)

        # Apply phase dependencies
        enforcer.enforce_phase_dependencies(tasks)

        # Auth implementation should ONLY be blocked by auth design
        assert auth_impl.dependencies == ["design-0"]  # Only auth design task

        # Should NOT be blocked by other feature design tasks
        assert "design-1" not in auth_impl.dependencies  # frontend
        assert "design-2" not in auth_impl.dependencies  # backend
        assert "design-3" not in auth_impl.dependencies  # api
