#!/usr/bin/env python3
"""Test deployment target filtering in PRD parser"""

import asyncio

from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser, ProjectConstraints


async def test_deployment_filtering():
    parser = AdvancedPRDParser()

    # Test PRD for a simple web app
    prd_content = """
    Create a simple Hello World web application with the following requirements:
    - REST API endpoint that returns "Hello, World!"
    - Basic error handling
    - Unit tests
    - Documentation
    - Production deployment with monitoring and scaling
    - Load balancing and CDN setup
    - Database backups and disaster recovery
    """

    # Test different deployment targets
    targets = ["local", "dev", "prod"]

    for target in targets:
        print(f"\n{'='*50}")
        print(f"Testing with deployment_target: {target}")
        print("=" * 50)

        constraints = ProjectConstraints(
            deployment_target=target,
            team_size=1,
            technology_constraints=["Python", "FastAPI"],
        )

        result = await parser.parse_prd_to_tasks(prd_content, constraints)

        print(f"Total tasks generated: {len(result.tasks)}")

        # Check for deployment-related tasks
        deployment_tasks = [
            task
            for task in result.tasks
            if any(
                keyword in task.name.lower() or task.id.lower()
                for keyword in [
                    "deploy",
                    "production",
                    "monitoring",
                    "scaling",
                    "cdn",
                    "backup",
                ]
            )
        ]

        print(f"Deployment-related tasks: {len(deployment_tasks)}")
        if deployment_tasks:
            print("Deployment task names:")
            for task in deployment_tasks:
                print(f"  - {task.name}")


if __name__ == "__main__":
    asyncio.run(test_deployment_filtering())
