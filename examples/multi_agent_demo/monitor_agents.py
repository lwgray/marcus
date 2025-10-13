#!/usr/bin/env python3
"""
Real-time Agent Monitor for Marcus Multi-Agent Demo

Monitors agent activity by:
- Watching log files for progress
- Checking Marcus for task status
- Displaying real-time metrics
"""

import asyncio
import curses
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class AgentMonitor:
    """Real-time monitor for autonomous agents."""

    def __init__(self, demo_root: Path):
        """
        Initialize the monitor.

        Parameters
        ----------
        demo_root : Path
            Root directory of the demo
        """
        self.demo_root = demo_root
        self.logs_dir = demo_root / "logs"
        self.project_info_file = demo_root / "project_info.json"

        self.agent_ids = [
            "agent_foundation",
            "agent_auth",
            "agent_api",
            "agent_integration",
        ]

        self.metrics: Dict[str, Dict[str, Any]] = {}

    def get_log_tail(self, agent_id: str, lines: int = 10) -> List[str]:
        """
        Get the last N lines from an agent's log.

        Parameters
        ----------
        agent_id : str
            Agent identifier
        lines : int
            Number of lines to retrieve

        Returns
        -------
        List[str]
            Last N lines from log
        """
        log_file = self.logs_dir / f"{agent_id}.log"
        if not log_file.exists():
            return [f"Waiting for {agent_id}..."]

        try:
            with open(log_file, "r") as f:
                all_lines = f.readlines()
                return all_lines[-lines:] if all_lines else ["No output yet"]
        except Exception as e:
            return [f"Error reading log: {e}"]

    def parse_agent_status(self, log_lines: List[str]) -> Dict[str, Any]:
        """
        Parse agent status from log lines.

        Parameters
        ----------
        log_lines : List[str]
            Recent log lines

        Returns
        -------
        Dict[str, Any]
            Status information
        """
        status: Dict[str, Any] = {
            "current_task": None,
            "progress": 0,
            "last_activity": None,
            "tasks_completed": 0,
        }

        log_text = " ".join(log_lines)

        # Look for task assignment
        if "request_next_task" in log_text or "TASK ASSIGNED" in log_text:
            status["last_activity"] = "Requesting task"

        # Look for progress (as strings)
        if "25%" in log_text:
            status["progress"] = "25%"
        elif "50%" in log_text:
            status["progress"] = "50%"
        elif "75%" in log_text:
            status["progress"] = "75%"
        elif "100%" in log_text or "completed" in log_text.lower():
            status["progress"] = "100%"

        # Look for activity indicators
        if "Implementing" in log_text or "Creating" in log_text:
            status["last_activity"] = "Working on task"
        elif "Testing" in log_text:
            status["last_activity"] = "Running tests"
        elif "Committing" in log_text:
            status["last_activity"] = "Committing code"

        return status

    def display_dashboard(self, stdscr: Any) -> None:
        """
        Display real-time dashboard using curses.

        Parameters
        ----------
        stdscr : Any
            Curses screen object
        """
        curses.curs_set(0)  # Hide cursor
        stdscr.nodelay(1)  # Non-blocking input
        stdscr.clear()

        while True:
            try:
                stdscr.clear()
                height, width = stdscr.getmaxyx()

                # Header
                header = "MARCUS MULTI-AGENT DEMO - LIVE MONITOR"
                stdscr.addstr(0, (width - len(header)) // 2, header, curses.A_BOLD)
                stdscr.addstr(1, 0, "=" * width)

                # Timestamp
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                stdscr.addstr(2, 2, f"Time: {timestamp}")

                # Project info
                if self.project_info_file.exists():
                    with open(self.project_info_file, "r") as f:
                        project_info = json.load(f)
                    stdscr.addstr(
                        3, 2, f"Project ID: {project_info.get('project_id', 'N/A')}"
                    )
                    stdscr.addstr(
                        4, 2, f"Board ID: {project_info.get('board_id', 'N/A')}"
                    )
                else:
                    stdscr.addstr(3, 2, "Waiting for project creation...")

                stdscr.addstr(5, 0, "-" * width)

                # Agent statuses
                row = 6
                for i, agent_id in enumerate(self.agent_ids):
                    if row >= height - 2:
                        break

                    # Agent header
                    stdscr.addstr(row, 2, f"{agent_id}", curses.A_BOLD)
                    row += 1

                    # Get recent log activity
                    log_lines = self.get_log_tail(agent_id, lines=5)
                    status = self.parse_agent_status(log_lines)

                    # Display status
                    stdscr.addstr(row, 4, f"Progress: {status['progress']}%")
                    row += 1

                    if status["last_activity"]:
                        stdscr.addstr(row, 4, f"Activity: {status['last_activity']}")
                        row += 1

                    # Show last log line
                    if log_lines:
                        last_line = log_lines[-1].strip()[: width - 6]
                        stdscr.addstr(row, 4, f"Log: {last_line}")
                    row += 2

                # Footer
                footer = "Press 'q' to quit | Refreshing every 5s"
                if row < height - 1:
                    stdscr.addstr(height - 1, 2, footer)

                stdscr.refresh()

                # Check for quit
                key = stdscr.getch()
                if key == ord("q"):
                    break

                time.sleep(5)

            except KeyboardInterrupt:
                break
            except Exception as e:
                stdscr.addstr(height - 2, 2, f"Error: {e}")
                stdscr.refresh()
                time.sleep(5)

    def run(self) -> None:
        """Run the monitor with curses UI."""
        curses.wrapper(self.display_dashboard)


def main() -> None:
    """Main entry point."""
    demo_root = Path(__file__).parent
    monitor = AgentMonitor(demo_root)

    print("Starting agent monitor...")
    print("Press 'q' to quit")

    monitor.run()


if __name__ == "__main__":
    main()
