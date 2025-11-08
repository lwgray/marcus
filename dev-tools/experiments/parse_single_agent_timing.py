#!/usr/bin/env python3
"""
Single-Agent Timing Parser.

Extracts timing checkpoints from single-agent experiment logs and
formats them for MLflow tracking and analysis.
"""

import argparse
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


class TimingParser:
    """Parses timing data from single-agent experiment logs."""

    def __init__(self, log_file: Path):
        """
        Initialize timing parser.

        Parameters
        ----------
        log_file : Path
            Path to experiment log file
        """
        self.log_file = log_file
        self.checkpoints: List[Dict[str, Any]] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    def parse_log(self) -> bool:
        """
        Parse log file for timing checkpoints.

        Returns
        -------
        bool
            True if parsing succeeded, False otherwise
        """
        if not self.log_file.exists():
            print(f"Error: Log file not found: {self.log_file}")
            return False

        with open(self.log_file, "r") as f:
            lines = f.readlines()

        # Skip the first 2000 lines (prompt section with examples)
        # Real timing from Claude appears later in the log
        prompt_skip_lines = min(2000, len(lines) // 2)
        actual_content = "".join(lines[prompt_skip_lines:])

        # Pattern for START timestamp - search in actual content only
        start_pattern = r"START:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})"

        # Find ALL matches and use the LAST one (Claude's real output)
        start_matches = list(re.finditer(start_pattern, actual_content))
        if start_matches:
            last_start = start_matches[-1]
            self.start_time = datetime.strptime(
                last_start.group(1), "%Y-%m-%d %H:%M:%S"
            )

        # Pattern for subtask checkpoints
        # Examples:
        #   SUBTASK 1.1 COMPLETE: 10:18:45 (3:13 elapsed)
        #   TASK 3 COMPLETE: 10:22:10 (6:38 elapsed)
        checkpoint_pattern = (
            r"(SUBTASK|TASK)\s+([\d.]+)\s+COMPLETE:\s+(\d{2}:\d{2}:\d{2})"
            r"(?:\s+\(([^\)]+)\s+elapsed\))?"
        )

        # Parse checkpoints from actual content (skip prompt examples)
        for match in re.finditer(checkpoint_pattern, actual_content, re.MULTILINE):
            checkpoint_type = match.group(1)  # "SUBTASK" or "TASK"
            task_id = match.group(2)  # "1.1" or "3"
            timestamp_str = match.group(3)  # "10:18:45"
            elapsed_str = match.group(4) if match.group(4) else None  # "3:13"

            # Parse timestamp (time only, use start date)
            if self.start_time:
                time_parts = timestamp_str.split(":")
                checkpoint_time = self.start_time.replace(
                    hour=int(time_parts[0]),
                    minute=int(time_parts[1]),
                    second=int(time_parts[2]),
                )

                # Handle day rollover (if checkpoint time is before start time)
                if checkpoint_time < self.start_time:
                    checkpoint_time += timedelta(days=1)
            else:
                # If we don't have start time, we can't determine full timestamp
                checkpoint_time = None

            # Parse elapsed time if provided
            elapsed_seconds = None
            if elapsed_str:
                elapsed_seconds = self._parse_elapsed(elapsed_str)

            self.checkpoints.append(
                {
                    "type": checkpoint_type.lower(),
                    "id": task_id,
                    "timestamp": checkpoint_time,
                    "elapsed_seconds": elapsed_seconds,
                }
            )

        # Pattern for END timestamp (more reliable than PROJECT COMPLETE)
        end_pattern = r"END:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})"
        end_matches = list(re.finditer(end_pattern, actual_content))
        if end_matches:
            last_end = end_matches[-1]
            self.end_time = datetime.strptime(last_end.group(1), "%Y-%m-%d %H:%M:%S")

        # Fallback: Pattern for PROJECT COMPLETE (old format)
        if not self.end_time:
            complete_pattern = r"PROJECT\s+COMPLETE(?::\s+(\d{2}:\d{2}:\d{2}))?"
            complete_matches = list(re.finditer(complete_pattern, actual_content))

            if complete_matches:
                last_complete = complete_matches[-1]
                if last_complete.group(1):
                    timestamp_str = last_complete.group(1)
                    if self.start_time:
                        time_parts = timestamp_str.split(":")
                        self.end_time = self.start_time.replace(
                            hour=int(time_parts[0]),
                            minute=int(time_parts[1]),
                            second=int(time_parts[2]),
                        )
                        if self.end_time < self.start_time:
                            self.end_time += timedelta(days=1)

        # Pattern for TOTAL time
        # Examples:
        #   TOTAL: 31 minutes 46 seconds
        #   TOTAL TIME: 1 hour 15 minutes
        total_pattern = (
            r"TOTAL(?:\s+TIME)?:\s+(?:(\d+)\s+hour[s]?)?\s*"
            r"(?:(\d+)\s+minute[s]?)?\s*(?:(\d+)\s+second[s]?)?"
        )

        # Find ALL matches and use the LAST one (Claude's real output)
        total_matches = list(re.finditer(total_pattern, actual_content, re.IGNORECASE))

        if total_matches:
            last_total = total_matches[-1]
            hours = int(last_total.group(1)) if last_total.group(1) else 0
            minutes = int(last_total.group(2)) if last_total.group(2) else 0
            seconds = int(last_total.group(3)) if last_total.group(3) else 0

            total_seconds = hours * 3600 + minutes * 60 + seconds

            # If we have start time but no end time, calculate it
            if self.start_time and not self.end_time:
                self.end_time = self.start_time + timedelta(seconds=total_seconds)

        return True

    def _parse_elapsed(self, elapsed_str: str) -> int:
        """
        Parse elapsed time string to seconds.

        Parameters
        ----------
        elapsed_str : str
            Elapsed time string (e.g., "3:13", "1:05:30")

        Returns
        -------
        int
            Elapsed time in seconds
        """
        parts = elapsed_str.split(":")

        if len(parts) == 2:
            # MM:SS
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            # HH:MM:SS
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        else:
            return 0

    def get_total_duration(self) -> Optional[int]:
        """
        Get total experiment duration in seconds.

        Returns
        -------
        Optional[int]
            Duration in seconds, or None if not available
        """
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return int(delta.total_seconds())
        return None

    def get_checkpoint_count(self) -> int:
        """
        Get number of checkpoints completed.

        Returns
        -------
        int
            Number of checkpoints
        """
        return len(self.checkpoints)

    def get_subtask_count(self) -> int:
        """
        Get number of subtasks completed.

        Returns
        -------
        int
            Number of subtasks
        """
        return sum(1 for cp in self.checkpoints if cp["type"] == "subtask")

    def get_task_count(self) -> int:
        """
        Get number of full tasks completed.

        Returns
        -------
        int
            Number of tasks
        """
        return sum(1 for cp in self.checkpoints if cp["type"] == "task")

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get all timing metrics for MLflow logging.

        Returns
        -------
        Dict[str, any]
            Dictionary of metrics
        """
        total_duration = self.get_total_duration()
        metrics = {
            "total_duration_seconds": total_duration,
            "total_duration_minutes": (total_duration / 60 if total_duration else None),
            "checkpoints_completed": self.get_checkpoint_count(),
            "subtasks_completed": self.get_subtask_count(),
            "tasks_completed": self.get_task_count(),
        }

        # Add per-checkpoint metrics
        for i, checkpoint in enumerate(self.checkpoints, 1):
            if checkpoint["elapsed_seconds"]:
                key = f"checkpoint_{checkpoint['id']}_duration_seconds"
                metrics[key] = checkpoint["elapsed_seconds"]

        return metrics

    def print_summary(self) -> None:
        """Print a human-readable summary of timing data."""
        print("\n=== Timing Summary ===\n")

        if self.start_time:
            print(f"Start time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        if self.end_time:
            print(f"End time: {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}")

        duration = self.get_total_duration()
        if duration:
            hours = duration // 3600
            minutes = (duration % 3600) // 60
            seconds = duration % 60

            print("Total duration: ", end="")
            if hours > 0:
                print(f"{hours}h ", end="")
            if minutes > 0:
                print(f"{minutes}m ", end="")
            print(f"{seconds}s")
        else:
            print("Total duration: Unknown")

        print(f"\nCheckpoints completed: {self.get_checkpoint_count()}")
        print(f"  Subtasks: {self.get_subtask_count()}")
        print(f"  Tasks: {self.get_task_count()}")

        if self.checkpoints:
            print("\nCheckpoint Details:")
            for checkpoint in self.checkpoints:
                elapsed = checkpoint["elapsed_seconds"]
                elapsed_str = (
                    f" ({elapsed // 60}:{elapsed % 60:02d})" if elapsed else ""
                )
                timestamp = (
                    checkpoint["timestamp"].strftime("%H:%M:%S")
                    if checkpoint["timestamp"]
                    else "Unknown"
                )
                print(
                    f"  {checkpoint['type'].upper()} {checkpoint['id']}: "
                    f"{timestamp}{elapsed_str}"
                )


def main() -> None:
    """Run the timing parser CLI."""
    parser = argparse.ArgumentParser(
        description="Parse timing data from single-agent experiment logs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Parse and display timing summary
  python parse_single_agent_timing.py logs/experiment.log

  # Parse and output JSON for MLflow
  python parse_single_agent_timing.py logs/experiment.log --json

  # Parse and save metrics to file
  python parse_single_agent_timing.py logs/experiment.log --output metrics.json
        """,
    )

    parser.add_argument(
        "log_file",
        type=str,
        help="Path to experiment log file",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output metrics in JSON format",
    )

    parser.add_argument(
        "--output",
        type=str,
        help="Save metrics to JSON file",
    )

    args = parser.parse_args()

    log_file = Path(args.log_file)

    timing_parser = TimingParser(log_file)

    if not timing_parser.parse_log():
        sys.exit(1)

    if args.json or args.output:
        import json

        metrics = timing_parser.get_metrics()

        # Remove None values for cleaner output
        metrics = {k: v for k, v in metrics.items() if v is not None}

        if args.output:
            output_path = Path(args.output)
            with open(output_path, "w") as f:
                json.dump(metrics, f, indent=2)
            print(f"✓ Metrics saved to {output_path}")
        else:
            print(json.dumps(metrics, indent=2))
    else:
        timing_parser.print_summary()


if __name__ == "__main__":
    main()
