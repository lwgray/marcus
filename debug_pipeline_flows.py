#!/usr/bin/env python3
"""
Debug pipeline flows
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.visualization.shared_pipeline_events import SharedPipelineVisualizer

def debug_flows():
    """Debug what flows are available"""
    
    visualizer = SharedPipelineVisualizer()
    
    # Get all flows
    flows = visualizer.get_active_flows()
    
    print(f"Found {len(flows)} active flows:")
    for flow in flows:
        print(f"\nFlow: {flow['id']}")
        print(f"  Project: {flow['project_name']}")
        print(f"  Started: {flow['started_at']}")
        print(f"  Events: {flow['event_count']}")
        print(f"  Stage: {flow.get('current_stage', 'unknown')}")
        
        # Get visualization data
        viz = visualizer.get_flow_visualization(flow['id'])
        print(f"  Visualization: {len(viz.get('nodes', []))} nodes, {len(viz.get('edges', []))} edges")
    
    # Check the raw file
    import json
    with open("logs/pipeline_events.json", "r") as f:
        data = json.load(f)
    
    print(f"\nRaw file data:")
    print(f"  Total flows: {len(data['flows'])}")
    print(f"  Total events: {len(data['events'])}")

if __name__ == "__main__":
    debug_flows()