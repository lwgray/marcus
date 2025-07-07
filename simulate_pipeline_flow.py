#!/usr/bin/env python3
"""
Simulate a pipeline flow with real-time events
"""
import asyncio
import sys
from pathlib import Path
import uuid

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.visualization.shared_pipeline_events import SharedPipelineVisualizer
from src.visualization.pipeline_flow import PipelineStage

async def simulate_flow():
    """Simulate a pipeline flow with delays"""
    
    visualizer = SharedPipelineVisualizer()
    flow_id = str(uuid.uuid4())
    
    print(f"Starting flow: {flow_id}")
    
    # Start flow
    visualizer.start_flow(flow_id, "Simulated Todo App")
    await asyncio.sleep(1)
    
    # MCP Request
    print("Stage 1: MCP Request")
    visualizer.add_event(
        flow_id=flow_id,
        stage=PipelineStage.MCP_REQUEST,
        event_type="create_project_request",
        data={"project_name": "Simulated Todo App"},
        status="completed"
    )
    await asyncio.sleep(2)
    
    # AI Analysis
    print("Stage 2: AI Analysis")
    visualizer.add_event(
        flow_id=flow_id,
        stage=PipelineStage.AI_ANALYSIS,
        event_type="ai_analysis_started",
        data={"prd_length": 500},
        status="in_progress"
    )
    await asyncio.sleep(3)
    
    visualizer.add_event(
        flow_id=flow_id,
        stage=PipelineStage.AI_ANALYSIS,
        event_type="ai_analysis_completed",
        data={"confidence": 0.92},
        status="completed",
        duration_ms=3000
    )
    await asyncio.sleep(1)
    
    # Task Generation
    print("Stage 3: Task Generation")
    visualizer.add_event(
        flow_id=flow_id,
        stage=PipelineStage.TASK_GENERATION,
        event_type="tasks_generated",
        data={
            "task_count": 10,
            "task_names": ["Design API", "Implement CRUD", "Add Auth", "Testing", "Deploy"]
        },
        status="completed",
        duration_ms=1500
    )
    await asyncio.sleep(2)
    
    # Task Creation
    print("Stage 4: Task Creation")
    for i, task_name in enumerate(["Design API", "Implement CRUD", "Add Auth"]):
        visualizer.track_task_creation(
            flow_id=flow_id,
            task_id=f"TASK-{i+1}",
            task_name=task_name,
            success=True
        )
        await asyncio.sleep(0.5)
    
    # Complete flow
    print("Stage 5: Completion")
    visualizer.complete_flow(flow_id)
    
    print(f"\nFlow completed! Check http://localhost:8080/pipeline")
    print(f"Flow ID: {flow_id}")

if __name__ == "__main__":
    asyncio.run(simulate_flow())