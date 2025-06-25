"""
Integration tests for the PM Agent visualization system
"""
import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import tempfile
from pathlib import Path

from src.visualization.conversation_stream import ConversationStreamProcessor, ConversationEvent
from src.visualization.decision_visualizer import DecisionVisualizer
from src.visualization.knowledge_graph import KnowledgeGraphBuilder
from src.visualization.health_monitor import HealthMonitor
from src.visualization.ui_server import VisualizationServer
from tests.unit.visualization.factories import (
    create_mock_conversation_event,
    create_mock_decision,
    create_mock_worker_status,
    create_mock_task,
    create_mock_project_state
)


class TestVisualizationIntegration:
    """Test integration between visualization components"""
    
    @pytest.mark.asyncio
    async def test_event_flow_end_to_end(self):
        """Test complete event flow from log to UI"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create components
            processor = ConversationStreamProcessor(log_dir=temp_dir)
            visualizer = DecisionVisualizer()
            server = VisualizationServer()
            
            # Mock server emit
            server.sio.emit = AsyncMock()
            
            # Connect components
            processor.add_event_handler(server.handle_conversation_event)
            
            # Write a log entry
            log_file = Path(temp_dir) / "test.jsonl"
            with open(log_file, 'w') as f:
                f.write(json.dumps({
                    "timestamp": datetime.now().isoformat(),
                    "event": "worker_communication",
                    "worker_id": "worker-123",
                    "conversation_type": "worker_to_pm",
                    "message": "Task completed",
                    "metadata": {"task_id": "task-456"}
                }) + '\n')
            
            # Process the log
            await processor._process_log_file(log_file)
            
            # Verify event was processed and emitted
            assert len(processor.conversation_history) == 1
            server.sio.emit.assert_called_once()
            
            # Check emitted data
            call_args = server.sio.emit.call_args
            assert call_args[0][0] == 'conversation_event'
            assert 'timestamp' in call_args[0][1]
    
    @pytest.mark.asyncio
    async def test_real_time_monitoring(self):
        """Test real-time monitoring capabilities"""
        # Create monitoring system
        monitor = HealthMonitor()
        monitor.ai_engine = MagicMock()
        monitor.ai_engine.initialize = AsyncMock()
        monitor.ai_engine.analyze_project_health = AsyncMock(return_value={
            "risk_assessment": {"level": "low", "score": 0.2},
            "recommendations": ["Continue current pace"],
            "key_insights": ["Project on track"]
        })
        
        # Initialize
        await monitor.initialize()
        
        # Create project state
        project_state = create_mock_project_state()
        team_status = [create_mock_worker_status() for _ in range(3)]
        
        # Start monitoring
        get_state_func = AsyncMock(return_value=(project_state, [], team_status))
        monitor.start_monitoring(get_state_func, interval=0.5)
        
        # Let it run
        await asyncio.sleep(1.0)
        
        # Should have collected some analyses
        assert len(monitor.analysis_history) > 0
        
        # Stop monitoring
        await monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_health_monitoring_integration(self):
        """Test health monitoring with decision tracking"""
        visualizer = DecisionVisualizer()
        monitor = HealthMonitor()
        
        # Mock AI engine
        monitor.ai_engine = MagicMock()
        monitor.ai_engine.analyze_project_health = AsyncMock(return_value={
            "risk_assessment": {"level": "medium", "score": 0.6},
            "recommendations": ["Review blocked tasks"],
            "key_insights": ["3 tasks blocked"]
        })
        
        # Add some decisions
        for i in range(5):
            decision_data = create_mock_decision(
                confidence=0.5 + i * 0.1
            )
            visualizer.add_decision(decision_data)
        
        # Get analytics
        decision_analytics = visualizer.get_decision_analytics()
        
        # Analyze health with decision context
        project_state = create_mock_project_state()
        health_analysis = await monitor.analyze_health(
            project_state,
            recent_activities=[],
            team_status=[]
        )
        
        # Verify integration
        assert decision_analytics['total_decisions'] == 5
        assert health_analysis['risk_level'] == "medium"
    
    @pytest.mark.asyncio
    async def test_decision_tracking_with_outcomes(self):
        """Test decision tracking with outcome updates"""
        visualizer = DecisionVisualizer()
        
        # Create and track decision
        decision_data = create_mock_decision()
        decision_id = visualizer.add_decision(decision_data)
        
        # Simulate time passing
        await asyncio.sleep(0.1)
        
        # Update with outcome
        visualizer.update_decision_outcome(
            decision_id, 
            "Task completed successfully"
        )
        
        # Verify outcome tracking
        decision = visualizer.decisions[decision_id]
        assert decision.outcome is not None
        assert decision.was_successful() is True
        assert decision.outcome_timestamp > decision.timestamp
    
    @pytest.mark.asyncio
    async def test_knowledge_graph_evolution(self):
        """Test knowledge graph evolution over time"""
        graph = KnowledgeGraphBuilder()
        
        # Initial state
        worker1 = graph.add_worker("w1", "Alice", "Developer", ["python", "api"])
        worker2 = graph.add_worker("w2", "Bob", "Frontend Dev", ["javascript", "react"])
        
        task1 = graph.add_task("t1", "Backend API", {
            "required_skills": ["python", "api"]
        })
        task2 = graph.add_task("t2", "Frontend UI", {
            "required_skills": ["javascript", "react"]
        })
        
        # Assign tasks
        graph.assign_task(task1, worker1, assignment_score=0.85)
        graph.assign_task(task2, worker2, assignment_score=0.85)
        
        # Verify graph structure
        assert len(graph.get_worker_tasks(worker1)) == 1
        assert len(graph.get_worker_tasks(worker2)) == 1
        
        # Complete task1
        graph.update_task_status(task1, "completed")
        # Also complete task2 to free worker2
        graph.update_task_status(task2, "completed")
        
        # Add new task depending on completed one
        task3 = graph.add_task("t3", "Integration", {
            "dependencies": [task1],
            "required_skills": ["python", "javascript"]
        })
        
        # Find candidates for new task
        candidates = graph.get_task_candidates(task3)
        assert worker1 in candidates  # Has python
        assert worker2 in candidates  # Has javascript
    
    @pytest.mark.asyncio
    async def test_performance_under_load(self):
        """Test system performance with many events"""
        processor = ConversationStreamProcessor()
        visualizer = DecisionVisualizer()
        
        # Process many events
        event_count = 100
        start_time = datetime.now()
        
        for i in range(event_count):
            # Create event
            event = ConversationEvent(
                id=f"event-{i}",
                timestamp=datetime.now(),
                source=f"worker-{i % 10}",
                target="pm_agent",
                event_type="progress_update",
                message=f"Progress update {i}",
                metadata={"progress": i}
            )
            
            # Add to history
            processor.conversation_history.append(event)
            
            # Add decision every 10 events
            if i % 10 == 0:
                decision_data = {
                    "id": f"decision-{i}",
                    "timestamp": datetime.now().isoformat(),
                    "decision": f"Decision {i}",
                    "rationale": "Test rationale",
                    "confidence_score": 0.8,
                    "alternatives_considered": [],
                    "decision_factors": {}
                }
                visualizer.add_decision(decision_data)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Verify performance
        assert len(processor.conversation_history) == event_count
        assert len(visualizer.decisions) == 10
        assert duration < 1.0  # Should process 100 events in under 1 second
        
        # Test summary generation performance
        summary_start = datetime.now()
        summary = processor.get_conversation_summary()
        analytics = visualizer.get_decision_analytics()
        summary_duration = (datetime.now() - summary_start).total_seconds()
        
        assert summary['total_events'] == event_count
        assert analytics['total_decisions'] == 10
        assert summary_duration < 0.1  # Summary should be fast
    
    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """Test system recovery from errors"""
        server = VisualizationServer()
        
        # Mock components with some failures
        server.sio.emit = AsyncMock(side_effect=[
            Exception("Network error"),
            None,  # Success on retry
            None   # Success
        ])
        
        # Process events despite errors
        events_processed = 0
        for i in range(3):
            event = create_mock_conversation_event()
            try:
                await server.handle_conversation_event(event)
                events_processed += 1
            except Exception:
                # Log error but continue
                pass
        
        # Should have processed 2 events (1 failed, 2 succeeded)
        assert server.sio.emit.call_count == 3
        
        # Verify server is still functional
        server.sio.emit = AsyncMock()  # Reset mock
        event = create_mock_conversation_event()
        await server.handle_conversation_event(event)
        server.sio.emit.assert_called_once()