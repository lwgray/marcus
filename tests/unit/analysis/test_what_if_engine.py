"""
Unit tests for What-If Analysis Engine
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import uuid

from src.analysis.what_if_engine import (
    WhatIfAnalysisEngine, 
    PipelineModification,
    ModificationType
)


class TestWhatIfAnalysisEngine:
    """Test suite for WhatIfAnalysisEngine"""
    
    @pytest.fixture
    def mock_comparator(self):
        """Create mock for PipelineComparator"""
        mock = Mock()
        mock._load_flow_with_metadata.return_value = {
            "flow_id": "test-flow-123",
            "project_name": "Test Project",
            "events": [],
            "metrics": {
                "task_count": 20,
                "complexity_score": 0.7,
                "total_cost": 5.0,
                "quality_score": 0.8
            },
            "requirements": [
                {"requirement": "User authentication", "confidence": 0.9},
                {"requirement": "Data persistence", "confidence": 0.85}
            ],
            "tasks": [
                {"name": "Setup authentication", "priority": "high"},
                {"name": "Create database schema", "priority": "medium"}
            ],
            "parameters": {
                "team_size": 3,
                "deadline": "2024-03-01",
                "tech_stack": ["Python", "PostgreSQL"]
            }
        }
        return mock
    
    @pytest.fixture
    def mock_shared_events(self):
        """Create mock for SharedPipelineEvents"""
        mock = Mock()
        mock.add_event = Mock()
        return mock
    
    @patch('src.analysis.what_if_engine.SharedPipelineEvents')
    @patch('src.analysis.what_if_engine.PipelineComparator')
    def test_initialization(self, mock_comp_class, mock_events_class, 
                          mock_comparator, mock_shared_events):
        """Test engine initialization"""
        mock_comp_class.return_value = mock_comparator
        mock_events_class.return_value = mock_shared_events
        
        engine = WhatIfAnalysisEngine("test-flow-123")
        
        assert engine.original_flow_id == "test-flow-123"
        assert engine.original_flow["flow_id"] == "test-flow-123"
        assert len(engine.variations) == 0
        mock_comparator._load_flow_with_metadata.assert_called_once_with("test-flow-123")
    
    @patch('src.analysis.what_if_engine.SharedPipelineEvents')
    @patch('src.analysis.what_if_engine.PipelineComparator')
    def test_get_modifiable_parameters(self, mock_comp_class, mock_events_class,
                                     mock_comparator, mock_shared_events):
        """Test getting modifiable parameters"""
        mock_comp_class.return_value = mock_comparator
        mock_events_class.return_value = mock_shared_events
        
        engine = WhatIfAnalysisEngine("test-flow-123")
        params = engine.get_modifiable_parameters()
        
        assert "requirements" in params
        assert "constraints" in params
        assert "parameters" in params
        assert len(params["requirements"]) == 2
        assert params["parameters"]["team_size"] == 3
    
    @pytest.mark.asyncio
    @patch('src.analysis.what_if_engine.SharedPipelineEvents')
    @patch('src.analysis.what_if_engine.PipelineComparator')
    @patch('src.analysis.what_if_engine.uuid.uuid4')
    async def test_simulate_variation_add_requirement(self, mock_uuid, mock_comp_class, 
                                                   mock_events_class, mock_comparator, 
                                                   mock_shared_events):
        """Test simulating variation with added requirement"""
        mock_comp_class.return_value = mock_comparator
        mock_events_class.return_value = mock_shared_events
        mock_uuid.return_value = "variation-123"
        
        engine = WhatIfAnalysisEngine("test-flow-123")
        
        modification = PipelineModification(
            parameter_type=ModificationType.REQUIREMENT,
            parameter_name="new_requirement",
            old_value=None,
            new_value="Add API versioning",
            description="Add new requirement for API versioning"
        )
        
        result = await engine.simulate_variation([modification])
        
        assert result["variation_id"] == "variation-123"
        assert result["original_flow_id"] == "test-flow-123"
        assert len(result["modifications"]) == 1
        assert len(result["modified_parameters"]["requirements"]) == 3
        assert result["predicted_metrics"]["task_count"] > 20  # Should increase
        assert result["predicted_metrics"]["cost"] > 5.0  # Should increase
    
    @pytest.mark.asyncio
    @patch('src.analysis.what_if_engine.SharedPipelineEvents')
    @patch('src.analysis.what_if_engine.PipelineComparator')
    async def test_simulate_variation_modify_parameter(self, mock_comp_class, 
                                                     mock_events_class, mock_comparator,
                                                     mock_shared_events):
        """Test simulating variation with modified parameter"""
        mock_comp_class.return_value = mock_comparator
        mock_events_class.return_value = mock_shared_events
        
        engine = WhatIfAnalysisEngine("test-flow-123")
        
        modification = PipelineModification(
            parameter_type=ModificationType.PARAMETER,
            parameter_name="team_size",
            old_value=3,
            new_value=5,
            description="Increase team size"
        )
        
        result = await engine.simulate_variation([modification])
        
        assert result["modified_parameters"]["parameters"]["team_size"] == 5
        assert result["predicted_metrics"]["cost"] > 5.0  # Should increase with team size
        assert result["impact_analysis"]["cost_change"]["reason"] == "Team size increase"
    
    @pytest.mark.asyncio
    @patch('src.analysis.what_if_engine.SharedPipelineEvents')
    @patch('src.analysis.what_if_engine.PipelineComparator')
    async def test_simulate_variation_remove_requirement(self, mock_comp_class,
                                                       mock_events_class, mock_comparator,
                                                       mock_shared_events):
        """Test simulating variation with removed requirement"""
        mock_comp_class.return_value = mock_comparator
        mock_events_class.return_value = mock_shared_events
        
        engine = WhatIfAnalysisEngine("test-flow-123")
        
        modification = PipelineModification(
            parameter_type=ModificationType.REQUIREMENT,
            parameter_name="Data persistence",
            old_value="Data persistence",
            new_value=None,
            description="Remove data persistence requirement"
        )
        
        result = await engine.simulate_variation([modification])
        
        assert len(result["modified_parameters"]["requirements"]) == 1
        assert result["predicted_metrics"]["task_count"] < 20  # Should decrease
        assert result["predicted_metrics"]["complexity_score"] < 0.7  # Should decrease
    
    @patch('src.analysis.what_if_engine.SharedPipelineEvents')
    @patch('src.analysis.what_if_engine.PipelineComparator')
    def test_compare_variations(self, mock_comp_class, mock_events_class,
                               mock_comparator, mock_shared_events):
        """Test comparing multiple variations"""
        mock_comp_class.return_value = mock_comparator
        mock_events_class.return_value = mock_shared_events
        
        engine = WhatIfAnalysisEngine("test-flow-123")
        
        # Add mock variations
        engine.variations = [
            {
                "variation_id": "var1",
                "predicted_metrics": {
                    "task_count": 25,
                    "cost": 6.0,
                    "quality_score": 0.85,
                    "complexity_score": 0.8
                },
                "modifications": [{"description": "Add features"}]
            },
            {
                "variation_id": "var2", 
                "predicted_metrics": {
                    "task_count": 15,
                    "cost": 4.0,
                    "quality_score": 0.75,
                    "complexity_score": 0.6
                },
                "modifications": [{"description": "Remove features"}]
            }
        ]
        
        comparison = engine.compare_all_variations()
        
        assert comparison["original_metrics"]["task_count"] == 20
        assert len(comparison["variations"]) == 2
        assert comparison["best_by_metric"]["cost"]["variation_id"] == "var2"
        assert comparison["best_by_metric"]["quality"]["variation_id"] == "var1"
        assert len(comparison["recommendations"]) > 0
    
    @patch('src.analysis.what_if_engine.SharedPipelineEvents')
    @patch('src.analysis.what_if_engine.PipelineComparator')
    def test_predict_impact_requirement_addition(self, mock_comp_class, mock_events_class,
                                               mock_comparator, mock_shared_events):
        """Test impact prediction for requirement addition"""
        mock_comp_class.return_value = mock_comparator
        mock_events_class.return_value = mock_shared_events
        
        engine = WhatIfAnalysisEngine("test-flow-123")
        
        impact = engine._predict_impact(
            engine.original_flow,
            {"requirements": engine.original_flow["requirements"] + [
                {"requirement": "New feature", "confidence": 0.8}
            ]}
        )
        
        assert impact["task_count"]["change"] > 0
        assert impact["cost"]["change"] > 0
        assert "requirement" in impact["task_count"]["reason"].lower()
    
    @patch('src.analysis.what_if_engine.SharedPipelineEvents')
    @patch('src.analysis.what_if_engine.PipelineComparator')
    def test_empty_flow_handling(self, mock_comp_class, mock_events_class,
                                mock_shared_events):
        """Test handling of empty flow data"""
        mock_comp = Mock()
        mock_comp._load_flow_with_metadata.return_value = None
        mock_comp_class.return_value = mock_comp
        mock_events_class.return_value = mock_shared_events
        
        with pytest.raises(ValueError, match="Flow test-flow-123 not found"):
            WhatIfAnalysisEngine("test-flow-123")