#!/usr/bin/env python3
"""
Visualization Script for Marcus Experiment Results.

Generate charts and plots comparing single-agent vs multi-agent performance.
"""

import argparse
from pathlib import Path
from typing import List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from compare_experiments import ExperimentAnalyzer, ExperimentRun
from matplotlib.figure import Figure

# Set style
sns.set_theme(style="whitegrid")
plt.rcParams["figure.figsize"] = (12, 8)


class ExperimentVisualizer:
    """Create visualizations for experiment results."""

    def __init__(self, analyzer: ExperimentAnalyzer):
        """
        Initialize visualizer.

        Parameters
        ----------
        analyzer : ExperimentAnalyzer
            Experiment analyzer instance
        """
        self.analyzer = analyzer

    def plot_speedup_vs_agents(
        self,
        runs: List[ExperimentRun],
        output_file: str = "speedup_vs_agents.png",
    ) -> Figure:
        """
        Plot speedup factor vs number of agents.

        Parameters
        ----------
        runs : List[ExperimentRun]
            Experiment runs
        output_file : str
            Output file path

        Returns
        -------
        Figure
            Matplotlib figure
        """
        df = self.analyzer.to_dataframe(runs)

        # Calculate speedup for each run
        speedups = []
        for complexity in df["complexity"].unique():
            complexity_df = df[df["complexity"] == complexity]
            single_agent_time = complexity_df[complexity_df["num_agents"] == 1][
                "duration_hours"
            ].mean()

            if pd.isna(single_agent_time) or single_agent_time == 0:
                continue

            for _, row in complexity_df.iterrows():
                if row["num_agents"] > 1:
                    speedup = single_agent_time / row["duration_hours"]
                    speedups.append(
                        {
                            "num_agents": row["num_agents"],
                            "speedup": speedup,
                            "complexity": complexity,
                            "efficiency": speedup / row["num_agents"],
                        }
                    )

        speedup_df = pd.DataFrame(speedups)

        # Create plot
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

        # Plot 1: Speedup vs Agents
        for complexity in speedup_df["complexity"].unique():
            subset = speedup_df[speedup_df["complexity"] == complexity]
            ax1.plot(
                subset["num_agents"],
                subset["speedup"],
                marker="o",
                linewidth=2,
                markersize=8,
                label=complexity.capitalize(),
            )

        # Add ideal speedup line
        max_agents = speedup_df["num_agents"].max()
        ax1.plot(
            range(2, int(max_agents) + 1),
            range(2, int(max_agents) + 1),
            "--",
            color="gray",
            alpha=0.5,
            label="Ideal (linear)",
        )

        ax1.set_xlabel("Number of Agents", fontsize=12)
        ax1.set_ylabel("Speedup Factor", fontsize=12)
        ax1.set_title("Speedup vs Number of Agents", fontsize=14, fontweight="bold")
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Plot 2: Efficiency vs Agents
        for complexity in speedup_df["complexity"].unique():
            subset = speedup_df[speedup_df["complexity"] == complexity]
            ax2.plot(
                subset["num_agents"],
                subset["efficiency"] * 100,
                marker="s",
                linewidth=2,
                markersize=8,
                label=complexity.capitalize(),
            )

        ax2.axhline(y=100, linestyle="--", color="gray", alpha=0.5, label="100%")
        ax2.set_xlabel("Number of Agents", fontsize=12)
        ax2.set_ylabel("Parallel Efficiency (%)", fontsize=12)
        ax2.set_title(
            "Parallel Efficiency vs Number of Agents", fontsize=14, fontweight="bold"
        )
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        print(f"Saved: {output_file}")

        return fig

    def plot_task_completion_time(
        self,
        runs: List[ExperimentRun],
        output_file: str = "completion_time.png",
    ) -> Figure:
        """
        Plot task completion time comparison.

        Parameters
        ----------
        runs : List[ExperimentRun]
            Experiment runs
        output_file : str
            Output file path

        Returns
        -------
        Figure
            Matplotlib figure
        """
        df = self.analyzer.to_dataframe(runs)

        fig, ax = plt.subplots(figsize=(14, 8))

        # Group by complexity and agent count
        grouped = (
            df.groupby(["complexity", "num_agents"])["duration_hours"]
            .agg(["mean", "std"])
            .reset_index()
        )

        # Plot grouped bar chart
        complexities = grouped["complexity"].unique()
        x = np.arange(len(complexities))
        width = 0.15

        agent_counts = sorted(grouped["num_agents"].unique())
        colors = sns.color_palette("husl", len(agent_counts))

        for i, agent_count in enumerate(agent_counts):
            subset = grouped[grouped["num_agents"] == agent_count]
            means = [
                (
                    subset[subset["complexity"] == c]["mean"].values[0]
                    if len(subset[subset["complexity"] == c]) > 0
                    else 0
                )
                for c in complexities
            ]
            stds = [
                (
                    subset[subset["complexity"] == c]["std"].values[0]
                    if len(subset[subset["complexity"] == c]) > 0
                    else 0
                )
                for c in complexities
            ]

            ax.bar(
                x + i * width,
                means,
                width,
                yerr=stds,
                label=f"{agent_count} agent{'s' if agent_count > 1 else ''}",
                color=colors[i],
                capsize=5,
            )

        ax.set_xlabel("Complexity Level", fontsize=12)
        ax.set_ylabel("Completion Time (hours)", fontsize=12)
        ax.set_title(
            "Project Completion Time by Complexity and Agent Count",
            fontsize=14,
            fontweight="bold",
        )
        ax.set_xticks(x + width * (len(agent_counts) - 1) / 2)
        ax.set_xticklabels([c.capitalize() for c in complexities])
        ax.legend()
        ax.grid(True, alpha=0.3, axis="y")

        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        print(f"Saved: {output_file}")

        return fig

    def plot_coordination_overhead(
        self,
        runs: List[ExperimentRun],
        output_file: str = "coordination_overhead.png",
    ) -> Figure:
        """
        Plot coordination overhead metrics.

        Parameters
        ----------
        runs : List[ExperimentRun]
            Experiment runs
        output_file : str
            Output file path

        Returns
        -------
        Figure
            Matplotlib figure
        """
        df = self.analyzer.to_dataframe(runs)
        multi_agent_df = df[df["num_agents"] > 1]

        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

        # Plot 1: Context Requests vs Agents
        for complexity in multi_agent_df["complexity"].unique():
            subset = multi_agent_df[multi_agent_df["complexity"] == complexity]
            if "total_context_requests" in subset.columns:
                ax1.scatter(
                    subset["num_agents"],
                    subset["total_context_requests"],
                    label=complexity.capitalize(),
                    s=100,
                    alpha=0.6,
                )

        ax1.set_xlabel("Number of Agents")
        ax1.set_ylabel("Context Requests")
        ax1.set_title("Context Requests vs Agent Count")
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Plot 2: Blockers vs Agents
        for complexity in multi_agent_df["complexity"].unique():
            subset = multi_agent_df[multi_agent_df["complexity"] == complexity]
            if "total_blockers" in subset.columns:
                ax2.scatter(
                    subset["num_agents"],
                    subset["total_blockers"],
                    label=complexity.capitalize(),
                    s=100,
                    alpha=0.6,
                )

        ax2.set_xlabel("Number of Agents")
        ax2.set_ylabel("Blockers")
        ax2.set_title("Blockers vs Agent Count")
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # Plot 3: Artifacts vs Agents
        for complexity in multi_agent_df["complexity"].unique():
            subset = multi_agent_df[multi_agent_df["complexity"] == complexity]
            if "total_artifacts" in subset.columns:
                ax3.scatter(
                    subset["num_agents"],
                    subset["total_artifacts"],
                    label=complexity.capitalize(),
                    s=100,
                    alpha=0.6,
                )

        ax3.set_xlabel("Number of Agents")
        ax3.set_ylabel("Artifacts Created")
        ax3.set_title("Artifacts vs Agent Count")
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        # Plot 4: Decisions vs Agents
        for complexity in multi_agent_df["complexity"].unique():
            subset = multi_agent_df[multi_agent_df["complexity"] == complexity]
            if "total_decisions" in subset.columns:
                ax4.scatter(
                    subset["num_agents"],
                    subset["total_decisions"],
                    label=complexity.capitalize(),
                    s=100,
                    alpha=0.6,
                )

        ax4.set_xlabel("Number of Agents")
        ax4.set_ylabel("Decisions Logged")
        ax4.set_title("Decisions vs Agent Count")
        ax4.legend()
        ax4.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        print(f"Saved: {output_file}")

        return fig

    def plot_cost_efficiency(
        self,
        runs: List[ExperimentRun],
        output_file: str = "cost_efficiency.png",
    ) -> Figure:
        """
        Plot cost efficiency metrics.

        Parameters
        ----------
        runs : List[ExperimentRun]
            Experiment runs
        output_file : str
            Output file path

        Returns
        -------
        Figure
            Matplotlib figure
        """
        df = self.analyzer.to_dataframe(runs)

        # Check if cost metrics exist
        if "total_tokens" not in df.columns or "api_cost_usd" not in df.columns:
            print("Cost metrics not available in runs")
            return None

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

        # Plot 1: Total Cost vs Agents
        for complexity in df["complexity"].unique():
            subset = df[df["complexity"] == complexity]
            ax1.plot(
                subset["num_agents"],
                subset["api_cost_usd"],
                marker="o",
                linewidth=2,
                markersize=8,
                label=complexity.capitalize(),
            )

        ax1.set_xlabel("Number of Agents")
        ax1.set_ylabel("Total Cost (USD)")
        ax1.set_title("Total API Cost vs Agent Count")
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Plot 2: Cost per Hour vs Agents
        df["cost_per_hour"] = df["api_cost_usd"] / df["duration_hours"]
        for complexity in df["complexity"].unique():
            subset = df[df["complexity"] == complexity]
            ax2.plot(
                subset["num_agents"],
                subset["cost_per_hour"],
                marker="s",
                linewidth=2,
                markersize=8,
                label=complexity.capitalize(),
            )

        ax2.set_xlabel("Number of Agents")
        ax2.set_ylabel("Cost per Hour (USD)")
        ax2.set_title("Cost Efficiency (Cost/Hour)")
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        print(f"Saved: {output_file}")

        return fig

    def generate_all_plots(
        self, runs: List[ExperimentRun], output_dir: str = "./plots"
    ) -> None:
        """
        Generate all visualization plots.

        Parameters
        ----------
        runs : List[ExperimentRun]
            Experiment runs
        output_dir : str
            Directory to save plots
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True, parents=True)

        print(f"Generating plots in {output_dir}...")

        self.plot_speedup_vs_agents(runs, str(output_path / "speedup_vs_agents.png"))
        self.plot_task_completion_time(runs, str(output_path / "completion_time.png"))
        self.plot_coordination_overhead(
            runs, str(output_path / "coordination_overhead.png")
        )
        self.plot_cost_efficiency(runs, str(output_path / "cost_efficiency.png"))

        print(f"\nAll plots saved to {output_dir}/")


def main() -> None:
    """Run the visualization script."""
    parser = argparse.ArgumentParser(description="Visualize Marcus experiment results")

    parser.add_argument(
        "--tracking-uri",
        type=str,
        default="./mlruns",
        help="MLflow tracking URI",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="./plots",
        help="Directory to save plots",
    )

    parser.add_argument(
        "--experiments",
        type=str,
        nargs="+",
        help="Specific experiments to visualize",
    )

    args = parser.parse_args()

    # Initialize analyzer
    analyzer = ExperimentAnalyzer(tracking_uri=args.tracking_uri)
    visualizer = ExperimentVisualizer(analyzer)

    # Load runs
    print("Loading experiment runs...")
    runs = analyzer.load_runs(experiment_names=args.experiments)
    print(f"Loaded {len(runs)} runs")

    if not runs:
        print("No runs found!")
        return

    # Generate all plots
    visualizer.generate_all_plots(runs, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
