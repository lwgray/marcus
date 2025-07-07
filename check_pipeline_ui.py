#!/usr/bin/env python3
"""
Check if pipeline UI can read events
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.visualization.shared_pipeline_events import SharedPipelineVisualizer

def check_pipeline_ui():
    """Check pipeline events from UI perspective"""
    
    visualizer = SharedPipelineVisualizer()
    
    # Get active flows
    active_flows = visualizer.get_active_flows()
    print(f"Active flows: {len(active_flows)}")
    
    # Get all flows (including completed)
    import json
    with open("logs/pipeline_events.json", "r") as f:
        data = json.load(f)
    
    print(f"\nAll flows: {len(data['flows'])}")
    for flow_id, flow_data in data['flows'].items():
        print(f"  - {flow_data['project_name']} (active: {flow_data.get('is_active', False)})")
        
        # Get visualization
        viz = visualizer.get_flow_visualization(flow_id)
        print(f"    Nodes: {len(viz.get('nodes', []))}")
        print(f"    Edges: {len(viz.get('edges', []))}")

if __name__ == "__main__":
    check_pipeline_ui()