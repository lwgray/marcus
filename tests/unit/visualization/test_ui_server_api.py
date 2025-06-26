"""
API tests for VisualizationServer HTTP endpoints
"""
import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock, ANY
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from src.visualization.ui_server import VisualizationServer
from src.visualization.conversation_stream import ConversationEvent
from tests.unit.visualization.factories import (
    create_mock_conversation_event,
    create_mock_decision,
    create_mock_health_data
)


class TestVisualizationServerAPI(AioHTTPTestCase):
    """Test HTTP API endpoints"""
    
    async def get_application(self):
        """Create app for testing"""
        server = VisualizationServer()
        await server.setup_routes()
        return server.app
    
    @unittest_run_loop
    async def test_status_endpoint(self):
        """Test /api/status endpoint"""
        resp = await self.client.request("GET", "/api/status")
        assert resp.status == 200
        
        data = await resp.json()
        assert "active_sessions" in data
        assert "conversation_summary" in data
        assert "decision_count" in data
        assert "knowledge_nodes" in data
    
    @unittest_run_loop
    async def test_conversation_history_endpoint(self):
        """Test /api/conversations endpoint"""
        resp = await self.client.request("GET", "/api/conversations")
        assert resp.status == 200
        
        data = await resp.json()
        assert "events" in data
        assert isinstance(data["events"], list)
    
    @unittest_run_loop
    async def test_decisions_endpoint(self):
        """Test /api/decisions endpoint"""
        resp = await self.client.request("GET", "/api/decisions")
        assert resp.status == 200
        
        data = await resp.json()
        assert "decisions" in data
        assert "analytics" in data
    
    @unittest_run_loop
    async def test_health_endpoint(self):
        """Test /api/health endpoint"""
        resp = await self.client.request("GET", "/api/health")
        assert resp.status == 200
        
        data = await resp.json()
        assert "status" in data
        assert "trends" in data
        assert "alerts" in data
    
    @unittest_run_loop
    async def test_knowledge_graph_endpoint(self):
        """Test /api/knowledge endpoint"""
        resp = await self.client.request("GET", "/api/knowledge")
        assert resp.status == 200
        
        data = await resp.json()
        assert "nodes" in data
        assert "edges" in data
    
    @unittest_run_loop
    async def test_static_files(self):
        """Test serving static files"""
        # Test main page
        resp = await self.client.request("GET", "/")
        assert resp.status == 200
        
        content = await resp.text()
        assert "Marcus Visualization" in content