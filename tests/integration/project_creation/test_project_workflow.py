#!/usr/bin/env python3
"""
Test script for the complete project workflow system.

This demonstrates:
1. Creating a project
2. Adding features
3. Starting the workflow
4. Monitoring pipeline events
"""

import asyncio
import json
import time
from datetime import datetime

import requests

API_BASE_URL = "http://localhost:5000/api"


def create_test_project():
    """Create a test project."""
    print("\n=== Creating Test Project ===")

    response = requests.post(
        f"{API_BASE_URL}/projects/create",
        json={
            "name": "Todo App with Authentication",
            "description": "A simple todo application with user authentication and REST API",
            "type": "web_app",
        },
    )

    if response.status_code == 200:
        data = response.json()
        if data["success"]:
            project = data["project"]
            print(f"✓ Project created: {project['name']} (ID: {project['id']})")
            return project

    print(f"✗ Failed to create project: {response.text}")
    return None


def add_features(project_id):
    """Add features to the project."""
    print("\n=== Adding Features ===")

    features = [
        {
            "title": "User Authentication",
            "description": "Implement user registration and login with JWT tokens",
            "priority": "high",
            "acceptance_criteria": "Users can register, Users can login, JWT tokens are generated, Passwords are hashed",
        },
        {
            "title": "Todo CRUD Operations",
            "description": "Create REST API endpoints for managing todos",
            "priority": "high",
            "acceptance_criteria": "Create todo endpoint, List todos endpoint, Update todo endpoint, Delete todo endpoint, Filter by status",
        },
        {
            "title": "React Frontend",
            "description": "Build a React frontend with Material-UI components",
            "priority": "medium",
            "acceptance_criteria": "Login page, Registration page, Todo list view, Add/edit todo form, Responsive design",
        },
    ]

    added_features = []
    for feature in features:
        response = requests.post(
            f"{API_BASE_URL}/projects/features/add",
            json={"project_id": project_id, **feature},
        )

        if response.status_code == 200:
            data = response.json()
            if data["success"]:
                added_features.append(data["feature"])
                print(f"✓ Added feature: {feature['title']}")
        else:
            print(f"✗ Failed to add feature: {feature['title']}")

    return added_features


def start_workflow(project_id):
    """Start the workflow for the project."""
    print("\n=== Starting Workflow ===")

    response = requests.post(
        f"{API_BASE_URL}/projects/workflow/start",
        json={
            "project_id": project_id,
            "options": {
                "auto_assign": True,
                "parallel_execution": True,
                "continuous_monitoring": True,
                "max_agents": 3,
            },
        },
    )

    if response.status_code == 200:
        data = response.json()
        if data["success"]:
            print(f"✓ Workflow started!")
            print(f"  Flow ID: {data['flow_id']}")
            print(f"  PM Project ID: {data.get('pm_project_id')}")
            print(f"  Workflow ID: {data.get('workflow_id')}")
            return data

    print(f"✗ Failed to start workflow: {response.text}")
    return None


def monitor_pipeline(flow_id, duration=30):
    """Monitor pipeline events for a duration."""
    print(f"\n=== Monitoring Pipeline (Flow: {flow_id}) ===")
    print(f"Monitoring for {duration} seconds...\n")

    start_time = time.time()
    last_check = 0

    while time.time() - start_time < duration:
        current_time = time.time()

        # Check dashboard every 5 seconds
        if current_time - last_check >= 5:
            response = requests.get(f"{API_BASE_URL}/pipeline/monitor/dashboard")
            if response.status_code == 200:
                data = response.json()
                if data["success"]:
                    dashboard = data["dashboard"]

                    # Find our flow
                    our_flow = None
                    for flow in dashboard.get("active_flows", []):
                        if flow["flow_id"] == flow_id:
                            our_flow = flow
                            break

                    if our_flow:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Flow Status:")
                        print(f"  Stage: {our_flow.get('current_stage', 'Unknown')}")
                        print(f"  Progress: {our_flow.get('progress_percentage', 0)}%")
                        print(
                            f"  Health: {our_flow.get('health_status', {}).get('status', 'Unknown')}"
                        )
                        print()

            last_check = current_time

        time.sleep(1)

    print("\nMonitoring complete!")


def main():
    """Run the complete test workflow."""
    print("=== Marcus Project Workflow Test ===")
    print("This test will create a project, add features, and start the workflow.")
    print("Make sure the API server is running on http://localhost:5000")

    input("\nPress Enter to continue...")

    # Step 1: Create project
    project = create_test_project()
    if not project:
        print("Failed to create project. Exiting.")
        return

    # Step 2: Add features
    features = add_features(project["id"])
    if not features:
        print("Failed to add features. Exiting.")
        return

    print(f"\nAdded {len(features)} features to the project.")

    # Step 3: Start workflow
    workflow_result = start_workflow(project["id"])
    if not workflow_result:
        print("Failed to start workflow. Exiting.")
        return

    # Step 4: Monitor pipeline
    print("\nThe workflow has been started! You can now:")
    print("1. Switch to the web interface and view the Live Monitor tab")
    print("2. Check the Agent Management tab to see agents picking up tasks")
    print("3. Use the Pipeline Replay tab to review the workflow")

    monitor = input("\nMonitor pipeline events here? (y/n): ")
    if monitor.lower() == "y":
        monitor_pipeline(workflow_result["flow_id"], duration=60)

    print("\n=== Test Complete ===")
    print(f"Project ID: {project['id']}")
    print(f"Flow ID: {workflow_result['flow_id']}")
    print("\nYou can continue monitoring in the web interface.")


if __name__ == "__main__":
    main()
