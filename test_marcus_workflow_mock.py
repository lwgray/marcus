#!/usr/bin/env python3
"""
Mock demonstration of Marcus workflow with two agents.

This shows:
1. Agent A getting a task with dependencies
2. Agent A making architectural decisions
3. Agent B getting a dependent task with context from Agent A
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List


# Mock Marcus state and tools
class MockMarcusState:
    def __init__(self):
        self.agents = {}
        self.tasks = {
            "task-001": {
                "id": "task-001",
                "name": "Design User Authentication System",
                "description": "Design secure authentication with JWT tokens",
                "dependencies": [],
                "status": "TODO",
                "type": "design",
            },
            "task-002": {
                "id": "task-002",
                "name": "Implement User Authentication API",
                "description": "Build the authentication endpoints based on design",
                "dependencies": ["task-001"],
                "status": "TODO",
                "type": "implementation",
            },
            "task-003": {
                "id": "task-003",
                "name": "Create User Profile API",
                "description": "Build user profile management endpoints",
                "dependencies": ["task-002"],
                "status": "TODO",
                "type": "implementation",
            },
        }
        self.decisions = {}
        self.implementations = {}
        self.task_assignments = {}
        self.task_progress = {}


# Mock tool implementations
async def register_agent(
    agent_id: str, name: str, role: str, skills: List[str]
) -> Dict[str, Any]:
    """Mock agent registration"""
    print(f"\n🤖 REGISTERING AGENT: {name}")
    print(f"   Role: {role}")
    print(f"   Skills: {', '.join(skills)}")
    return {"success": True, "agent_id": agent_id}


async def request_next_task(agent_id: str, state: MockMarcusState) -> Dict[str, Any]:
    """Mock task assignment with dependency context"""
    # Find next available task
    for task_id, task in state.tasks.items():
        if task["status"] == "TODO":
            # Check if dependencies are complete
            deps_complete = all(
                state.tasks.get(dep_id, {}).get("status") == "DONE"
                for dep_id in task.get("dependencies", [])
            )

            if deps_complete:
                # Assign task
                state.task_assignments[task_id] = agent_id
                state.tasks[task_id]["status"] = "IN_PROGRESS"

                # Build response with context
                response = {
                    "success": True,
                    "task": {
                        "id": task_id,
                        "name": task["name"],
                        "description": task["description"],
                        "dependencies": task.get("dependencies", []),
                    },
                }

                # Add implementation context from dependencies
                if task.get("dependencies"):
                    print(f"\n📋 TASK ASSIGNMENT TO {agent_id}")
                    print(f"   Task: {task['name']}")
                    print(f"   Dependencies: {task['dependencies']}")

                    implementation_context = []
                    for dep_id in task["dependencies"]:
                        if dep_id in state.implementations:
                            implementation_context.append(state.implementations[dep_id])

                    if implementation_context:
                        response["task"][
                            "implementation_context"
                        ] = implementation_context
                        print(f"\n   📚 Previous Implementation Context:")
                        for ctx in implementation_context:
                            print(f"      - {ctx['summary']}")

                # Add dependency awareness
                dependent_tasks = [
                    t
                    for t_id, t in state.tasks.items()
                    if task_id in t.get("dependencies", [])
                ]
                if dependent_tasks:
                    response["task"][
                        "dependency_awareness"
                    ] = f"{len(dependent_tasks)} future tasks depend on your work"
                    print(
                        f"\n   ⚠️  {len(dependent_tasks)} future tasks depend on this work"
                    )

                return response

    return {"success": False, "message": "No tasks available"}


async def get_task_context(task_id: str, state: MockMarcusState) -> Dict[str, Any]:
    """Mock getting full context for a task"""
    context = {
        "task": state.tasks.get(task_id, {}),
        "decisions": [],
        "implementations": [],
    }

    # Get decisions from dependencies
    for dep_id in state.tasks.get(task_id, {}).get("dependencies", []):
        if dep_id in state.decisions:
            context["decisions"].extend(state.decisions[dep_id])
        if dep_id in state.implementations:
            context["implementations"].append(state.implementations[dep_id])

    print(f"\n🔍 CONTEXT LOOKUP for {task_id}")
    print(f"   Found {len(context['decisions'])} decisions")
    print(f"   Found {len(context['implementations'])} implementations")

    return {"success": True, "context": context}


async def log_decision(
    agent_id: str, task_id: str, decision: str, state: MockMarcusState
) -> Dict[str, Any]:
    """Mock logging an architectural decision"""
    if task_id not in state.decisions:
        state.decisions[task_id] = []

    decision_record = {
        "agent_id": agent_id,
        "task_id": task_id,
        "decision": decision,
        "timestamp": datetime.now().isoformat(),
    }

    state.decisions[task_id].append(decision_record)

    print(f"\n🏗️  ARCHITECTURAL DECISION by {agent_id}")
    print(f"   Decision: {decision}")

    # Find dependent tasks
    dependent_tasks = [
        t_id for t_id, t in state.tasks.items() if task_id in t.get("dependencies", [])
    ]
    if dependent_tasks:
        print(f"   ⚡ This decision affects {len(dependent_tasks)} dependent tasks")

    return {"success": True, "decision_id": f"decision-{len(state.decisions)}"}


async def report_task_progress(
    agent_id: str,
    task_id: str,
    status: str,
    progress: int,
    message: str,
    state: MockMarcusState,
) -> Dict[str, Any]:
    """Mock progress reporting"""
    state.task_progress[task_id] = {
        "progress": progress,
        "status": status,
        "message": message,
    }

    print(f"\n📊 PROGRESS UPDATE from {agent_id}")
    print(f"   Task: {state.tasks[task_id]['name']}")
    print(f"   Progress: {progress}%")
    print(f"   Message: {message}")

    if status == "completed":
        state.tasks[task_id]["status"] = "DONE"

        # Store implementation details
        if "implement" in state.tasks[task_id]["name"].lower():
            state.implementations[task_id] = {
                "task_id": task_id,
                "summary": message,
                "api_endpoints": [],
                "data_models": [],
            }

            # Extract API endpoints from message
            if "POST /api" in message or "GET /api" in message:
                import re

                endpoints = re.findall(r"(GET|POST|PUT|DELETE) (/api/\S+)", message)
                state.implementations[task_id]["api_endpoints"] = [
                    {"method": m, "path": p} for m, p in endpoints
                ]

    return {"success": True}


# Agent workflows
async def agent_a_workflow(state: MockMarcusState):
    """Agent A: Works on authentication design and implementation"""
    print("\n" + "=" * 60)
    print("AGENT A STARTING")
    print("=" * 60)

    # Register
    await register_agent(
        "agent-a", "Alice", "Backend Developer", ["Python", "API", "Security"]
    )

    # Request first task
    task_response = await request_next_task("agent-a", state)
    if task_response["success"]:
        task = task_response["task"]

        # Work on task
        await report_task_progress(
            "agent-a",
            task["id"],
            "in_progress",
            25,
            "Researching authentication best practices and JWT standards",
            state,
        )

        # Make architectural decision
        await log_decision(
            "agent-a",
            task["id"],
            "I chose JWT tokens over sessions because they're stateless and work better with our microservices architecture. This affects all API endpoints which will need to validate JWT tokens.",
            state,
        )

        await report_task_progress(
            "agent-a",
            task["id"],
            "in_progress",
            50,
            "Designing token structure and refresh token flow",
            state,
        )

        # Make another decision
        await log_decision(
            "agent-a",
            task["id"],
            "I decided to use RS256 (RSA) instead of HS256 for JWT signing because it allows microservices to verify tokens without sharing secrets. This affects how services will validate tokens.",
            state,
        )

        # Complete task
        await report_task_progress(
            "agent-a",
            task["id"],
            "completed",
            100,
            "Completed authentication design: JWT with RS256, refresh tokens, 15min access token expiry",
            state,
        )

    # Request second task (implementation)
    print("\n" + "-" * 40)
    print("Agent A requesting next task...")
    print("-" * 40)

    task_response = await request_next_task("agent-a", state)
    if task_response["success"]:
        task = task_response["task"]

        # Check context from previous task
        context = await get_task_context(task["id"], state)

        await report_task_progress(
            "agent-a",
            task["id"],
            "in_progress",
            25,
            "Setting up authentication module structure",
            state,
        )

        await report_task_progress(
            "agent-a",
            task["id"],
            "in_progress",
            50,
            "Implementing JWT token generation and validation",
            state,
        )

        # Log implementation decision
        await log_decision(
            "agent-a",
            task["id"],
            "I'm storing public keys in Redis for fast access across services because of the RS256 decision. This affects how other services will initialize their auth validation.",
            state,
        )

        # Complete with implementation details
        await report_task_progress(
            "agent-a",
            task["id"],
            "completed",
            100,
            "Implemented authentication API: POST /api/auth/login returns {token, refreshToken, expiresIn}, POST /api/auth/refresh, GET /api/auth/verify. Using Redis for key storage.",
            state,
        )


async def agent_b_workflow(state: MockMarcusState):
    """Agent B: Works on user profile API that depends on Agent A's work"""
    print("\n" + "=" * 60)
    print("AGENT B STARTING")
    print("=" * 60)

    # Register
    await register_agent(
        "agent-b", "Bob", "Backend Developer", ["Python", "API", "Database"]
    )

    # Request task
    task_response = await request_next_task("agent-b", state)
    if task_response["success"]:
        task = task_response["task"]

        # Agent B sees the implementation context!
        if "implementation_context" in task:
            print("\n💡 Agent B sees previous implementations and can use them!")

        # Get full context to see decisions
        context = await get_task_context(task["id"], state)
        if context["success"]:
            decisions = context["context"]["decisions"]
            if decisions:
                print(
                    f"\n📋 Agent B reviewing {len(decisions)} architectural decisions:"
                )
                for dec in decisions:
                    print(f"   - {dec['decision'][:100]}...")

        await report_task_progress(
            "agent-b",
            task["id"],
            "in_progress",
            25,
            "Setting up user profile module, integrating with auth system",
            state,
        )

        # Make decision based on previous context
        await log_decision(
            "agent-b",
            task["id"],
            "I'm using the JWT validation from auth module for all profile endpoints because of the RS256 setup. This affects any future user-related endpoints.",
            state,
        )

        await report_task_progress(
            "agent-b",
            task["id"],
            "in_progress",
            75,
            "Implementing profile CRUD operations with JWT auth",
            state,
        )

        # Complete
        await report_task_progress(
            "agent-b",
            task["id"],
            "completed",
            100,
            "Implemented user profile API: GET /api/users/profile (requires JWT), PUT /api/users/profile, GET /api/users/{id}/public. All endpoints validate JWT using shared Redis keys.",
            state,
        )


async def main():
    """Run the mock workflow"""
    state = MockMarcusState()

    print("🚀 MARCUS WORKFLOW DEMONSTRATION")
    print("=" * 60)
    print("Showing how agents work with dependencies and share context")

    # Run Agent A's workflow
    await agent_a_workflow(state)

    # Simulate time passing
    await asyncio.sleep(1)

    # Run Agent B's workflow
    await agent_b_workflow(state)

    # Show final state
    print("\n" + "=" * 60)
    print("FINAL PROJECT STATE")
    print("=" * 60)

    print("\n📋 All Decisions Made:")
    for task_id, decisions in state.decisions.items():
        print(f"\n   Task {task_id}:")
        for dec in decisions:
            print(f"   - {dec['agent_id']}: {dec['decision'][:80]}...")

    print("\n🔗 Implementation Chain:")
    for task_id, impl in state.implementations.items():
        print(f"\n   {task_id}: {impl['summary']}")
        if impl.get("api_endpoints"):
            for ep in impl["api_endpoints"]:
                print(f"      - {ep['method']} {ep['path']}")


if __name__ == "__main__":
    asyncio.run(main())
