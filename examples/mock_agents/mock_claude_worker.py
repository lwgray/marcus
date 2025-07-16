#!/usr/bin/env python3
"""
Mock Claude Worker

Simulates a Claude agent that:
1. Registers with PM Agent
2. Requests tasks
3. Reports progress
4. Completes tasks
"""

import argparse
import asyncio
import os
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from src.integrations.kanban_factory import KanbanFactory
from src.logging.conversation_logger import conversation_logger


class MockClaudeWorker:
    """Simulates a Claude worker agent"""

    def __init__(
        self, name: str, skills: List[str], role: str = "Full Stack Developer"
    ):
        self.agent_id = f"claude_{name}"
        self.name = name
        self.role = role
        self.skills = skills
        self.current_task: Optional[Dict[str, Any]] = None
        self.pm_client = None  # Would be MCP client in real scenario
        self.system_prompt = self._load_system_prompt(role)

    async def register(self) -> None:
        """Register with PM Agent"""
        print(f"[{self.name}] Registering with PM Agent...")

        # In real scenario, this would use MCP client
        # For demo, we'll simulate the registration
        response = {
            "success": True,
            "message": f"Agent {self.name} registered successfully",
            "agent_id": self.agent_id,
        }

        if response["success"]:
            print(f"[{self.name}] ✓ Registered successfully")
        else:
            print(f"[{self.name}] ✗ Registration failed")

        # Log the registration
        conversation_logger.log_worker_message(
            self.agent_id,
            "to_pm",
            f"Registering as {self.role} with skills: {self.skills}",
            {"name": self.name, "role": self.role, "skills": self.skills},
        )

    def _load_system_prompt(self, role: str) -> str:
        """Load the appropriate system prompt based on role"""
        prompts_file = Path(__file__).parent / "prompts" / "system_prompts.md"
        if not prompts_file.exists():
            return "Default worker prompt"

        content = prompts_file.read_text()

        # Extract the appropriate prompt section based on role
        if "backend" in role.lower():
            start = content.find("BACKEND_AGENT_PROMPT = ")
            if start != -1:
                start = content.find('"""', start) + 3
                end = content.find('"""', start)
                if end != -1:
                    return content[start:end].strip()
        elif "frontend" in role.lower():
            start = content.find("FRONTEND_AGENT_PROMPT = ")
            if start != -1:
                start = content.find('"""', start) + 3
                end = content.find('"""', start)
                if end != -1:
                    return content[start:end].strip()
        elif "test" in role.lower() or "qa" in role.lower():
            start = content.find("TESTING_AGENT_PROMPT = ")
            if start != -1:
                start = content.find('"""', start) + 3
                end = content.find('"""', start)
                if end != -1:
                    return content[start:end].strip()

        # Return base prompt if no specific role found
        start = content.find("WORKER_SYSTEM_PROMPT: |")
        if start != -1:
            start = content.find("\n", start) + 1
            end = content.find("```", start)
            if end != -1:
                return content[start:end].strip()

        return "Default worker prompt"

    async def request_task(self) -> Optional[Dict[str, Any]]:
        """Request next task from PM Agent"""
        print(f"[{self.name}] Requesting next task...")

        # Simulate MCP call to request_next_task
        # In real scenario, this would call the actual MCP tool

        # For demo, simulate task assignment
        if random.random() > 0.3:  # 70% chance of getting a task
            task = {
                "has_task": True,
                "task": {
                    "id": f"task_{random.randint(100, 999)}",
                    "title": random.choice(
                        [
                            "Implement user authentication",
                            "Create API endpoints",
                            "Add database migrations",
                            "Fix bug in payment system",
                            "Optimize query performance",
                        ]
                    ),
                    "description": "Task description here",
                    "instructions": "Detailed instructions for completing this task",
                    "estimated_hours": random.randint(2, 8),
                    "priority": random.choice(["high", "medium", "low"]),
                },
            }

            task_data = task["task"]
            if isinstance(task_data, dict):
                self.current_task = task_data
                print(f"[{self.name}] ✓ Assigned task: {task_data['title']}")

                # Log task assignment
                conversation_logger.log_worker_message(
                    self.agent_id,
                    "from_pm",
                    f"Task assigned: {task_data['title']}",
                    task_data,
                )

            return task
        else:
            print(f"[{self.name}] No tasks available")
            return {"has_task": False}

    async def work_on_task(self) -> None:
        """Simulate working on the assigned task"""
        if not self.current_task:
            return

        task_id = self.current_task["id"]
        task_title = self.current_task["title"]
        estimated_hours = self.current_task.get("estimated_hours", 4)
        instructions = self.current_task.get("instructions", "")

        print(f"[{self.name}] Starting work on: {task_title}")

        # Check for implementation context in instructions
        if "Previous Implementation Context" in instructions:
            print(
                f"[{self.name}] Found implementation context, will integrate with existing work"
            )

        # Simulate progress updates
        progress_points = [25, 50, 75, 100]

        for progress in progress_points:
            # Simulate work time (accelerated for demo)
            work_time = random.uniform(3, 8)  # seconds
            print(f"[{self.name}] Working... ({progress-25}% -> {progress}%)")
            await asyncio.sleep(work_time)

            # Report progress
            status = "completed" if progress == 100 else "in_progress"
            message = self._generate_progress_message(progress)

            print(f"[{self.name}] Reporting progress: {progress}% - {message}")

            # Log progress update
            conversation_logger.log_worker_message(
                self.agent_id,
                "to_pm",
                f"Progress update: {progress}% - {message}",
                {"task_id": task_id, "status": status, "progress": progress},
            )

            # Simulate MCP call to report_task_progress
            response = {"success": True, "message": "Progress updated successfully"}

            # Small chance of encountering a blocker
            if progress < 100 and random.random() < 0.1:
                await self._report_blocker(task_id)
                await asyncio.sleep(5)  # Wait before continuing

        # Removed line with unreachable issue
        print(f"[{self.name}] ✓ Task completed: {task_title}")
        self.current_task = None

    async def _report_blocker(self, task_id: str) -> None:
        """Report a blocker"""
        blockers = [
            "Database connection timeout",
            "Missing API credentials",
            "Dependency version conflict",
            "Test suite failing",
            "Unclear requirements",
        ]

        blocker = random.choice(blockers)
        severity = random.choice(["low", "medium", "high"])

        print(f"[{self.name}] 🚫 Encountered blocker: {blocker} ({severity})")

        # Log blocker
        conversation_logger.log_worker_message(
            self.agent_id,
            "to_pm",
            f"BLOCKER: {blocker} (Severity: {severity})",
            {"task_id": task_id, "severity": severity},
        )

        # Simulate MCP call to report_blocker
        response = {
            "success": True,
            "suggestions": [
                "Check environment variables",
                "Restart the service",
                "Contact DevOps team",
            ],
            "escalated": severity == "high",
        }

        suggestions = response.get("suggestions", [])
        if suggestions and isinstance(suggestions, list):
            suggestion_strs = [str(s) for s in suggestions]
            print(
                f"[{self.name}] Received suggestions: {', '.join(suggestion_strs)}"
            )

    def _generate_progress_message(self, progress: int) -> str:
        """Generate realistic progress messages based on role"""
        # Role-specific messages following the system prompt patterns
        if "backend" in self.role.lower():
            messages = {
                25: [
                    "Created FastAPI app structure and user model, committed feat(task-001): initialize API structure",
                    "Set up database models with SQLAlchemy, following existing patterns from context",
                    "Configured authentication middleware using Bearer tokens as shown in context",
                ],
                50: [
                    "Implemented POST /api/users and GET /api/users endpoints returning {id, email, created_at}",
                    "Created REST endpoints following existing URL patterns /api/v1/resources",
                    "API endpoints working with proper error handling {error: message, code: ERROR_CODE}",
                ],
                75: [
                    "Added comprehensive error handling and input validation to all endpoints",
                    "Integrated with existing authentication system from previous implementation",
                    "Unit tests written for all endpoints, 95% coverage achieved",
                ],
                100: [
                    "All endpoints complete: GET /api/users (list), POST /api/users (create), PUT /api/users/:id (update). Uses Bearer auth from context.",
                    "API fully implemented with documentation. Endpoints follow existing patterns and error formats.",
                    "Task complete. Created 5 endpoints, all tested and documented with request/response examples.",
                ],
            }
        elif "frontend" in self.role.lower():
            messages = {
                25: [
                    "Created component structure using TypeScript and React hooks",
                    "Set up component with proper TypeScript interfaces based on API response format",
                    "Configured API client to use endpoints from implementation context",
                ],
                50: [
                    "Integrated with GET /api/users endpoint from context, handling pagination",
                    "Component fetching data from backend APIs shown in context, proper error handling",
                    "UI components working with loading states and error boundaries",
                ],
                75: [
                    "Added responsive design for mobile and desktop viewports",
                    "Implemented proper authentication flow using Bearer tokens from context",
                    "Component tests written using Jest and React Testing Library",
                ],
                100: [
                    "UserList component complete. Integrates with GET /api/users, handles auth, fully responsive.",
                    "Component finished with full API integration. Uses all endpoints from context correctly.",
                    "UI complete. Successfully integrated with 3 API endpoints, all error states handled.",
                ],
            }
        elif "test" in self.role.lower():
            messages = {
                25: [
                    "Identified 5 endpoints from context to test, setting up test structure",
                    "Created test fixtures based on API response formats from implementation context",
                    "Test environment configured with proper mocking for external dependencies",
                ],
                50: [
                    "Unit tests complete for auth API (12 tests), matches implementation from context",
                    "API contract tests written, verifying request/response formats match documentation",
                    "Component tests created, mocking API responses based on context",
                ],
                75: [
                    "Integration tests for auth flow complete, testing token propagation",
                    "End-to-end tests written for critical user paths",
                    "Performance tests added for API endpoints, all within acceptable limits",
                ],
                100: [
                    "43 tests total: 25 unit, 18 integration. Coverage: auth 95%, API 92%, components 88%.",
                    "Test suite complete. All endpoints from context tested with positive and negative cases.",
                    "Testing finished. 100% of implementation context covered, all tests passing.",
                ],
            }
        else:
            # Default messages
            messages = {
                25: ["Initial setup complete", "Requirements analyzed"],
                50: ["Core functionality implemented", "Main features working"],
                75: ["Tests written and passing", "Edge cases handled"],
                100: ["Task fully completed", "All tests passing"],
            }

        return random.choice(messages.get(progress, ["Progress update"]))

    async def run(self) -> None:
        """Main worker loop"""
        print(f"\n[{self.name}] Claude Worker Starting...")
        print(f"[{self.name}] Skills: {', '.join(self.skills)}")
        print("-" * 50)

        # Register with PM Agent
        await self.register()
        await asyncio.sleep(2)

        # Work loop
        work_cycles = 0
        max_cycles = 5  # Complete 5 tasks then stop

        while work_cycles < max_cycles:
            # Request a task
            task_response = await self.request_task()

            if task_response and task_response.get("has_task"):
                # Work on the task
                await self.work_on_task()
                work_cycles += 1

                # Short break between tasks
                break_time = random.uniform(2, 5)
                print(f"[{self.name}] Taking a {break_time:.1f}s break...")
                await asyncio.sleep(break_time)
            else:
                # No task available, wait and try again
                wait_time = random.uniform(10, 20)
                print(f"[{self.name}] No tasks available. Waiting {wait_time:.1f}s...")
                await asyncio.sleep(wait_time)

        print(f"\n[{self.name}] Completed {work_cycles} tasks. Shutting down.")


async def main() -> None:
    """Run the mock worker"""
    parser = argparse.ArgumentParser(description="Mock Claude Worker")
    parser.add_argument("--name", default="worker_1", help="Worker name")
    parser.add_argument("--role", default="Backend Developer", help="Worker role")
    parser.add_argument(
        "--skills", default="backend,api,database", help="Comma-separated skills"
    )
    args = parser.parse_args()

    skills = [s.strip() for s in args.skills.split(",")]
    worker = MockClaudeWorker(args.name, skills, args.role)

    print(f"\n[System] Loaded prompt for role: {args.role}")
    print(
        f"[System] First 200 chars of prompt: {worker.system_prompt[:200]}...\n"
        if worker.system_prompt
        else "[System] No prompt loaded\n"
    )

    try:
        await worker.run()
    except KeyboardInterrupt:
        print(f"\n[{args.name}] Shutting down...")


if __name__ == "__main__":
    from pathlib import Path

    asyncio.run(main())
