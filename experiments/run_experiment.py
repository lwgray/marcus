#!/usr/bin/env python3
"""
Marcus Experiment Launcher.

Convenience script to run Marcus multi-agent experiments.
Creates experiment directory structure if needed and launches agents.
"""

import argparse
import shutil
import sys
from pathlib import Path

from spawn_agents import AgentSpawner, ExperimentConfig


def create_experiment_structure(experiment_dir: Path, templates_dir: Path) -> bool:
    """
    Create experiment directory structure with templates.

    Parameters
    ----------
    experiment_dir : Path
        Directory for the experiment
    templates_dir : Path
        Directory containing templates
    """
    import subprocess

    experiment_dir.mkdir(parents=True, exist_ok=True)

    config_file = experiment_dir / "config.yaml"
    spec_file = experiment_dir / "project_spec.md"

    # Copy templates if they don't exist
    if not config_file.exists():
        template_config = templates_dir / "config.yaml.template"
        shutil.copy(template_config, config_file)
        print("✓ Created config.yaml from template")
        print(f"  Edit {config_file} to configure your experiment")

    if not spec_file.exists():
        # Create a minimal project spec template
        with open(spec_file, "w") as f:
            f.write(
                """# Project Specification

## Overview
[Describe what you want to build]

## Features
- [Feature 1]
- [Feature 2]
- [Feature 3]

## Technical Requirements
- [Requirement 1]
- [Requirement 2]

## Deliverables
- [Deliverable 1]
- [Deliverable 2]
"""
            )
        print("✓ Created project_spec.md template")
        print(f"  Edit {spec_file} to describe your project")

    # Create subdirectories
    (experiment_dir / "prompts").mkdir(exist_ok=True)
    (experiment_dir / "logs").mkdir(exist_ok=True)
    implementation_dir = experiment_dir / "implementation"
    implementation_dir.mkdir(exist_ok=True)

    # Initialize git repository in implementation directory
    git_dir = implementation_dir / ".git"  # pragma: allowlist secret
    if not git_dir.exists():
        print("\n[Setup] Initializing git repository...")
        try:
            subprocess.run(
                ["git", "init"],  # pragma: allowlist secret
                cwd=implementation_dir,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "checkout", "-b", "main"],  # pragma: allowlist secret
                cwd=implementation_dir,
                check=True,
                capture_output=True,
            )
            print(
                "✓ Git repository initialized on main branch"
            )  # pragma: allowlist secret
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Git initialization failed: {e}")

    # Verify Marcus MCP is configured
    print("\n[Setup] Verifying Marcus MCP configuration...")
    try:
        result = subprocess.run(
            ["claude", "mcp", "list"],  # pragma: allowlist secret
            capture_output=True,
            text=True,
            check=True,
        )
        if "marcus" in result.stdout:
            print("✓ Marcus MCP is configured")
            print("  Agents will have access to Marcus tools")
        else:
            print("⚠️  Marcus MCP not found in configuration")
            # pragma: allowlist secret
            print(
                "  Please run: claude mcp add marcus -t http "
                "http://localhost:4298/mcp"
            )
    except subprocess.CalledProcessError:
        print("⚠️  Could not verify MCP configuration")
        print("  Ensure Claude Code CLI is installed")
        # pragma: allowlist secret
        print(
            "  To configure Marcus: claude mcp add marcus -t http "
            "http://localhost:4298/mcp"
        )

    return not (config_file.exists() and spec_file.exists())


def validate_experiment(experiment_dir: Path) -> bool:
    """
    Validate that experiment directory is ready to run.

    Parameters
    ----------
    experiment_dir : Path
        Directory for the experiment

    Returns
    -------
    bool
        True if valid, False otherwise
    """
    config_file = experiment_dir / "config.yaml"
    spec_file = experiment_dir / "project_spec.md"

    errors = []

    if not config_file.exists():
        errors.append(f"Missing config.yaml at {config_file}")

    if not spec_file.exists():
        errors.append(f"Missing project_spec.md at {spec_file}")

    if errors:
        print("Validation errors:")
        for error in errors:
            print(f"  ✗ {error}")
        return False

    return True


def main() -> None:
    """Run the experiment launcher."""
    parser = argparse.ArgumentParser(
        description="Run a Marcus multi-agent experiment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a new experiment
  python run_experiment.py --init ~/experiments/my-project

  # Run an existing experiment
  python run_experiment.py ~/experiments/my-project

  # Validate experiment config without running
  python run_experiment.py --validate ~/experiments/my-project
        """,
    )

    parser.add_argument(
        "experiment_dir",
        type=str,
        help="Path to experiment directory (will be created if --init)",
    )

    parser.add_argument(
        "--init",
        action="store_true",
        help="Initialize a new experiment with templates",
    )

    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate experiment configuration without running",
    )

    args = parser.parse_args()

    experiment_dir = Path(args.experiment_dir).resolve()

    # Find templates directory
    script_dir = Path(__file__).parent
    templates_dir = script_dir / "templates"

    if not templates_dir.exists():
        print(f"Error: Templates directory not found at {templates_dir}")
        sys.exit(1)

    # Initialize mode
    if args.init:
        print(f"Initializing experiment at: {experiment_dir}")
        print()
        create_experiment_structure(experiment_dir, templates_dir)
        print()
        print("✓ Experiment initialized!")
        print()
        print("Next steps:")
        print(f"  1. Edit {experiment_dir / 'config.yaml'}")
        print(f"  2. Edit {experiment_dir / 'project_spec.md'}")
        print(f"  3. Run: python run_experiment.py {experiment_dir}")
        sys.exit(0)

    # Validate experiment exists
    if not experiment_dir.exists():
        print(f"Error: Experiment directory not found: {experiment_dir}")
        print()
        print("To create it, run:")
        print(f"  python run_experiment.py --init {experiment_dir}")
        sys.exit(1)

    # Validate configuration
    if not validate_experiment(experiment_dir):
        sys.exit(1)

    # Validate-only mode
    if args.validate:
        print(f"✓ Experiment configuration is valid: {experiment_dir}")
        sys.exit(0)

    # Run the experiment
    print(f"Running experiment: {experiment_dir}")
    print()

    config_file = experiment_dir / "config.yaml"
    config = ExperimentConfig(config_file)
    spawner = AgentSpawner(config, templates_dir)

    success = spawner.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
