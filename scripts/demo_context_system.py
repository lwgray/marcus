#!/usr/bin/env python3
"""
Demonstration of the Enhanced Context System

Shows how the context system manages dependencies, decisions, and
shared knowledge between agents.
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from typing import List

from src.core.context import Context
from src.core.events import Events, EventTypes
from src.core.persistence import Persistence, MemoryPersistence
from src.core.models import Task, TaskStatus, Priority


async def create_example_project() -> List[Task]:
    """Create a realistic e-commerce project with complex dependencies"""
    
    tasks = [
        # Infrastructure layer
        Task(
            id="infra_1",
            name="Setup Development Environment",
            description="Configure Docker, databases, and tools",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=4.0,
            labels=["setup", "infrastructure"],
            dependencies=[]
        ),
        
        # Database layer
        Task(
            id="db_1",
            name="Design Database Schema",
            description="Design tables for products, users, orders",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=6.0,
            labels=["database", "design"],
            dependencies=["infra_1"]
        ),
        
        Task(
            id="db_2",
            name="Implement Database Models",
            description="Create ORM models for all entities",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=8.0,
            labels=["database", "backend", "models"],
            dependencies=[]  # Will be inferred
        ),
        
        # Backend layer
        Task(
            id="api_1",
            name="Build Authentication API",
            description="JWT-based auth endpoints",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=10.0,
            labels=["api", "auth", "backend"],
            dependencies=[]  # Will be inferred
        ),
        
        Task(
            id="api_2",
            name="Create Product API",
            description="CRUD endpoints for products",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=12.0,
            labels=["api", "backend", "products"],
            dependencies=[]  # Will be inferred
        ),
        
        # Frontend layer
        Task(
            id="ui_1",
            name="Design UI Components",
            description="Create reusable React components",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=8.0,
            labels=["frontend", "ui", "design"],
            dependencies=[]
        ),
        
        Task(
            id="ui_2",
            name="Implement Product Catalog UI",
            description="Product listing and detail pages",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=10.0,
            labels=["frontend", "ui", "products"],
            dependencies=[]  # Will be inferred
        ),
        
        # Testing layer
        Task(
            id="test_1",
            name="Test Authentication System",
            description="Unit and integration tests for auth",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=6.0,
            labels=["test", "auth"],
            dependencies=[]  # Will be inferred
        ),
        
        # Deployment
        Task(
            id="deploy_1",
            name="Deploy to Production",
            description="Deploy all services to AWS",
            status=TaskStatus.TODO,
            priority=Priority.LOW,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=4.0,
            labels=["deploy", "production"],
            dependencies=[]  # Will be inferred
        )
    ]
    
    return tasks


async def demonstrate_dependency_inference(context: Context, tasks: List[Task]):
    """Show how the context system infers dependencies"""
    
    print("\n\n🔗 DEPENDENCY INFERENCE DEMONSTRATION")
    print("=" * 60)
    
    # Show tasks without explicit dependencies
    print("\n1. Tasks with missing dependencies:")
    for task in tasks:
        if not task.dependencies and task.id != "infra_1":
            print(f"   - {task.name} (no explicit dependencies)")
    
    # Analyze with inference
    print("\n2. Analyzing dependencies with inference...")
    dep_map = await context.analyze_dependencies(tasks, infer_implicit=True)
    
    # Show inferred dependencies
    print("\n3. Inferred dependency graph:")
    for dependency_id, dependents in sorted(dep_map.items()):
        dependency_task = next(t for t in tasks if t.id == dependency_id)
        if dependents:
            print(f"\n   {dependency_task.name} blocks:")
            for dependent_id in dependents:
                dependent_task = next(t for t in tasks if t.id == dependent_id)
                print(f"     → {dependent_task.name}")
    
    # Check for circular dependencies
    print("\n4. Circular dependency check:")
    cycles = context._detect_circular_dependencies(dep_map, tasks)
    if cycles:
        print("   ⚠️  Circular dependencies detected:")
        for cycle in cycles:
            print(f"     {' → '.join(cycle)}")
    else:
        print("   ✅ No circular dependencies found")
    
    # Get optimal task order
    print("\n5. Optimal task execution order:")
    ordered_tasks = context._get_optimal_task_order(dep_map, tasks)
    for i, task_id in enumerate(ordered_tasks[:5], 1):
        task = next(t for t in tasks if t.id == task_id)
        print(f"   {i}. {task.name}")
    if len(ordered_tasks) > 5:
        print(f"   ... and {len(ordered_tasks) - 5} more tasks")


async def demonstrate_decision_tracking(context: Context):
    """Show architectural decision logging and retrieval"""
    
    print("\n\n📋 ARCHITECTURAL DECISION TRACKING")
    print("=" * 60)
    
    # Log some architectural decisions
    decisions = [
        {
            "agent_id": "alice",
            "task_id": "db_1",
            "what": "Use PostgreSQL as primary database",
            "why": "Need ACID compliance, complex queries, and JSON support",
            "impact": "All services must use PostgreSQL client libraries"
        },
        {
            "agent_id": "bob",
            "task_id": "api_1",
            "what": "Implement JWT authentication",
            "why": "Stateless, scalable, and works well with microservices",
            "impact": "Frontend must store tokens securely, API gateway needs JWT validation"
        },
        {
            "agent_id": "alice",
            "task_id": "db_1",
            "what": "Use UUID for primary keys",
            "why": "Better for distributed systems and prevents ID enumeration",
            "impact": "Slightly larger storage, need UUID generation in all services"
        }
    ]
    
    print("\n1. Logging architectural decisions:")
    for decision in decisions:
        await context.log_decision(**decision)
        print(f"   ✓ Logged: {decision['what']}")
    
    # Retrieve decisions
    print("\n2. Retrieving decisions by task:")
    db_decisions = await context.get_decisions_for_task("db_1")
    print(f"   Database decisions ({len(db_decisions)} total):")
    for dec in db_decisions:
        print(f"     - {dec['what']}")
        print(f"       Why: {dec['why']}")
        print(f"       Impact: {dec['impact']}")
    
    # Show decision impact analysis
    print("\n3. Decision Impact Analysis:")
    all_decisions = []
    for task_id in ["db_1", "api_1"]:
        all_decisions.extend(await context.get_decisions_for_task(task_id))
    
    impacts = {}
    for dec in all_decisions:
        for word in dec['impact'].lower().split():
            if len(word) > 5:  # Significant words
                impacts[word] = impacts.get(word, 0) + 1
    
    print("   Most mentioned in impacts:")
    for word, count in sorted(impacts.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"     - {word}: {count} times")


async def demonstrate_implementation_sharing(context: Context):
    """Show how implementations are shared between tasks"""
    
    print("\n\n🔄 IMPLEMENTATION SHARING")
    print("=" * 60)
    
    # Add implementations
    implementations = [
        {
            "task_id": "db_1",
            "details": {
                "database": "PostgreSQL 13",
                "schema": {
                    "users": {
                        "id": "UUID PRIMARY KEY",
                        "email": "VARCHAR(255) UNIQUE",
                        "password_hash": "VARCHAR(255)",
                        "created_at": "TIMESTAMP"
                    },
                    "products": {
                        "id": "UUID PRIMARY KEY",
                        "name": "VARCHAR(255)",
                        "price": "DECIMAL(10,2)",
                        "inventory": "INTEGER"
                    }
                },
                "connection": "postgresql://localhost:5432/ecommerce",
                "migrations": ["001_initial.sql", "002_add_indexes.sql"]
            }
        },
        {
            "task_id": "api_1",
            "details": {
                "framework": "FastAPI",
                "auth_type": "JWT",
                "endpoints": {
                    "/auth/login": "POST - Login with email/password",
                    "/auth/refresh": "POST - Refresh access token",
                    "/auth/logout": "POST - Invalidate refresh token"
                },
                "token_config": {
                    "access_token_expire": "15 minutes",
                    "refresh_token_expire": "7 days",
                    "algorithm": "HS256"
                }
            }
        }
    ]
    
    print("\n1. Adding implementations:")
    for impl in implementations:
        await context.add_implementation(impl["task_id"], impl["details"])
        task_name = impl["task_id"].replace("_", " ").title()
        print(f"   ✓ Added implementation for {task_name}")
    
    # Get context for dependent task
    print("\n2. Getting context for dependent task (Product API):")
    ctx = await context.get_context("api_2", ["db_1", "api_1"])
    
    print("\n   Previous implementations available:")
    for task_id, impl in ctx.previous_implementations.items():
        print(f"\n   From {task_id}:")
        if "schema" in impl:
            print(f"     - Database schema with {len(impl['schema'])} tables")
        if "endpoints" in impl:
            print(f"     - API with {len(impl['endpoints'])} endpoints")
        if "auth_type" in impl:
            print(f"     - Authentication: {impl['auth_type']}")
    
    print("\n   Architectural decisions to consider:")
    for dec in ctx.architectural_decisions[:3]:
        print(f"     - {dec['what']}")
    
    # Show how context helps
    print("\n3. How context helps the next agent:")
    print("   The agent building Product API now knows:")
    print("     ✓ Database schema for products table")
    print("     ✓ Authentication is JWT-based")
    print("     ✓ Must use PostgreSQL client")
    print("     ✓ Should follow UUID pattern for IDs")


async def demonstrate_context_updates(context: Context, events: Events):
    """Show real-time context updates through events"""
    
    print("\n\n📡 REAL-TIME CONTEXT UPDATES")
    print("=" * 60)
    
    # Subscribe to context events
    context_updates = []
    
    async def track_updates(event):
        context_updates.append(event)
    
    events.subscribe(EventTypes.CONTEXT_UPDATED, track_updates)
    
    print("\n1. Making context changes:")
    
    # Add a new decision
    await context.log_decision(
        agent_id="charlie",
        task_id="ui_1",
        what="Use Material-UI component library",
        why="Consistent design, good accessibility, TypeScript support",
        impact="All UI components must follow Material Design principles"
    )
    print("   ✓ Logged new architectural decision")
    
    # Add implementation
    await context.add_implementation(
        "ui_1",
        {
            "component_library": "Material-UI v5",
            "theme": {
                "primary_color": "#1976d2",
                "secondary_color": "#dc004e"
            },
            "components_created": ["Button", "Card", "Form", "Table"]
        }
    )
    print("   ✓ Added UI implementation details")
    
    # Wait for events to process
    await asyncio.sleep(0.1)
    
    print(f"\n2. Context update events fired: {len(context_updates)}")
    for event in context_updates:
        print(f"   - {event.event_type}: {event.data.get('update_type', 'unknown')}")


async def demonstrate_dependency_workflow():
    """Show the complete dependency awareness workflow"""
    
    print("\n\n🔄 DEPENDENCY AWARENESS WORKFLOW")
    print("=" * 60)
    
    print("""
The dependency awareness workflow helps Marcus understand task relationships
and prevent illogical assignments:

1. DEPENDENCY INFERENCE
   ├─ Pattern matching (setup→build→test→deploy)
   ├─ Label analysis (shared components)
   ├─ Temporal logic (creation order)
   └─ AI enhancement (complex relationships)

2. CIRCULAR DEPENDENCY DETECTION
   ├─ DFS cycle detection
   ├─ Automatic resolution (remove weakest link)
   └─ Warning generation

3. OPTIMAL ORDERING
   ├─ Topological sort
   ├─ Priority consideration
   ├─ Resource optimization
   └─ Parallel task identification

4. CONTEXT PROPAGATION
   ├─ Implementation sharing
   ├─ Decision inheritance
   ├─ Cross-task learning
   └─ Conflict detection

5. REAL-TIME UPDATES
   ├─ Event-driven notifications
   ├─ Context synchronization
   ├─ Dependency recalculation
   └─ Impact analysis

BENEFITS:
✓ Prevents "deploy before build" scenarios
✓ Ensures architectural consistency
✓ Reduces agent confusion
✓ Accelerates development
✓ Improves quality
""")


async def main():
    """Run the context system demonstration"""
    
    print("\n🌟 MARCUS CONTEXT SYSTEM DEMONSTRATION")
    print("=" * 60)
    print("This demo shows how the enhanced context system manages")
    print("dependencies, decisions, and shared knowledge.")
    
    # Set up environment
    print("\n⚙️  Setting up environment...")
    persistence = Persistence(backend=MemoryPersistence())
    events = Events(store_history=True, persistence=persistence)
    context = Context(events=events, persistence=persistence)
    
    # Create example project
    tasks = await create_example_project()
    
    # Run demonstrations
    await demonstrate_dependency_inference(context, tasks)
    await demonstrate_decision_tracking(context)
    await demonstrate_implementation_sharing(context)
    await demonstrate_context_updates(context, events)
    await demonstrate_dependency_workflow()
    
    # Summary
    print("\n\n📈 CONTEXT SYSTEM BENEFITS")
    print("=" * 60)
    print("""
The enhanced context system provides:

1. Smart Dependency Management
   - Infers implicit dependencies
   - Prevents circular dependencies
   - Optimizes task execution order

2. Knowledge Sharing
   - Shares implementations between agents
   - Preserves architectural decisions
   - Maintains consistency

3. Real-time Awareness
   - Updates propagate immediately
   - Agents see latest context
   - Conflicts detected early

4. Better Agent Coordination
   - Reduced miscommunication
   - Faster development
   - Higher quality results
""")
    
    print("\n✅ Demonstration complete!")


if __name__ == "__main__":
    asyncio.run(main())