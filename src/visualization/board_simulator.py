"""
Kanban board simulator for the ``marcus board --demo`` command.

This module fakes a Marcus run.  It seeds a throwaway project with a
small dependency graph of tasks and then drives a pool of *fake agents*
that claim tasks, work them, occasionally hit a blocker, and finish —
moving cards ``backlog -> in progress -> done`` exactly the way real
Marcus agents do.

The point is purely visual: paired with the live board watcher
(``src/visualization/live_board.py``) it lets a person run a single
command, watch tasks move across the terminal kanban board, and have
the command exit on its own when every task is done.  No Marcus
server, no Docker, no real agents.

Glossary
--------
kanban board
    The shared task list.  Here it is a local SQLite file
    (``src/integrations/providers/sqlite_kanban.py``).
task spec
    A plain dict describing one fake task before it is written to the
    board: a stable ``key``, a name, an estimate, and which other
    specs it ``depends_on`` (by key).
fake agent
    An async coroutine that loops: pick an eligible task, work it,
    complete it.  ``agents`` of them run concurrently.
virtual clock
    Wall-clock time a task takes is ``estimated_hours / speed``.  A
    higher ``speed`` makes the demo run faster.

Classes
-------
BoardSimulator
    Seeds the fake project and runs the fake agents.
"""

import asyncio
import random
from typing import Any, Dict, List, Optional

from src.core.models import Task, TaskStatus
from src.integrations.providers.sqlite_kanban import SQLiteKanban

# Human-readable name shown in the board header during the demo.
DEMO_PROJECT_NAME = "Demo: Recipe Sharing App"

# The built-in fake project.  Specs MUST be topologically sorted:
# every key in ``depends_on`` has to be defined by an earlier entry.
# That ordering guarantee is what keeps the task graph a DAG (no
# cycles), so the fake agents can never deadlock.
DEMO_TASK_SPECS: List[Dict[str, Any]] = [
    {
        "key": "schema",
        "name": "Design database schema",
        "description": "Tables for users, recipes, and ratings.",
        "priority": "high",
        "estimated_hours": 3.0,
        "labels": ["backend", "design"],
        "depends_on": [],
    },
    {
        "key": "ui-scaffold",
        "name": "Scaffold frontend app",
        "description": "Routing, layout shell, and shared components.",
        "priority": "medium",
        "estimated_hours": 2.0,
        "labels": ["frontend"],
        "depends_on": [],
    },
    {
        "key": "db-migrations",
        "name": "Write database migrations",
        "description": "Migration scripts for the recipe schema.",
        "priority": "medium",
        "estimated_hours": 2.0,
        "labels": ["backend"],
        "depends_on": ["schema"],
    },
    {
        "key": "api-auth",
        "name": "Build authentication API",
        "description": "Signup, login, and session endpoints.",
        "priority": "high",
        "estimated_hours": 5.0,
        "labels": ["backend", "api"],
        "depends_on": ["schema"],
    },
    {
        "key": "api-recipes",
        "name": "Build recipe CRUD API",
        "description": "Create, read, update, and delete recipes.",
        "priority": "high",
        "estimated_hours": 6.0,
        "labels": ["backend", "api"],
        "depends_on": ["schema"],
    },
    {
        "key": "ui-login",
        "name": "Build login screen",
        "description": "Login and signup forms wired to the auth API.",
        "priority": "medium",
        "estimated_hours": 3.0,
        "labels": ["frontend"],
        "depends_on": ["api-auth", "ui-scaffold"],
    },
    {
        "key": "ui-recipes",
        "name": "Build recipe browser",
        "description": "Recipe list and detail views.",
        "priority": "medium",
        "estimated_hours": 4.0,
        "labels": ["frontend"],
        "depends_on": ["api-recipes", "ui-scaffold"],
    },
    {
        "key": "tests",
        "name": "Write integration tests",
        "description": "End-to-end tests across the auth and recipe APIs.",
        "priority": "medium",
        "estimated_hours": 4.0,
        "labels": ["testing"],
        "depends_on": ["api-auth", "api-recipes"],
    },
    {
        "key": "deploy",
        "name": "Deploy to staging",
        "description": "Ship the full stack to the staging environment.",
        "priority": "high",
        "estimated_hours": 2.0,
        "labels": ["devops"],
        "depends_on": ["ui-login", "ui-recipes", "tests", "db-migrations"],
    },
]


class BoardSimulator:
    """Seed a fake project and drive fake agents across the board.

    Parameters
    ----------
    kanban : SQLiteKanban
        SQLite-backed kanban provider the simulation writes to.  It
        does not need to be connected yet — :meth:`seed` connects it.
    task_specs : Optional[List[Dict[str, Any]]]
        Task specs to seed.  Defaults to :data:`DEMO_TASK_SPECS`.
        Must be topologically sorted (see module docstring).
    project_name : str
        Project name shown on the board.  Defaults to
        :data:`DEMO_PROJECT_NAME`.
    agents : int
        Number of fake agents working concurrently.  Clamped to a
        minimum of 1.
    speed : float
        Virtual-clock divisor.  A task's wall-clock duration is
        ``estimated_hours / speed`` seconds.  Higher is faster.
    blocker_rate : float
        Probability in ``[0, 1]`` that a worked task hits a transient
        blocker before completing.  Blocked tasks always recover.
    seed : Optional[int]
        Seed for the internal random generator, making blocker timing
        reproducible.

    Notes
    -----
    The simulator mirrors the real Marcus agent cycle — claim a task,
    move it to ``in progress``, report progress, occasionally report a
    blocker, then complete — so the demo board behaves like a genuine
    run rather than randomly shuffled cards.
    """

    #: Floor on any simulated wait, so a very high ``speed`` never
    #: produces a zero-second (busy) loop.
    _MIN_STEP_SECONDS = 0.05

    #: Wall-clock seconds an idle agent waits before re-checking the
    #: board for newly unblocked work.
    _POLL_SECONDS = 0.3

    def __init__(
        self,
        kanban: SQLiteKanban,
        *,
        task_specs: Optional[List[Dict[str, Any]]] = None,
        project_name: str = DEMO_PROJECT_NAME,
        agents: int = 3,
        speed: float = 2.0,
        blocker_rate: float = 0.15,
        seed: Optional[int] = None,
    ) -> None:
        self.kanban = kanban
        self.task_specs = task_specs if task_specs is not None else DEMO_TASK_SPECS
        self.project_name = project_name
        self.agents = max(1, agents)
        self.speed = speed if speed > 0 else 1.0
        self.blocker_rate = min(1.0, max(0.0, blocker_rate))
        self._rng = random.Random(seed)

        # ``key`` from a task spec -> generated kanban task id.
        self._id_by_key: Dict[str, str] = {}
        # Task ids an agent has picked but not yet written to the
        # board, so two agents cannot claim the same task.
        self._claimed: set[str] = set()
        self._seeded = False
        self._project_id: Optional[str] = None

    # ------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------

    async def seed(self) -> List[Task]:
        """Create the fake project and all of its tasks in ``backlog``.

        Validates that the specs are topologically sorted, creates a
        project row, scopes the kanban provider to it, then writes one
        task per spec — translating ``depends_on`` keys into the real
        task ids assigned during creation.

        Returns
        -------
        List[Task]
            The created tasks, in spec order.

        Raises
        ------
        ValueError
            If a spec depends on a key not defined by an earlier spec.
        """
        self._validate_specs()

        if not self.kanban.connected:
            await self.kanban.connect()

        project = await self.kanban.create_project(
            self.project_name, "Board simulator demo project"
        )
        # Scope every read/write on this provider to the demo project.
        self._project_id = project["id"]
        self.kanban.project_id = project["id"]
        self.kanban.project_name = self.project_name

        created: List[Task] = []
        for spec in self.task_specs:
            dependencies = [
                self._id_by_key[dep_key] for dep_key in spec.get("depends_on", [])
            ]
            task = await self.kanban.create_task(
                {
                    "name": spec["name"],
                    "description": spec.get("description", ""),
                    "priority": spec.get("priority", "medium"),
                    "estimated_hours": spec.get("estimated_hours", 1.0),
                    "labels": spec.get("labels", []),
                    "dependencies": dependencies,
                    "status": "todo",
                    "project_name": self.project_name,
                }
            )
            self._id_by_key[spec["key"]] = task.id
            created.append(task)

        self._seeded = True
        return created

    def _validate_specs(self) -> None:
        """Ensure specs form a DAG written in topological order.

        Raises
        ------
        ValueError
            If a dependency key has not been defined by an earlier
            spec, or if two specs share a key.
        """
        seen: set[str] = set()
        for spec in self.task_specs:
            key = spec["key"]
            if key in seen:
                raise ValueError(f"Duplicate task spec key: '{key}'")
            for dep_key in spec.get("depends_on", []):
                if dep_key not in seen:
                    raise ValueError(
                        f"Task '{key}' depends on '{dep_key}', which is not "
                        "defined by an earlier spec. Task specs must be "
                        "topologically sorted."
                    )
            seen.add(key)

    # ------------------------------------------------------------
    # Running
    # ------------------------------------------------------------

    async def run(self) -> Dict[str, Any]:
        """Seed if needed, then run all fake agents to completion.

        Returns
        -------
        Dict[str, Any]
            Final board metrics from
            :meth:`SQLiteKanban.get_project_metrics` — task counts by
            status.  When the run finishes, ``completed_tasks`` equals
            ``total_tasks``.
        """
        if not self._seeded:
            await self.seed()

        await asyncio.gather(
            *(self._agent_loop(f"sim-agent-{i + 1}") for i in range(self.agents))
        )
        return await self.kanban.get_project_metrics()

    async def _agent_loop(self, agent_id: str) -> None:
        """Run one fake agent until every task on the board is done.

        The agent repeatedly claims the highest-priority eligible task,
        moves it through ``in progress`` (and possibly ``blocked``),
        and finishes it.  When no task is eligible but some remain
        unfinished, it polls until a dependency clears.

        Parameters
        ----------
        agent_id : str
            Identifier recorded as the task assignee and comment author.
        """
        while True:
            tasks = await self.kanban.get_all_tasks()
            # An empty board is trivially "all done" — exit so a
            # simulator seeded with no task specs returns cleanly
            # instead of polling forever.
            if not tasks or self._all_done(tasks):
                return

            eligible = self._eligible(tasks)
            if not eligible:
                # Work remains but is gated on an in-flight dependency.
                await asyncio.sleep(self._POLL_SECONDS)
                continue

            task = eligible[0]
            # Reserve the task synchronously (no await before this
            # line runs) so a sibling agent cannot also claim it.
            self._claimed.add(task.id)
            try:
                await self._work_task(agent_id, task)
            except Exception:
                # Release the reservation so a sibling agent can retry
                # the task on the next tick. Without this, a transient
                # provider error would strand the task in `_claimed`
                # forever, deadlocking the run.
                self._claimed.discard(task.id)
                raise

    async def _work_task(self, agent_id: str, task: Task) -> None:
        """Carry one task from ``backlog`` to ``done``.

        Each provider write goes through :meth:`_require` so a ``False``
        return (e.g. a transient provider error) raises and triggers
        the claim-release path in :meth:`_agent_loop`.  Without that,
        a silently-dropped assign/move would leave the task ``TODO``
        but permanently in ``_claimed``, deadlocking the run.

        Parameters
        ----------
        agent_id : str
            The fake agent performing the work.
        task : Task
            The task to claim and complete.
        """
        # Claim: assign + move to "in progress".
        await self._require(
            self.kanban.assign_task(task.id, agent_id), "assign_task", task
        )
        await self.kanban.add_comment(task.id, f"{agent_id} started work")
        await asyncio.sleep(self._work_seconds(task))

        # Occasionally hit a transient blocker, then recover from it.
        if self._rng.random() < self.blocker_rate:
            await self._require(
                self.kanban.report_blocker(
                    task.id, "Waiting on an upstream interface change", "medium"
                ),
                "report_blocker",
                task,
            )
            await asyncio.sleep(self._blocker_seconds())
            await self._require(
                self.kanban.move_task_to_column(task.id, "in progress"),
                "move_task_to_column(in progress)",
                task,
            )
            await self.kanban.add_comment(task.id, f"{agent_id} unblocked, resuming")
            await asyncio.sleep(self._work_seconds(task) * 0.4)

        # Complete.
        await self._require(
            self.kanban.move_task_to_column(task.id, "done"),
            "move_task_to_column(done)",
            task,
        )
        await self.kanban.add_comment(task.id, f"{agent_id} completed work")

    @staticmethod
    async def _require(coro: Any, op: str, task: Task) -> None:
        """Await a provider call and raise if it reports failure.

        The SQLite provider returns ``True``/``False`` rather than
        raising; this helper bridges that convention to exceptions so
        callers can rely on normal Python error flow.

        Parameters
        ----------
        coro : Any
            The provider coroutine to await.
        op : str
            Operation name, included in the error message.
        task : Task
            Task the operation targeted, included in the error message.

        Raises
        ------
        RuntimeError
            When the provider call returns a falsy value.
        """
        result = await coro
        if result is False:
            raise RuntimeError(
                f"Provider operation '{op}' failed for task {task.id} "
                f"('{task.name}')"
            )

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------

    def _eligible(self, tasks: List[Task]) -> List[Task]:
        """Return claimable tasks, highest priority first.

        A task is eligible when it is in ``TODO``, unassigned, not
        already claimed by a sibling agent this tick, and all of its
        dependencies are ``DONE``.

        Parameters
        ----------
        tasks : List[Task]
            Current board snapshot.

        Returns
        -------
        List[Task]
            Eligible tasks, ordered by descending priority.
        """
        done_ids = {t.id for t in tasks if t.status == TaskStatus.DONE}
        eligible = [
            t
            for t in tasks
            if t.status == TaskStatus.TODO
            and not t.assigned_to
            and t.id not in self._claimed
            and all(dep in done_ids for dep in t.dependencies)
        ]
        priority_rank = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
        eligible.sort(key=lambda t: priority_rank.get(t.priority.value, 2))
        return eligible

    @staticmethod
    def _all_done(tasks: List[Task]) -> bool:
        """Return ``True`` when every task on the board is ``DONE``.

        Parameters
        ----------
        tasks : List[Task]
            Current board snapshot.

        Returns
        -------
        bool
            ``True`` if all tasks have reached ``DONE``.
        """
        return all(t.status == TaskStatus.DONE for t in tasks)

    def _work_seconds(self, task: Task) -> float:
        """Wall-clock seconds the agent spends on ``task``.

        Parameters
        ----------
        task : Task
            The task being worked.

        Returns
        -------
        float
            ``estimated_hours / speed``, floored at
            :data:`_MIN_STEP_SECONDS`.
        """
        return max(self._MIN_STEP_SECONDS, task.estimated_hours / self.speed)

    def _blocker_seconds(self) -> float:
        """Wall-clock seconds a task stays ``blocked`` before recovery.

        Returns
        -------
        float
            A short pause scaled by the virtual clock.
        """
        return max(self._MIN_STEP_SECONDS, 2.0 / self.speed)
