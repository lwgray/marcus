#!/usr/bin/env python3
"""View Marcus MLflow Experiment Data.

This script retrieves and displays experiment metrics from the
User Management API experiment run.
"""

from datetime import datetime

import mlflow
import pandas as pd
from mlflow.tracking import MlflowClient


def main() -> None:
    """Query and display MLflow experiment data."""
    # Set MLflow tracking URI (local directory)
    mlflow.set_tracking_uri("file:./mlruns")

    client = MlflowClient()

    print("=" * 80)
    print("MARCUS MLFLOW EXPERIMENT DATA")
    print("=" * 80)
    print()

    # List all experiments
    experiments = client.search_experiments()
    print(f"📁 Total Experiments: {len(experiments)}\n")

    for exp in experiments:
        print(f"Experiment: {exp.name}")
        print(f"  ID: {exp.experiment_id}")
        print(f"  Lifecycle: {exp.lifecycle_stage}")
        print()

        # Get runs for this experiment
        runs = client.search_runs(
            experiment_ids=[exp.experiment_id], order_by=["start_time DESC"]
        )

        if runs:
            print(f"  📊 Runs: {len(runs)}")
            for run in runs:
                print(f"\n  Run: {run.info.run_name or run.info.run_id}")
                print(f"    Run ID: {run.info.run_id}")
                print(f"    Status: {run.info.status}")

                # Format timestamps
                start_time = datetime.fromtimestamp(run.info.start_time / 1000)
                end_time = (
                    datetime.fromtimestamp(run.info.end_time / 1000)
                    if run.info.end_time
                    else None
                )

                print(f"    Start Time: {start_time}")
                if end_time:
                    print(f"    End Time: {end_time}")
                    duration = (run.info.end_time - run.info.start_time) / 1000
                    print(f"    Duration: {duration:.2f} seconds")

                # Display metrics
                if run.data.metrics:
                    print("\n    📈 Metrics:")
                    for metric_key, metric_value in sorted(run.data.metrics.items()):
                        print(f"      {metric_key}: {metric_value}")

                # Display parameters
                if run.data.params:
                    print("\n    ⚙️  Parameters:")
                    for param_key, param_value in sorted(run.data.params.items()):
                        print(f"      {param_key}: {param_value}")

                # Display tags
                if run.data.tags:
                    print("\n    🏷️  Tags:")
                    for tag_key, tag_value in sorted(run.data.tags.items()):
                        if not tag_key.startswith("mlflow."):
                            print(f"      {tag_key}: {tag_value}")

                print()
        else:
            print("  No runs found for this experiment\n")

    print("=" * 80)

    # Create summary DataFrame
    print("\n📊 EXPERIMENT SUMMARY (All Runs)\n")

    all_runs = []
    for exp in experiments:
        runs = client.search_runs(
            experiment_ids=[exp.experiment_id], order_by=["start_time DESC"]
        )
        for run in runs:
            run_data = {
                "Experiment": exp.name,
                "Run Name": run.info.run_name or run.info.run_id[:8],
                "Status": run.info.status,
                "Duration (s)": (
                    (run.info.end_time - run.info.start_time) / 1000
                    if run.info.end_time
                    else None
                ),
            }
            # Add metrics
            run_data.update(run.data.metrics)
            all_runs.append(run_data)

    if all_runs:
        df = pd.DataFrame(all_runs)
        pd.set_option("display.max_columns", None)
        pd.set_option("display.width", None)
        print(df.to_string(index=False))
    else:
        print("No runs found.")

    print("\n" + "=" * 80)
    print("💡 TIP: View detailed visualizations at http://localhost:5000")
    print("=" * 80)


if __name__ == "__main__":
    main()
