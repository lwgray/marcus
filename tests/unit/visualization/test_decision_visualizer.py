"""
Unit tests for DecisionVisualizer
"""
import pytest
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile

from src.visualization.decision_visualizer import (
    DecisionVisualizer, 
    Decision,
    DecisionNode
)
from tests.unit.visualization.factories import create_mock_decision


class TestDecisionVisualizer:
    """Test cases for DecisionVisualizer"""
    
    @pytest.fixture
    def visualizer(self):
        """Create a DecisionVisualizer instance"""
        return DecisionVisualizer()
    
    
    def test_add_decision(self, visualizer):
        """Test adding a new decision"""
        decision_data = create_mock_decision()
        
        decision_id = visualizer.add_decision(decision_data)
        
        # Verify decision was recorded
        assert decision_id in visualizer.decisions
        decision = visualizer.decisions[decision_id]
        assert isinstance(decision, Decision)
        assert decision.decision == decision_data["decision"]
        assert decision.confidence_score == decision_data["confidence_score"]
        assert decision.rationale == decision_data["rationale"]
        
        # Verify nodes were added to graph
        expected_nodes = [
            f"decision_{decision_id}",
            f"rationale_{decision_id}"
        ]
        for node in expected_nodes:
            assert node in visualizer.decision_graph.nodes()
    
    def test_update_decision_outcome(self, visualizer):
        """Test updating decision outcome"""
        decision_data = create_mock_decision()
        decision_id = visualizer.add_decision(decision_data)
        
        # Update outcome
        outcome = "Task completed successfully"
        visualizer.update_decision_outcome(decision_id, outcome)
        
        # Verify outcome was updated
        assert visualizer.decisions[decision_id].outcome == outcome
        assert visualizer.decisions[decision_id].outcome_timestamp is not None
    
    def test_decision_was_successful(self):
        """Test decision success determination"""
        # Test successful outcomes
        successful_decision = Decision(
            id="1",
            timestamp=datetime.now(),
            decision="Test",
            rationale="Test",
            confidence_score=0.8,
            outcome="Task completed successfully"
        )
        assert successful_decision.was_successful() is True
        
        # Test failed outcomes
        failed_decision = Decision(
            id="2",
            timestamp=datetime.now(),
            decision="Test",
            rationale="Test",
            confidence_score=0.8,
            outcome="Task failed due to error"
        )
        assert failed_decision.was_successful() is False
        
        # Test unknown outcomes
        unknown_decision = Decision(
            id="3",
            timestamp=datetime.now(),
            decision="Test",
            rationale="Test",
            confidence_score=0.8,
            outcome="Task is pending"
        )
        assert unknown_decision.was_successful() is None
    
    def test_classify_decision(self, visualizer):
        """Test decision classification"""
        assert visualizer._classify_decision("Assign task to worker") == "task_assignment"
        assert visualizer._classify_decision("Resolve blocker issue") == "blocker_resolution"
        assert visualizer._classify_decision("Prioritize feature X") == "prioritization"
        assert visualizer._classify_decision("Escalate to manager") == "escalation"
        assert visualizer._classify_decision("Random decision") == "other"
    
    @patch('src.visualization.decision_visualizer.Network')
    def test_generate_decision_tree_html(self, mock_network, visualizer):
        """Test generating HTML visualization"""
        # Add a decision
        decision_data = create_mock_decision()
        decision_id = visualizer.add_decision(decision_data)
        
        # Mock the network
        mock_net_instance = MagicMock()
        mock_network.return_value = mock_net_instance
        
        # Generate HTML
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as tmp:
            output_file = visualizer.generate_decision_tree_html(
                decision_id, 
                output_file=tmp.name
            )
        
        # Verify network was created and saved
        mock_network.assert_called_once()
        mock_net_instance.from_nx.assert_called_once()
        mock_net_instance.save_graph.assert_called_once_with(tmp.name)
        
        assert output_file == tmp.name
    
    def test_generate_decision_tree_html_invalid_id(self, visualizer):
        """Test generating HTML for non-existent decision"""
        result = visualizer.generate_decision_tree_html("non-existent-id")
        assert result is None
    
    def test_get_decision_analytics(self, visualizer):
        """Test getting decision analytics"""
        # Add multiple decisions
        for i in range(5):
            decision_data = create_mock_decision(
                confidence=0.6 + i * 0.08  # Varying confidence
            )
            visualizer.add_decision(decision_data)
        
        analytics = visualizer.get_decision_analytics()
        
        assert analytics['total_decisions'] == 5
        assert 0.6 <= analytics['average_confidence'] <= 1.0
        assert 'task_assignment' in analytics['decision_types']
        assert analytics['average_alternatives_considered'] > 0
    
    def test_get_confidence_trends(self, visualizer):
        """Test getting confidence trends over time"""
        # Add decisions with different timestamps
        base_time = datetime.now()
        for i in range(3):
            decision_data = create_mock_decision(confidence=0.5 + i * 0.2)
            decision_data['timestamp'] = (base_time + timedelta(hours=i)).isoformat()
            visualizer.add_decision(decision_data)
        
        trends = visualizer.get_confidence_trends()
        
        assert len(trends) == 3
        # Check trends are sorted by time
        for i in range(1, len(trends)):
            assert trends[i][0] > trends[i-1][0]
        # Check confidence values
        assert trends[0][1] == 0.5
        assert trends[1][1] == 0.7
        assert trends[2][1] == 0.9
    
    def test_find_similar_decisions(self, visualizer):
        """Test finding similar decisions"""
        # Add decisions with similar factors
        decision1_data = create_mock_decision()
        decision1_data['decision_factors'] = {'skill_match': 0.9, 'availability': 0.8}
        decision1_id = visualizer.add_decision(decision1_data)
        
        decision2_data = create_mock_decision()
        decision2_data['decision_factors'] = {'skill_match': 0.85, 'availability': 0.75}
        decision2_id = visualizer.add_decision(decision2_data)
        
        decision3_data = create_mock_decision()
        decision3_data['decision_factors'] = {'cost': 100, 'timeline': 5}
        visualizer.add_decision(decision3_data)
        
        similar = visualizer.find_similar_decisions(decision1_id, threshold=0.5)
        
        # Decision 2 should be similar (same factors)
        assert decision2_id in similar
        # Decision 3 should not be similar (different factors)
        assert len(similar) == 1
    
    def test_export_decision_data(self, visualizer):
        """Test exporting decision data"""
        # Add some decisions
        for i in range(3):
            decision_data = create_mock_decision()
            visualizer.add_decision(decision_data)
        
        # Export as JSON
        exported = visualizer.export_decision_data(format='json')
        data = json.loads(exported)
        
        assert 'decisions' in data
        assert 'patterns' in data
        assert 'analytics' in data
        assert len(data['decisions']) == 3
        assert data['analytics']['total_decisions'] == 3