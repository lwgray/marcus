#!/usr/bin/env python3
"""
False Positive Recovery Monitoring Script.

This script monitors the assignment lease system for false positive recoveries
where a task is recovered from an agent that is still working on it.

Usage:
    python scripts/monitor_false_positives.py [--days 14] [--output report.json]

The script analyzes conversation logs to:
1. Identify lease recovery events
2. Detect false positives (agent still active after recovery)
3. Calculate false positive rate
4. Provide recommendations for timeout tuning
"""

import argparse
import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FalsePositiveMonitor:
    """Monitor false positive recovery events."""

    def __init__(self, logs_dir: Path, lookback_days: int = 14):
        """
        Initialize the false positive monitor.

        Parameters
        ----------
        logs_dir : Path
            Path to conversation logs directory
        lookback_days : int
            Number of days to analyze (default: 14)
        """
        self.logs_dir = logs_dir
        self.lookback_days = lookback_days
        self.cutoff_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)

        # Tracking data
        self.recovery_events: List[Dict[str, Any]] = []
        self.false_positives: List[Dict[str, Any]] = []
        self.progress_updates: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    def analyze_logs(self) -> Dict[str, Any]:
        """
        Analyze conversation logs for recovery events.

        Returns
        -------
        Dict[str, Any]
            Analysis results including FP rate and recommendations
        """
        logger.info(f"Analyzing logs in {self.logs_dir}")
        logger.info(f"Looking back {self.lookback_days} days from {self.cutoff_date}")

        # Scan all conversation logs
        log_files = list(self.logs_dir.glob("*.jsonl"))
        logger.info(f"Found {len(log_files)} conversation log files")

        for log_file in log_files:
            self._process_log_file(log_file)

        # Identify false positives
        self._identify_false_positives()

        # Calculate metrics
        return self._calculate_metrics()

    def _process_log_file(self, log_file: Path) -> None:
        """Process a single conversation log file."""
        try:
            with open(log_file, "r") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        self._process_log_entry(entry, log_file.name)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.warning(f"Error processing {log_file}: {e}")

    def _process_log_entry(self, entry: Dict[str, Any], log_filename: str) -> None:
        """Process a single log entry."""
        timestamp_str = entry.get("timestamp")
        if not timestamp_str:
            return

        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return

        # Skip entries before cutoff
        if timestamp < self.cutoff_date:
            return

        content = entry.get("content", "")

        # Look for recovery events
        if "recovering task" in content.lower() or "lease_recovered" in content.lower():
            self._extract_recovery_event(entry, timestamp, log_filename)

        # Look for progress updates
        if "progress" in content.lower() and "%" in content:
            self._extract_progress_update(entry, timestamp, log_filename)

    def _extract_recovery_event(
        self, entry: Dict[str, Any], timestamp: datetime, log_filename: str
    ) -> None:
        """Extract recovery event details from log entry."""
        content = entry.get("content", "")

        # Try to extract task_id and agent_id from content
        # Example: "Recovering task task-123 from agent agent-456"
        task_id = None
        agent_id = None

        if "task" in content:
            # Simple pattern matching - adjust based on actual log format
            parts = content.split()
            for i, part in enumerate(parts):
                if part.lower() == "task" and i + 1 < len(parts):
                    task_id = parts[i + 1].strip(",:;")
                if part.lower() == "agent" and i + 1 < len(parts):
                    agent_id = parts[i + 1].strip(",:;")

        self.recovery_events.append(
            {
                "timestamp": timestamp.isoformat(),
                "task_id": task_id,
                "agent_id": agent_id,
                "log_file": log_filename,
                "content": content,
            }
        )

    def _extract_progress_update(
        self, entry: Dict[str, Any], timestamp: datetime, log_filename: str
    ) -> None:
        """Extract progress update details from log entry."""
        content = entry.get("content", "")

        # Extract agent_id and task_id if present
        agent_id = entry.get("agent_id")
        task_id = entry.get("task_id")

        # Try to extract from content if not in structured fields
        if not agent_id or not task_id:
            # Pattern matching based on actual log format
            parts = content.split()
            for i, part in enumerate(parts):
                if "agent" in part.lower() and i + 1 < len(parts):
                    agent_id = parts[i + 1].strip(",:;")
                if "task" in part.lower() and i + 1 < len(parts):
                    task_id = parts[i + 1].strip(",:;")

        if agent_id:
            self.progress_updates[agent_id].append(
                {
                    "timestamp": timestamp.isoformat(),
                    "task_id": task_id,
                    "log_file": log_filename,
                    "content": content,
                }
            )

    def _identify_false_positives(self) -> None:
        """Identify false positive recoveries."""
        logger.info(f"Analyzing {len(self.recovery_events)} recovery events")

        for recovery in self.recovery_events:
            recovery_time = datetime.fromisoformat(recovery["timestamp"])
            agent_id = recovery["agent_id"]

            if not agent_id:
                continue

            # Check if agent reported progress within 5 minutes after recovery
            # This indicates the agent was still working (false positive)
            false_positive_window = timedelta(minutes=5)

            agent_updates = self.progress_updates.get(agent_id, [])
            for update in agent_updates:
                update_time = datetime.fromisoformat(update["timestamp"])

                # Check if update came after recovery but within window
                if recovery_time < update_time < recovery_time + false_positive_window:
                    self.false_positives.append(
                        {
                            "recovery": recovery,
                            "subsequent_update": update,
                            "time_delta": (update_time - recovery_time).total_seconds(),
                        }
                    )
                    time_delta_sec = (update_time - recovery_time).total_seconds()
                    logger.info(
                        f"False positive detected: Task {recovery['task_id']} "
                        f"recovered at {recovery_time}, but agent {agent_id} "
                        f"reported progress {time_delta_sec:.0f}s later"
                    )
                    break

    def _calculate_metrics(self) -> Dict[str, Any]:
        """
        Calculate false positive metrics.

        Returns
        -------
        Dict[str, Any]
            Metrics and recommendations
        """
        total_recoveries = len(self.recovery_events)
        false_positives = len(self.false_positives)

        if total_recoveries == 0:
            fp_rate = 0.0
        else:
            fp_rate = (false_positives / total_recoveries) * 100

        # Calculate recommendation
        recommendation = self._generate_recommendation(fp_rate)

        metrics = {
            "analysis_period": {
                "start_date": self.cutoff_date.isoformat(),
                "end_date": datetime.now(timezone.utc).isoformat(),
                "days": self.lookback_days,
            },
            "summary": {
                "total_recoveries": total_recoveries,
                "false_positives": false_positives,
                "true_positives": total_recoveries - false_positives,
                "false_positive_rate": round(fp_rate, 2),
            },
            "false_positive_details": self.false_positives,
            "recommendation": recommendation,
        }

        return metrics

    def _generate_recommendation(self, fp_rate: float) -> Dict[str, Any]:
        """
        Generate tuning recommendations based on FP rate.

        Parameters
        ----------
        fp_rate : float
            False positive rate percentage

        Returns
        -------
        Dict[str, Any]
            Recommendation details
        """
        if fp_rate < 3:
            action = "MAINTAIN"
            message = (
                f"False positive rate is excellent ({fp_rate:.1f}%). "
                "Current aggressive timeouts are working well. "
                "Continue monitoring but no changes needed."
            )
            suggested_timeout = "Keep current: 90s (aggressive)"

        elif fp_rate < 5:
            action = "MONITOR"
            message = (
                f"False positive rate is acceptable ({fp_rate:.1f}%). "
                "Continue monitoring for another week. "
                "Consider slightly increasing if rate trends upward."
            )
            suggested_timeout = "Keep current: 90s, consider 100s if rate increases"

        elif fp_rate < 10:
            action = "TUNE_MODERATE"
            message = (
                f"False positive rate is moderate ({fp_rate:.1f}%). "
                "Consider increasing initial timeout to reduce false positives. "
                "Trade-off: slightly slower recovery (10-20s)."
            )
            suggested_timeout = "Increase to 100-110s (from 90s)"

        else:
            action = "TUNE_AGGRESSIVE"
            message = (
                f"False positive rate is high ({fp_rate:.1f}%). "
                "Strongly recommend increasing timeouts. "
                "Current settings are too aggressive for your workload."
            )
            suggested_timeout = "Increase to 120s (conservative)"

        return {
            "action": action,
            "message": message,
            "suggested_timeout": suggested_timeout,
            "current_timeout": "90s (aggressive)",
        }


def main() -> int:
    """Run false positive monitoring and generate report."""
    parser = argparse.ArgumentParser(
        description="Monitor false positive recovery events"
    )
    parser.add_argument(
        "--logs-dir",
        type=Path,
        default=Path("logs/conversations"),
        help="Path to conversation logs directory (default: logs/conversations)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=14,
        help="Number of days to analyze (default: 14)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file for JSON report (optional)",
    )

    args = parser.parse_args()

    # Verify logs directory exists
    if not args.logs_dir.exists():
        logger.error(f"Logs directory not found: {args.logs_dir}")
        return 1

    # Run analysis
    monitor = FalsePositiveMonitor(args.logs_dir, args.days)
    results = monitor.analyze_logs()

    # Print summary
    print("\n" + "=" * 70)
    print("FALSE POSITIVE RECOVERY ANALYSIS")
    print("=" * 70)
    print(f"\nAnalysis Period: {results['analysis_period']['days']} days")
    print(f"Start: {results['analysis_period']['start_date']}")
    print(f"End: {results['analysis_period']['end_date']}")

    print("\n" + "-" * 70)
    print("SUMMARY")
    print("-" * 70)
    summary = results["summary"]
    print(f"Total Recoveries: {summary['total_recoveries']}")
    print(f"False Positives: {summary['false_positives']}")
    print(f"True Positives: {summary['true_positives']}")
    fp_rate = summary["false_positive_rate"]
    if fp_rate < 5:
        status = "🟢 Excellent"
    elif fp_rate < 10:
        status = "🟡 Moderate"
    else:
        status = "🔴 High"
    print(f"False Positive Rate: {fp_rate:.2f}% ({status})")

    print("\n" + "-" * 70)
    print("RECOMMENDATION")
    print("-" * 70)
    rec = results["recommendation"]
    print(f"Action: {rec['action']}")
    print(f"Current Timeout: {rec['current_timeout']}")
    print(f"Suggested: {rec['suggested_timeout']}")
    print(f"\n{rec['message']}")

    if results["false_positive_details"]:
        print("\n" + "-" * 70)
        print("FALSE POSITIVE DETAILS")
        print("-" * 70)
        for i, fp in enumerate(results["false_positive_details"][:5], 1):
            print(f"\n{i}. Task: {fp['recovery']['task_id']}")
            print(f"   Agent: {fp['recovery']['agent_id']}")
            print(f"   Recovered at: {fp['recovery']['timestamp']}")
            print(f"   Agent responded {fp['time_delta']:.0f}s later")

        if len(results["false_positive_details"]) > 5:
            print(f"\n... and {len(results['false_positive_details']) - 5} more")

    print("\n" + "=" * 70)

    # Save to file if requested
    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        logger.info(f"Full report saved to {args.output}")

    return 0


if __name__ == "__main__":
    exit(main())
