#!/usr/bin/env python3
"""
Demonstration of the Enhanced Visibility System

Shows how the visibility system integrates with events to provide
real-time insights into Marcus operations.
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from src.core.events import Events, EventTypes
from src.core.persistence import Persistence, MemoryPersistence
from src.visualization.event_integrated_visualizer import EventIntegratedVisualizer
from src.core.models import Task, TaskStatus, Priority


async def simulate_project_workflow(events: Events):
    """Simulate a realistic project workflow with various events"""
    
    print("\n📊 Simulating project workflow...")
    print("-" * 60)
    
    # Project start
    await events.publish(
        EventTypes.PROJECT_CREATED,
        "marcus",
        {
            "project_id": "todo_app",
            "project_name": "Todo Application",
            "total_tasks": 12,
            "estimated_hours": 80
        }
    )
    
    # Task assignments
    tasks = [
        ("task_1", "Design Database Schema", "alice", ["database", "design"]),
        ("task_2", "Build User API", "bob", ["api", "backend"]),
        ("task_3", "Create React UI", "charlie", ["frontend", "react"])
    ]
    
    for task_id, task_name, agent_id, labels in tasks:
        await events.publish(
            EventTypes.TASK_ASSIGNED,
            "marcus",
            {
                "task_id": task_id,
                "task_name": task_name,
                "agent_id": agent_id,
                "labels": labels,
                "has_context": True,
                "has_predictions": True
            }
        )
        await asyncio.sleep(0.1)  # Small delay for realism
    
    # Simulate progress
    print("\n🚀 Agents working on tasks...")
    
    # Alice makes quick progress
    for progress in [25, 50, 75, 100]:
        await events.publish(
            EventTypes.TASK_PROGRESS,
            "alice",
            {
                "task_id": "task_1",
                "progress": progress,
                "status": "completed" if progress == 100 else "in_progress",
                "message": f"Database schema {progress}% complete"
            }
        )
        await asyncio.sleep(0.05)
    
    # Bob encounters a blocker
    await events.publish(
        EventTypes.TASK_BLOCKED,
        "bob",
        {
            "task_id": "task_2",
            "blocker": "Missing database connection details",
            "severity": "high",
            "suggested_resolution": "Get connection string from Alice"
        }
    )
    
    # Context update resolves blocker
    await events.publish(
        EventTypes.CONTEXT_UPDATED,
        "context_system",
        {
            "task_id": "task_2",
            "update_type": "implementation_shared",
            "from_task": "task_1",
            "shared_data": {"connection": "postgres://localhost/todo_app"}
        }
    )
    
    # Bob continues
    await events.publish(
        EventTypes.BLOCKER_RESOLVED,
        "bob",
        {
            "task_id": "task_2",
            "resolution": "Received database connection from context"
        }
    )
    
    # Memory system makes predictions
    await events.publish(
        EventTypes.PREDICTION_MADE,
        "memory_system",
        {
            "agent_id": "charlie",
            "task_id": "task_3",
            "prediction": {
                "success_probability": 0.85,
                "estimated_hours": 12,
                "confidence": 0.75,
                "risk_factors": ["First React task for this agent"]
            }
        }
    )
    
    # Architectural decision logged
    await events.publish(
        EventTypes.DECISION_LOGGED,
        "alice",
        {
            "decision_id": "arch_1",
            "what": "Use PostgreSQL for database",
            "why": "Need ACID compliance and complex queries",
            "impact": "All services must use PostgreSQL client",
            "task_id": "task_1"
        }
    )


async def demonstrate_visibility_features(visualizer: EventIntegratedVisualizer):
    """Show various visibility system features"""
    
    print("\n\n🔍 VISIBILITY SYSTEM FEATURES")
    print("=" * 60)
    
    # 1. Event Statistics
    print("\n1. Event Statistics:")
    stats = visualizer.get_event_statistics()
    print(f"   Total events: {stats['total_events']}")
    print(f"   Event types: {len(stats['event_counts'])}")
    print("   Top events:")
    for event_type, count in sorted(stats['event_counts'].items(), 
                                   key=lambda x: x[1], reverse=True)[:5]:
        print(f"     - {event_type}: {count}")
    
    # 2. Active Flow Analysis
    print("\n2. Active Flow Analysis:")
    if hasattr(visualizer, 'active_flows') and visualizer.active_flows:
        print(f"   Active task flows: {len(visualizer.active_flows)}")
        for flow_id, flow_data in list(visualizer.active_flows.items())[:5]:
            if 'stage' in flow_data:
                print(f"     - Flow {flow_id[:8]}: Stage {flow_data['stage']}")
    else:
        print("   No active flows tracked yet")
    
    # 3. Feature Usage
    print("\n3. Feature Usage (from event types):")
    feature_map = {
        'task_assigned': 'Task Management',
        'context_updated': 'Context System',
        'prediction_made': 'Memory System',
        'decision_logged': 'Decision Tracking'
    }
    
    for event_type, feature in feature_map.items():
        count = stats['event_counts'].get(event_type, 0)
        if count > 0:
            print(f"   {feature}: used {count} times")
    
    # 4. Event Flow Analysis
    print("\n4. Event Flow Analysis:")
    if hasattr(visualizer, 'active_flows'):
        print(f"   Active flows: {len(visualizer.active_flows)}")
        for flow_id, flow_data in list(visualizer.active_flows.items())[:3]:
            print(f"     - Flow {flow_id[:8]}: {len(flow_data.get('events', []))} events")


async def demonstrate_event_filtering(visualizer: EventIntegratedVisualizer, events: Events):
    """Show event filtering capabilities"""
    
    print("\n\n🎯 EVENT FILTERING CAPABILITIES")
    print("=" * 60)
    
    # Subscribe to specific patterns
    print("\n1. Subscribing to specific event patterns:")
    
    # Track only critical events
    critical_events = []
    
    async def track_critical(event):
        if event.metadata and event.metadata.get("severity") == "high":
            critical_events.append(event)
    
    events.subscribe(EventTypes.TASK_BLOCKED, track_critical)
    events.subscribe(EventTypes.ERROR, track_critical)
    
    # Generate some test events
    await events.publish(
        EventTypes.ERROR,
        "test_service",
        {"error": "Connection timeout"},
        metadata={"severity": "high"}
    )
    
    await events.publish(
        EventTypes.WARNING,
        "test_service",
        {"warning": "Slow response"},
        metadata={"severity": "low"}
    )
    
    print(f"   Captured {len(critical_events)} critical events")
    
    # 2. Event type filtering demonstration
    print("\n2. Event Type Filtering:")
    stats = visualizer.get_event_statistics()
    task_events = ['task_assigned', 'task_started', 'task_progress', 'task_completed']
    task_event_count = sum(stats['event_counts'].get(evt, 0) for evt in task_events)
    print(f"   Task-related events: {task_event_count}")
    print(f"   Other events: {stats['total_events'] - task_event_count}")
    
    # 3. Pattern analysis from statistics
    print("\n3. Event Pattern Analysis:")
    if stats['event_counts']:
        # Find most common event type
        most_common = max(stats['event_counts'].items(), key=lambda x: x[1])
        print(f"   Most frequent event: {most_common[0]} ({most_common[1]} occurrences)")
        
        # Check for imbalances
        if 'task_assigned' in stats['event_counts'] and 'task_completed' in stats['event_counts']:
            assigned = stats['event_counts']['task_assigned']
            completed = stats['event_counts'].get('task_completed', 0)
            if assigned > completed:
                print(f"   Tasks in progress: {assigned - completed}")


async def demonstrate_integration_points(visualizer: EventIntegratedVisualizer):
    """Show how visibility integrates with other systems"""
    
    print("\n\n🔗 INTEGRATION WITH OTHER SYSTEMS")
    print("=" * 60)
    
    print("\n1. Context System Integration:")
    print("   ✓ Tracks context updates in real-time")
    print("   ✓ Shows which tasks share context")
    print("   ✓ Monitors architectural decisions")
    
    print("\n2. Memory System Integration:")
    print("   ✓ Displays predictions as they're made")
    print("   ✓ Shows confidence levels")
    print("   ✓ Tracks learning progress")
    
    print("\n3. Task Management Integration:")
    print("   ✓ Real-time task status updates")
    print("   ✓ Progress tracking")
    print("   ✓ Blocker detection and resolution")
    
    # Show cross-system insights from statistics
    print("\n4. Cross-System Insights:")
    stats = visualizer.get_event_statistics()
    
    # Estimate from event counts
    context_updates = stats['event_counts'].get('context_updated', 0)
    predictions = stats['event_counts'].get('prediction_made', 0)
    blockers_resolved = stats['event_counts'].get('blocker_resolved', 0)
    
    print(f"   Context updates: {context_updates}")
    print(f"   Predictions made: {predictions}")
    print(f"   Blockers resolved: {blockers_resolved}")
    
    # Show integration health
    if stats['total_events'] > 0:
        integration_ratio = (context_updates + predictions) / stats['total_events']
        print(f"   Integration ratio: {integration_ratio:.1%} of events from integrated systems")


async def main():
    """Run the visibility system demonstration"""
    
    print("\n🌟 MARCUS VISIBILITY SYSTEM DEMONSTRATION")
    print("=" * 60)
    print("This demo shows how the enhanced visibility system provides")
    print("real-time insights into Marcus operations through event integration.")
    
    # Set up the environment
    print("\n⚙️  Setting up environment...")
    persistence = Persistence(backend=MemoryPersistence())
    events = Events(store_history=True, persistence=persistence)
    visualizer = EventIntegratedVisualizer(events_system=events)
    await visualizer.initialize()
    
    # Run demonstrations
    await simulate_project_workflow(events)
    await demonstrate_visibility_features(visualizer)
    await demonstrate_event_filtering(visualizer, events)
    await demonstrate_integration_points(visualizer)
    
    # Summary
    print("\n\n📈 VISIBILITY SYSTEM BENEFITS")
    print("=" * 60)
    print("""
1. Real-time Monitoring:
   - Track all system events as they happen
   - See agent activity and task progress
   - Monitor feature usage and adoption

2. Historical Analysis:
   - Query past events with filters
   - Detect patterns and trends
   - Generate insights from event data

3. Integration Hub:
   - Unified view of all Marcus systems
   - Cross-system correlations
   - Identify bottlenecks and inefficiencies

4. Debugging & Troubleshooting:
   - Trace event flows
   - Find root causes of issues
   - Monitor system health

5. Performance Optimization:
   - Identify slow operations
   - Track resource usage
   - Optimize based on real usage patterns
""")
    
    print("\n✅ Demonstration complete!")


if __name__ == "__main__":
    asyncio.run(main())