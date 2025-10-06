"""
Marcus Multi-Agent Demo Runner with Experiment Tracking

This script orchestrates the complete multi-agent demo with MLflow experiment tracking.
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.client.stdio import stdio_client

from mcp import ClientSession, StdioServerParameters


class MultiAgentDemo:
    """Orchestrates multi-agent development demo with experiment tracking."""

    def __init__(self, demo_root: Path):
        """
        Initialize the demo runner.

        Parameters
        ----------
        demo_root : Path
            Root directory of the demo
        """
        self.demo_root = demo_root
        self.spec_path = demo_root / "task_management_api_spec.yaml"
        self.project_spec_path = demo_root / "PROJECT_SPEC.md"
        self.impl_root = demo_root / "implementation"

        self.project_id: Optional[str] = None
        self.board_id: Optional[str] = None
        self.experiment_active = False
        self.start_time: Optional[float] = None
        self.metrics: Dict[str, Any] = {}

    async def start_experiment(self, session: ClientSession) -> None:
        """
        Start MLflow experiment tracking.

        Parameters
        ----------
        session : ClientSession
            MCP client session
        """
        print("\n" + "=" * 60)
        print("Starting MLflow Experiment Tracking")
        print("=" * 60)

        # Start experiment with Marcus MCP
        result = await session.call_tool(
            "start_experiment",
            arguments={
                "experiment_name": "marcus_multi_agent_demo",
                "run_name": f"task_api_build_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "tags": {
                    "project_type": "rest_api",
                    "language": "python",
                    "framework": "fastapi",
                    "demo_type": "multi_agent",
                },
                "params": {
                    "num_agents": 4,
                    "target_coverage": 80,
                    "target_mypy_errors": 0,
                    "api_endpoints": 15,
                    "complexity": "standard",
                },
                "tracking_interval": 30,  # Log metrics every 30 seconds
            },
        )

        print(f"✓ Experiment started: {result}")
        self.experiment_active = True
        self.start_time = time.time()

    async def create_project(self, session: ClientSession) -> Dict[str, Any]:
        """
        Create Marcus project from specification.

        Parameters
        ----------
        session : ClientSession
            MCP client session

        Returns
        -------
        Dict[str, Any]
            Project creation result
        """
        print("\n" + "=" * 60)
        print("Creating Marcus Project from Specification")
        print("=" * 60)

        # Read project specification
        with open(self.project_spec_path, "r") as f:
            project_description = f.read()

        # Create project via Marcus MCP
        result = await session.call_tool(
            "create_project",
            arguments={
                "project_name": "Task Management API Demo",
                "description": project_description,
                "options": {
                    "complexity": "standard",
                    "provider": "planka",
                    "mode": "auto",
                },
            },
        )

        if result.get("success"):
            self.project_id = result.get("project_id")
            self.board_id = result.get("board", {}).get("board_id")

            print(f"✓ Project created successfully")
            print(f"  Project ID: {self.project_id}")
            print(f"  Board ID: {self.board_id}")
            print(f"  Tasks created: {result.get('tasks_created', 0)}")
        else:
            print(f"✗ Project creation failed: {result.get('error')}")

        return result

    async def deploy_agents(
        self, session: ClientSession, num_agents: int = 4
    ) -> List[str]:
        """
        Deploy multiple agents to work on the project.

        Parameters
        ----------
        session : ClientSession
            MCP client session
        num_agents : int
            Number of agents to deploy

        Returns
        -------
        List[str]
            List of agent IDs
        """
        print("\n" + "=" * 60)
        print(f"Deploying {num_agents} Agents")
        print("=" * 60)

        agent_configs = [
            {
                "agent_id": "agent_auth",
                "name": "Authentication Agent",
                "role": "backend",
                "skills": ["python", "fastapi", "jwt", "security", "testing"],
            },
            {
                "agent_id": "agent_projects",
                "name": "Projects Agent",
                "role": "backend",
                "skills": ["python", "fastapi", "sqlalchemy", "testing"],
            },
            {
                "agent_id": "agent_tasks",
                "name": "Tasks Agent",
                "role": "backend",
                "skills": ["python", "fastapi", "sqlalchemy", "testing"],
            },
            {
                "agent_id": "agent_integration",
                "name": "Integration Agent",
                "role": "backend",
                "skills": ["python", "testing", "integration", "api"],
            },
        ]

        agent_ids = []
        for i, config in enumerate(agent_configs[:num_agents], 1):
            print(f"\n[{i}/{num_agents}] Registering {config['name']}...")

            result = await session.call_tool("register_agent", arguments=config)

            agent_ids.append(config["agent_id"])
            print(f"  ✓ {config['agent_id']} registered")

        return agent_ids

    async def monitor_progress(
        self, session: ClientSession, agent_ids: List[str]
    ) -> None:
        """
        Monitor agent progress and update metrics.

        Parameters
        ----------
        session : ClientSession
            MCP client session
        agent_ids : List[str]
            List of agent IDs to monitor
        """
        print("\n" + "=" * 60)
        print("Monitoring Multi-Agent Progress")
        print("=" * 60)

        while True:
            await asyncio.sleep(30)  # Check every 30 seconds

            # Get status for each agent
            all_complete = True
            progress_summary = {}

            for agent_id in agent_ids:
                status = await session.call_tool(
                    "get_agent_status", arguments={"agent_id": agent_id}
                )

                if status.get("current_task"):
                    all_complete = False
                    progress_summary[agent_id] = {
                        "task": status.get("current_task", {}).get("title", "Unknown"),
                        "progress": status.get("current_task", {}).get("progress", 0),
                    }

            # Display progress
            elapsed = time.time() - self.start_time if self.start_time else 0
            print(f"\n[{elapsed/60:.1f} min] Agent Status:")
            for agent_id, info in progress_summary.items():
                print(f"  {agent_id}: {info['task']} ({info['progress']}%)")

            # Check quality metrics
            await self.update_metrics(session)

            if all_complete:
                print("\n✓ All agents completed their tasks!")
                break

    async def update_metrics(self, session: ClientSession) -> None:
        """
        Update quality metrics during the build.

        Parameters
        ----------
        session : ClientSession
            MCP client session
        """
        if not self.impl_root.exists():
            return

        # This would be called periodically to track metrics
        # In a real implementation, you'd measure coverage, mypy errors, etc.
        # and log them to the experiment
        pass

    async def validate_results(self) -> Dict[str, Any]:
        """
        Run final validation and collect metrics.

        Returns
        -------
        Dict[str, Any]
            Validation results
        """
        print("\n" + "=" * 60)
        print("Validating Results")
        print("=" * 60)

        results = {
            "api_compliance": 0,
            "test_coverage": 0,
            "mypy_errors": 0,
            "endpoints_working": 0,
            "total_time_minutes": 0,
        }

        if self.start_time:
            results["total_time_minutes"] = (time.time() - self.start_time) / 60

        # Run validation script
        # (In real implementation, would call validate_api.py)

        print(f"\n Results:")
        print(f"  API Compliance: {results['api_compliance']}%")
        print(f"  Test Coverage: {results['test_coverage']}%")
        print(f"  Mypy Errors: {results['mypy_errors']}")
        print(f"  Endpoints Working: {results['endpoints_working']}/15")
        print(f"  Total Time: {results['total_time_minutes']:.1f} minutes")

        return results

    async def end_experiment(
        self, session: ClientSession, results: Dict[str, Any]
    ) -> None:
        """
        End experiment and log final metrics.

        Parameters
        ----------
        session : ClientSession
            MCP client session
        results : Dict[str, Any]
            Final validation results
        """
        print("\n" + "=" * 60)
        print("Finalizing Experiment")
        print("=" * 60)

        if self.experiment_active:
            # End experiment via Marcus MCP
            result = await session.call_tool("end_experiment", arguments={})

            print(f"✓ Experiment ended")
            print(f"  MLflow tracking complete")
            print(f"  View results in MLflow UI")

    async def run_demo(self) -> None:
        """Run the complete demo workflow."""
        print("\n" + "=" * 60)
        print("Marcus Multi-Agent Development Demo")
        print("=" * 60)
        print(f"Demo root: {self.demo_root}")
        print(f"Specification: {self.spec_path.name}")

        # Connect to Marcus MCP server
        server_params = StdioServerParameters(
            command="python",
            args=["-m", "src.marcus_mcp.server"],
            env=None,
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Phase 1: Start experiment tracking
                await self.start_experiment(session)

                # Phase 2: Create project from spec
                await self.create_project(session)

                # Phase 3: Deploy agents
                agent_ids = await self.deploy_agents(session, num_agents=4)

                # Phase 4: Monitor progress (in real demo, agents would be working)
                # await self.monitor_progress(session, agent_ids)

                # Phase 5: Validate results
                results = await self.validate_results()

                # Phase 6: End experiment
                await self.end_experiment(session, results)

                print("\n" + "=" * 60)
                print("Demo Complete!")
                print("=" * 60)


async def main():
    """Main entry point for demo runner."""
    demo_root = Path(__file__).parent
    demo = MultiAgentDemo(demo_root)
    await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main())
