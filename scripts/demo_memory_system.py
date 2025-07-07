#!/usr/bin/env python3
"""
Demonstration of the Enhanced Memory System

Shows how the memory system learns from agent experiences and provides
intelligent predictions with confidence intervals.
"""

import asyncio
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from typing import Any, Dict, List

from src.core.events import Events, EventTypes
from src.core.memory_enhanced import MemoryEnhanced
from src.core.models import Priority, Task, TaskStatus, WorkerStatus
from src.core.persistence import MemoryPersistence, Persistence


async def simulate_agent_history(memory: MemoryEnhanced) -> Dict[str, List[Dict]]:
    """Simulate realistic agent work history"""

    print("\n📊 Building agent work history...")
    print("-" * 60)

    agents = {
        "alice": {
            "expertise": ["database", "backend", "architecture"],
            "success_rate": 0.9,
            "speed_factor": 0.8,  # Faster than average
        },
        "bob": {
            "expertise": ["api", "backend", "integration"],
            "success_rate": 0.85,
            "speed_factor": 1.0,  # Average speed
        },
        "charlie": {
            "expertise": ["frontend", "ui", "react"],
            "success_rate": 0.75,  # Still learning
            "speed_factor": 1.2,  # Slower, more careful
        },
    }

    history = {}

    for agent_id, profile in agents.items():
        print(f"\n🤖 Simulating history for {agent_id}...")
        agent_history = []

        # Generate 20 past tasks per agent
        for i in range(20):
            # Pick random expertise area
            area = random.choice(profile["expertise"])

            # Create task
            task = Task(
                id=f"{agent_id}_task_{i}",
                name=f"{area.title()} Task {i}",
                description=f"Work on {area} component",
                status=TaskStatus.TODO,
                priority=random.choice([Priority.HIGH, Priority.MEDIUM, Priority.LOW]),
                assigned_to=agent_id,
                created_at=datetime.now() - timedelta(days=30 - i),
                updated_at=datetime.now() - timedelta(days=30 - i),
                due_date=None,
                estimated_hours=random.uniform(2, 16),
                labels=[area, random.choice(["feature", "bugfix", "refactor"])],
                dependencies=[],
            )

            # Record task execution
            await memory.record_task_start(agent_id, task)

            # Determine outcome based on profile
            success = random.random() < profile["success_rate"]

            # Add some complexity factors
            if "complex" in task.name.lower() or task.estimated_hours > 10:
                success = success and random.random() < 0.8  # Harder

            # Calculate actual time
            actual_hours = task.estimated_hours * profile["speed_factor"]
            actual_hours *= random.uniform(0.8, 1.2)  # Add variance

            # Record completion
            blockers = []
            if not success and random.random() < 0.5:
                blockers = [
                    random.choice(
                        [
                            "unclear_requirements",
                            "technical_debt",
                            "missing_dependency",
                            "api_changes",
                        ]
                    )
                ]

            await memory.record_task_completion(
                agent_id=agent_id,
                task_id=task.id,
                success=success,
                actual_hours=actual_hours,
                blockers=blockers,
            )

            agent_history.append(
                {
                    "task": task,
                    "success": success,
                    "actual_hours": actual_hours,
                    "blockers": blockers,
                }
            )

        history[agent_id] = agent_history

        # Show summary
        successes = sum(1 for h in agent_history if h["success"])
        avg_time = sum(h["actual_hours"] for h in agent_history) / len(agent_history)
        print(f"   ✓ Success rate: {successes/len(agent_history)*100:.0f}%")
        print(f"   ✓ Average time: {avg_time:.1f} hours")

    return history


async def demonstrate_basic_predictions(memory: MemoryEnhanced):
    """Show basic prediction capabilities"""

    print("\n\n🔮 BASIC PREDICTION CAPABILITIES")
    print("=" * 60)

    # Create test tasks
    test_tasks = [
        Task(
            id="predict_1",
            name="Simple Database Migration",
            description="Add new column to users table",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=2.0,
            labels=["database", "migration"],
            dependencies=[],
        ),
        Task(
            id="predict_2",
            name="Complex API Integration",
            description="Integrate with third-party payment system",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=16.0,
            labels=["api", "integration", "complex"],
            dependencies=[],
        ),
        Task(
            id="predict_3",
            name="React Component Library",
            description="Build reusable UI components",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=12.0,
            labels=["frontend", "react", "ui"],
            dependencies=[],
        ),
    ]

    agents = ["alice", "bob", "charlie"]

    print("\n1. Predictions for each agent-task combination:")
    print("-" * 80)
    print(f"{'Agent':<10} {'Task':<30} {'Success':<10} {'Duration':<12} {'Risk':<10}")
    print("-" * 80)

    for task in test_tasks:
        print(f"\n{task.name}:")
        for agent_id in agents:
            prediction = await memory.predict_task_outcome(agent_id, task)

            success_prob = prediction["success_probability"]
            duration = prediction["estimated_duration"]
            risk = prediction.get("blockage_risk", 0)

            print(
                f"{agent_id:<10} {task.name[:28]:<30} "
                f"{success_prob*100:<9.0f}% {duration:<11.1f}h "
                f"{risk*100:<9.0f}%"
            )


async def demonstrate_enhanced_predictions(memory: MemoryEnhanced):
    """Show enhanced prediction features with confidence"""

    print("\n\n🎯 ENHANCED PREDICTIONS WITH CONFIDENCE")
    print("=" * 60)

    # Complex task for detailed analysis
    complex_task = Task(
        id="complex_1",
        name="Build Microservice Architecture",
        description="Design and implement microservices with message queue",
        status=TaskStatus.TODO,
        priority=Priority.HIGH,
        assigned_to=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        due_date=None,
        estimated_hours=40.0,  # Very complex
        labels=["architecture", "backend", "complex", "microservices"],
        dependencies=[],
    )

    print("\n1. Enhanced predictions for complex task:")

    for agent_id in ["alice", "bob", "charlie"]:
        print(f"\n📊 Agent: {agent_id}")
        print("-" * 40)

        # Get enhanced predictions
        predictions = await memory.predict_task_outcome_v2(agent_id, complex_task)

        # Basic predictions
        print(f"Success Probability: {predictions['success_probability']*100:.0f}%")
        print(f"Estimated Duration: {predictions['estimated_duration']:.1f} hours")
        print(f"Confidence Level: {predictions['confidence']*100:.0f}%")

        # Confidence interval
        ci = predictions["confidence_interval"]
        print(
            f"Success Range: {ci['lower']*100:.0f}% - {ci['upper']*100:.0f}%"
        )
        
        # Duration confidence interval
        duration_ci = predictions["duration_confidence_interval"]
        print(
            f"Duration Range: {duration_ci['lower']:.1f} - {duration_ci['upper']:.1f} hours"
        )

        # Complexity analysis
        print(f"Complexity Factor: {predictions['complexity_factor']:.2f}x")

        # Risk analysis
        print("\nRisk Factors:")
        for risk in predictions["risk_analysis"]["factors"][:3]:
            print(f"  - {risk['description']}")
            print(f"    Type: {risk['type']} | Severity: {risk['severity']}")

        # Calculate overall risk from factors
        risk_count = len(predictions["risk_analysis"]["factors"])
        high_severity = sum(1 for r in predictions["risk_analysis"]["factors"] if r.get("severity") == "high")
        if high_severity > 0:
            overall_risk = "High"
        elif risk_count > 2:
            overall_risk = "Medium"
        elif risk_count > 0:
            overall_risk = "Low"
        else:
            overall_risk = "Minimal"
        print(f"\nOverall Risk Level: {overall_risk} ({risk_count} factors)")


async def demonstrate_learning_progress(memory: MemoryEnhanced, events: Events):
    """Show how the system learns and improves predictions"""

    print("\n\n📈 LEARNING AND ADAPTATION")
    print("=" * 60)

    # Charlie is learning frontend development
    agent_id = "charlie"

    print(f"\n1. Tracking {agent_id}'s learning progress in React:")
    print("-" * 60)

    # Create a series of React tasks
    react_tasks = []
    for i in range(5):
        task = Task(
            id=f"learn_{i}",
            name=f"React Learning Task {i+1}",
            description="Build React component with increasing complexity",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=agent_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=6.0 + i * 2,  # Increasing complexity
            labels=["frontend", "react", "learning"],
            dependencies=[],
        )
        react_tasks.append(task)

    # Show predictions before learning
    print("\nInitial prediction for final task:")
    initial_pred = await memory.predict_task_outcome_v2(agent_id, react_tasks[-1])
    print(f"  Success: {initial_pred['success_probability']*100:.0f}%")
    print(f"  Confidence: {initial_pred['confidence']*100:.0f}%")

    # Simulate learning process
    print("\nLearning progress:")
    for i, task in enumerate(react_tasks[:-1]):
        await memory.record_task_start(agent_id, task)

        # Improving success rate
        success = i >= 1  # Fails first task, succeeds rest
        actual_hours = task.estimated_hours * (1.3 - i * 0.1)  # Getting faster

        await memory.record_task_completion(
            agent_id=agent_id,
            task_id=task.id,
            success=success,
            actual_hours=actual_hours,
            blockers=["learning_curve"] if i == 0 else [],
        )

        print(
            f"  Task {i+1}: {'✓ Success' if success else '✗ Failed'} "
            f"({actual_hours:.1f}h)"
        )

        # Fire learning event
        await events.publish(
            EventTypes.AGENT_LEARNED,
            "memory_system",
            {"agent_id": agent_id, "skill": "react", "improvement": 0.2 * (i + 1)},
        )

    # Show improved predictions
    print("\nUpdated prediction for final task:")
    updated_pred = await memory.predict_task_outcome_v2(agent_id, react_tasks[-1])
    print(
        f"  Success: {updated_pred['success_probability']*100:.0f}% "
        f"(+{(updated_pred['success_probability'] - initial_pred['success_probability'])*100:.0f}%)"
    )
    print(
        f"  Confidence: {updated_pred['confidence']*100:.0f}% "
        f"(+{(updated_pred['confidence'] - initial_pred['confidence'])*100:.0f}%)"
    )

    # Show learning curve
    print("\n2. Agent skill progression:")
    profile = memory.semantic["agent_profiles"].get(agent_id)
    if profile:
        print(f"  Tasks completed: {profile.total_tasks}")
        print(f"  Success rate: {profile.successful_tasks/max(1, profile.total_tasks)*100:.0f}%")
        top_skills = sorted(profile.skill_success_rates.items(), key=lambda x: x[1], reverse=True)[:3]
        print(f"  Top skills: {', '.join([skill for skill, rate in top_skills])}")
    else:
        print("  No profile data available yet")


async def demonstrate_pattern_detection(memory: MemoryEnhanced):
    """Show how memory detects patterns and anomalies"""

    print("\n\n🔍 PATTERN DETECTION AND INSIGHTS")
    print("=" * 60)

    print("\n1. Common failure patterns:")

    # Analyze failure patterns
    failure_patterns = {}
    for outcome in memory.episodic.get("outcomes", []):
        if not outcome.success and outcome.blockers:
            for blocker in outcome.blockers:
                failure_patterns[blocker] = failure_patterns.get(blocker, 0) + 1

    if failure_patterns:
        for blocker, count in sorted(
            failure_patterns.items(), key=lambda x: x[1], reverse=True
        )[:5]:
            print(f"   - {blocker}: {count} occurrences")

    print("\n2. Task complexity vs actual time:")

    # Analyze estimation accuracy
    estimation_data = []
    for outcome in memory.episodic.get("outcomes", []):
        if outcome.success and hasattr(outcome, 'estimated_hours'):
            estimated = outcome.estimated_hours
            actual = outcome.actual_hours
            if estimated and actual:
                ratio = actual / estimated
                estimation_data.append((estimated, ratio))

    if estimation_data:
        # Group by complexity
        simple = [r for e, r in estimation_data if e <= 4]
        medium = [r for e, r in estimation_data if 4 < e <= 10]
        complex = [r for e, r in estimation_data if e > 10]

        if simple:
            print(f"   Simple tasks (≤4h): {sum(simple)/len(simple):.2f}x estimated")
        if medium:
            print(f"   Medium tasks (4-10h): {sum(medium)/len(medium):.2f}x estimated")
        if complex:
            print(
                f"   Complex tasks (>10h): {sum(complex)/len(complex):.2f}x estimated"
            )

    print("\n3. Agent specialization insights:")
    print("   (Using profile data from semantic memory)")

    # Show agent strengths from profiles
    for agent_id in ["alice", "bob", "charlie"]:
        profile = memory.semantic["agent_profiles"].get(agent_id)
        if profile:
            print(f"\n   {agent_id}:")
            top_skills = sorted(profile.skill_success_rates.items(), key=lambda x: x[1], reverse=True)[:3]
            for skill, rate in top_skills:
                print(f"     - {skill}: {rate:.0%} success rate")


async def demonstrate_time_relevance(memory: MemoryEnhanced):
    """Show how predictions account for time-based relevance"""

    print("\n\n⏰ TIME-BASED RELEVANCE WEIGHTING")
    print("=" * 60)

    print("\n1. How recency affects predictions:")
    print("   Recent tasks have more weight in predictions")
    print("   Weight decreases exponentially over time")

    # Create two similar tasks
    task_old = Task(
        id="old_task",
        name="API Development (6 months ago)",
        description="Old API task",
        status=TaskStatus.TODO,
        priority=Priority.HIGH,
        assigned_to=None,
        created_at=datetime.now() - timedelta(days=180),
        updated_at=datetime.now() - timedelta(days=180),
        due_date=None,
        estimated_hours=8.0,
        labels=["api", "backend"],
        dependencies=[],
    )

    task_new = Task(
        id="new_task",
        name="API Development (current)",
        description="Current API task",
        status=TaskStatus.TODO,
        priority=Priority.HIGH,
        assigned_to=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        due_date=None,
        estimated_hours=8.0,
        labels=["api", "backend"],
        dependencies=[],
    )

    # Add some recent history for Bob
    for i in range(3):
        recent_task = Task(
            id=f"recent_{i}",
            name=f"Recent API Task {i}",
            description="Recent work",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to="bob",
            created_at=datetime.now() - timedelta(days=i + 1),
            updated_at=datetime.now() - timedelta(days=i + 1),
            due_date=None,
            estimated_hours=6.0,
            labels=["api", "backend"],
            dependencies=[],
        )

        await memory.record_task_start("bob", recent_task)
        await memory.record_task_completion(
            agent_id="bob",
            task_id=recent_task.id,
            success=True,
            actual_hours=5.0,  # Bob got faster recently
        )

    print("\n2. Impact on predictions:")

    # Get predictions for both
    pred_old = await memory.predict_task_outcome_v2("bob", task_old)
    pred_new = await memory.predict_task_outcome_v2("bob", task_new)

    print(f"\n   Prediction confidence comparison:")
    print(f"   - Using old data: {pred_old['confidence']*100:.0f}%")
    print(f"   - Using recent data: {pred_new['confidence']*100:.0f}%")
    print(f"\n   The recent improvements in Bob's API development")
    print(f"   are weighted more heavily in current predictions.")


async def main():
    """Run the memory system demonstration"""

    print("\n🌟 MARCUS MEMORY SYSTEM DEMONSTRATION")
    print("=" * 60)
    print("This demo shows how the enhanced memory system learns from")
    print("agent experiences and provides intelligent predictions.")

    # Set up environment
    print("\n⚙️  Setting up environment...")
    persistence = Persistence(backend=MemoryPersistence())
    events = Events(store_history=True, persistence=persistence)
    memory = MemoryEnhanced(events=events, persistence=persistence)

    # Build agent history
    history = await simulate_agent_history(memory)

    # Run demonstrations
    await demonstrate_basic_predictions(memory)
    await demonstrate_enhanced_predictions(memory)
    await demonstrate_learning_progress(memory, events)
    await demonstrate_pattern_detection(memory)
    await demonstrate_time_relevance(memory)

    # Summary
    print("\n\n📈 MEMORY SYSTEM BENEFITS")
    print("=" * 60)
    print(
        """
The enhanced memory system provides:

1. Intelligent Predictions
   - Success probability estimation
   - Duration predictions with confidence
   - Risk analysis and mitigation

2. Continuous Learning
   - Improves with experience
   - Adapts to agent growth
   - Detects skill development

3. Pattern Recognition
   - Identifies failure patterns
   - Finds estimation biases
   - Discovers agent strengths

4. Time-Aware Analysis
   - Recent data weighted higher
   - Accounts for skill changes
   - Adapts to new patterns

5. Confidence Intervals
   - Quantifies prediction uncertainty
   - Helps with planning
   - Improves decision making

The memory system helps Marcus:
✓ Assign tasks to the right agents
✓ Estimate project timelines accurately
✓ Identify and mitigate risks early
✓ Support agent growth and learning
✓ Continuously improve predictions
"""
    )

    print("\n✅ Demonstration complete!")


if __name__ == "__main__":
    asyncio.run(main())
