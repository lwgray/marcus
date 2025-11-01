#!/usr/bin/env python3
"""
Single-Agent Experiment Launcher.

Creates controlled single-agent experiments for comparison with Marcus
multi-agent system. Generates prompts from templates and launches Claude
in isolated environment.
"""

import argparse
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import yaml


class SingleAgentConfig:
    """Configuration for a single-agent experiment."""

    def __init__(self, config_path: Path):
        """
        Initialize experiment configuration from YAML file.

        Parameters
        ----------
        config_path : Path
            Path to config.yaml file
        """
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        # Validate experiment type
        exp_type = self.config.get("experiment_type")
        if exp_type != "single_agent":
            raise ValueError(
                f"Invalid experiment_type: {exp_type}. "
                "Expected 'single_agent' for this runner."
            )

        self.experiment_dir = config_path.parent
        self.project_name = self.config["project_name"]
        self.project_spec_file = self.experiment_dir / self.config["project_spec_file"]

        # Task generation settings
        self.task_generation = self.config.get("task_generation", {})
        self.mode = self.task_generation.get("mode", "predefined")
        self.task_source = self.task_generation.get("source")
        self.template_type = self.task_generation.get("template")

        # Single-agent settings
        self.single_agent = self.config.get("single_agent", {})
        self.model = self.single_agent.get("model", "claude-sonnet-4-5-20250929")
        self.agent_mode = self.single_agent.get(
            "mode", "structured"
        )  # structured or unstructured
        self.checkpoint_mode = self.single_agent.get("checkpoint_mode", True)
        self.time_tracking = self.single_agent.get("time_tracking", True)
        self.working_dir_name = self.single_agent.get(
            "working_directory", "./implementation"
        )

        # MLflow tracking
        self.experiment_tracking = self.config.get("experiment_tracking", {})
        self.tracking_enabled = self.experiment_tracking.get("enabled", True)

        # Marcus baseline (optional)
        self.marcus_baseline = self.config.get("marcus_baseline", {})

        # Timeouts
        self.timeouts = self.config.get("timeouts", {})
        self.max_duration = self.timeouts.get("max_experiment_duration", 14400)

        # Set up experiment directories
        self.prompts_dir = self.experiment_dir / "prompts"
        self.logs_dir = self.experiment_dir / "logs"
        self.implementation_dir = self.experiment_dir / "implementation"

        # Create directories
        self.prompts_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        self.implementation_dir.mkdir(exist_ok=True)


class PromptGenerator:
    """Generates single-agent prompts from templates and task breakdowns."""

    def __init__(self, config: SingleAgentConfig, templates_dir: Path):
        """
        Initialize prompt generator.

        Parameters
        ----------
        config : SingleAgentConfig
            Experiment configuration
        templates_dir : Path
            Path to templates directory
        """
        self.config = config
        self.templates_dir = templates_dir
        self.template_path = templates_dir / "single_agent_prompt.template.md"

    def load_task_breakdown(self) -> Dict[str, Any]:
        """
        Load task breakdown from source file.

        Returns
        -------
        Dict[str, Any]
            Task breakdown structure
        """
        # Skip task breakdown for unstructured mode
        if self.config.agent_mode == "unstructured":
            return {"tasks": []}

        if self.config.mode == "predefined" and self.config.task_source:
            source_path = self.config.experiment_dir / self.config.task_source
            if not source_path.exists():
                raise FileNotFoundError(f"Task breakdown file not found: {source_path}")

            with open(source_path, "r") as f:
                data = yaml.safe_load(f)
                return data if isinstance(data, dict) else {"tasks": []}

        # TODO: Implement template and ai_generated modes
        raise NotImplementedError(
            f"Task generation mode '{self.config.mode}' not yet implemented. "
            "Use 'predefined' mode with a task_breakdown.yaml file."
        )

    def format_task_structure(self, tasks: List[Dict[str, Any]]) -> str:
        """
        Format task breakdown into markdown structure.

        Parameters
        ----------
        tasks : list
            List of task dictionaries from task_breakdown.yaml

        Returns
        -------
        str
            Formatted markdown task structure
        """
        output = []

        for task in tasks:
            task_num = task["number"]
            task_title = task["name"]
            subtasks = task.get("subtasks", [])

            # Task header
            output.append(
                f"## Task {task_num}: {task_title} ({len(subtasks)} subtasks)"
            )
            output.append("")

            # Process subtasks
            for subtask in subtasks:
                subtask_num = subtask["number"]
                subtask_name = subtask["name"]
                requirements = subtask.get("requirements", [])
                deliverable = subtask.get("deliverable", "")

                # Subtask header
                output.append(f"### Subtask {subtask_num}: {subtask_name}")
                output.append("")

                # Requirements
                if requirements:
                    for req in requirements:
                        output.append(f"- {req}")
                    output.append("")

                # Deliverable
                if deliverable:
                    output.append(f"**Deliverable**: {deliverable}")
                    output.append("")

                # Checkpoint
                output.append(
                    f'**CHECKPOINT**: State "SUBTASK {subtask_num} COMPLETE" '
                    "and show what you created."
                )
                output.append("")
                output.append("---")
                output.append("")

        return "\n".join(output)

    def format_completion_checklist(self, tasks: List[Dict[str, Any]]) -> str:
        """
        Generate completion checklist from task structure.

        Parameters
        ----------
        tasks : list
            List of task dictionaries

        Returns
        -------
        str
            Formatted markdown checklist
        """
        output = []
        total_items = 0

        for task in tasks:
            task_num = task["number"]
            subtasks = task.get("subtasks", [])

            if subtasks:
                output.append(
                    f"- [ ] Task {task_num} completed with all {len(subtasks)} subtasks"
                )
                total_items += len(subtasks)
            else:
                output.append(f"- [ ] Task {task_num} completed")
                total_items += 1

        # Add standard checklist items
        output.extend(
            [
                f"- [ ] Total: {total_items} tasks/subtasks completed",
                "- [ ] All documentation created",
                "- [ ] All code files created and working",
                "- [ ] All tests written and passing",
                "- [ ] Error handling implemented",
                "- [ ] No partial implementations or stubs",
            ]
        )

        return "\n".join(output)

    def generate_prompt(self) -> str:
        """
        Generate complete prompt from template.

        Returns
        -------
        str
            Complete prompt ready for Claude
        """
        # Load project description
        with open(self.config.project_spec_file, "r") as f:
            project_description = f.read()

        # Check if we're in unstructured mode
        if self.config.agent_mode == "unstructured":
            return self._generate_unstructured_prompt(project_description)

        # Structured mode - use full template
        # Load template
        with open(self.template_path, "r") as f:
            template = f.read()

        # Load task breakdown
        task_data = self.load_task_breakdown()
        tasks = task_data.get("tasks", [])

        # Format task structure
        task_structure = self.format_task_structure(tasks)
        completion_checklist = self.format_completion_checklist(tasks)

        # Determine final task number
        final_task_num = tasks[-1]["number"] if tasks else "X"

        # Format Marcus baseline (if provided)
        marcus_baseline_text = ""
        if self.config.marcus_baseline.get("enabled"):
            time_minutes = self.config.marcus_baseline.get("time_minutes")
            tasks_completed = self.config.marcus_baseline.get("tasks_completed")
            reference = self.config.marcus_baseline.get("reference")

            if time_minutes and tasks_completed:
                marcus_baseline_text = (
                    f"**Marcus baseline**: Completed similar project in "
                    f"{time_minutes} minutes with {tasks_completed} subtasks"
                )
                if reference:
                    marcus_baseline_text += f" ({reference})"
                marcus_baseline_text += "\n\n"

        # Substitute variables
        prompt = template.replace("{PROJECT_NAME}", self.config.project_name)
        prompt = prompt.replace("{PROJECT_DESCRIPTION}", project_description.strip())
        prompt = prompt.replace("{TASK_STRUCTURE}", task_structure.strip())
        prompt = prompt.replace("{COMPLETION_CHECKLIST}", completion_checklist)
        prompt = prompt.replace("{FINAL_TASK_NUMBER}", str(final_task_num))
        prompt = prompt.replace("{MARCUS_BASELINE}", marcus_baseline_text)

        return prompt

    def _generate_unstructured_prompt(self, project_description: str) -> str:
        """
        Generate unstructured prompt (raw project description only).

        This mode mimics a pure single-agent baseline with no scaffolding,
        no task breakdown, no checkpoints - just the project description
        and basic time tracking instructions.

        Parameters
        ----------
        project_description : str
            Raw project description

        Returns
        -------
        str
            Unstructured prompt for pure baseline comparison
        """
        # Format Marcus baseline if provided
        marcus_baseline_text = ""
        if self.config.marcus_baseline.get("enabled"):
            time_minutes = self.config.marcus_baseline.get("time_minutes")
            tasks_completed = self.config.marcus_baseline.get("tasks_completed")
            reference = self.config.marcus_baseline.get("reference")

            if time_minutes and tasks_completed:
                marcus_baseline_text = (
                    "\n\n**For comparison**: A multi-agent system "
                    f"completed a similar project in {time_minutes} minutes "
                    f"with {tasks_completed} subtasks"
                )
                if reference:
                    marcus_baseline_text += f" ({reference})"
                marcus_baseline_text += ".\n"

        prompt = f"""# {self.config.project_name}

{project_description.strip()}

---

## Instructions

Please implement the project described above. You have complete freedom to decide:
- How to break down the work
- What files to create
- What tests to write
- How to organize the code

**Time Tracking**: Please note your start time and end time so we can
measure how long this takes.

Example:
```
START: 2025-10-23 10:15:32
... your work ...
END: 2025-10-23 10:47:18
TOTAL: 31 minutes 46 seconds
```
{marcus_baseline_text}
Organize your files and code however you think is best. Focus on
delivering a working, tested implementation.
"""
        return prompt


class SingleAgentExperiment:
    """Runs a single-agent experiment."""

    def __init__(self, config: SingleAgentConfig, templates_dir: Path):
        """
        Initialize experiment runner.

        Parameters
        ----------
        config : SingleAgentConfig
            Experiment configuration
        templates_dir : Path
            Path to templates directory
        """
        self.config = config
        self.templates_dir = templates_dir
        self.tmux_session = (
            f"single_agent_{self.config.project_name.lower().replace(' ', '_')}"
        )

    def generate_and_save_prompt(self) -> Path:
        """
        Generate prompt and save to prompts directory.

        Returns
        -------
        Path
            Path to generated prompt file
        """
        generator = PromptGenerator(self.config, self.templates_dir)
        prompt = generator.generate_prompt()

        # Save prompt
        prompt_file = (
            self.config.prompts_dir
            / f"single_agent_prompt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        )

        with open(prompt_file, "w") as f:
            f.write(prompt)

        print(f"✓ Generated prompt: {prompt_file}")
        return prompt_file

    def setup_tmux_session(self) -> bool:
        """
        Create tmux session for the experiment.

        Returns
        -------
        bool
            True if successful, False otherwise
        """
        # Kill existing session if it exists
        subprocess.run(
            ["tmux", "kill-session", "-t", self.tmux_session],
            capture_output=True,
        )

        # Create new session
        try:
            subprocess.run(
                ["tmux", "new-session", "-d", "-s", self.tmux_session],
                check=True,
                capture_output=True,
            )
            print(f"✓ Created tmux session: {self.tmux_session}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to create tmux session: {e}")
            return False

    def launch_claude(self, prompt_file: Path) -> bool:
        """
        Launch Claude in tmux with the generated prompt.

        Parameters
        ----------
        prompt_file : Path
            Path to prompt file

        Returns
        -------
        bool
            True if successful, False otherwise
        """
        log_file = (
            self.config.logs_dir
            / f"single_agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )

        # Read prompt content
        with open(prompt_file, "r") as f:
            prompt_content = f.read()

        # Escape special characters for shell
        escaped_prompt = prompt_content.replace('"', '\\"').replace("$", "\\$")

        # Create script to launch Claude
        launch_script = f"""#!/bin/bash
# Source shell profiles to get nvm, claude, etc.
[ -f ~/.zshrc ] && source ~/.zshrc
[ -f ~/.bashrc ] && source ~/.bashrc

# Change to implementation directory
cd {self.config.implementation_dir}

# Launch Claude with prompt
echo "{escaped_prompt}" | claude 2>&1 | tee {log_file}
"""

        script_file = self.config.logs_dir / "launch_claude.sh"
        with open(script_file, "w") as f:
            f.write(launch_script)

        script_file.chmod(0o755)

        # Send script to tmux
        try:
            subprocess.run(
                [
                    "tmux",
                    "send-keys",
                    "-t",
                    self.tmux_session,
                    f"bash {script_file}",
                    "C-m",
                ],
                check=True,
                capture_output=True,
            )
            print("✓ Launched Claude in tmux session")
            print(f"  Log file: {log_file}")
            print(f"  Attach with: tmux attach -t {self.tmux_session}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to launch Claude: {e}")
            return False

    def run(self) -> bool:
        """
        Run the single-agent experiment.

        Returns
        -------
        bool
            True if successful, False otherwise
        """
        print(
            f"\n=== Starting Single-Agent Experiment: {self.config.project_name} ===\n"
        )

        # Generate prompt
        print("[1/3] Generating prompt...")
        try:
            prompt_file = self.generate_and_save_prompt()
        except Exception as e:
            print(f"✗ Failed to generate prompt: {e}")
            return False

        # Setup tmux
        print("\n[2/3] Setting up tmux session...")
        if not self.setup_tmux_session():
            return False

        # Launch Claude
        print("\n[3/3] Launching Claude...")
        if not self.launch_claude(prompt_file):
            return False

        print("\n=== Experiment Started Successfully ===\n")
        print(f"Session: {self.tmux_session}")
        print(f"Working directory: {self.config.implementation_dir}")
        print(f"Prompt: {prompt_file}")
        print("\nTo monitor:")
        print(f"  tmux attach -t {self.tmux_session}")
        print("\nTo kill session:")
        print(f"  tmux kill-session -t {self.tmux_session}")

        return True


def create_experiment_structure(experiment_dir: Path, templates_dir: Path) -> bool:
    """
    Create experiment directory structure with templates.

    Parameters
    ----------
    experiment_dir : Path
        Directory for the experiment
    templates_dir : Path
        Directory containing templates

    Returns
    -------
    bool
        True if files need editing, False if ready to run
    """
    experiment_dir.mkdir(parents=True, exist_ok=True)

    config_file = experiment_dir / "config.yaml"
    spec_file = experiment_dir / "project_spec.md"
    task_file = experiment_dir / "task_breakdown.yaml"

    # Copy config template
    if not config_file.exists():
        template_config = templates_dir / "config_single_agent.yaml"
        shutil.copy(template_config, config_file)
        print("✓ Created config.yaml from template")
        print(f"  Edit {config_file} to configure your experiment")

    # Create project spec template
    if not spec_file.exists():
        with open(spec_file, "w") as f:
            f.write(
                """# Project Specification

## Overview
[Describe what you want to build - this is used in the generated prompt]

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

    # Create task breakdown template
    if not task_file.exists():
        with open(task_file, "w") as f:
            f.write(
                """# Task Breakdown for Single-Agent Experiment
# Define the task structure that will be used to generate the prompt

tasks:
  - number: 1
    name: "Task Name"
    subtasks:
      - number: 1.1
        name: "Subtask Name"
        requirements:
          - "Requirement 1"
          - "Requirement 2"
        deliverable: "What should be created"

  - number: 2
    name: "Another Task"
    subtasks:
      - number: 2.1
        name: "Another Subtask"
        requirements:
          - "Requirement 1"
        deliverable: "Deliverable description"
"""
            )
        print("✓ Created task_breakdown.yaml template")
        print(f"  Edit {task_file} to define task structure")

    # Create subdirectories
    (experiment_dir / "prompts").mkdir(exist_ok=True)
    (experiment_dir / "logs").mkdir(exist_ok=True)
    implementation_dir = experiment_dir / "implementation"
    implementation_dir.mkdir(exist_ok=True)

    # Initialize git repository
    git_dir = implementation_dir / ".git"
    if not git_dir.exists():
        print("\n[Setup] Initializing git repository...")
        try:
            subprocess.run(
                ["git", "init"],
                cwd=implementation_dir,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "checkout", "-b", "main"],
                cwd=implementation_dir,
                check=True,
                capture_output=True,
            )
            print("✓ Git repository initialized on main branch")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Git initialization failed: {e}")

    return not (config_file.exists() and spec_file.exists() and task_file.exists())


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
    errors = []

    if not config_file.exists():
        errors.append(f"Missing config.yaml at {config_file}")
        print("Validation errors:")
        for error in errors:
            print(f"  ✗ {error}")
        return False

    # Read config
    try:
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)
    except Exception as e:
        errors.append(f"Error reading config.yaml: {e}")
        print("Validation errors:")
        for error in errors:
            print(f"  ✗ {error}")
        return False

    # Validate experiment type
    exp_type = config.get("experiment_type")
    if exp_type != "single_agent":
        errors.append(f"Invalid experiment_type: {exp_type}. Expected 'single_agent'")

    # Validate project spec file
    spec_filename = config.get("project_spec_file", "project_spec.md")
    spec_file = experiment_dir / spec_filename
    if not spec_file.exists():
        errors.append(f"Missing {spec_filename} at {spec_file}")

    # Validate task breakdown file (only for structured mode with predefined tasks)
    single_agent = config.get("single_agent", {})
    agent_mode = single_agent.get("mode", "structured")

    if agent_mode == "structured":
        task_gen = config.get("task_generation", {})
        if task_gen.get("mode") == "predefined":
            task_source = task_gen.get("source")
            if not task_source:
                errors.append(
                    "task_generation.source is required for structured predefined mode"
                )
            else:
                task_file = experiment_dir / task_source
                if not task_file.exists():
                    errors.append(f"Missing task breakdown file at {task_file}")

    if errors:
        print("Validation errors:")
        for error in errors:
            print(f"  ✗ {error}")
        return False

    return True


def main() -> None:
    """Run the single-agent experiment launcher."""
    parser = argparse.ArgumentParser(
        description="Run a single-agent controlled experiment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a new experiment
  python run_single_agent_experiment.py --init ~/experiments/my-project

  # Run an existing experiment
  python run_single_agent_experiment.py ~/experiments/my-project

  # Validate experiment config without running
  python run_single_agent_experiment.py --validate ~/experiments/my-project
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
        print(f"Initializing single-agent experiment at: {experiment_dir}")
        print()
        create_experiment_structure(experiment_dir, templates_dir)
        print()
        print("✓ Experiment initialized!")
        print()
        print("Next steps:")
        print(f"  1. Edit {experiment_dir / 'config.yaml'}")
        print(f"  2. Edit {experiment_dir / 'project_spec.md'}")
        print(f"  3. Edit {experiment_dir / 'task_breakdown.yaml'}")
        print(f"  4. Run: python run_single_agent_experiment.py {experiment_dir}")
        sys.exit(0)

    # Validate experiment exists
    if not experiment_dir.exists():
        print(f"Error: Experiment directory not found: {experiment_dir}")
        print()
        print("To create it, run:")
        print(f"  python run_single_agent_experiment.py --init {experiment_dir}")
        sys.exit(1)

    # Validate configuration
    if not validate_experiment(experiment_dir):
        sys.exit(1)

    # Validate-only mode
    if args.validate:
        print(f"✓ Experiment configuration is valid: {experiment_dir}")
        sys.exit(0)

    # Load config and run experiment
    config_file = experiment_dir / "config.yaml"
    config = SingleAgentConfig(config_file)
    experiment = SingleAgentExperiment(config, templates_dir)

    success = experiment.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
