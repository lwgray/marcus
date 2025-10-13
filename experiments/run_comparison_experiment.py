#!/usr/bin/env python3
"""
Automated Experiment Runner for Single vs Multi-Agent Comparison.

This script automates the entire experimental process:
1. Runs projects with single-agent configuration
2. Runs projects with various multi-agent configurations
3. Collects metrics via MLflow
4. Generates comparison reports and visualizations
"""

import argparse
import concurrent.futures
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class ExperimentRunner:
    """
    Automate running controlled experiments comparing agent configurations.

    Parameters
    ----------
    base_dir : Path
        Base directory containing test projects
    results_dir : Path
        Directory to store results
    """

    def __init__(
        self,
        base_dir: Path,
        results_dir: Path,
        parallel: bool = False,
        max_parallel: int = 3,
        marcus_instances: Optional[List[Dict[str, str]]] = None,
    ):
        """
        Initialize the experiment runner.

        Parameters
        ----------
        base_dir : Path
            Base directory containing test projects
        results_dir : Path
            Directory to store results
        parallel : bool
            If True, run experiments in parallel across Marcus instances
        max_parallel : int
            Maximum number of parallel experiments (default: 3)
        marcus_instances : List[Dict], optional
            List of Marcus instance configurations. Each dict should have:
            - url: str (e.g., "http://localhost:4298")
            - board_id: str (Planka board ID)
            If None and parallel=True, will use default localhost instances
        """
        self.base_dir = base_dir
        self.results_dir = results_dir
        self.results_dir.mkdir(exist_ok=True, parents=True)
        self.parallel = parallel
        self.max_parallel = max_parallel

        # Configure Marcus instances for parallel execution
        if parallel and marcus_instances is None:
            # Default: Use localhost with different ports
            self.marcus_instances = [
                {"url": f"http://localhost:{4298 + i}", "board_id": f"board_{i}"}
                for i in range(max_parallel)
            ]
        else:
            self.marcus_instances = marcus_instances or []

        # Thread-safe print lock
        self._print_lock = threading.Lock()

        # Paths to scripts
        self.run_experiment_script = base_dir.parent / "run_experiment.py"
        self.analysis_script = base_dir.parent / "analysis" / "compare_experiments.py"
        self.visualization_script = (
            base_dir.parent / "analysis" / "visualize_results.py"
        )

    def get_project_configs(self, project_dir: Path) -> List[Path]:
        """
        Get all configuration files for a project.

        Parameters
        ----------
        project_dir : Path
            Project directory

        Returns
        -------
        List[Path]
            List of config file paths
        """
        configs = list(project_dir.glob("config_*.yaml"))
        # Sort to ensure single_agent runs first
        return sorted(configs, key=lambda p: ("single" not in p.name, p.name))

    def _thread_safe_print(self, *args: Any, **kwargs: Any) -> None:
        """Thread-safe print for parallel execution."""
        with self._print_lock:
            print(*args, **kwargs)

    def run_experiment(
        self,
        project_dir: Path,
        config_file: Path,
        marcus_instance: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Run a single experiment configuration.

        Parameters
        ----------
        project_dir : Path
            Project directory
        config_file : Path
            Configuration file

        Returns
        -------
        bool
            True if successful, False otherwise
        """
        instance_info = ""
        if marcus_instance:
            instance_info = f" on {marcus_instance['url']}"

        self._thread_safe_print("\n" + "=" * 80)
        self._thread_safe_print(f"Running: {config_file.name}{instance_info}")
        self._thread_safe_print("=" * 80)

        # Create experiment directory for this run
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        config_name = config_file.stem  # e.g., "config_single_agent"
        exp_dir = self.results_dir / f"{project_dir.name}_{config_name}_{timestamp}"
        exp_dir.mkdir(exist_ok=True, parents=True)

        # Copy config and project description
        import shutil

        shutil.copy(config_file, exp_dir / "config.yaml")
        desc_file = project_dir / "project_description.txt"
        if desc_file.exists():
            shutil.copy(desc_file, exp_dir / "project_spec.md")

        # Run the experiment
        try:
            cmd = [
                sys.executable,
                str(self.run_experiment_script),
                str(exp_dir),
            ]

            self._thread_safe_print(f"Command: {' '.join(cmd)}")
            self._thread_safe_print(f"Experiment directory: {exp_dir}")

            if marcus_instance:
                self._thread_safe_print(f"Marcus instance: {marcus_instance['url']}")
                self._thread_safe_print(f"Board ID: {marcus_instance['board_id']}")

            self._thread_safe_print("\nStarting experiment... (this may take a while)")

            # Set environment variables for Marcus instance if provided
            env = None
            if marcus_instance:
                env = dict(os.environ)
                env["MARCUS_URL"] = marcus_instance["url"]
                env["MARCUS_BOARD_ID"] = marcus_instance["board_id"]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600 * 4,  # 4 hour timeout
                env=env,
            )

            if result.returncode == 0:
                self._thread_safe_print(
                    f"✓ Experiment completed successfully: {config_file.name}"
                )
                return True
            else:
                self._thread_safe_print(
                    f"✗ Experiment failed: {config_file.name} "
                    f"(code: {result.returncode})"
                )
                self._thread_safe_print(f"STDOUT:\n{result.stdout}")
                self._thread_safe_print(f"STDERR:\n{result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self._thread_safe_print(
                f"✗ Experiment timed out after 4 hours: {config_file.name}"
            )
            return False
        except Exception as e:
            self._thread_safe_print(
                f"✗ Experiment failed with error: {config_file.name} - {e}"
            )
            return False

    def run_project_comparison_parallel(
        self,
        project_dir: Path,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Run all configurations for a project in parallel.

        Parameters
        ----------
        project_dir : Path
            Project directory
        dry_run : bool
            If True, only print what would be done

        Returns
        -------
        Dict
            Results summary
        """
        configs = self.get_project_configs(project_dir)

        if not configs:
            print(f"⚠️  No configurations found in {project_dir}")
            return {"error": "No configs found"}

        print(f"\n{'=' * 80}")
        print(f"PROJECT: {project_dir.name} (PARALLEL MODE)")
        print(f"{'=' * 80}")
        print(f"Found {len(configs)} configurations to run in parallel:")
        for config in configs:
            print(f"  - {config.name}")
        print(f"Max parallel: {self.max_parallel}")
        print(f"Available instances: {len(self.marcus_instances)}")

        if dry_run:
            print("\n[DRY RUN] Would run these experiments in parallel")
            return {"dry_run": True, "configs": [str(c) for c in configs]}

        # Run experiments in parallel using ThreadPoolExecutor
        results: Dict[str, Any] = {"project": project_dir.name, "runs": []}

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_parallel
        ) as executor:
            # Submit all experiments
            future_to_config = {}
            for i, config in enumerate(configs):
                # Assign Marcus instance (round-robin)
                instance = self.marcus_instances[i % len(self.marcus_instances)]
                future = executor.submit(
                    self.run_experiment,
                    project_dir,
                    config,
                    instance,
                )
                future_to_config[future] = config

            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_config):
                config = future_to_config[future]
                try:
                    success = future.result()
                    results["runs"].append({"config": config.name, "success": success})
                except Exception as e:
                    print(f"✗ Exception in {config.name}: {e}")
                    results["runs"].append(
                        {"config": config.name, "success": False, "error": str(e)}
                    )

        # Summary
        total = len(results["runs"])
        successful = sum(1 for r in results["runs"] if r["success"])
        print(f"\n{'=' * 80}")
        print(f"PROJECT SUMMARY: {project_dir.name}")
        print(f"{'=' * 80}")
        print(f"Total runs: {total}")
        print(f"Successful: {successful}")
        print(f"Failed: {total - successful}")

        return results

    def run_project_comparison(
        self,
        project_dir: Path,
        dry_run: bool = False,
        skip_analysis: bool = False,
    ) -> Dict[str, Any]:
        """
        Run all configurations for a project and compare results.

        Parameters
        ----------
        project_dir : Path
            Project directory
        dry_run : bool
            If True, only print what would be done
        skip_analysis : bool
            If True, skip analysis and visualization

        Returns
        -------
        Dict
            Results summary
        """
        configs = self.get_project_configs(project_dir)

        if not configs:
            print(f"⚠️  No configurations found in {project_dir}")
            return {"error": "No configs found"}

        print(f"\n{'=' * 80}")
        print(f"PROJECT: {project_dir.name}")
        print(f"{'=' * 80}")
        print(f"Found {len(configs)} configurations:")
        for config in configs:
            print(f"  - {config.name}")

        if dry_run:
            print("\n[DRY RUN] Would run these experiments")
            return {"dry_run": True, "configs": [str(c) for c in configs]}

        # Run each configuration
        results: Dict[str, Any] = {"project": project_dir.name, "runs": []}

        for config in configs:
            success = self.run_experiment(project_dir, config)
            results["runs"].append({"config": config.name, "success": success})

            # Wait between runs
            if success:
                print("\nWaiting 30 seconds before next run...")
                time.sleep(30)

        # Summary
        total = len(results["runs"])
        successful = sum(1 for r in results["runs"] if r["success"])
        print(f"\n{'=' * 80}")
        print(f"PROJECT SUMMARY: {project_dir.name}")
        print(f"{'=' * 80}")
        print(f"Total runs: {total}")
        print(f"Successful: {successful}")
        print(f"Failed: {total - successful}")

        return results

    def run_all_projects(
        self,
        project_filter: Optional[List[str]] = None,
        dry_run: bool = False,
        skip_analysis: bool = False,
    ) -> Dict[str, Any]:
        """
        Run experiments for all projects.

        Uses parallel or sequential mode based on self.parallel setting.

        Parameters
        ----------
        project_filter : List[str], optional
            List of project names to run. If None, runs all.
        dry_run : bool
            If True, only print what would be done
        skip_analysis : bool
            If True, skip final analysis

        Returns
        -------
        Dict
            Overall results
        """
        # Find all project directories
        project_dirs = [
            d
            for d in self.base_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]

        if project_filter:
            project_dirs = [d for d in project_dirs if d.name in project_filter]

        if not project_dirs:
            print("No projects found!")
            return {"error": "No projects"}

        mode = "PARALLEL" if self.parallel else "SEQUENTIAL"
        print(f"\n{'=' * 80}")
        print(f"EXPERIMENT BATCH ({mode} MODE)")
        print(f"{'=' * 80}")
        print(f"Projects to run: {len(project_dirs)}")
        for project in project_dirs:
            print(f"  - {project.name}")

        if self.parallel:
            print("\nParallel execution:")
            print(f"  - Max concurrent experiments: {self.max_parallel}")
            print(f"  - Marcus instances: {len(self.marcus_instances)}")
            for i, inst in enumerate(self.marcus_instances):
                print(f"    {i+1}. {inst['url']} (board: {inst['board_id']})")

        if dry_run:
            print(f"\n[DRY RUN] Would run these projects in {mode} mode")
            return {"dry_run": True, "mode": mode}

        # Run each project
        all_results: Dict[str, Any] = {"projects": [], "mode": mode}

        for i, project_dir in enumerate(project_dirs, 1):
            print(f"\n\n{'#' * 80}")
            print(f"# PROJECT {i}/{len(project_dirs)}: {project_dir.name}")
            print(f"{'#' * 80}\n")

            if self.parallel:
                # Run configs for this project in parallel
                project_results = self.run_project_comparison_parallel(
                    project_dir, dry_run=dry_run
                )
            else:
                # Run configs sequentially
                project_results = self.run_project_comparison(
                    project_dir, dry_run=dry_run, skip_analysis=True
                )

            all_results["projects"].append(project_results)

            # Wait between projects (even in parallel mode)
            if i < len(project_dirs):
                wait_time = 30 if self.parallel else 60
                print(f"\nWaiting {wait_time} seconds before next project...")
                time.sleep(wait_time)

        # Final analysis
        if not skip_analysis:
            print(f"\n\n{'=' * 80}")
            print("GENERATING FINAL ANALYSIS")
            print(f"{'=' * 80}\n")
            self.run_analysis()

        return all_results

    def run_analysis(self) -> None:
        """Run analysis and generate visualizations."""
        print("Running analysis script...")

        try:
            # Run comparison analysis
            analysis_output = self.results_dir / "comparison_report.json"
            cmd = [
                sys.executable,
                str(self.analysis_script),
                "--report",
                str(analysis_output),
            ]
            subprocess.run(cmd, check=True)
            print(f"✓ Analysis complete: {analysis_output}")

            # Generate visualizations
            plots_dir = self.results_dir / "plots"
            cmd = [
                sys.executable,
                str(self.visualization_script),
                "--output-dir",
                str(plots_dir),
            ]
            subprocess.run(cmd, check=True)
            print(f"✓ Visualizations complete: {plots_dir}")

        except subprocess.CalledProcessError as e:
            print(f"✗ Analysis failed: {e}")
        except Exception as e:
            print(f"✗ Analysis error: {e}")


def main() -> None:
    """Run the experiment runner."""
    parser = argparse.ArgumentParser(
        description="Automated single vs multi-agent comparison experiments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run to see what would be executed
  python run_comparison_experiment.py --dry-run

  # Run all experiments
  python run_comparison_experiment.py

  # Run specific projects only
  python run_comparison_experiment.py --projects 01_simple_calculator \\
    04_medium_ecommerce

  # Run without final analysis (useful for testing)
  python run_comparison_experiment.py --skip-analysis

  # PARALLEL MODE: Run experiments in parallel (requires multiple Marcus instances)
  python run_comparison_experiment.py --parallel --max-parallel 3

  # Parallel with custom instance configuration
  python run_comparison_experiment.py --parallel \\
    --marcus-instances instances.json

Experiment Structure:
  Each project should have multiple config files:
    - config_single_agent.yaml (baseline)
    - config_multi_agent.yaml (multi-agent)
    - config_multi_agent_4.yaml (4 agents)
    - config_multi_agent_8.yaml (8 agents)
    etc.

Results will be saved to ./results/ by default.
        """,
    )

    parser.add_argument(
        "--test-projects-dir",
        type=Path,
        default=Path(__file__).parent / "test_projects",
        help="Directory containing test projects",
    )

    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path(__file__).parent / "results",
        help="Directory to store results",
    )

    parser.add_argument(
        "--projects",
        nargs="+",
        help="Specific projects to run (by directory name)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without running",
    )

    parser.add_argument(
        "--skip-analysis",
        action="store_true",
        help="Skip final analysis and visualization",
    )

    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run experiments in parallel across multiple Marcus instances",
    )

    parser.add_argument(
        "--max-parallel",
        type=int,
        default=3,
        help="Maximum number of parallel experiments (default: 3)",
    )

    parser.add_argument(
        "--marcus-instances",
        type=str,
        help="JSON file with Marcus instance configurations (url, board_id)",
    )

    args = parser.parse_args()

    # Load Marcus instances if provided
    marcus_instances = None
    if args.marcus_instances:
        import json

        with open(args.marcus_instances, "r") as f:
            marcus_instances = json.load(f)

    # Validate paths
    if not args.test_projects_dir.exists():
        print(f"Error: Test projects directory not found: {args.test_projects_dir}")
        sys.exit(1)

    # Warn about parallel mode requirements
    if args.parallel:
        print("\n⚠️  PARALLEL MODE ENABLED")
        print("=" * 80)
        print("Requirements for parallel execution:")
        print("  1. Multiple Marcus instances running on different ports")
        print("  2. Each instance connected to a separate Planka board")
        print("  3. Sufficient system resources (CPU, memory)")
        print()
        if not marcus_instances:
            print("Using default configuration:")
            for i in range(args.max_parallel):
                print(f"  - Instance {i+1}: http://localhost:{4298+i} (board_{i})")
        print("=" * 80)
        print()

        response = input("Continue with parallel mode? (y/n): ")
        if response.lower() != "y":
            print("Exiting...")
            sys.exit(0)

    # Create runner
    runner = ExperimentRunner(
        base_dir=args.test_projects_dir,
        results_dir=args.results_dir,
        parallel=args.parallel,
        max_parallel=args.max_parallel,
        marcus_instances=marcus_instances,
    )

    # Run experiments
    results = runner.run_all_projects(
        project_filter=args.projects,
        dry_run=args.dry_run,
        skip_analysis=args.skip_analysis,
    )

    # Print final summary
    if not args.dry_run and "error" not in results:
        print(f"\n\n{'=' * 80}")
        print("EXPERIMENT BATCH COMPLETE")
        print(f"{'=' * 80}")
        print(f"Results saved to: {args.results_dir}")
        print("\nTo view analysis:")
        print(f"  1. Check: {args.results_dir}/comparison_report.json")
        print(f"  2. View plots: {args.results_dir}/plots/")
        print("\nTo re-run analysis:")
        print(f"  python {runner.analysis_script}")
        print(f"  python {runner.visualization_script}")


if __name__ == "__main__":
    main()
