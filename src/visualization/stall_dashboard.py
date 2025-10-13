"""
Terminal dashboard for visualizing project stall snapshots.

Uses rich library for beautiful terminal output with colors, tables, and trees.
"""

from datetime import datetime
from typing import Any, Dict, List

from src.visualization.causal_analyzer import analyze_why

try:
    from rich import box
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.tree import Tree

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    # Fallback to plain text


class StallDashboard:
    """
    Rich terminal dashboard for stall analysis visualization.

    Parameters
    ----------
    snapshot : Dict[str, Any]
        Complete stall snapshot data
    """

    def __init__(self, snapshot: Dict[str, Any]):
        """Initialize dashboard with snapshot data."""
        self.snapshot = snapshot
        self.console = Console() if RICH_AVAILABLE else None
        self.causal_analysis = analyze_why(snapshot)

    def render(self) -> None:
        """Render the complete dashboard."""
        if not RICH_AVAILABLE:
            self._render_plain()
            return

        console = self.console
        if console is None:
            self._render_plain()
            return

        # Header
        console.print()
        console.print(self._build_header())
        console.print()

        # Summary
        console.print(self._build_summary())
        console.print()

        # ROOT CAUSE ANALYSIS (WHY)
        console.print(self._build_root_causes())
        console.print()

        # CAUSAL NARRATIVE
        console.print(self._build_narrative())
        console.print()

        # Issues
        issues = self.snapshot.get("diagnostic_report", {}).get("issues", [])
        if issues:
            console.print(self._build_issues(issues))
            console.print()

        # Dependency Locks
        locks = self.snapshot.get("dependency_locks", {})
        if locks.get("total_locks", 0) > 0:
            console.print(self._build_dependency_locks(locks))
            console.print()

        # Early Completions
        early_completions = self.snapshot.get("early_completions", [])
        if early_completions:
            console.print(self._build_early_completions(early_completions))
            console.print()

        # Timeline
        timeline = self.snapshot.get("task_completion_timeline", [])
        if timeline:
            console.print(self._build_timeline(timeline))
            console.print()

        # Conversation Patterns
        conversation = self.snapshot.get("conversation_history", [])
        if conversation:
            console.print(self._build_conversation_patterns())
            console.print()

        # SYSTEM FAILURES (detailed technical analysis)
        system_failures = self.causal_analysis.get("system_failures", [])
        if system_failures:
            console.print(self._build_system_failures(system_failures))
            console.print()

        # ACTIONABLE FIXES (specific code changes)
        actionable_fixes = self.causal_analysis.get("actionable_fixes", [])
        if actionable_fixes:
            console.print(self._build_actionable_fixes(actionable_fixes))
            console.print()

        # PREVENTION STRATEGIES (long-term)
        prevention = self.causal_analysis.get("prevention_strategies", [])
        if prevention:
            console.print(self._build_prevention_strategies(prevention))
            console.print()

        # Recommendations (old generic ones)
        recommendations = self.snapshot.get("recommendations", [])
        if recommendations:
            console.print(self._build_recommendations(recommendations))
            console.print()

    def _build_header(self) -> Panel:
        """Build header panel."""
        project_name = self.snapshot.get("project_name", "Unknown")
        timestamp = self.snapshot.get("timestamp", "Unknown")

        title = Text()
        title.append("PROJECT STALL ANALYSIS", style="bold white on blue")

        content = Text()
        content.append("Project: ", style="bold")
        content.append(f"{project_name}\n", style="cyan")
        content.append("Captured: ", style="bold")
        content.append(f"{timestamp}", style="dim")

        return Panel(content, title=title, border_style="blue", box=box.DOUBLE)

    def _build_root_causes(self) -> Panel:
        """Build root cause analysis panel - explains WHY."""
        root_causes = self.causal_analysis.get("root_causes", [])

        if not root_causes:
            return Panel(
                Text("No root causes identified", style="green"),
                title="[bold]🔍 ROOT CAUSE ANALYSIS[/bold]",
                border_style="green",
            )

        content = Text()

        for i, cause in enumerate(root_causes[:5], 1):  # Top 5
            severity = cause.get("severity", "unknown")

            # Severity styling
            if severity == "critical":
                icon = "🔴"
                style = "red bold"
            elif severity == "high":
                icon = "🟠"
                style = "yellow bold"
            else:
                icon = "🟡"
                style = "yellow"

            content.append(f"{i}. {icon} ", style=style)
            content.append(
                f"{cause.get('type', 'unknown').replace('_', ' ').title()}\n",
                style=style,
            )

            # WHAT happened
            content.append("   WHAT: ", style="bold cyan")
            content.append(f"{cause.get('explanation', 'Unknown')}\n")

            # WHY it happened
            content.append("   WHY:  ", style="bold magenta")
            content.append(f"{cause.get('why', 'Unknown')}\n")

            # IMPACT
            content.append("   IMPACT: ", style="bold red")
            content.append(f"{cause.get('impact', 'Unknown')}\n\n")

        return Panel(
            content,
            title="[bold]🔍 ROOT CAUSE ANALYSIS - WHY THIS HAPPENED[/bold]",
            border_style="magenta",
        )

    def _build_narrative(self) -> Panel:
        """Build narrative explanation panel."""
        narrative = self.causal_analysis.get("narrative", "")

        if not narrative:
            return Panel(
                Text("No narrative available", style="dim"),
                title="[bold]📖 WHAT HAPPENED[/bold]",
                border_style="cyan",
            )

        return Panel(
            Text(narrative),
            title="[bold]📖 THE FULL STORY - FROM START TO STALL[/bold]",
            border_style="cyan",
            subtitle="[dim]Understanding the complete chain of events[/dim]",
        )

    def _build_summary(self) -> Panel:
        """Build summary panel."""
        summary = self.snapshot.get("summary", {})
        diag_report = self.snapshot.get("diagnostic_report", {})

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Metric", style="bold")
        table.add_column("Value")

        # Stall reason
        stall_reason = summary.get("stall_reason", "Unknown")
        table.add_row("Stall Reason:", Text(stall_reason, style="red bold"))

        # Issues
        total_issues = summary.get("total_issues", 0)
        issues_style = "red bold" if total_issues > 0 else "green"
        table.add_row("Total Issues:", Text(str(total_issues), style=issues_style))

        # Locks
        locks = summary.get("dependency_locks", 0)
        locks_style = "red bold" if locks > 0 else "green"
        table.add_row("Dependency Locks:", Text(str(locks), style=locks_style))

        # Early completions
        early = summary.get("early_completions", 0)
        early_style = "yellow bold" if early > 0 else "green"
        table.add_row(
            "Early Completions:",
            Text(f"{early} ⚠️" if early > 0 else "0", style=early_style),
        )

        # Tasks
        total_tasks = diag_report.get("total_tasks", 0)
        available = diag_report.get("available_tasks", 0)
        blocked = diag_report.get("blocked_tasks", 0)

        table.add_row("", "")  # Spacer
        table.add_row("Total Tasks:", str(total_tasks))
        table.add_row(
            "Available:",
            Text(str(available), style="green" if available > 0 else "red"),
        )
        table.add_row(
            "Blocked:", Text(str(blocked), style="red" if blocked > 0 else "green")
        )

        return Panel(table, title="📊 [bold]SUMMARY[/bold]", border_style="cyan")

    def _build_issues(self, issues: List[Dict[str, Any]]) -> Panel:
        """Build issues panel."""
        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_issues = sorted(
            issues, key=lambda x: severity_order.get(x.get("severity", "low"), 99)
        )

        content = []

        for i, issue in enumerate(sorted_issues[:10], 1):  # Top 10
            severity = issue.get("severity", "unknown")
            issue_type = issue.get("type", "unknown")
            description = issue.get("description", "")
            recommendation = issue.get("recommendation", "")

            # Severity icon and color
            if severity == "critical":
                icon = "🔴"
                color = "red bold"
            elif severity == "high":
                icon = "🟠"
                color = "yellow bold"
            elif severity == "medium":
                icon = "🟡"
                color = "yellow"
            else:
                icon = "⚪"
                color = "white"

            issue_text = Text()
            issue_text.append(f"{i}. {icon} ", style=color)
            issue_text.append(f"{issue_type.replace('_', ' ').title()}\n", style=color)
            issue_text.append(f"   {description}\n", style="white")
            issue_text.append(f"   💡 {recommendation}\n", style="cyan")

            content.append(issue_text)

        if len(issues) > 10:
            more = Text(f"\n... and {len(issues) - 10} more issues", style="dim")
            content.append(more)

        has_critical = any(i.get("severity") == "critical" for i in issues)
        has_high_severity = any(
            i.get("severity") in ["critical", "high"] for i in issues
        )
        title_prefix = "🔴 CRITICAL " if has_critical else "⚠️  "

        return Panel(
            (
                Text.assemble(*content)
                if content
                else Text("No issues found", style="green")
            ),
            title=f"[bold]{title_prefix}ISSUES ({len(issues)})[/bold]",
            border_style="red" if has_high_severity else "yellow",
        )

    def _build_dependency_locks(self, locks_data: Dict[str, Any]) -> Panel:
        """Build dependency locks visualization."""
        locks = locks_data.get("locks", [])

        tree = Tree("🔒 [bold]Blocked Tasks[/bold]")

        for lock in locks[:10]:  # Show top 10
            blocked = lock.get("blocked_task", {})
            blockers = lock.get("blocking_tasks", [])

            # Add blocked task
            blocked_name = blocked.get("name", "Unknown")
            blocked_status = blocked.get("status", "unknown")

            status_icon = "❌" if blocked_status == "todo" else "⏳"
            blocked_branch = tree.add(
                f"{status_icon} [red]{blocked_name}[/red] [dim]({blocked_status})[/dim]"
            )

            # Add blocking tasks
            blocked_branch.add("[dim]Waiting for:[/dim]")
            for blocker in blockers:
                blocker_name = blocker.get("name", "Unknown")
                blocker_status = blocker.get("status", "unknown")

                if blocker_status == "in_progress":
                    icon = "⏳"
                    style = "yellow"
                else:
                    icon = "❌"
                    style = "red"

                blocker_text = (
                    f"{icon} [{style}]{blocker_name}[/{style}] "
                    f"[dim]({blocker_status})[/dim]"
                )
                blocked_branch.add(blocker_text)

        if len(locks) > 10:
            tree.add(f"[dim]... and {len(locks) - 10} more locks[/dim]")

        # Add metrics
        metrics = locks_data.get("metrics", {})
        avg_depth = metrics.get("average_lock_depth", 0)
        max_depth = metrics.get("max_lock_depth", 0)

        # Create a group with tree and metrics
        from rich.console import Group

        metrics_text = Text()
        metrics_text.append(f"\nAverage lock depth: {avg_depth:.1f} | ", style="dim")
        metrics_text.append(f"Max depth: {max_depth}", style="dim")

        combined = Group(tree, metrics_text)

        total_locks = locks_data.get("total_locks", 0)
        return Panel(
            combined,
            title=f"[bold]🔒 DEPENDENCY LOCKS ({total_locks})[/bold]",
            border_style="red",
        )

    def _build_early_completions(self, completions: List[Dict[str, Any]]) -> Panel:
        """Build early completions panel."""
        table = Table(show_header=True, box=box.SIMPLE)
        table.add_column("Task", style="cyan")
        table.add_column("Completed At", justify="right")
        table.add_column("Expected", justify="right")
        table.add_column("Issue", style="red")

        for completion in completions[:10]:
            task_name = completion.get("task_name", "Unknown")
            pct = completion.get("completion_percentage", 0)
            issue = completion.get("issue", "")

            table.add_row(task_name, f"{pct:.0f}%", ">80%", issue)

        return Panel(
            table, title="[bold]⚠️  ANOMALOUS COMPLETIONS[/bold]", border_style="yellow"
        )

    def _build_timeline(self, timeline: List[Dict[str, Any]]) -> Panel:
        """Build completion timeline."""
        table = Table(show_header=True, box=box.SIMPLE)
        table.add_column("#", justify="right", style="dim")
        table.add_column("Status", justify="center")
        table.add_column("Task", style="cyan")
        table.add_column("Timestamp", style="dim")
        table.add_column("Notes", style="yellow")

        # Get early completion task IDs
        early_task_ids = {
            ec.get("task_id") for ec in self.snapshot.get("early_completions", [])
        }

        for item in timeline[:15]:  # Show first 15
            seq = item.get("sequence", "?")
            task_name = item.get("task_name", "Unknown")
            timestamp = item.get("timestamp", "")
            task_id = item.get("task_id", "")

            # Format timestamp
            try:
                dt = datetime.fromisoformat(timestamp)
                time_str = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                time_str = timestamp[:16] if timestamp else "Unknown"

            # Check if completed
            status = "✅"
            notes = ""

            if task_id in early_task_ids:
                notes = "⚠️ TOO EARLY"

            table.add_row(str(seq), status, task_name, time_str, notes)

        return Panel(
            table, title="[bold]📅 COMPLETION TIMELINE[/bold]", border_style="cyan"
        )

    def _build_conversation_patterns(self) -> Panel:
        """Build conversation patterns analysis."""
        conversation = self.snapshot.get("conversation_history", [])

        # Count event types
        event_types: Dict[str, int] = {}
        for event in conversation:
            event_type = event.get("type", "unknown")
            event_types[event_type] = event_types.get(event_type, 0) + 1

        # Identify patterns
        patterns = []

        # Check for repeated "no task"
        no_task_count = sum(
            count
            for event_type, count in event_types.items()
            if "no_task" in event_type.lower()
        )
        if no_task_count >= 3:
            patterns.append(
                ("⚠️", f"Repeated 'no tasks' ({no_task_count} times)", "yellow")
            )

        # Check for failures
        failure_count = sum(
            count
            for event_type, count in event_types.items()
            if "fail" in event_type.lower() or "error" in event_type.lower()
        )
        if failure_count >= 2:
            patterns.append(("⚠️", f"Multiple failures ({failure_count} times)", "red"))

        # Check for low activity
        if len(conversation) < 10:
            patterns.append(
                ("ℹ️", f"Low activity: {len(conversation)} events in 24h", "dim")
            )

        # Build output
        content = Text()

        if patterns:
            for icon, message, style in patterns:
                content.append(f"{icon} {message}\n", style=style)
        else:
            content.append("No significant patterns detected", style="green")

        content.append(f"\nTotal events analyzed: {len(conversation)}", style="dim")

        # Top event types
        if event_types:
            content.append("\n\nTop event types:\n", style="bold")
            sorted_types = sorted(event_types.items(), key=lambda x: x[1], reverse=True)
            for event_type, count in sorted_types[:5]:
                content.append(f"  • {event_type}: {count}\n", style="dim")

        return Panel(
            content, title="[bold]🗣️  CONVERSATION PATTERNS[/bold]", border_style="cyan"
        )

    def _build_recommendations(self, recommendations: List[str]) -> Panel:
        """Build recommendations panel."""
        content = Text()

        for i, rec in enumerate(recommendations[:10], 1):
            # Color code by severity
            if "[CRITICAL]" in rec or "critical" in rec.lower():
                style = "red bold"
                icon = "🔴"
            elif "[HIGH]" in rec or "high" in rec.lower():
                style = "yellow bold"
                icon = "🟠"
            else:
                style = "white"
                icon = "💡"

            content.append(f"{icon} ", style=style)
            content.append(f"{i}. {rec}\n", style=style)

        if len(recommendations) > 10:
            content.append(f"\n... and {len(recommendations) - 10} more", style="dim")

        return Panel(
            content, title="[bold]💡 RECOMMENDATIONS[/bold]", border_style="green"
        )

    def _render_plain(self) -> None:
        """Fallback plain text rendering when rich is not available."""
        print("\n" + "=" * 70)
        print("PROJECT STALL ANALYSIS")
        print("=" * 70)

        project_name = self.snapshot.get("project_name", "Unknown")
        timestamp = self.snapshot.get("timestamp", "Unknown")
        print(f"Project: {project_name}")
        print(f"Captured: {timestamp}")

        print("\n" + "-" * 70)
        print("SUMMARY")
        print("-" * 70)

        summary = self.snapshot.get("summary", {})
        print(f"Stall Reason: {summary.get('stall_reason', 'Unknown')}")
        print(f"Total Issues: {summary.get('total_issues', 0)}")
        print(f"Dependency Locks: {summary.get('dependency_locks', 0)}")
        print(f"Early Completions: {summary.get('early_completions', 0)}")

        print("\nFor better visualization, install rich:")
        print("  pip install rich")

    def _build_system_failures(self, failures: List[Dict[str, Any]]) -> Panel:
        """Build system failures panel with technical details."""
        content = Text()

        for i, failure in enumerate(failures, 1):
            severity = failure.get("severity", "unknown")
            icon = "🔴" if severity == "critical" else "🟠"
            style = "red bold" if severity == "critical" else "yellow bold"

            content.append(f"{i}. {icon} ", style=style)
            content.append(f"{failure['system']}\n", style=style)

            content.append("   FAILURE: ", style="bold red")
            content.append(f"{failure['failure']}\n")

            content.append("   EVIDENCE: ", style="bold yellow")
            content.append(f"{failure['evidence']}\n")

            content.append("   CODE: ", style="bold cyan")
            content.append(f"{failure['code_location']}\n")

            content.append("   ROOT CAUSE: ", style="bold magenta")
            content.append(f"{failure['root_cause']}\n")

            content.append("   WHY CHECKS FAILED: ", style="bold red")
            content.append(f"{failure['why_checks_failed']}\n\n")

        return Panel(
            content,
            title="[bold]🔧 SYSTEM FAILURES - TECHNICAL ANALYSIS[/bold]",
            border_style="red",
            subtitle="[dim]Understanding which parts of Marcus broke and why[/dim]",
        )

    def _build_actionable_fixes(self, fixes: List[Dict[str, Any]]) -> Panel:
        """Build actionable fixes panel with specific code changes."""
        content = Text()

        for i, fix in enumerate(fixes, 1):
            priority = fix.get("priority", "")
            if "P0" in priority:
                icon = "🔴"
                style = "red bold"
            elif "P1" in priority:
                icon = "🟠"
                style = "yellow bold"
            else:
                icon = "🟡"
                style = "yellow"

            content.append(f"{i}. {icon} ", style=style)
            content.append(f"[{priority}] {fix['title']}\n", style=style)

            content.append("   PROBLEM: ", style="bold red")
            content.append(f"{fix['problem']}\n")

            content.append("   SOLUTION: ", style="bold green")
            content.append(f"{fix['solution']}\n")

            content.append("   FILES TO MODIFY:\n", style="bold cyan")
            for file in fix["files_to_modify"]:
                content.append(f"      • {file}\n", style="cyan")

            content.append("   SPECIFIC CHANGES:\n", style="bold magenta")
            for change in fix["specific_changes"]:
                content.append(f"      📄 {change['file']}\n", style="cyan")
                content.append(f"         {change['change']}\n", style="dim")

            content.append("   TEST: ", style="bold yellow")
            content.append(f"{fix['test_validation']}\n")

            content.append("   ESTIMATED TIME: ", style="bold")
            content.append(f"{fix['estimated_time']}\n\n")

        return Panel(
            content,
            title="[bold]🛠️  ACTIONABLE FIXES - IMMEDIATE ACTIONS[/bold]",
            border_style="green",
            subtitle="[dim]Specific code changes to implement right now[/dim]",
        )

    def _build_prevention_strategies(self, strategies: List[Dict[str, Any]]) -> Panel:
        """Build prevention strategies panel."""
        content = Text()

        for i, strategy in enumerate(strategies, 1):
            category = strategy.get("category", "General")
            content.append(f"{i}. ", style="bold")
            content.append(f"[{category}] ", style="cyan bold")
            content.append(f"{strategy['strategy']}\n", style="bold")

            content.append("   DESCRIPTION: ", style="bold")
            content.append(f"{strategy['description']}\n")

            content.append("   BENEFITS:\n", style="bold green")
            for benefit in strategy["benefits"]:
                content.append(f"      ✓ {benefit}\n", style="green")

            content.append("   IMPLEMENTATION:\n", style="bold cyan")
            content.append(f"      {strategy['implementation']}\n\n", style="dim")

        return Panel(
            content,
            title="[bold]🛡️  PREVENTION STRATEGIES - LONG-TERM[/bold]",
            border_style="blue",
            subtitle="[dim]Architectural changes to prevent future stalls[/dim]",
        )


def render_snapshot(snapshot: Dict[str, Any]) -> None:
    """
    Render a stall snapshot as a rich terminal dashboard.

    Parameters
    ----------
    snapshot : Dict[str, Any]
        Complete stall snapshot data
    """
    dashboard = StallDashboard(snapshot)
    dashboard.render()
