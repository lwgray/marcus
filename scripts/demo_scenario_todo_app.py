#!/usr/bin/env python3
"""
Marcus Enhanced Systems Demo: Building a Todo App

This demo shows a realistic project scenario where Marcus's enhanced systems
work together to manage a team building a Todo application. You'll see:

1. How the Context system shares knowledge between agents
2. How the Memory system learns and predicts outcomes  
3. How the Visibility system provides real-time insights
4. How all systems work together to prevent common project issues

Follow along as Alice, Bob, and Charlie build a Todo app and see Marcus
intelligently coordinate their work.
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from src.core.events import Events, EventTypes
from src.core.context import Context
from src.core.memory_enhanced import MemoryEnhanced
from src.core.persistence import Persistence, MemoryPersistence
from src.core.models import Task, TaskStatus, Priority
from src.visualization.event_integrated_visualizer import EventIntegratedVisualizer
import time

class TodoAppDemo:
    def __init__(self):
        self.persistence = Persistence(backend=MemoryPersistence())
        self.events = Events(store_history=True, persistence=self.persistence)
        self.context = Context(events=self.events, persistence=self.persistence)
        self.memory = MemoryEnhanced(events=self.events, persistence=self.persistence)
        # INTEGRATED VISIBILITY: Connect all systems to visibility
        self.visualizer = EventIntegratedVisualizer(
            events_system=self.events,
            context_system=self.context,
            memory_system=self.memory
        )
        
    async def initialize(self):
        """Set up the demo environment"""
        await self.visualizer.initialize()
        print("🚀 Marcus Enhanced Systems Demo: Todo App Project")
        print("=" * 60)
        print("Watch as Marcus intelligently coordinates Alice, Bob, and Charlie")
        print("building a Todo application. See how the enhanced systems prevent")
        print("common project issues through smart context sharing, predictions,")
        print("and real-time insights.")
        print()
        
    async def create_project_tasks(self):
        """Create the Todo app project tasks"""
        print("📋 PROJECT SETUP: Creating Todo App Tasks")
        print("-" * 50)
        
        tasks = [
            Task(
                id="task_1",
                name="Design Database Schema", 
                description="Design tables for users, todos, and categories",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=4.0,
                labels=["database", "design", "backend"],
                dependencies=[]
            ),
            Task(
                id="task_2", 
                name="Build User Authentication API",
                description="JWT-based login/signup endpoints",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=8.0,
                labels=["api", "auth", "backend"],
                dependencies=[]  # Marcus will infer dependency on database
            ),
            Task(
                id="task_3",
                name="Create Todo CRUD API", 
                description="REST endpoints for todo operations",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=6.0,
                labels=["api", "crud", "backend"],
                dependencies=[]  # Marcus will infer dependencies
            ),
            Task(
                id="task_4",
                name="Build React Frontend",
                description="Todo list UI with login/signup forms", 
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=12.0,
                labels=["frontend", "react", "ui"],
                dependencies=[]  # Marcus will infer API dependencies
            ),
            Task(
                id="task_5", 
                name="Write API Tests",
                description="Unit and integration tests for all endpoints",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=4.0,
                labels=["test", "api", "quality"],
                dependencies=[]  # Marcus will infer dependencies
            )
        ]
        
        print("✅ Created 5 tasks for Todo App development")
        for task in tasks:
            print(f"   • {task.name} ({task.estimated_hours}h)")
            
        return tasks
        
    async def demonstrate_smart_dependency_detection(self, tasks):
        """Show how Marcus automatically detects task dependencies"""
        print("\n🧠 SMART DEPENDENCY DETECTION")
        print("-" * 50)
        print("Marcus analyzes the tasks and automatically detects logical dependencies...")
        
        # Let Marcus analyze dependencies
        dependency_map = await self.context.analyze_dependencies(tasks, infer_implicit=True)
        
        print("\n📊 Dependencies Marcus Found:")
        task_lookup = {t.id: t.name for t in tasks}
        
        for dep_id, dependents in dependency_map.items():
            if dependents:
                print(f"\n   '{task_lookup[dep_id]}' must complete before:")
                for dependent_id in dependents:
                    print(f"     → {task_lookup[dependent_id]}")
                    
        # Show optimal task order
        ordered_tasks = await self.context.suggest_task_order(tasks)
        print(f"\n🎯 Optimal Task Execution Order:")
        for i, task in enumerate(ordered_tasks, 1):
            print(f"   {i}. {task.name}")
            
        print(f"\n💡 Marcus Insight: By following this order, the team avoids")
        print(f"   situations like 'trying to build the frontend before the API exists'")
        
        return ordered_tasks
        
    async def demonstrate_intelligent_task_assignment(self, ordered_tasks):
        """Show how Marcus makes intelligent task assignments based on predictions"""
        print(f"\n🎯 INTELLIGENT TASK ASSIGNMENT")
        print("-" * 50)
        
        # Simulate some agent history first
        await self._build_agent_history()
        
        agents = ["alice", "bob", "charlie"]
        agent_skills = {
            "alice": "Database expert - loves data modeling and architecture",
            "bob": "Backend specialist - strong with APIs and authentication", 
            "charlie": "Frontend developer - React and UI/UX focused"
        }
        
        print("👥 Available Team Members:")
        for agent, description in agent_skills.items():
            print(f"   • {agent}: {description}")
            
        print(f"\n🤔 Marcus is analyzing who should do what...")
        await asyncio.sleep(1)  # Dramatic pause
        
        # Assign first few tasks based on predictions
        task1 = ordered_tasks[0]  # Database schema
        task2 = ordered_tasks[1] if len(ordered_tasks) > 1 else None  # Auth API
        
        # Get predictions for task 1
        print(f"\n📊 For '{task1.name}':")
        for agent in agents:
            prediction = await self.memory.predict_task_outcome_v2(agent, task1)
            success_prob = prediction['success_probability'] * 100
            duration = prediction['estimated_duration']
            confidence = prediction['confidence'] * 100
            
            print(f"   {agent}: {success_prob:.0f}% success, {duration:.1f}h duration (confidence: {confidence:.0f}%)")
            
        print(f"\n✅ Marcus assigns '{task1.name}' to Alice")
        print(f"   Reason: Highest success probability for database work")
        
        # Emit assignment event
        await self.events.publish(
            EventTypes.TASK_ASSIGNED,
            "marcus",
            {
                "task_id": task1.id,
                "task_name": task1.name,
                "agent_id": "alice",
                "prediction_success_rate": 85,
                "estimated_duration": 3.8
            }
        )
        
        return {"alice": [task1]}
    
    async def demonstrate_context_sharing(self):
        """Show how context gets shared between agents"""
        print(f"\n🔄 CONTEXT SHARING IN ACTION")
        print("-" * 50)
        
        # Alice starts and makes decisions
        print(f"👩‍💻 Alice starts working on the database schema...")
        await asyncio.sleep(1)
        
        # Alice makes architectural decisions
        print(f"\n💭 Alice makes some key architectural decisions:")
        
        decisions = [
            {
                "what": "Use PostgreSQL as the database",
                "why": "Need ACID compliance and complex queries for todo relationships",
                "impact": "All services must use PostgreSQL client libraries"
            },
            {
                "what": "Use UUID for primary keys", 
                "why": "Better for distributed systems and security",
                "impact": "All tables use UUID instead of auto-increment IDs"
            }
        ]
        
        for i, decision in enumerate(decisions, 1):
            await self.context.log_decision(
                agent_id="alice",
                task_id="task_1", 
                **decision
            )
            print(f"   {i}. {decision['what']}")
            print(f"      Why: {decision['why']}")
            
        # Alice completes her task
        print(f"\n✅ Alice completes the database schema!")
        
        # Share implementation details
        schema_implementation = {
            "database": "PostgreSQL 13",
            "schema": {
                "users": {
                    "id": "UUID PRIMARY KEY",
                    "email": "VARCHAR(255) UNIQUE", 
                    "password_hash": "VARCHAR(255)",
                    "created_at": "TIMESTAMP"
                },
                "todos": {
                    "id": "UUID PRIMARY KEY",
                    "user_id": "UUID REFERENCES users(id)",
                    "title": "VARCHAR(255)",
                    "completed": "BOOLEAN DEFAULT FALSE",
                    "created_at": "TIMESTAMP"
                }
            },
            "connection_string": "postgresql://localhost:5432/todoapp"
        }
        
        await self.context.add_implementation("task_1", schema_implementation)
        print(f"📚 Alice's work is now available as context for other team members")
        
        # Bob starts next task 
        print(f"\n👨‍💻 Bob is assigned the Authentication API task...")
        print(f"🔍 Marcus provides Bob with relevant context from Alice's work:")
        
        # Get context for Bob
        context = await self.context.get_context("task_2", ["task_1"])
        
        print(f"\n📋 Context Bob receives:")
        print(f"   • Database schema with users table structure")
        print(f"   • Connection string for PostgreSQL")
        print(f"   • Architectural decisions about UUIDs and database choice")
        print(f"   • Why these decisions were made")
        
        print(f"\n💡 Marcus Insight: Bob doesn't need to guess about the database")
        print(f"   structure or spend time figuring out connection details!")
        
        return context
        
    async def demonstrate_predictive_problem_prevention(self):
        """Show how Marcus predicts and prevents problems"""
        print(f"\n🔮 PREDICTIVE PROBLEM PREVENTION") 
        print("-" * 50)
        
        # Bob is about to start auth work
        task_auth = Task(
            id="task_2",
            name="Build User Authentication API",
            description="JWT-based login/signup endpoints", 
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to="bob",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=8.0,
            labels=["api", "auth", "backend"],
            dependencies=["task_1"]
        )
        
        # Get enhanced prediction
        print(f"🔍 Marcus analyzes Bob's assignment for potential risks...")
        prediction = await self.memory.predict_task_outcome_v2("bob", task_auth)
        
        print(f"\n📊 Risk Analysis for Bob + Authentication API:")
        print(f"   Success Probability: {prediction['success_probability']*100:.0f}%")
        print(f"   Estimated Duration: {prediction['estimated_duration']:.1f} hours")
        print(f"   Confidence Level: {prediction['confidence']*100:.0f}%")
        
        # Show risk factors
        risk_factors = prediction['risk_analysis']['factors']
        if risk_factors:
            print(f"\n⚠️  Potential Risk Factors:")
            for risk in risk_factors[:3]:
                print(f"   • {risk['description']} ({risk['severity']} severity)")
                
        # Show mitigation suggestions
        suggestions = prediction['risk_analysis']['mitigation_suggestions']
        if suggestions:
            print(f"\n💡 Marcus suggests mitigation strategies:")
            for suggestion in suggestions[:3]:
                print(f"   • {suggestion}")
                
        print(f"\n🎯 Marcus Insight: By identifying risks early, the team can")
        print(f"   take preventive action instead of dealing with problems later!")
        
    async def demonstrate_real_time_visibility(self):
        """Show real-time visibility into project progress"""
        print(f"\n👀 REAL-TIME PROJECT VISIBILITY")
        print("-" * 50)
        
        # Simulate some project activity
        events_to_simulate = [
            ("Bob starts authentication work", EventTypes.TASK_STARTED, "bob", {"task_id": "task_2"}),
            ("Bob hits a blocker", EventTypes.TASK_BLOCKED, "bob", {
                "task_id": "task_2", 
                "blocker": "JWT library documentation unclear",
                "severity": "medium"
            }),
            ("Alice helps resolve blocker", EventTypes.BLOCKER_RESOLVED, "alice", {
                "task_id": "task_2",
                "resolution": "Shared JWT implementation example from previous project"
            }),
            ("Bob makes progress", EventTypes.TASK_PROGRESS, "bob", {
                "task_id": "task_2",
                "progress": 75,
                "message": "Authentication endpoints working"
            }),
        ]
        
        print(f"📡 Live Project Activity:")
        for description, event_type, agent, data in events_to_simulate:
            await self.events.publish(event_type, agent, data)
            print(f"   • {description}")
            await asyncio.sleep(0.5)  # Realistic timing
            
        # Show visibility insights
        print(f"\n📊 Marcus Dashboard Insights:")
        stats = self.visualizer.get_event_statistics()
        
        print(f"   • Total events tracked: {stats['total_events']}")
        print(f"   • Active tasks: {stats['event_counts'].get('task_started', 0)}")
        print(f"   • Blockers resolved: {stats['event_counts'].get('blocker_resolved', 0)}")
        print(f"   • Context updates: {stats['event_counts'].get('context_updated', 0)}")
        
        print(f"\n💡 Marcus Insight: Project managers can see exactly what's")
        print(f"   happening without interrupting developers with status meetings!")
        
    async def demonstrate_learning_and_adaptation(self):
        """Show how Marcus learns from the project"""
        print(f"\n🧠 LEARNING AND CONTINUOUS IMPROVEMENT")
        print("-" * 50)
        
        print(f"🎓 As the project progresses, Marcus learns:")
        print(f"   • Alice is very accurate with database estimates")
        print(f"   • Bob needs extra time for authentication tasks") 
        print(f"   • The team works well when Alice provides context early")
        print(f"   • JWT integration often causes blockers for this team")
        
        print(f"\n📈 For the next project, Marcus will:")
        print(f"   • Assign database tasks to Alice with high confidence")
        print(f"   • Add buffer time for Bob's authentication work")
        print(f"   • Proactively share authentication examples")
        print(f"   • Suggest JWT training or pair programming")
        
        print(f"\n💡 Marcus Insight: Every project makes the system smarter")
        print(f"   and more helpful for future work!")
        
    async def _build_agent_history(self):
        """Build some sample agent history for realistic predictions"""
        # Quick simulation of past work for each agent
        agents_work = {
            "alice": [
                ("Database Migration", True, 3.5, ["database", "migration"]),
                ("Schema Design", True, 4.2, ["database", "design"]),
                ("Data Modeling", False, 6.0, ["database", "complex"]),  # Failed - too complex
            ],
            "bob": [
                ("REST API", True, 5.5, ["api", "backend"]),
                ("Authentication", False, 9.0, ["auth", "jwt"]),  # Failed - auth is tricky for Bob
                ("CRUD Endpoints", True, 4.0, ["api", "crud"]),
            ],
            "charlie": [
                ("React Component", True, 6.0, ["frontend", "react"]),
                ("UI Design", True, 8.0, ["ui", "design"]),
                ("Complex Dashboard", False, 15.0, ["frontend", "complex"]),  # Failed - too complex
            ]
        }
        
        for agent_id, work_history in agents_work.items():
            for task_name, success, actual_hours, labels in work_history:
                task = Task(
                    id=f"history_{agent_id}_{len(work_history)}",
                    name=task_name,
                    description=f"Historical work: {task_name}",
                    status=TaskStatus.COMPLETED,
                    priority=Priority.MEDIUM,
                    assigned_to=agent_id,
                    created_at=datetime.now() - timedelta(days=30),
                    updated_at=datetime.now() - timedelta(days=29),
                    due_date=None,
                    estimated_hours=actual_hours * 0.9,  # Slight underestimate
                    labels=labels,
                    dependencies=[]
                )
                
                await self.memory.record_task_start(agent_id, task)
                await self.memory.record_task_completion(
                    agent_id=agent_id,
                    task_id=task.id,
                    success=success,
                    actual_hours=actual_hours,
                    blockers=[] if success else ["complexity"]
                )

async def main():
    """Run the Todo App demo"""
    demo = TodoAppDemo()
    await demo.initialize()
    
    # Run the demo story
    tasks = await demo.create_project_tasks()
    ordered_tasks = await demo.demonstrate_smart_dependency_detection(tasks)
    assignments = await demo.demonstrate_intelligent_task_assignment(ordered_tasks)
    context = await demo.demonstrate_context_sharing()
    await demo.demonstrate_predictive_problem_prevention()
    await demo.demonstrate_real_time_visibility()
    await demo.demonstrate_learning_and_adaptation()
    
    # Conclusion
    print(f"\n🎉 DEMO COMPLETE: Todo App Success Story")
    print("=" * 60)
    print(f"""
What you just saw:

✅ SMART COORDINATION: Marcus automatically figured out that the database 
   must be built before the API, and the API before the frontend.

✅ INTELLIGENT ASSIGNMENT: Marcus predicted Alice would be 85% successful 
   with database work, so assigned it to her instead of someone less likely to succeed.

✅ SEAMLESS CONTEXT SHARING: When Bob started the API, he immediately had
   Alice's database schema, connection details, and architectural decisions.

✅ PREDICTIVE PROBLEM PREVENTION: Marcus identified that Bob might struggle
   with authentication and suggested mitigation strategies.

✅ REAL-TIME VISIBILITY: Project managers could see blockers and progress
   without interrupting developers.

✅ CONTINUOUS LEARNING: The system got smarter with each task completion.

The Result: A Todo app project that runs smoothly with fewer delays, 
better coordination, and happier developers.

This is Marcus Enhanced Systems in action! 🚀
""")

if __name__ == "__main__":
    asyncio.run(main())