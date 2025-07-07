"""
Integration tests for Pipeline Enhancement API endpoints
"""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from flask import Flask
from flask.testing import FlaskClient

from src.api.pipeline_enhancement_api import pipeline_api


class TestPipelineEnhancementAPI:
    """Test suite for Pipeline Enhancement API endpoints"""
    
    @pytest.fixture
    def app(self):
        """Create Flask test app"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(pipeline_api)
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()
    
    @pytest.fixture
    def mock_pipeline_tools(self):
        """Mock pipeline tools"""
        with patch('src.api.pipeline_enhancement_api.pipeline_tools') as mock:
            # Setup async mocks for all methods
            mock.start_replay = AsyncMock(return_value={
                "success": True,
                "flow_id": "test-123",
                "total_events": 10,
                "current_position": 0
            })
            
            mock.replay_step_forward = AsyncMock(return_value={
                "success": True,
                "state": {"position": 1},
                "has_more": True
            })
            
            mock.replay_step_backward = AsyncMock(return_value={
                "success": True,
                "state": {"position": 0},
                "has_previous": False
            })
            
            mock.get_live_dashboard = AsyncMock(return_value={
                "success": True,
                "dashboard": {
                    "active_flows": [],
                    "system_metrics": {"flows_per_hour": 5}
                }
            })
            
            mock.get_recommendations = AsyncMock(return_value={
                "success": True,
                "recommendations": [
                    {
                        "type": "add_testing",
                        "confidence": 0.9,
                        "message": "Add testing tasks",
                        "impact": "Improve quality"
                    }
                ]
            })
            
            yield mock
    
    # ==================== Replay Tests ====================
    
    @pytest.mark.asyncio
    async def test_start_replay_success(self, client, mock_pipeline_tools):
        """Test successful replay start"""
        response = client.post('/api/pipeline/replay/start',
                              json={'flow_id': 'test-123'},
                              content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['flow_id'] == 'test-123'
        assert data['total_events'] == 10
        
        mock_pipeline_tools.start_replay.assert_called_once_with('test-123')
    
    @pytest.mark.asyncio
    async def test_start_replay_missing_flow_id(self, client, mock_pipeline_tools):
        """Test replay start with missing flow_id"""
        response = client.post('/api/pipeline/replay/start',
                              json={},
                              content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'flow_id is required' in data['error']
    
    @pytest.mark.asyncio
    async def test_replay_forward(self, client, mock_pipeline_tools):
        """Test replay step forward"""
        response = client.post('/api/pipeline/replay/forward')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['has_more'] is True
        
        mock_pipeline_tools.replay_step_forward.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_replay_backward(self, client, mock_pipeline_tools):
        """Test replay step backward"""
        response = client.post('/api/pipeline/replay/backward')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['has_previous'] is False
        
        mock_pipeline_tools.replay_step_backward.assert_called_once()
    
    # ==================== What-If Analysis Tests ====================
    
    @pytest.mark.asyncio
    async def test_start_whatif_success(self, client, mock_pipeline_tools):
        """Test successful what-if analysis start"""
        mock_pipeline_tools.start_what_if_analysis = AsyncMock(return_value={
            "success": True,
            "flow_id": "test-123",
            "original_metrics": {
                "task_count": 20,
                "complexity": 0.7
            }
        })
        
        response = client.post('/api/pipeline/whatif/start',
                              json={'flow_id': 'test-123'},
                              content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['original_metrics']['task_count'] == 20
    
    @pytest.mark.asyncio
    async def test_simulate_whatif(self, client, mock_pipeline_tools):
        """Test what-if simulation"""
        mock_pipeline_tools.simulate_modification = AsyncMock(return_value={
            "success": True,
            "simulation": {
                "predicted_metrics": {"task_count": 25}
            }
        })
        
        modifications = [
            {
                "parameter_type": "requirement",
                "parameter_name": "new_req",
                "new_value": "Add feature X"
            }
        ]
        
        response = client.post('/api/pipeline/whatif/simulate',
                              json={'modifications': modifications},
                              content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'simulation' in data
    
    # ==================== Comparison Tests ====================
    
    @pytest.mark.asyncio
    async def test_compare_flows_success(self, client, mock_pipeline_tools):
        """Test successful flow comparison"""
        mock_pipeline_tools.compare_pipelines = AsyncMock(return_value={
            "success": True,
            "report": {
                "flow_summaries": [],
                "recommendations": ["Consider phased approach"]
            }
        })
        
        response = client.post('/api/pipeline/compare',
                              json={'flow_ids': ['flow1', 'flow2']},
                              content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'report' in data
    
    @pytest.mark.asyncio
    async def test_compare_flows_insufficient_ids(self, client, mock_pipeline_tools):
        """Test comparison with insufficient flow IDs"""
        response = client.post('/api/pipeline/compare',
                              json={'flow_ids': ['flow1']},
                              content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'At least 2 flow_ids' in data['error']
    
    # ==================== Report Generation Tests ====================
    
    @pytest.mark.asyncio
    async def test_generate_report_html(self, client, mock_pipeline_tools):
        """Test HTML report generation"""
        mock_pipeline_tools.generate_report = AsyncMock(return_value={
            "success": True,
            "format": "html",
            "content": "<html><body>Report</body></html>"
        })
        
        response = client.get('/api/pipeline/report/test-123?format=html')
        
        assert response.status_code == 200
        assert response.content_type == 'text/html'
        assert b"Report" in response.data
    
    @pytest.mark.asyncio
    async def test_generate_report_json(self, client, mock_pipeline_tools):
        """Test JSON report generation"""
        mock_pipeline_tools.generate_report = AsyncMock(return_value={
            "success": True,
            "format": "json",
            "content": '{"project": "test"}'
        })
        
        response = client.get('/api/pipeline/report/test-123?format=json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
    
    # ==================== Monitoring Tests ====================
    
    @pytest.mark.asyncio
    async def test_get_dashboard(self, client, mock_pipeline_tools):
        """Test dashboard endpoint"""
        response = client.get('/api/pipeline/monitor/dashboard')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'dashboard' in data
        assert data['dashboard']['system_metrics']['flows_per_hour'] == 5
    
    @pytest.mark.asyncio
    async def test_track_flow_progress(self, client, mock_pipeline_tools):
        """Test flow progress tracking"""
        mock_pipeline_tools.track_flow_progress = AsyncMock(return_value={
            "success": True,
            "progress": {
                "flow_id": "test-123",
                "percentage": 75.0,
                "stage": "task_generation"
            }
        })
        
        response = client.get('/api/pipeline/monitor/flow/test-123')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['progress']['percentage'] == 75.0
    
    @pytest.mark.asyncio
    async def test_predict_risk(self, client, mock_pipeline_tools):
        """Test risk prediction endpoint"""
        mock_pipeline_tools.predict_failure_risk = AsyncMock(return_value={
            "success": True,
            "risk_assessment": {
                "flow_id": "test-123",
                "overall_risk": 0.3,
                "risk_category": "low"
            }
        })
        
        response = client.get('/api/pipeline/monitor/risk/test-123')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['risk_assessment']['risk_category'] == 'low'
    
    # ==================== Recommendations Tests ====================
    
    @pytest.mark.asyncio
    async def test_get_recommendations(self, client, mock_pipeline_tools):
        """Test recommendations endpoint"""
        response = client.get('/api/pipeline/recommendations/test-123')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['recommendations']) == 1
        assert data['recommendations'][0]['type'] == 'add_testing'
    
    @pytest.mark.asyncio
    async def test_find_similar_flows(self, client, mock_pipeline_tools):
        """Test similar flows endpoint"""
        mock_pipeline_tools.find_similar_flows = AsyncMock(return_value={
            "success": True,
            "similar_flows": [
                {
                    "flow_id": "similar-123",
                    "project_name": "Similar Project",
                    "similarity": 0.85
                }
            ]
        })
        
        response = client.get('/api/pipeline/similar/test-123?limit=3')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['similar_flows']) == 1
        assert data['similar_flows'][0]['similarity'] == 0.85