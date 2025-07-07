#!/usr/bin/env python3
"""
Demonstration of the Dependency Awareness Workflow

Shows how Marcus prevents illogical task assignments and ensures
proper task execution order through intelligent dependency inference.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from typing import Dict, List

from src.config.hybrid_inference_config import HybridInferenceConfig
from src.core.context import Context
from src.core.events import Events
from src.core.models import Priority, Task, TaskStatus
from src.core.persistence import MemoryPersistence, Persistence
from src.intelligence.dependency_inferer import DependencyInferer
from src.intelligence.dependency_inferer_hybrid import HybridDependencyInferer


async def create_problematic_scenario() -> List[Task]:
    """Create a scenario that would cause problems without dependency awareness"""

    # This represents a common problem: tasks created in wrong order
    # or without explicit dependencies
    tasks = [
        # These were created out of logical order
        Task(
            id="deploy_prod",
            name="Deploy to Production",
            description="Deploy the application to production servers",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,  # High priority but depends on everything!
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=2.0,
            labels=["deploy", "production"],
            dependencies=[]  # No explicit dependencies!
        ),

        Task(
            id="write_tests",
            name="Write Integration Tests",
            description="Create comprehensive integration test suite",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=8.0,
            labels=["test", "integration"],
            dependencies=[]
        ),

        Task(
            id="build_api",
            name="Build REST API",
            description="Implement REST endpoints for the application",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=16.0,
            labels=["api", "backend", "implementation"],
            dependencies=[]
        ),

        Task(
            id="design_db",
            name="Design Database Schema",
            description="Design tables and relationships",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=4.0,
            labels=["database", "design"],
            dependencies=[]
        ),

        Task(
            id="setup_env",
            name="Setup Development Environment",
            description="Configure Docker, databases, and tools",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,  # Lower priority but needed first!
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=3.0,
            labels=["setup", "infrastructure"],
            dependencies=[]
        ),

        Task(
            id="create_ui",
            name="Create User Interface",
            description="Build React components for the frontend",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=12.0,
            labels=["frontend", "ui", "react"],
            dependencies=[]
        ),

        Task(
            id="security_audit",
            name="Security Audit",
            description="Perform security audit before deployment",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=4.0,
            labels=["security", "audit"],
            dependencies=[]
        )
    ]

    return tasks


async def demonstrate_problem_without_dependencies():
    """Show what happens without dependency awareness"""

    print("\n\n❌ PROBLEM: Task Assignment Without Dependencies")
    print("=" * 60)

    print("\n1. Tasks ordered by priority (naive approach):")

    tasks = await create_problematic_scenario()

    # Sort by priority (what a naive system might do)
    sorted_tasks = sorted(tasks, key=lambda t: (
        0 if t.priority == Priority.HIGH else
        1 if t.priority == Priority.MEDIUM else 2
    ))

    print("\n   Priority-based order:")
    for i, task in enumerate(sorted_tasks, 1):
        print(f"   {i}. [{task.priority.value}] {task.name}")

    print("\n⚠️  PROBLEMS with this order:")
    print("   - Deploy to Production comes before building anything!")
    print("   - Database design comes after API implementation")
    print("   - Setup comes last despite being needed first")
    print("   - Security audit might be forgotten")

    print("\n   This would lead to:")
    print("   ❌ Agents getting blocked immediately")
    print("   ❌ Wasted time and confusion")
    print("   ❌ Poor quality due to out-of-order execution")
    print("   ❌ Security vulnerabilities")


async def demonstrate_pattern_based_inference():
    """Show pattern-based dependency inference"""

    print("\n\n🔍 PATTERN-BASED DEPENDENCY INFERENCE")
    print("=" * 60)

    tasks = await create_problematic_scenario()
    inferer = DependencyInferer()

    print("\n1. Analyzing task relationships using patterns...")

    # Infer dependencies
    graph = await inferer.infer_dependencies(tasks)

    print(f"\n2. Found {len(graph.edges)} implicit dependencies:")

    # Group dependencies by pattern
    pattern_groups = {}
    for dep in graph.edges:
        pattern = dep.reasoning.split(": ")[1] if ": " in dep.reasoning else "Unknown"
        if pattern not in pattern_groups:
            pattern_groups[pattern] = []
        pattern_groups[pattern].append(dep)

    for pattern, deps in pattern_groups.items():
        print(f"\n   {pattern}:")
        for dep in deps:
            dependent = next(t for t in tasks if t.id == dep.dependent_task_id)
            dependency = next(t for t in tasks if t.id == dep.dependency_task_id)
            print(f"     {dependent.name} → requires → {dependency.name}")


async def demonstrate_hybrid_inference():
    """Show hybrid dependency inference with AI enhancement"""

    print("\n\n🤖 HYBRID DEPENDENCY INFERENCE (Pattern + AI)")
    print("=" * 60)

    tasks = await create_problematic_scenario()

    # Mock AI engine for demo
    class MockAIEngine:
        async def _call_claude(self, prompt: str) -> str:
            # Simulate finding a subtle dependency
            return """[
                {
                    "task1_id": "security_audit",
                    "task2_id": "write_tests",
                    "dependency_direction": "1->2",
                    "confidence": 0.85,
                    "reasoning": "Security audit should review test coverage",
                    "dependency_type": "soft"
                }
            ]"""

    config = HybridInferenceConfig(pattern_confidence_threshold=0.8)
    inferer = HybridDependencyInferer(MockAIEngine(), config)

    print("\n1. Analyzing with hybrid approach...")
    graph = await inferer.infer_dependencies(tasks)

    # Show inference methods
    pattern_deps = [d for d in graph.edges if hasattr(d, 'inference_method')
                   and d.inference_method == 'pattern']
    ai_deps = [d for d in graph.edges if hasattr(d, 'inference_method')
              and d.inference_method == 'ai']
    both_deps = [d for d in graph.edges if hasattr(d, 'inference_method')
                and d.inference_method == 'both']

    print(f"\n2. Inference results:")
    print(f"   Pattern-based: {len(pattern_deps)} dependencies")
    print(f"   AI-discovered: {len(ai_deps)} dependencies")
    print(f"   Both agreed: {len(both_deps)} dependencies")

    if ai_deps:
        print("\n3. AI found subtle dependencies:")
        for dep in ai_deps:
            dependent = next(t for t in tasks if t.id == dep.dependent_task_id)
            dependency = next(t for t in tasks if t.id == dep.dependency_task_id)
            print(f"   {dependent.name} → {dependency.name}")
            print(f"   Reasoning: {dep.reasoning}")


async def demonstrate_circular_detection():
    """Show circular dependency detection and resolution"""

    print("\n\n🔄 CIRCULAR DEPENDENCY DETECTION")
    print("=" * 60)

    # Create tasks with circular dependencies
    circular_tasks = [
        Task(
            id="task_a",
            name="Frontend Components",
            description="Build UI components",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=8.0,
            labels=["frontend"],
            dependencies=["task_b"]  # Depends on API
        ),
        Task(
            id="task_b",
            name="API Endpoints",
            description="Build REST API",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=10.0,
            labels=["backend"],
            dependencies=["task_c"]  # Depends on Auth
        ),
        Task(
            id="task_c",
            name="Authentication",
            description="Implement auth system",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=6.0,
            labels=["auth"],
            dependencies=["task_a"]  # Depends on Frontend! (circular)
        )
    ]

    print("\n1. Tasks with circular dependency:")
    print("   Frontend → API → Auth → Frontend (circular!)")

    # Set up context for analysis
    persistence = Persistence(backend=MemoryPersistence())
    events = Events(store_history=True, persistence=persistence)
    context = Context(events=events, persistence=persistence)

    # Detect circular dependencies
    dep_map = {
        "task_a": ["task_b"],
        "task_b": ["task_c"],
        "task_c": ["task_a"]
    }

    cycles = context._detect_circular_dependencies(dep_map, circular_tasks)

    print(f"\n2. Detected {len(cycles)} circular dependency chain(s):")
    for i, cycle in enumerate(cycles, 1):
        print(f"   Chain {i}: {' → '.join(cycle)}")

    print("\n3. Resolution strategies:")
    print("   a) Remove weakest dependency link")
    print("   b) Refactor tasks to break cycle")
    print("   c) Create interface/contract task")
    print("   d) Use feature flags for gradual rollout")

    # Show resolution
    inferer = DependencyInferer()
    graph = await inferer.infer_dependencies(circular_tasks)

    if not graph.has_cycle():
        print("\n✅ Circular dependency automatically resolved!")
        print("   Removed lowest confidence edge to break cycle")


async def demonstrate_optimal_ordering(context: Context):
    """Show how optimal task ordering works"""

    print("\n\n📊 OPTIMAL TASK ORDERING")
    print("=" * 60)

    tasks = await create_problematic_scenario()

    # Analyze dependencies
    dep_map = await context.analyze_dependencies(tasks, infer_implicit=True)

    # Get optimal order using suggest_task_order
    ordered_tasks = await context.suggest_task_order(tasks)

    print("\n1. Optimal execution order:")
    for i, task in enumerate(ordered_tasks, 1):
        # Find what this task depends on
        deps = []
        for dep_id, dependent_ids in dep_map.items():
            if task.id in dependent_ids:
                deps.append(dep_id)

        print(f"\n   {i}. {task.name}")
        print(f"      Priority: {task.priority.value}")
        if deps:
            dep_names = [next(t for t in tasks if t.id == d).name for d in deps]
            print(f"      Depends on: {', '.join(dep_names)}")
        else:
            print(f"      No dependencies (can start immediately)")

    # Show parallelization opportunities
    print("\n\n2. Parallelization opportunities:")

    # Find tasks that can run in parallel
    ready_tasks = []
    completed = set()

    for task in ordered_tasks:
        # Find dependencies for this task
        deps = []
        for dep_id, dependent_ids in dep_map.items():
            if task.id in dependent_ids:
                deps.append(dep_id)

        if all(d in completed for d in deps):
            ready_tasks.append(task.id)

        # Simulate completion
        if len(ready_tasks) >= 2:
            print(f"\n   Can run in parallel:")
            for tid in ready_tasks:
                task_obj = next(t for t in tasks if t.id == tid)
                print(f"     - {task_obj.name}")
            completed.update(ready_tasks)
            ready_tasks = []
        else:
            completed.add(task.id)


async def demonstrate_real_world_benefits():
    """Show real-world benefits of dependency awareness"""

    print("\n\n💡 REAL-WORLD BENEFITS")
    print("=" * 60)

    print("\n1. Prevents Common Problems:")
    print("   ✓ No more 'deploy before build' scenarios")
    print("   ✓ Agents don't get blocked on missing dependencies")
    print("   ✓ Proper setup ensures smooth development")
    print("   ✓ Security and testing happen at right time")

    print("\n2. Improves Efficiency:")
    print("   ✓ Identifies tasks that can run in parallel")
    print("   ✓ Reduces agent idle time")
    print("   ✓ Minimizes rework from out-of-order execution")
    print("   ✓ Faster overall project completion")

    print("\n3. Enhances Quality:")
    print("   ✓ Ensures proper architectural foundations")
    print("   ✓ Testing happens when components are ready")
    print("   ✓ Security reviews at appropriate stages")
    print("   ✓ Documentation created at right time")

    print("\n4. Supports Different Workflows:")

    workflows = [
        ("Waterfall", ["Design", "Implement", "Test", "Deploy"]),
        ("Agile Sprint", ["Plan", "Develop", "Review", "Retrospective"]),
        ("Feature Branch", ["Branch", "Develop", "Test", "Merge", "Deploy"]),
        ("Hotfix", ["Identify", "Fix", "Test", "Deploy", "Monitor"])
    ]

    for workflow_name, stages in workflows:
        print(f"\n   {workflow_name}:")
        print(f"     {' → '.join(stages)}")

    print("\n   Dependency awareness adapts to any workflow!")


async def main():
    """Run the dependency awareness demonstration"""

    print("\n🌟 MARCUS DEPENDENCY AWARENESS DEMONSTRATION")
    print("=" * 60)
    print("This demo shows how Marcus prevents illogical task assignments")
    print("through intelligent dependency inference.")

    # Set up context
    persistence = Persistence(backend=MemoryPersistence())
    events = Events(store_history=True, persistence=persistence)
    context = Context(events=events, persistence=persistence)

    # Run demonstrations
    await demonstrate_problem_without_dependencies()
    await demonstrate_pattern_based_inference()
    await demonstrate_hybrid_inference()
    await demonstrate_circular_detection()
    await demonstrate_optimal_ordering(context)
    await demonstrate_real_world_benefits()

    # Summary
    print("\n\n📈 DEPENDENCY AWARENESS SUMMARY")
    print("=" * 60)
    print("""
The dependency awareness system provides:

1. Intelligent Inference
   - Pattern-based rules for common relationships
   - AI enhancement for subtle dependencies
   - Confidence scoring for each dependency

2. Cycle Detection & Resolution
   - Finds circular dependencies automatically
   - Resolves cycles by removing weak links
   - Prevents deadlock situations

3. Optimal Ordering
   - Topological sort for correct execution
   - Identifies parallelization opportunities
   - Respects both priorities and dependencies

4. Continuous Improvement
   - Learns from task outcomes
   - Adapts patterns based on success/failure
   - Hybrid approach minimizes AI costs

Without dependency awareness:
❌ "Deploy to production" assigned before code exists
❌ Agents blocked waiting for prerequisites
❌ Rework due to out-of-order execution
❌ Security vulnerabilities from skipped steps

With dependency awareness:
✅ Tasks execute in logical order
✅ Agents work efficiently without blocks
✅ Higher quality from proper sequencing
✅ Security and testing at right stages
""")

    print("\n✅ Demonstration complete!")


if __name__ == "__main__":
    asyncio.run(main())
