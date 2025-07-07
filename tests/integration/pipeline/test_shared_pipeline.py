#!/usr/bin/env python3
"""
Test shared pipeline events
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.visualization.shared_pipeline_events import SharedPipelineVisualizer
from src.visualization.pipeline_flow import PipelineStage

def test_shared_pipeline():
    """Test that shared pipeline events work"""
    
    visualizer = SharedPipelineVisualizer()
    
    # Start a flow
    flow_id = "test-flow-123"
    visualizer.start_flow(flow_id, "Test Project")
    
    # Add some events
    visualizer.add_event(
        flow_id=flow_id,
        stage=PipelineStage.MCP_REQUEST,
        event_type="create_project_request",
        data={"project_name": "Test Project"},
        status="completed"
    )
    
    visualizer.add_event(
        flow_id=flow_id,
        stage=PipelineStage.AI_ANALYSIS,
        event_type="ai_analysis_started",
        data={"prd_length": 500},
        status="in_progress"
    )
    
    visualizer.add_event(
        flow_id=flow_id,
        stage=PipelineStage.AI_ANALYSIS,
        event_type="ai_analysis_completed",
        data={"confidence": 0.95},
        status="completed",
        duration_ms=2500
    )
    
    # Check active flows
    active_flows = visualizer.get_active_flows()
    print(f"Active flows: {len(active_flows)}")
    for flow in active_flows:
        print(f"  - {flow['project_name']} ({flow['event_count']} events)")
    
    # Get visualization
    viz = visualizer.get_flow_visualization(flow_id)
    print(f"\nVisualization has {len(viz.get('nodes', []))} nodes")
    
    # Complete the flow
    visualizer.complete_flow(flow_id)
    
    print("\nShared pipeline events test passed!")

if __name__ == "__main__":
    test_shared_pipeline()