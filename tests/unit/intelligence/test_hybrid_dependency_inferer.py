"""
Unit tests for Hybrid Dependency Inferer

Tests the combination of pattern-based and AI-powered dependency inference
with configurable thresholds.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import json

from src.intelligence.dependency_inferer_hybrid import HybridDependencyInferer, HybridDependency
from src.config.hybrid_inference_config import HybridInferenceConfig, get_preset_config
from src.core.models import Task, TaskStatus, Priority


class TestHybridDependencyInferer:
    """Test suite for hybrid dependency inference"""
    
    @pytest.fixture
    def mock_ai_engine(self):
        """Create mock AI engine"""
        engine = Mock()
        engine._call_claude = AsyncMock()
        return engine
    
    @pytest.fixture
    def test_tasks(self):
        """Create test tasks"""
        return [
            Task(
                id="1",
                name="Design User Authentication",
                description="Design auth system architecture",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=4.0,
                labels=["design", "auth"],
                dependencies=[]
            ),
            Task(
                id="2",
                name="Implement User Login",
                description="Build login functionality",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=8.0,
                labels=["backend", "auth"],
                dependencies=[]
            ),
            Task(
                id="3",
                name="Test Authentication Flow",
                description="Test login and auth",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=4.0,
                labels=["test", "auth"],
                dependencies=[]
            ),
            Task(
                id="4",
                name="Deploy to Production",
                description="Deploy auth service",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=2.0,
                labels=["deploy", "production"],
                dependencies=[]
            )
        ]
    
    @pytest.mark.asyncio
    async def test_pattern_only_mode(self, test_tasks):
        """Test inference with AI disabled"""
        config = HybridInferenceConfig(enable_ai_inference=False)
        inferer = HybridDependencyInferer(None, config)
        
        # Should use only patterns
        graph = await inferer.infer_dependencies(test_tasks)
        
        # Check expected dependencies
        assert "1" in graph.adjacency_list  # Design has dependents
        assert "2" in graph.adjacency_list["1"]  # Implement depends on Design
        assert "2" in graph.adjacency_list  # Implement has dependents
        assert "3" in graph.adjacency_list["2"]  # Test depends on Implement
        assert "3" in graph.adjacency_list  # Test has dependents
        assert "4" in graph.adjacency_list["3"]  # Deploy depends on Test
    
    @pytest.mark.asyncio
    async def test_hybrid_mode_high_confidence_patterns(self, mock_ai_engine, test_tasks):
        """Test that high confidence patterns don't trigger AI"""
        config = HybridInferenceConfig(
            pattern_confidence_threshold=0.8,
            enable_ai_inference=True
        )
        inferer = HybridDependencyInferer(mock_ai_engine, config)
        
        # Run inference
        graph = await inferer.infer_dependencies(test_tasks)
        
        # AI should not be called for high confidence patterns
        mock_ai_engine._call_claude.assert_not_called()
        
        # But dependencies should still be found
        assert len(graph.edges) > 0
    
    @pytest.mark.asyncio
    async def test_hybrid_mode_low_confidence_triggers_ai(self, mock_ai_engine, test_tasks):
        """Test that low confidence patterns trigger AI analysis"""
        # Set very high pattern threshold so AI is triggered
        config = HybridInferenceConfig(
            pattern_confidence_threshold=0.99,  # Very high
            enable_ai_inference=True
        )
        
        # Mock AI response
        mock_ai_engine._call_claude.return_value = json.dumps([
            {
                "task1_id": "2",
                "task2_id": "1",
                "dependency_direction": "2->1",
                "confidence": 0.85,
                "reasoning": "Login implementation requires auth design",
                "dependency_type": "hard"
            }
        ])
        
        inferer = HybridDependencyInferer(mock_ai_engine, config)
        
        # Run inference
        graph = await inferer.infer_dependencies(test_tasks)
        
        # AI should be called
        mock_ai_engine._call_claude.assert_called_once()
        
        # Check AI-inferred dependency exists
        assert "1" in graph.adjacency_list
        assert "2" in graph.adjacency_list["1"]
    
    @pytest.mark.asyncio
    async def test_combined_confidence_boost(self, mock_ai_engine, test_tasks):
        """Test confidence boost when pattern and AI agree"""
        config = HybridInferenceConfig(
            pattern_confidence_threshold=0.7,
            combined_confidence_boost=0.15
        )
        
        # Mock AI to agree with pattern
        mock_ai_engine._call_claude.return_value = json.dumps([
            {
                "task1_id": "3",
                "task2_id": "2",
                "dependency_direction": "3->2",
                "confidence": 0.8,
                "reasoning": "Tests need implementation to exist",
                "dependency_type": "hard"
            }
        ])
        
        inferer = HybridDependencyInferer(mock_ai_engine, config)
        graph = await inferer.infer_dependencies(test_tasks)
        
        # Find the test->implement dependency
        test_impl_dep = None
        for dep in graph.edges:
            if dep.dependent_task_id == "3" and dep.dependency_task_id == "2":
                test_impl_dep = dep
                break
        
        assert test_impl_dep is not None
        assert isinstance(test_impl_dep, HybridDependency)
        assert test_impl_dep.inference_method == "both"
        # Confidence should be boosted
        assert test_impl_dep.confidence > test_impl_dep.pattern_confidence
        assert test_impl_dep.confidence > test_impl_dep.ai_confidence
    
    @pytest.mark.asyncio
    async def test_cache_functionality(self, mock_ai_engine, test_tasks):
        """Test that AI results are cached"""
        config = HybridInferenceConfig(
            pattern_confidence_threshold=0.99,  # Force AI
            cache_ttl_hours=24
        )
        
        mock_ai_engine._call_claude.return_value = json.dumps([])
        
        inferer = HybridDependencyInferer(mock_ai_engine, config)
        
        # First call
        await inferer.infer_dependencies(test_tasks)
        assert mock_ai_engine._call_claude.call_count == 1
        
        # Second call should use cache
        await inferer.infer_dependencies(test_tasks)
        assert mock_ai_engine._call_claude.call_count == 1  # Still 1
    
    def test_preset_configurations(self):
        """Test preset configurations"""
        # Conservative preset
        conservative = get_preset_config('conservative')
        assert conservative.pattern_confidence_threshold == 0.9
        assert conservative.ai_confidence_threshold == 0.8
        
        # Cost optimized preset
        cost_opt = get_preset_config('cost_optimized')
        assert cost_opt.pattern_confidence_threshold == 0.85
        assert cost_opt.max_ai_pairs_per_batch == 50
        
        # Pattern only preset
        pattern_only = get_preset_config('pattern_only')
        assert pattern_only.enable_ai_inference is False
    
    def test_config_validation(self):
        """Test configuration validation"""
        # Invalid threshold
        with pytest.raises(ValueError):
            config = HybridInferenceConfig(pattern_confidence_threshold=1.5)
            config.validate()
        
        # Invalid batch size
        with pytest.raises(ValueError):
            config = HybridInferenceConfig(max_ai_pairs_per_batch=0)
            config.validate()
    
    @pytest.mark.asyncio
    async def test_min_shared_keywords_config(self, mock_ai_engine):
        """Test minimum shared keywords configuration"""
        tasks = [
            Task(id="1", name="User API", **self._task_defaults()),
            Task(id="2", name="Product API", **self._task_defaults()),  # Only shares "API"
        ]
        
        # With min_shared_keywords=2, these shouldn't be considered related
        config = HybridInferenceConfig(
            min_shared_keywords=2,
            enable_ai_inference=True
        )
        inferer = HybridDependencyInferer(mock_ai_engine, config)
        
        mock_ai_engine._call_claude.return_value = json.dumps([])
        
        await inferer.infer_dependencies(tasks)
        
        # AI should not be called since they don't meet min shared keywords
        mock_ai_engine._call_claude.assert_not_called()
    
    def _task_defaults(self):
        """Default task fields for testing"""
        return {
            "description": "",
            "status": TaskStatus.TODO,
            "priority": Priority.MEDIUM,
            "assigned_to": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "due_date": None,
            "estimated_hours": 4.0,
            "labels": [],
            "dependencies": []
        }