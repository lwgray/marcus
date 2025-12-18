#!/usr/bin/env python3
"""
AppForge Task Converter.

Converts AppForge benchmark tasks into Marcus experiment format.
Fetches task specifications from AppForge repository and generates
the necessary Marcus configuration files.
"""

import json
from pathlib import Path
from typing import Any

import requests
import yaml


def fetch_appforge_task(
    task_id: int, cache_dir: Path, bench_folder: Path | None = None
) -> dict[str, Any]:
    """
    Fetch AppForge task specification from tasks.json and task_info.json.

    IMPORTANT: Combines data from two sources:
    1. tasks.json - app description and features
    2. task_info.json - package name, permissions, test counts (from modern fork)

    Parameters
    ----------
    task_id : int
        AppForge task ID (0-100)
    cache_dir : Path
        Directory to cache fetched tasks
    bench_folder : Path, optional
        Path to modern AppForge fork (e.g., ~/dev/AppForge_Bench_Modern)
        If provided, reads task_info.json for package name and permissions

    Returns
    -------
    dict[str, Any]
        Task specification with app_key, refined_features, package_name, etc.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"task_{task_id}.json"

    # Check cache first
    if cache_file.exists():
        print(f"  Using cached task spec: {cache_file}")
        with open(cache_file, "r") as f:
            return json.load(f)

    # Fetch tasks.json from AppForge repository
    url = "https://raw.githubusercontent.com/AppForge-Bench/AppForge/main/tasks/tasks.json"

    print(f"  Fetching task {task_id} from AppForge tasks.json...")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        all_tasks = response.json()

        if task_id < 0 or task_id >= len(all_tasks):
            raise ValueError(f"Task ID {task_id} out of range (0-{len(all_tasks)-1})")

        task_data = all_tasks[task_id]
        task_data["id"] = task_id  # Add ID field

    except (requests.RequestException, ValueError) as e:
        # Fallback: create placeholder task for development
        print(f"  Warning: Could not fetch task {task_id}: {e}")
        task_data = {
            "id": task_id,
            "app_key": f"AppForge_Task_{task_id}",
            "refined_features": f"Build an Android application for task {task_id}",
        }

    # Extract package name and permissions from task_info.json (modern fork)
    if bench_folder:
        task_info_path = (
            bench_folder / "tasks" / task_data["app_key"] / "task_info.json"
        )
        if task_info_path.exists():
            print(f"  Reading package name from: {task_info_path}")
            with open(task_info_path, "r") as f:
                task_info = json.load(f)
                task_data["package_name"] = task_info.get("package_name")
                task_data["permissions"] = task_info.get("permissions", [])
                print(f"  ✓ Package name: {task_data['package_name']}")
                print(f"  ✓ Permissions: {task_data['permissions']}")
        else:
            print(f"  Warning: task_info.json not found at {task_info_path}")
            task_data["package_name"] = None
            task_data["permissions"] = []

    # Cache for future use
    with open(cache_file, "w") as f:
        json.dump(task_data, f, indent=2)

    return task_data


def generate_project_spec(task_data: dict[str, Any]) -> str:
    """
    Generate Marcus project_spec.md from AppForge task.

    Parameters
    ----------
    task_data : dict
        AppForge task specification

    Returns
    -------
    str
        Markdown content for project_spec.md
    """
    app_key = task_data.get("app_key", f"Task {task_data['id']}")
    refined_features = task_data.get("refined_features", "")
    package_name = task_data.get("package_name")
    permissions = task_data.get("permissions", [])

    # Build package name section
    if package_name:
        package_section = f"""
## CRITICAL: Package Name

**YOU MUST USE THIS EXACT PACKAGE NAME:**

```
{package_name}
```

This package name is required for AppForge test compatibility. Set it in both:
1. app/build.gradle: `namespace '{package_name}'`
2. AndroidManifest.xml: `package="{package_name}"`
"""
    else:
        package_section = """
## Package Name

Use a standard package name format (e.g., com.example.{app_key.lower()})
"""

    # Build permissions section
    if permissions:
        permissions_text = "\n".join(f"- {p}" for p in permissions)
        permissions_section = f"""
## Required Permissions

Add these permissions to AndroidManifest.xml:

{permissions_text}
"""
    else:
        permissions_section = ""

    spec = f"""# {app_key} Android App

## Overview

This is an Android application development task from the AppForge benchmark suite.

Build a fully functional Android application named "{app_key}" that implements the features described below.
{package_section}

## Feature Specifications

{refined_features}

## Technical Stack

- **Platform**: Android
- **Language**: Java or Kotlin
- **Build**: Gradle
- **Minimum SDK**: API 24 (Android 7.0)
- **Target SDK**: API 34 (Android 14)
- **Target Device**: Modern Android emulator
{permissions_section}

## Deliverables

1. Complete Android application source code
2. Gradle build configuration (build.gradle files)
3. AndroidManifest.xml with all required permissions
4. All necessary XML layouts and resources
5. Working APK that passes AppForge test suite

## Acceptance Criteria

- App compiles without errors using Gradle
- App installs successfully on Android emulator
- All features from the specification work correctly
- App handles user interactions as described
- No crashes during normal usage
- Passes all AppForge automated tests
- CRITICAL: Uses the exact package name specified above

## Development Notes

- **CRITICAL**: Use the exact package name specified above - tests depend on it
- Read the feature specifications carefully - they include specific resource IDs and UI elements
- Follow Android development best practices
- Ensure proper error handling
- Test thoroughly before submission

## Agent Notes

All agents are full-stack developers capable of Android development.
Work together to implement all required features and ensure quality.
Coordinate on architecture and division of work.
"""
    return spec


def generate_config_yaml(
    task_data: dict[str, Any], num_agents: int = 5
) -> dict[str, Any]:
    """
    Generate Marcus config.yaml from AppForge task.

    Parameters
    ----------
    task_data : dict
        AppForge task specification
    num_agents : int
        Number of Marcus agents to use

    Returns
    -------
    dict
        Configuration dictionary for Marcus
    """
    app_key = task_data.get("app_key", f"Task {task_data['id']}")

    # All AppForge tasks are complex Android apps - use "standard" complexity
    complexity = "standard"

    config = {
        "project_name": app_key,
        "project_spec_file": "project_spec.md",
        "project_options": {
            "mode": "new_project",
            "complexity": complexity,
            "provider": "planka",
        },
        "agents": [],
        "timeouts": {
            "project_creation": 300,
            "max_experiment_duration": 3600,  # 1 hour for Android apps
        },
    }

    # Generate agent configurations
    agent_roles = [
        (
            "android_dev_1",
            "Android Developer 1",
            "android",
            ["java", "kotlin", "android", "gradle"],
        ),
        (
            "android_dev_2",
            "Android Developer 2",
            "android",
            ["java", "kotlin", "android", "ui"],
        ),
        (
            "backend_dev",
            "Backend Developer",
            "backend",
            ["java", "kotlin", "api", "database"],
        ),
        ("qa_engineer", "QA Engineer", "qa", ["testing", "android", "junit"]),
        (
            "tech_lead",
            "Technical Lead",
            "lead",
            ["android", "architecture", "code-review"],
        ),
    ]

    for i in range(min(num_agents, len(agent_roles))):
        agent_id, name, role, skills = agent_roles[i]
        config["agents"].append(
            {
                "id": agent_id,
                "name": name,
                "role": role,
                "skills": skills,
                "subagents": 0,
            }
        )

    return config


def convert_appforge_to_marcus_spec(
    task_id: int,
    num_agents: int = 5,
    output_dir: Path | None = None,
    cache_dir: Path | None = None,
    bench_folder: Path | None = None,
) -> Path:
    """
    Convert AppForge task to Marcus experiment format.

    Parameters
    ----------
    task_id : int
        AppForge task ID
    num_agents : int
        Number of Marcus agents (default: 5)
    output_dir : Path, optional
        Output directory for experiment (default: /tmp/appforge_task_{id})
    cache_dir : Path, optional
        Cache directory for task specs (default: ~/appforge_benchmarks/cache)
    bench_folder : Path, optional
        Path to modern AppForge fork (default: ~/dev/AppForge_Bench_Modern)
        Required to extract package name from task_info.json

    Returns
    -------
    Path
        Path to created experiment directory
    """
    if output_dir is None:
        output_dir = Path(f"/tmp/appforge_task_{task_id}")

    if cache_dir is None:
        cache_dir = Path.home() / "appforge_benchmarks" / "cache"

    if bench_folder is None:
        bench_folder = Path.home() / "dev" / "AppForge_Bench_Modern"

    print(f"Converting AppForge task {task_id} to Marcus format...")

    # Fetch task specification (includes package name from task_info.json)
    task_data = fetch_appforge_task(task_id, cache_dir, bench_folder)

    # Create experiment directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate project_spec.md (includes package name requirement)
    spec_content = generate_project_spec(task_data)
    spec_file = output_dir / "project_spec.md"
    with open(spec_file, "w") as f:
        f.write(spec_content)
    print(f"  Created: {spec_file}")

    # Generate config.yaml
    config_data = generate_config_yaml(task_data, num_agents)
    config_file = output_dir / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
    print(f"  Created: {config_file}")

    # Create subdirectories
    (output_dir / "prompts").mkdir(exist_ok=True)
    (output_dir / "logs").mkdir(exist_ok=True)
    (output_dir / "implementation").mkdir(exist_ok=True)

    print(f"✓ Conversion complete: {output_dir}")
    return output_dir


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert AppForge task to Marcus format"
    )
    parser.add_argument("--task-id", type=int, required=True, help="AppForge task ID")
    parser.add_argument("--num-agents", type=int, default=5, help="Number of agents")
    parser.add_argument("--output-dir", type=Path, help="Output directory")
    parser.add_argument("--cache-dir", type=Path, help="Cache directory")
    parser.add_argument(
        "--bench-folder",
        type=Path,
        help="Modern AppForge fork path (default: ~/dev/AppForge_Bench_Modern)",
    )

    args = parser.parse_args()

    experiment_dir = convert_appforge_to_marcus_spec(
        task_id=args.task_id,
        num_agents=args.num_agents,
        output_dir=args.output_dir,
        cache_dir=args.cache_dir,
        bench_folder=args.bench_folder,
    )

    print(f"\nExperiment directory ready: {experiment_dir}")
    print(
        f"Run Marcus with: python dev-tools/experiments/run_experiment.py {experiment_dir}"
    )
