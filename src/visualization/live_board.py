"""
Live terminal kanban board watcher.

Polls a kanban provider at a configurable interval and renders an
in-place updating board using Rich's ``Live`` display, similar to
``htop`` or ``watch``.

Classes
-------
LiveBoardWatcher
    Continuously fetches tasks and refreshes the terminal board.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, List, Optional

from rich import box
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel

from src.core.models import Task
from src.visualization.board_renderer import BoardRenderer


class LiveBoardWatcher:
    """Polls a kanban provider and renders a continuously updating board.

    Parameters
    ----------
    kanban : KanbanInterface
        Any kanban provider implementing ``connect``, ``disconnect``,
        and ``get_all_tasks``.
    project_filter : Optional[str]
        Project ID prefix used to filter tasks.  Falls back to name
        matching against ``project_name`` when no ID matches.
    project_name : str
        Human-readable name shown in the board header.
    interval : float
        Seconds between database polls.  Defaults to ``2.0``.
    """

    def __init__(
        self,
        kanban: Any,
        project_filter: Optional[str] = None,
        project_name: str = "Marcus Board",
        interval: float = 2.0,
    ) -> None:
        self.kanban = kanban
        self.project_filter = project_filter
        self.project_name = project_name
        self.interval = interval
        self._renderer = BoardRenderer(project_name=project_name)

    async def watch(self, console: Optional[Console] = None) -> None:
        """Run the live board until Ctrl+C is pressed.

        Connects to the kanban provider, enters a ``rich.live.Live``
        full-screen context, polls for task updates on every iteration,
        and disconnects cleanly when interrupted.

        Parameters
        ----------
        console : Optional[Console]
            Rich console to render into.  A new one is created when
            ``None``.
        """
        if console is None:
            console = Console()

        await self.kanban.connect()
        try:
            with Live(
                console=console,
                screen=True,
                auto_refresh=False,
            ) as live:
                while True:
                    try:
                        tasks = await self._fetch_tasks()
                        live.update(self._build_live_renderable(tasks))
                        live.refresh()
                        await asyncio.sleep(self.interval)
                    except asyncio.CancelledError:
                        break
        finally:
            await self.kanban.disconnect()

    async def _fetch_tasks(self) -> List[Task]:
        """Fetch tasks from the kanban provider, applying project filter.

        Returns
        -------
        List[Task]
            Filtered task list; all tasks when no filter is set.
        """
        tasks: List[Task] = await self.kanban.get_all_tasks()
        if not self.project_filter:
            return tasks

        filtered = [
            t
            for t in tasks
            if t.project_id and t.project_id.startswith(self.project_filter)
        ]
        if not filtered:
            base_name = self.project_name.split(" - ")[0].strip()
            filtered = [
                t
                for t in tasks
                if t.project_name
                and t.project_name.lower() == base_name.lower()
            ]
        return filtered if filtered else tasks

    def _build_live_renderable(self, tasks: List[Task]) -> Group:
        """Combine the board renderable with a live-status footer.

        Parameters
        ----------
        tasks : List[Task]
            Current task snapshot to display.

        Returns
        -------
        Group
            Board group with an appended timestamp/help footer.
        """
        board = self._renderer.build_renderable(tasks)
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
        footer = Panel(
            f"[dim]Updated: {ts}  ·  Refresh every {self.interval:.0f}s"
            "  ·  Ctrl+C to stop[/dim]",
            box=box.SIMPLE,
            style="dim",
        )
        return Group(board, footer)
