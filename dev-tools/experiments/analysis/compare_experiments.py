#!/usr/bin/env python3
"""
Experiment Comparison and Analysis Script.

Compare MLflow experiment runs to analyze single-agent vs multi-agent performance,
test hypotheses, and generate statistical reports.
"""

import argparse
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import mlflow
import numpy as np
import pandas as pd
from mlflow.tracking import MlflowClient
from scipy import stats


@dataclass
class ExperimentRun:
    """Data class for experiment run information."""

    run_id: str
    run_name: str
    experiment_name: str
    params: Dict[str, Any]
    metrics: Dict[str, float]
    start_time: int
    end_time: int
    duration_hours: float
    num_agents: int
    complexity: str


class ExperimentAnalyzer:
    """
    Analyze and compare Marcus experiment runs.

    Provides statistical analysis, hypothesis testing, and visualization
    of single-agent vs multi-agent performance.
    """

    def __init__(self, tracking_uri: str = "./mlruns"):
        """
        Initialize the experiment analyzer.

        Parameters
        ----------
        tracking_uri : str
            MLflow tracking URI
        """
        self.tracking_uri = tracking_uri
        mlflow.set_tracking_uri(tracking_uri)
        self.client = MlflowClient()

    def load_runs(
        self, experiment_names: Optional[List[str]] = None
    ) -> List[ExperimentRun]:
        """
        Load experiment runs from MLflow.

        Parameters
        ----------
        experiment_names : List[str], optional
            List of experiment names to load. If None, loads all experiments.

        Returns
        -------
        List[ExperimentRun]
            List of experiment run objects
        """
        runs = []

        if experiment_names is None:
            # Get all experiments
            experiments = self.client.search_experiments()
        else:
            experiments = [
                self.client.get_experiment_by_name(name) for name in experiment_names
            ]
            experiments = [e for e in experiments if e is not None]

        for experiment in experiments:
            mlflow_runs = self.client.search_runs(experiment.experiment_id)

            for run in mlflow_runs:
                # Extract duration
                duration_ms = run.info.end_time - run.info.start_time
                duration_hours = duration_ms / (1000 * 60 * 60)

                # Extract num_agents from params
                num_agents = int(run.data.params.get("num_agents", 1))
                complexity = run.data.params.get("complexity", "unknown")

                runs.append(
                    ExperimentRun(
                        run_id=run.info.run_id,
                        run_name=run.info.run_name or run.info.run_id[:8],
                        experiment_name=experiment.name,
                        params=run.data.params,
                        metrics=run.data.metrics,
                        start_time=run.info.start_time,
                        end_time=run.info.end_time,
                        duration_hours=duration_hours,
                        num_agents=num_agents,
                        complexity=complexity,
                    )
                )

        return runs

    def to_dataframe(self, runs: List[ExperimentRun]) -> pd.DataFrame:
        """
        Convert experiment runs to pandas DataFrame.

        Parameters
        ----------
        runs : List[ExperimentRun]
            List of experiment runs

        Returns
        -------
        pd.DataFrame
            DataFrame with run data
        """
        data = []
        for run in runs:
            row = {
                "run_id": run.run_id,
                "run_name": run.run_name,
                "experiment_name": run.experiment_name,
                "num_agents": run.num_agents,
                "complexity": run.complexity,
                "duration_hours": run.duration_hours,
                **run.metrics,
            }
            data.append(row)

        return pd.DataFrame(data)

    def compare_single_vs_multi(
        self, runs: List[ExperimentRun], project_name: str
    ) -> Dict[str, Any]:
        """
        Compare single-agent vs multi-agent performance for a project.

        Parameters
        ----------
        runs : List[ExperimentRun]
            List of experiment runs
        project_name : str
            Name of project to compare (e.g., "Calculator API")

        Returns
        -------
        Dict[str, Any]
            Comparison results with statistical analysis
        """
        # Filter runs for this project
        project_runs = [
            r for r in runs if project_name.lower() in r.experiment_name.lower()
        ]

        if not project_runs:
            return {"error": f"No runs found for project: {project_name}"}

        # Group by agent count
        single_agent = [r for r in project_runs if r.num_agents == 1]
        multi_agent = [r for r in project_runs if r.num_agents > 1]

        if not single_agent or not multi_agent:
            return {
                "error": "Need both single and multi-agent runs for comparison",
                "single_count": len(single_agent),
                "multi_count": len(multi_agent),
            }

        # Calculate speedup factors
        single_times = [r.duration_hours for r in single_agent]
        multi_times = [r.duration_hours for r in multi_agent]

        avg_single = np.mean(single_times)
        avg_multi = np.mean(multi_times)
        speedup = avg_single / avg_multi if avg_multi > 0 else 0

        # Statistical significance test (t-test)
        t_stat, p_value = stats.ttest_ind(single_times, multi_times)

        # Calculate efficiency
        avg_agents = np.mean([r.num_agents for r in multi_agent])
        efficiency = speedup / avg_agents if avg_agents > 0 else 0

        return {
            "project": project_name,
            "single_agent": {
                "count": len(single_agent),
                "avg_time_hours": avg_single,
                "std_time_hours": np.std(single_times),
                "min_time_hours": np.min(single_times),
                "max_time_hours": np.max(single_times),
            },
            "multi_agent": {
                "count": len(multi_agent),
                "avg_agents": avg_agents,
                "avg_time_hours": avg_multi,
                "std_time_hours": np.std(multi_times),
                "min_time_hours": np.min(multi_times),
                "max_time_hours": np.max(multi_times),
            },
            "comparison": {
                "speedup_factor": speedup,
                "parallel_efficiency": efficiency,
                "time_saved_hours": avg_single - avg_multi,
                "time_saved_percent": (
                    ((avg_single - avg_multi) / avg_single * 100)
                    if avg_single > 0
                    else 0
                ),
            },
            "statistics": {
                "t_statistic": t_stat,
                "p_value": p_value,
                "significant": p_value < 0.05,
                "conclusion": (
                    "Statistically significant difference"
                    if p_value < 0.05
                    else "No significant difference"
                ),
            },
        }

    def analyze_coordination_overhead(
        self, runs: List[ExperimentRun]
    ) -> Dict[str, Any]:
        """
        Analyze coordination overhead in multi-agent systems.

        Parameters
        ----------
        runs : List[ExperimentRun]
            List of experiment runs

        Returns
        -------
        Dict[str, Any]
            Coordination overhead analysis
        """
        multi_agent_runs = [r for r in runs if r.num_agents > 1]

        if not multi_agent_runs:
            return {"error": "No multi-agent runs found"}

        overhead_data = []
        for run in multi_agent_runs:
            overhead_data.append(
                {
                    "num_agents": run.num_agents,
                    "context_requests": run.metrics.get("total_context_requests", 0),
                    "blockers": run.metrics.get("total_blockers", 0),
                    "decisions": run.metrics.get("total_decisions", 0),
                    "artifacts": run.metrics.get("total_artifacts", 0),
                }
            )

        df = pd.DataFrame(overhead_data)

        # Analyze correlation between agents and overhead
        correlations = {}
        for col in ["context_requests", "blockers", "decisions", "artifacts"]:
            if col in df.columns:
                corr, p_val = stats.pearsonr(df["num_agents"], df[col])
                correlations[col] = {"correlation": corr, "p_value": p_val}

        return {
            "total_runs": len(multi_agent_runs),
            "avg_overhead_per_agent_count": df.groupby("num_agents").mean().to_dict(),
            "correlations_with_agent_count": correlations,
            "summary": {
                "avg_context_requests": df["context_requests"].mean(),
                "avg_blockers": df["blockers"].mean(),
                "avg_decisions": df["decisions"].mean(),
                "avg_artifacts": df["artifacts"].mean(),
            },
        }

    def test_hypothesis_throughput(
        self, runs: List[ExperimentRun], complexity_level: str
    ) -> Dict[str, Any]:
        """
        Test H1: Throughput & Parallelization hypothesis.

        Parameters
        ----------
        runs : List[ExperimentRun]
            List of experiment runs
        complexity_level : str
            Complexity level to test (prototype, standard, enterprise)

        Returns
        -------
        Dict[str, Any]
            Hypothesis test results
        """
        # Filter by complexity
        filtered_runs = [r for r in runs if r.complexity == complexity_level]

        if not filtered_runs:
            return {"error": f"No runs found for complexity: {complexity_level}"}

        # Group by agent count
        by_agent_count: Dict[int, List[float]] = {}
        for run in filtered_runs:
            count = run.num_agents
            if count not in by_agent_count:
                by_agent_count[count] = []
            by_agent_count[count].append(run.duration_hours)

        # Calculate speedup for each configuration
        if 1 not in by_agent_count:
            return {"error": "No single-agent baseline found"}

        baseline = np.mean(by_agent_count[1])
        speedups = {}
        efficiencies = {}

        for count, times in by_agent_count.items():
            avg_time = np.mean(times)
            speedup = baseline / avg_time if avg_time > 0 else 0
            efficiency = speedup / count if count > 0 else 0
            speedups[count] = speedup
            efficiencies[count] = efficiency

        return {
            "complexity": complexity_level,
            "baseline_single_agent_hours": baseline,
            "speedups_by_agent_count": speedups,
            "efficiencies_by_agent_count": efficiencies,
            "hypothesis_test": {
                "H1": "Multi-agent faster than single for parallelizable tasks",
                "result": "SUPPORTED" if max(speedups.values()) > 1.5 else "REJECTED",
                "max_speedup": max(speedups.values()),
                "optimal_agent_count": max(speedups.keys(), key=lambda k: speedups[k]),
            },
        }

    def generate_report(
        self, runs: List[ExperimentRun], output_file: str = "experiment_report.json"
    ) -> None:
        """
        Generate comprehensive experiment report.

        Parameters
        ----------
        runs : List[ExperimentRun]
            List of experiment runs
        output_file : str
            Path to save the report
        """
        # Extract unique project names
        projects = list(set([r.experiment_name.split(" - ")[0] for r in runs]))

        report = {
            "summary": {
                "total_runs": len(runs),
                "total_projects": len(projects),
                "complexity_levels": list(set([r.complexity for r in runs])),
                "agent_counts": sorted(list(set([r.num_agents for r in runs]))),
            },
            "projects": {},
            "coordination_overhead": self.analyze_coordination_overhead(runs),
            "hypotheses": {},
        }

        # Compare each project
        for project in projects:
            comparison = self.compare_single_vs_multi(runs, project)
            if "error" not in comparison:
                report["projects"][project] = comparison

        # Test hypotheses for each complexity level
        for complexity in ["prototype", "standard", "enterprise"]:
            h1_test = self.test_hypothesis_throughput(runs, complexity)
            if "error" not in h1_test:
                report["hypotheses"][f"H1_{complexity}"] = h1_test

        # Save report
        with open(output_file, "w") as f:
            json.dump(report, f, indent=2)

        print(f"Report generated: {output_file}")

    def print_summary(self, runs: List[ExperimentRun]) -> None:
        """
        Print a summary of experiment results.

        Parameters
        ----------
        runs : List[ExperimentRun]
            List of experiment runs
        """
        df = self.to_dataframe(runs)

        print("\n" + "=" * 80)
        print("EXPERIMENT SUMMARY")
        print("=" * 80)
        print(f"\nTotal Runs: {len(runs)}")
        print(f"Complexity Levels: {df['complexity'].unique().tolist()}")
        print(f"Agent Counts: {sorted(df['num_agents'].unique().tolist())}")

        print("\n" + "-" * 80)
        print("PERFORMANCE BY AGENT COUNT")
        print("-" * 80)
        summary = df.groupby("num_agents")["duration_hours"].agg(
            ["count", "mean", "std", "min", "max"]
        )
        print(summary)

        print("\n" + "-" * 80)
        print("SPEEDUP ANALYSIS")
        print("-" * 80)

        # Calculate speedup for each complexity level
        for complexity in df["complexity"].unique():
            complexity_df = df[df["complexity"] == complexity]
            single_agent = complexity_df[complexity_df["num_agents"] == 1]
            multi_agent = complexity_df[complexity_df["num_agents"] > 1]

            if not single_agent.empty and not multi_agent.empty:
                baseline = single_agent["duration_hours"].mean()
                for agent_count in sorted(multi_agent["num_agents"].unique()):
                    subset = multi_agent[multi_agent["num_agents"] == agent_count]
                    avg_time = subset["duration_hours"].mean()
                    speedup = baseline / avg_time if avg_time > 0 else 0
                    efficiency = speedup / agent_count if agent_count > 0 else 0

                    print(
                        f"{complexity:15} | {agent_count:2} agents | "
                        f"Speedup: {speedup:.2f}x | "
                        f"Efficiency: {efficiency:.2%}"
                    )


def main() -> None:
    """Run the experiment analysis."""
    parser = argparse.ArgumentParser(
        description="Analyze Marcus experiment runs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze all experiments
  python compare_experiments.py

  # Analyze specific experiments
  python compare_experiments.py --experiments "Calculator API" "Blog API"

  # Generate detailed report
  python compare_experiments.py --report experiment_analysis.json

  # Show summary only
  python compare_experiments.py --summary-only
        """,
    )

    parser.add_argument(
        "--tracking-uri",
        type=str,
        default="./mlruns",
        help="MLflow tracking URI (default: ./mlruns)",
    )

    parser.add_argument(
        "--experiments",
        type=str,
        nargs="+",
        help="Specific experiment names to analyze",
    )

    parser.add_argument(
        "--report",
        type=str,
        help="Generate detailed report and save to file",
    )

    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Only print summary, don't generate report",
    )

    args = parser.parse_args()

    # Initialize analyzer
    analyzer = ExperimentAnalyzer(tracking_uri=args.tracking_uri)

    # Load runs
    print("Loading experiment runs...")
    runs = analyzer.load_runs(experiment_names=args.experiments)
    print(f"Loaded {len(runs)} runs")

    if not runs:
        print("No runs found!")
        return

    # Print summary
    analyzer.print_summary(runs)

    # Generate report if requested
    if not args.summary_only:
        report_file = args.report or "experiment_report.json"
        print("\nGenerating detailed report...")
        analyzer.generate_report(runs, output_file=report_file)


if __name__ == "__main__":
    main()
