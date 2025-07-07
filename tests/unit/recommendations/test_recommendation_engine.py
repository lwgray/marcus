"""
Unit tests for Pipeline Recommendation Engine
"""

import pytest
from unittest.mock import Mock, patch, mock_open
import json
from pathlib import Path

from src.recommendations.recommendation_engine import (
    PipelineRecommendationEngine,
    Recommendation,
    PatternDatabase,
    SuccessAnalyzer,
    ProjectOutcome
)


class TestPatternDatabase:
    """Test suite for PatternDatabase"""
    
    @pytest.fixture
    def sample_patterns(self):
        """Sample pattern data"""
        return {
            "success_patterns": [
                {
                    "project_type": "api",
                    "task_count": 25,
                    "complexity": 0.6,
                    "confidence": 0.85
                }
            ],
            "failure_patterns": [],
            "templates": {},
            "optimization_rules": []
        }
    
    @patch('src.recommendations.recommendation_engine.Path.exists')
    @patch('src.recommendations.recommendation_engine.Path.mkdir')
    def test_initialization_no_existing_db(self, mock_mkdir, mock_exists):
        """Test pattern database initialization without existing file"""
        mock_exists.return_value = False
        
        db = PatternDatabase()
        
        assert db.patterns["success_patterns"] == []
        assert db.patterns["failure_patterns"] == []
        mock_mkdir.assert_called_once()
    
    @patch('src.recommendations.recommendation_engine.Path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='{"success_patterns": []}')
    def test_initialization_with_existing_db(self, mock_file, mock_exists):
        """Test pattern database initialization with existing file"""
        mock_exists.return_value = True
        
        db = PatternDatabase()
        
        assert db.patterns["success_patterns"] == []
        mock_file.assert_called_once()
    
    @patch('builtins.open', new_callable=mock_open)
    def test_save_patterns(self, mock_file):
        """Test saving patterns to disk"""
        db = PatternDatabase()
        db.patterns = {"test": "data"}
        
        db.save_patterns()
        
        mock_file.assert_called_once()
        handle = mock_file()
        written_data = ''.join(call.args[0] for call in handle.write.call_args_list)
        assert json.loads(written_data) == {"test": "data"}
    
    def test_extract_pattern(self):
        """Test pattern extraction from flow data"""
        db = PatternDatabase()
        
        flow_data = {
            "requirements": [
                {"requirement": "API endpoints for CRUD", "confidence": 0.9},
                {"requirement": "Authentication", "confidence": 0.85}
            ],
            "tasks": [
                {"name": "Create API endpoints"},
                {"name": "Setup authentication"}
            ],
            "metrics": {
                "task_count": 10,
                "complexity_score": 0.7,
                "confidence_avg": 0.87
            },
            "decisions": [
                {
                    "stage": "tech_stack",
                    "decision": "Use FastAPI",
                    "confidence": 0.9
                }
            ]
        }
        
        pattern = db._extract_pattern(flow_data)
        
        assert pattern["project_type"] == "api"
        assert pattern["task_count"] == 10
        assert pattern["complexity"] == 0.7
        assert pattern["task_categories"]["implementation"] == 2
        assert len(pattern["decisions"]) == 1


class TestPipelineRecommendationEngine:
    """Test suite for PipelineRecommendationEngine"""
    
    @pytest.fixture
    def mock_flow_data(self):
        """Mock flow data for testing"""
        return {
            "flow_id": "test-flow-123",
            "project_name": "Test API Project",
            "metrics": {
                "task_count": 30,
                "complexity_score": 0.9,
                "total_cost": 2.0,
                "quality_score": 0.6,
                "confidence_avg": 0.65,
                "total_duration_ms": 45000
            },
            "tasks": [
                {"name": "Create user API"},
                {"name": "Implement authentication"},
                {"name": "Setup database"}
            ],
            "requirements": [
                {"requirement": "User management", "confidence": 0.7}
            ],
            "decisions": [
                {"stage": "planning", "decision": "Microservices", "confidence": 0.6}
            ]
        }
    
    @pytest.fixture
    def mock_dependencies(self):
        """Create mocked dependencies"""
        mocks = {
            'shared_events': Mock(),
            'comparator': Mock(),
            'pattern_db': Mock(),
            'success_analyzer': Mock()
        }
        
        # Setup shared events mock
        mocks['shared_events']._read_events.return_value = {
            "flows": {},
            "events": []
        }
        
        # Setup comparator mock
        mocks['comparator']._load_flow_with_metadata.return_value = None
        
        # Setup pattern database mock
        mocks['pattern_db'].patterns = {
            "success_patterns": [],
            "failure_patterns": []
        }
        
        # Setup success analyzer mock
        mocks['success_analyzer'].analyze_success_factors.return_value = {
            "optimal_task_count_range": (15, 35),
            "min_confidence_threshold": 0.7,
            "ideal_task_distribution": {"testing": 0.2, "documentation": 0.1}
        }
        
        return mocks
    
    @patch('src.recommendations.recommendation_engine.SharedPipelineEvents')
    @patch('src.recommendations.recommendation_engine.PipelineComparator')
    @patch('src.recommendations.recommendation_engine.PatternDatabase')
    @patch('src.recommendations.recommendation_engine.SuccessAnalyzer')
    def test_initialization(self, mock_analyzer_class, mock_db_class, 
                          mock_comp_class, mock_events_class, mock_dependencies):
        """Test engine initialization"""
        mock_events_class.return_value = mock_dependencies['shared_events']
        mock_comp_class.return_value = mock_dependencies['comparator']
        mock_db_class.return_value = mock_dependencies['pattern_db']
        mock_analyzer_class.return_value = mock_dependencies['success_analyzer']
        
        engine = PipelineRecommendationEngine()
        
        assert engine.shared_events is not None
        assert engine.comparator is not None
        assert engine.pattern_db is not None
        assert engine.success_analyzer is not None
    
    @patch('src.recommendations.recommendation_engine.SharedPipelineEvents')
    @patch('src.recommendations.recommendation_engine.PipelineComparator')
    @patch('src.recommendations.recommendation_engine.PatternDatabase')
    @patch('src.recommendations.recommendation_engine.SuccessAnalyzer')
    def test_get_recommendations_high_complexity(self, mock_analyzer_class, mock_db_class,
                                               mock_comp_class, mock_events_class,
                                               mock_dependencies, mock_flow_data):
        """Test recommendations for high complexity project"""
        mock_events_class.return_value = mock_dependencies['shared_events']
        mock_comp_class.return_value = mock_dependencies['comparator']
        mock_db_class.return_value = mock_dependencies['pattern_db']
        mock_analyzer_class.return_value = mock_dependencies['success_analyzer']
        
        # Setup comparator to return our mock flow
        mock_dependencies['comparator']._load_flow_with_metadata.return_value = mock_flow_data
        
        engine = PipelineRecommendationEngine()
        engine.comparator = mock_dependencies['comparator']
        
        recommendations = engine.get_recommendations("test-flow-123")
        
        # Should recommend phasing due to high complexity
        phase_rec = next((r for r in recommendations if r.type == "phase_project"), None)
        assert phase_rec is not None
        assert phase_rec.confidence >= 0.8
        assert "complexity" in phase_rec.message.lower()
    
    @patch('src.recommendations.recommendation_engine.SharedPipelineEvents')
    @patch('src.recommendations.recommendation_engine.PipelineComparator')
    @patch('src.recommendations.recommendation_engine.PatternDatabase')
    @patch('src.recommendations.recommendation_engine.SuccessAnalyzer')
    def test_get_recommendations_missing_testing(self, mock_analyzer_class, mock_db_class,
                                               mock_comp_class, mock_events_class,
                                               mock_dependencies, mock_flow_data):
        """Test recommendations for missing testing tasks"""
        mock_events_class.return_value = mock_dependencies['shared_events']
        mock_comp_class.return_value = mock_dependencies['comparator']
        mock_db_class.return_value = mock_dependencies['pattern_db']
        mock_analyzer_class.return_value = mock_dependencies['success_analyzer']
        
        mock_dependencies['comparator']._load_flow_with_metadata.return_value = mock_flow_data
        
        engine = PipelineRecommendationEngine()
        engine.comparator = mock_dependencies['comparator']
        
        recommendations = engine.get_recommendations("test-flow-123")
        
        # Should recommend adding testing
        test_rec = next((r for r in recommendations if r.type == "add_testing"), None)
        assert test_rec is not None
        assert test_rec.confidence >= 0.8
        assert "test coverage" in test_rec.message.lower()
    
    def test_calculate_similarity(self):
        """Test flow similarity calculation"""
        engine = PipelineRecommendationEngine()
        
        flow1 = {
            "project_name": "User API Service",
            "metrics": {"task_count": 20},
            "requirements": [
                {"requirement": "User authentication"},
                {"requirement": "CRUD operations"}
            ]
        }
        
        flow2 = {
            "project_name": "User Management API",
            "metrics": {"task_count": 22},
            "requirements": [
                {"requirement": "User auth system"},
                {"requirement": "CRUD functionality"}
            ]
        }
        
        similarity = engine._calculate_similarity(flow1, flow2)
        
        assert 0.7 < similarity < 0.9  # Should be similar but not identical
    
    def test_detect_high_complexity(self):
        """Test high complexity detection"""
        engine = PipelineRecommendationEngine()
        
        # High complexity due to complexity score
        flow1 = {"metrics": {"complexity_score": 0.85, "task_count": 30}}
        assert engine.detect_high_complexity(flow1) is True
        
        # High complexity due to task count
        flow2 = {"metrics": {"complexity_score": 0.5, "task_count": 45}}
        assert engine.detect_high_complexity(flow2) is True
        
        # Normal complexity
        flow3 = {"metrics": {"complexity_score": 0.5, "task_count": 20}}
        assert engine.detect_high_complexity(flow3) is False
    
    def test_suggest_phases(self):
        """Test project phase suggestions"""
        engine = PipelineRecommendationEngine()
        
        flow = {
            "tasks": [{"name": f"Task {i}"} for i in range(36)]
        }
        
        phases = engine.suggest_phases(flow)
        
        assert len(phases) == 3  # Should split into 3 phases
        assert phases[0]["phase"] == "Foundation"
        assert len(phases[0]["tasks"]) == 12
        assert phases[2]["phase"] == "Polish & Deploy"
    
    def test_learn_from_outcome(self):
        """Test learning from project outcome"""
        engine = PipelineRecommendationEngine()
        
        # Mock the pattern database
        engine.pattern_db = Mock()
        engine._load_flow_data = Mock(return_value={"flow_id": "test-123"})
        
        outcome = ProjectOutcome(
            successful=True,
            completion_time_days=10.5,
            quality_score=0.85,
            cost=3.5
        )
        
        engine.learn_from_outcome("test-123", outcome)
        
        engine.pattern_db.add_success_pattern.assert_called_once()
        
        # Test failure outcome
        failure_outcome = ProjectOutcome(
            successful=False,
            completion_time_days=15.0,
            quality_score=0.4,
            cost=5.0,
            failure_reasons=["Scope creep", "Technical debt"]
        )
        
        engine.learn_from_outcome("test-123", failure_outcome)
        
        engine.pattern_db.add_failure_pattern.assert_called_once()