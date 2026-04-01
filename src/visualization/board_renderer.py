"""
Rich-based terminal kanban board renderer.

Renders a 4-column board (Backlog, In Progress, Blocked, Done)
from a list of Task objects. Designed for ``marcus board`` CLI command.

Classes
-------
BoardRenderer
    Renders tasks as a terminal kanban board using Rich.
"""

from typing import List, Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.core.models import Priority, Task, TaskStatus

# Column definitions: (display_name, status, border_style)
_COLUMNS = [
    ("Backlog", TaskStatus.TODO, "yellow"),
    ("In Progress", TaskStatus.IN_PROGRESS, "cyan"),
    ("Blocked", TaskStatus.BLOCKED, "red"),
    ("Done", TaskStatus.DONE, "green"),
]

_PRIORITY_INDICATORS = {
    Priority.URGENT: "[bold red]URGENT[/bold red]",
    Priority.HIGH: "[red]HIGH[/red]",
    Priority.MEDIUM: "[yellow]med[/yellow]",
    Priority.LOW: "[dim]low[/dim]",
}


class BoardRenderer:
    """Render a kanban board in the terminal using Rich.

    Parameters
    ----------
    project_name : Optional[str]
        Project name shown in the board header.
        Defaults to ``"Marcus Board"``.
    """

    def __init__(self, project_name: Optional[str] = None) -> None:
        self.project_name = project_name or "Marcus Board"

    def render(
        self,
        tasks: List[Task],
        console: Optional[Console] = None,
    ) -> None:
        """Render the kanban board to the terminal.

        Parameters
        ----------
        tasks : List[Task]
            All tasks to display on the board.
        console : Optional[Console]
            Rich console to render to. Creates a new one if None.
        """
        if console is None:
            console = Console()

        # Group tasks by status
        grouped: dict[TaskStatus, list[Task]] = {
            status: [] for _, status, _ in _COLUMNS
        }
        for task in tasks:
            if task.status in grouped:
                grouped[task.status].append(task)

        # Build column panels
        panels: list[Panel] = []
        for label, status, color in _COLUMNS:
            column_tasks = grouped[status]
            count = len(column_tasks)

            card_texts: list[str] = []
            for task in column_tasks:
                card_texts.append(self._render_card(task, status))

            body = "\n\n".join(card_texts) if card_texts else "[dim](empty)[/dim]"

            panel = Panel(
                body,
                title=f"{label} ({count})",
                border_style=color,
                expand=True,
                padding=(0, 1),
            )
            panels.append(panel)

        # Board header
        console.print()
        console.print(
            Panel(
                f"[bold]{self.project_name}[/bold]",
                style="blue",
                box=box.DOUBLE,
                expand=True,
            )
        )
        console.print()

        # Layout: 2x2 grid for narrow terminals, 4-across for wide
        term_width = console.width or 80
        if term_width >= 160:
            grid = Table.grid(expand=True)
            for _ in _COLUMNS:
                grid.add_column(ratio=1)
            grid.add_row(*panels)
        else:
            grid = Table.grid(expand=True)
            grid.add_column(ratio=1)
            grid.add_column(ratio=1)
            grid.add_row(panels[0], panels[1])
            grid.add_row(panels[2], panels[3])
        console.print(grid)

        # Summary bar
        console.print()
        console.print(self._render_summary(tasks, grouped))
        console.print()

    def _render_card(self, task: Task, column_status: TaskStatus) -> str:
        """Render a single task card as a Rich markup string.

        Parameters
        ----------
        task : Task
            The task to render.
        column_status : TaskStatus
            The column this card is in (for context-aware rendering).

        Returns
        -------
        str
            Rich markup string for the card.
        """
        short_id = task.id[:8]
        lines: list[str] = []

        # Line 1: ID + name
        lines.append(f"[bold]#{short_id}[/bold] {task.name}")

        # Description (first meaningful line, truncated)
        if task.description:
            desc = task.description.strip().split("\n")[0].strip()
            # Strip markdown artifacts
            desc = desc.lstrip("#").lstrip("*").strip()
            if len(desc) > 60:
                desc = desc[:57] + "..."
            if desc:
                lines.append(f" [dim italic]{desc}[/dim italic]")

        # Line 2: context (priority · assignee · hours)
        context_parts: list[str] = []

        if task.priority in (Priority.URGENT, Priority.HIGH):
            context_parts.append(_PRIORITY_INDICATORS.get(task.priority, ""))
        elif column_status == TaskStatus.TODO:
            context_parts.append(_PRIORITY_INDICATORS.get(task.priority, ""))

        if task.assigned_to:
            context_parts.append(f"[cyan]{task.assigned_to}[/cyan]")

        if task.estimated_hours and task.estimated_hours > 0:
            minutes = int(task.estimated_hours * 60)
            context_parts.append(f"[dim]{minutes}m[/dim]")

        if context_parts:
            lines.append(" " + " · ".join(context_parts))

        # Labels (compact)
        if task.labels:
            label_str = " ".join(
                f"[magenta]\\[{lbl}][/magenta]" for lbl in task.labels[:3]
            )
            if len(task.labels) > 3:
                label_str += f" [dim]+{len(task.labels) - 3}[/dim]"
            lines.append(" " + label_str)

        return "\n".join(lines)

    def _render_summary(
        self,
        tasks: List[Task],
        grouped: dict[TaskStatus, list[Task]],
    ) -> Panel:
        """Render the summary bar at the bottom.

        Parameters
        ----------
        tasks : List[Task]
            All tasks.
        grouped : dict[TaskStatus, list[Task]]
            Tasks grouped by status.

        Returns
        -------
        Panel
            Rich Panel with summary statistics.
        """
        total = len(tasks)
        done = len(grouped.get(TaskStatus.DONE, []))
        blocked = len(grouped.get(TaskStatus.BLOCKED, []))
        in_progress = grouped.get(TaskStatus.IN_PROGRESS, [])

        # Completion percentage
        pct = round(done / total * 100) if total > 0 else 0

        # Count unique active agents
        active_agents = {t.assigned_to for t in in_progress if t.assigned_to}
        agent_count = len(active_agents)

        parts: list[str] = [
            f"[bold]{total}[/bold] tasks",
            f"[green]{pct}%[/green] complete",
            f"[cyan]{agent_count}[/cyan] agents active",
        ]

        if blocked > 0:
            parts.append(f"[red]{blocked}[/red] blocker{'s' if blocked != 1 else ''}")

        summary_text = "  ·  ".join(parts)

        return Panel(
            summary_text,
            style="dim",
            box=box.ROUNDED,
        )
