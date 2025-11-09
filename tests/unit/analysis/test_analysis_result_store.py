"""
Unit tests for analysis result store.

Tests SQLite storage for LLM analysis results, including caching, versioning,
and retrieval of analysis outputs.
"""

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from src.analysis.storage.analysis_results import AnalysisResult, AnalysisResultStore


class TestAnalysisResultStore:
    """Test suite for AnalysisResultStore."""

    @pytest.fixture
    def temp_marcus_root(self):
        """Create temporary Marcus root directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # Create data directory
            (root / "data").mkdir(parents=True)
            yield root

    @pytest.mark.asyncio
    async def test_store_analysis_result(self, temp_marcus_root):
        """Test storing a new analysis result."""
        # Arrange
        store = AnalysisResultStore(temp_marcus_root)
        result = AnalysisResult(
            analysis_id="anl_001",
            project_id="proj-1",
            task_id="task-1",
            analysis_type="requirement_divergence",
            timestamp=datetime.now(timezone.utc),
            version="1.0",
            result={
                "fidelity_score": 0.85,
                "divergences": [],
                "llm_interpretation": "Implementation matches requirements",
            },
        )

        # Act
        await store.store_result(result)

        # Assert - verify it was stored
        retrieved = await store.get_result(result.analysis_id)
        assert retrieved is not None
        assert retrieved.analysis_id == "anl_001"
        assert retrieved.project_id == "proj-1"
        assert retrieved.task_id == "task-1"
        assert retrieved.result["fidelity_score"] == 0.85

    @pytest.mark.asyncio
    async def test_get_nonexistent_result(self, temp_marcus_root):
        """Test retrieving a result that doesn't exist."""
        # Arrange
        store = AnalysisResultStore(temp_marcus_root)

        # Act
        result = await store.get_result("nonexistent")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_results_for_project(self, temp_marcus_root):
        """Test retrieving all results for a project."""
        # Arrange
        store = AnalysisResultStore(temp_marcus_root)

        # Store multiple results
        results = [
            AnalysisResult(
                analysis_id=f"anl_{i}",
                project_id="proj-1",
                task_id=f"task-{i}",
                analysis_type="requirement_divergence",
                timestamp=datetime.now(timezone.utc),
                version="1.0",
                result={"score": i * 0.1},
            )
            for i in range(3)
        ]

        for result in results:
            await store.store_result(result)

        # Also store result for different project
        await store.store_result(
            AnalysisResult(
                analysis_id="anl_other",
                project_id="proj-2",
                task_id="task-1",
                analysis_type="requirement_divergence",
                timestamp=datetime.now(timezone.utc),
                version="1.0",
                result={"score": 0.9},
            )
        )

        # Act
        proj1_results = await store.get_results_for_project("proj-1")

        # Assert
        assert len(proj1_results) == 3
        assert all(r.project_id == "proj-1" for r in proj1_results)
        assert "anl_other" not in [r.analysis_id for r in proj1_results]

    @pytest.mark.asyncio
    async def test_get_results_for_task(self, temp_marcus_root):
        """Test retrieving all results for a specific task."""
        # Arrange
        store = AnalysisResultStore(temp_marcus_root)

        # Store results for same task but different analysis types
        results = [
            AnalysisResult(
                analysis_id=f"anl_{analysis_type}",
                project_id="proj-1",
                task_id="task-1",
                analysis_type=analysis_type,
                timestamp=datetime.now(timezone.utc),
                version="1.0",
                result={"type": analysis_type},
            )
            for analysis_type in [
                "requirement_divergence",
                "instruction_quality",
                "decision_impact",
            ]
        ]

        for result in results:
            await store.store_result(result)

        # Act
        task_results = await store.get_results_for_task("proj-1", "task-1")

        # Assert
        assert len(task_results) == 3
        analysis_types = {r.analysis_type for r in task_results}
        assert analysis_types == {
            "requirement_divergence",
            "instruction_quality",
            "decision_impact",
        }

    @pytest.mark.asyncio
    async def test_get_latest_result_by_type(self, temp_marcus_root):
        """Test retrieving the most recent result for a specific analysis type."""
        # Arrange
        store = AnalysisResultStore(temp_marcus_root)

        # Store multiple results with different timestamps
        old_result = AnalysisResult(
            analysis_id="anl_old",
            project_id="proj-1",
            task_id="task-1",
            analysis_type="requirement_divergence",
            timestamp=datetime(2025, 11, 1, 10, 0, 0, tzinfo=timezone.utc),
            version="1.0",
            result={"fidelity_score": 0.7},
        )

        new_result = AnalysisResult(
            analysis_id="anl_new",
            project_id="proj-1",
            task_id="task-1",
            analysis_type="requirement_divergence",
            timestamp=datetime(2025, 11, 8, 10, 0, 0, tzinfo=timezone.utc),
            version="1.0",
            result={"fidelity_score": 0.85},
        )

        await store.store_result(old_result)
        await store.store_result(new_result)

        # Act
        latest = await store.get_latest_result(
            "proj-1", "task-1", "requirement_divergence"
        )

        # Assert
        assert latest is not None
        assert latest.analysis_id == "anl_new"
        assert latest.result["fidelity_score"] == 0.85

    @pytest.mark.asyncio
    async def test_update_existing_result(self, temp_marcus_root):
        """Test updating an existing analysis result."""
        # Arrange
        store = AnalysisResultStore(temp_marcus_root)

        original = AnalysisResult(
            analysis_id="anl_001",
            project_id="proj-1",
            task_id="task-1",
            analysis_type="requirement_divergence",
            timestamp=datetime.now(timezone.utc),
            version="1.0",
            result={"fidelity_score": 0.7},
        )

        await store.store_result(original)

        # Act - update with new data
        updated = AnalysisResult(
            analysis_id="anl_001",  # Same ID
            project_id="proj-1",
            task_id="task-1",
            analysis_type="requirement_divergence",
            timestamp=datetime.now(timezone.utc),
            version="1.1",  # New version
            result={"fidelity_score": 0.85},  # Updated score
        )

        await store.store_result(updated)

        # Assert
        retrieved = await store.get_result("anl_001")
        assert retrieved is not None
        assert retrieved.version == "1.1"
        assert retrieved.result["fidelity_score"] == 0.85

    @pytest.mark.asyncio
    async def test_delete_result(self, temp_marcus_root):
        """Test deleting an analysis result."""
        # Arrange
        store = AnalysisResultStore(temp_marcus_root)

        result = AnalysisResult(
            analysis_id="anl_001",
            project_id="proj-1",
            task_id="task-1",
            analysis_type="requirement_divergence",
            timestamp=datetime.now(timezone.utc),
            version="1.0",
            result={"fidelity_score": 0.85},
        )

        await store.store_result(result)

        # Act
        deleted = await store.delete_result("anl_001")

        # Assert
        assert deleted is True
        retrieved = await store.get_result("anl_001")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_result(self, temp_marcus_root):
        """Test deleting a result that doesn't exist."""
        # Arrange
        store = AnalysisResultStore(temp_marcus_root)

        # Act
        deleted = await store.delete_result("nonexistent")

        # Assert
        assert deleted is False

    @pytest.mark.asyncio
    async def test_clear_project_results(self, temp_marcus_root):
        """Test clearing all results for a project."""
        # Arrange
        store = AnalysisResultStore(temp_marcus_root)

        # Store results for multiple projects
        for project_num in range(1, 3):
            for task_num in range(1, 4):
                await store.store_result(
                    AnalysisResult(
                        analysis_id=f"anl_p{project_num}_t{task_num}",
                        project_id=f"proj-{project_num}",
                        task_id=f"task-{task_num}",
                        analysis_type="requirement_divergence",
                        timestamp=datetime.now(timezone.utc),
                        version="1.0",
                        result={"score": 0.8},
                    )
                )

        # Act
        cleared = await store.clear_project_results("proj-1")

        # Assert
        assert cleared == 3  # Should have cleared 3 results

        # Verify proj-1 results are gone
        proj1_results = await store.get_results_for_project("proj-1")
        assert len(proj1_results) == 0

        # Verify proj-2 results still exist
        proj2_results = await store.get_results_for_project("proj-2")
        assert len(proj2_results) == 3

    @pytest.mark.asyncio
    async def test_result_versioning(self, temp_marcus_root):
        """Test that we can store multiple versions of same analysis."""
        # Arrange
        store = AnalysisResultStore(temp_marcus_root)

        # Store v1.0
        v1 = AnalysisResult(
            analysis_id="anl_v1",
            project_id="proj-1",
            task_id="task-1",
            analysis_type="requirement_divergence",
            timestamp=datetime.now(timezone.utc),
            version="1.0",
            result={"algorithm": "basic"},
        )

        # Store v2.0 (different analysis_id, same task)
        v2 = AnalysisResult(
            analysis_id="anl_v2",
            project_id="proj-1",
            task_id="task-1",
            analysis_type="requirement_divergence",
            timestamp=datetime.now(timezone.utc),
            version="2.0",
            result={"algorithm": "advanced"},
        )

        await store.store_result(v1)
        await store.store_result(v2)

        # Act - get latest should return v2
        latest = await store.get_latest_result(
            "proj-1", "task-1", "requirement_divergence"
        )

        # Assert
        assert latest is not None
        assert latest.version == "2.0"
        assert latest.result["algorithm"] == "advanced"

        # Both versions should be retrievable by ID
        v1_retrieved = await store.get_result("anl_v1")
        v2_retrieved = await store.get_result("anl_v2")
        assert v1_retrieved is not None
        assert v2_retrieved is not None

    @pytest.mark.asyncio
    async def test_project_level_analysis(self, temp_marcus_root):
        """Test storing project-level analysis (no task_id)."""
        # Arrange
        store = AnalysisResultStore(temp_marcus_root)

        result = AnalysisResult(
            analysis_id="anl_project",
            project_id="proj-1",
            task_id=None,  # Project-level analysis
            analysis_type="overall_assessment",
            timestamp=datetime.now(timezone.utc),
            version="1.0",
            result={
                "requirement_fidelity": 0.82,
                "user_alignment": 0.75,
                "functional_status": "PARTIAL",
            },
        )

        # Act
        await store.store_result(result)

        # Assert
        retrieved = await store.get_result("anl_project")
        assert retrieved is not None
        assert retrieved.task_id is None
        assert retrieved.result["functional_status"] == "PARTIAL"
