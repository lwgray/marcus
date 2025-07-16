#!/usr/bin/env python3
"""
Real MCP Tool Interaction Examples

This shows the ACTUAL MCP tools Claude uses when talking to Marcus
"""

from typing import Any, Dict, List

print("🔧 MARCUS MCP TOOLS - WHAT CLAUDE ACTUALLY CALLS")
print("=" * 70)
print()

# Show the real interaction flow
print("📱 REAL EXAMPLE: Building a Todo App")
print("-" * 70)
print()

interactions: List[Dict[str, Any]] = [
    {
        "step": 1,
        "user_says": "I want to build a todo app with user accounts",
        "claude_thinks": "User wants to start a new project",
        "mcp_calls": [
            {
                "tool": "register_agent",
                "params": {
                    "agent_id": "claude-assistant-001",
                    "name": "Claude",
                    "role": "AI Assistant",
                    "skills": ["planning", "architecture", "full-stack"],
                },
            }
        ],
        "marcus_returns": {
            "success": True,
            "agent_id": "claude-assistant-001",
            "message": "Agent registered successfully",
        },
    },
    {
        "step": 2,
        "user_says": None,
        "claude_thinks": "Need to get a task to work on",
        "mcp_calls": [
            {
                "tool": "request_next_task",
                "params": {"agent_id": "claude-assistant-001"},
            }
        ],
        "marcus_returns": {
            "task": {
                "id": "task-001",
                "name": "Design database schema for todos and users",
                "description": "Create ERD with users, todos, and relationships",
                "priority": "HIGH",
                "estimated_hours": 4,
                "dependencies": [],
            },
            "reason": "Foundation task - no dependencies",
        },
    },
    {
        "step": 3,
        "user_says": "I've finished the database design",
        "claude_thinks": "Report task completion and get next task",
        "mcp_calls": [
            {
                "tool": "report_task_progress",
                "params": {
                    "agent_id": "claude-assistant-001",
                    "task_id": "task-001",
                    "status": "completed",
                    "progress": 100,
                    "message": "Database schema complete with users and todos tables",
                },
            },
            {
                "tool": "request_next_task",
                "params": {"agent_id": "claude-assistant-001"},
            },
        ],
        "marcus_returns": {
            "task": {
                "id": "task-002",
                "name": "Implement user authentication API",
                "description": "Create login, register, and JWT token endpoints",
                "priority": "HIGH",
                "estimated_hours": 8,
                "dependencies": ["task-001"],
            },
            "reason": "Auth is required before todo features",
        },
    },
    {
        "step": 4,
        "user_says": "Deploy this to production",
        "claude_thinks": "User wants to deploy, let me check if it's ready",
        "mcp_calls": [{"tool": "get_project_status", "params": {}}],
        "marcus_returns": {
            "total_tasks": 24,
            "completed_tasks": 2,
            "in_progress_tasks": 1,
            "blocked_tasks": 0,
            "completion_percentage": 8.3,
            "critical_incomplete": [
                "Backend API implementation",
                "Frontend UI",
                "Testing",
                "Security review",
            ],
            "can_deploy": False,
            "deployment_blockers": [
                "No implementation exists",
                "No tests written",
                "No security review",
            ],
        },
    },
    {
        "step": 5,
        "user_says": "I'm stuck on JWT implementation",
        "claude_thinks": "User has a blocker, report it",
        "mcp_calls": [
            {
                "tool": "report_blocker",
                "params": {
                    "agent_id": "claude-assistant-001",
                    "task_id": "task-002",
                    "blocker_type": "technical",
                    "description": "JWT token generation failing with invalid signature error",
                    "severity": "high",
                },
            }
        ],
        "marcus_returns": {
            "blocker_id": "blocker-001",
            "ai_suggestions": [
                "Check JWT secret is properly configured in environment",
                "Verify token expiration time is valid",
                "Ensure using correct algorithm (HS256 vs RS256)",
                "Example code: jwt.sign(payload, process.env.JWT_SECRET, {expiresIn: '1h'})",
            ],
            "similar_issues": [
                {
                    "task": "Previous auth implementation",
                    "resolution": "Missing JWT_SECRET in .env file",
                }
            ],
        },
    },
    {
        "step": 6,
        "user_says": "What's the overall status?",
        "claude_thinks": "Get comprehensive project status",
        "mcp_calls": [
            {"tool": "get_project_status", "params": {}},
            {"tool": "list_registered_agents", "params": {}},
        ],
        "marcus_returns": {
            "project": {
                "completion": "12.5%",
                "velocity": "2.5 tasks/day",
                "estimated_completion": "9 days",
                "health": "HEALTHY",
            },
            "agents": [
                {
                    "agent_id": "claude-assistant-001",
                    "current_task": "Implement user authentication API",
                    "tasks_completed": 2,
                    "active_blockers": 1,
                }
            ],
        },
    },
]

# Print each interaction
for interaction in interactions:
    print(f"\n{'='*70}")
    print(f"STEP {interaction['step']}:")

    if interaction["user_says"]:
        print(f"\n👤 User: \"{interaction['user_says']}\"")

    print(f"\n🤔 Claude thinks: {interaction['claude_thinks']}")

    print(f"\n📞 Claude calls Marcus MCP:")
    for call in interaction["mcp_calls"]:
        print(f"\n   Tool: {call['tool']}")
        print(f"   Parameters:")
        for key, value in call["params"].items():
            print(f"      {key}: {value}")

    print(f"\n📨 Marcus returns:")
    import json

    response_str = json.dumps(interaction["marcus_returns"], indent=6)
    for line in response_str.split("\n"):
        print(f"   {line}")

print("\n\n" + "=" * 70)
print("🎯 KEY INSIGHTS:")
print("=" * 70)
print()
print("1. Claude ONLY uses Marcus MCP tools, never Planka directly")
print("2. Marcus handles all the complex logic internally")
print("3. Natural language → Claude interprets → MCP calls → Results")
print("4. Safety checks happen inside Marcus before any action")
print("5. Users never see or know about MCP tools")
print()
print("The user experience is just natural conversation!")
print("=" * 70)
