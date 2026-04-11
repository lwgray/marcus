#!/usr/bin/env python3
"""
GH-320 Experiment 4 — contract-first decomposition smoke test.

Connects to a running Marcus HTTP server, creates a project with
``MARCUS_DECOMPOSER=contract_first`` enabled via the options dict,
waits for Phase A (background design content + contract generation)
to complete, and verifies the contract-first invariants:

1. More than one domain was discovered (single-domain PRDs collapse
   to the same topology-coupling failure mode contract-first is
   supposed to solve — the Experiment is vacuous on a 1-domain
   project).
2. Implementation tasks carry ``Task.responsibility`` set (or have
   the ``MARCUS_CONTRACT_FIRST`` marker embedded in their
   description as the persistence fallback).
3. The integration verification task's description includes the
   ``CONTRACT-FIRST PROJECT`` preamble naming the contract file.

This is a pipeline validation gate. It does NOT spawn agents or
measure contribution distribution — that is the full Experiment 4
and requires multi-agent orchestration outside this script.

If all three invariants hold, PR #327's contract-first path is
wired correctly end-to-end and the real Experiment 4 (2-agent
snake or dashboard run) can proceed. If any invariant fails, this
script reports which one and PR #327 needs a fix before burning
agent API credits.

Usage
-----
Prerequisites:
    - Marcus HTTP server running (``python -m src.marcus_mcp.server --http``)
    - Default endpoint: ``http://localhost:4298/mcp``
    - A writable ``project_root`` for the test project (defaults to
      ``/tmp/gh320_experiment_4_smoke_<timestamp>``)

Run:
    python dev-tools/examples/gh320_experiment_4_smoke.py
"""

from __future__ import annotations

import asyncio
import json
import re
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to sys.path so imports resolve when running this
# script directly from the dev-tools/examples directory.
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.worker.inspector import Inspector  # noqa: E402

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

MARCUS_URL = "http://localhost:4298/mcp"
PROJECT_NAME = f"gh320_smoke_{int(time.time())}"
PROJECT_ROOT = f"/tmp/{PROJECT_NAME}"  # nosec B108 — smoke test temp dir

# Rich description that forces at least 2 domains.
#
# The dashboard-v16 experiment proved feature-based decomposition
# could split Weather and Time cleanly when the PRD described them
# as independent concerns. The prior smoke test (2026-04-11)
# collapsed "weather + time widgets" into one domain because the
# description was too terse. This version is explicit about
# ownership boundaries and data-flow independence.
PROJECT_DESCRIPTION = (
    "Build a dashboard web app with two independent widgets that "
    "share no state or code.\n\n"
    "1. WeatherWidget: fetches current weather from a public API "
    "(e.g. OpenWeatherMap), displays temperature and conditions, "
    "refreshes every 10 minutes. Owns all weather-related data "
    "fetching, state management, and rendering.\n\n"
    "2. TimeWidget: displays the current local time and updates "
    "every second. Supports optional timezone selection. Owns all "
    "time-related state and rendering. No network calls.\n\n"
    "The two widgets must be fully independent modules. Each widget "
    "owns its own data fetching and its own display logic. They "
    "communicate only through a shared Dashboard container "
    "component that arranges them on the page. The WeatherWidget "
    "must never import from the TimeWidget and vice versa."
)
# Note: the word "test" was intentionally removed from the description
# because ``should_add_integration_task`` substring-matches the skip
# keyword "test" against the description. Using "test suite" here
# would cause Marcus to skip the integration verification task and
# invariant 3 would fail for the wrong reason. This is a pre-existing
# bug in integration_verification.py, tracked separately.

# --------------------------------------------------------------------------
# MCP result parsing helpers
# --------------------------------------------------------------------------


KANBAN_DB_PATH = project_root / "data" / "kanban.db"


def _read_sqlite_tasks_for_project(project_id: str) -> List[Dict[str, Any]]:
    """
    Read task records for a project directly from the SQLite kanban.

    Marcus's MCP surface doesn't expose a "list all tasks on the board"
    tool — ``query_project_history`` returns historical tasks from the
    project_history store, which is empty for a fresh project.
    ``get_task_context`` returns dependency context (artifacts,
    decisions, dependent tasks) but NOT the task's own fields. For
    this smoke test we read directly from the SQLite kanban provider
    since we're running on localhost and the schema is stable.

    Parameters
    ----------
    project_id : str
        Project ID returned by ``create_project``.

    Returns
    -------
    List[Dict[str, Any]]
        Task dicts with fields: id, name, description, source_context
        (parsed JSON), labels (list of strings), project_id.
    """
    if not KANBAN_DB_PATH.exists():
        print(f"  ⚠️  kanban.db not found at {KANBAN_DB_PATH}")
        return []

    conn = sqlite3.connect(str(KANBAN_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        task_rows = conn.execute(
            "SELECT id, name, description, source_type, source_context, "
            "provides, requires, project_id "
            "FROM tasks WHERE project_id = ?",
            (project_id,),
        ).fetchall()

        tasks: List[Dict[str, Any]] = []
        for row in task_rows:
            # Labels live in a separate join table.
            label_rows = conn.execute(
                "SELECT label FROM task_labels WHERE task_id = ?",
                (row["id"],),
            ).fetchall()
            labels = [r["label"] for r in label_rows]

            # source_context is JSON-serialized text
            source_context: Optional[Dict[str, Any]] = None
            if row["source_context"]:
                try:
                    source_context = json.loads(row["source_context"])
                except (json.JSONDecodeError, TypeError):
                    source_context = None

            tasks.append(
                {
                    "id": row["id"],
                    "name": row["name"],
                    "description": row["description"] or "",
                    "source_type": row["source_type"],
                    "source_context": source_context,
                    "provides": row["provides"],
                    "requires": row["requires"],
                    "labels": labels,
                    # ``responsibility`` is NOT a top-level SQLite
                    # column as of 2026-04-11. Contract-first tasks
                    # persist responsibility via source_context and
                    # via the MARCUS_CONTRACT_FIRST description marker.
                    # check_task_responsibility reads both fallbacks.
                }
            )
        return tasks
    finally:
        conn.close()


def _extract_result_data(result: Any) -> Dict[str, Any]:
    """
    Extract the JSON payload from an MCP CallToolResult.

    MCP results wrap the payload in a ``content`` list of text
    blocks. This helper returns the parsed JSON from the first
    text block, or an empty dict if nothing is found.
    """
    if not hasattr(result, "content") or not result.content:
        return {}
    text = result.content[0].text if result.content else ""
    if not text:
        return {}
    try:
        parsed: Dict[str, Any] = json.loads(text)
        return parsed
    except (json.JSONDecodeError, TypeError):
        return {}


# --------------------------------------------------------------------------
# Invariant checks
# --------------------------------------------------------------------------


def check_domain_count(project_root_path: Path) -> Dict[str, Any]:
    """
    Check how many domains were discovered via artifact file tree.

    Phase A writes each domain's artifacts under a filename
    pattern like ``{domain-slug}-architecture.md``,
    ``{domain-slug}-api-contracts.md``, etc. Counting unique
    slug prefixes tells us how many distinct domains were
    discovered without needing to parse state or query Marcus.

    Parameters
    ----------
    project_root_path : Path
        Project root directory where Phase A wrote its artifacts.

    Returns
    -------
    Dict[str, Any]
        ``{"pass": bool, "count": int, "domains": List[str]}``
    """
    docs_dir = project_root_path / "docs"
    if not docs_dir.exists():
        return {
            "pass": False,
            "count": 0,
            "domains": [],
            "error": f"docs/ not found at {docs_dir}",
        }

    artifact_files: List[Path] = []
    for subdir in ("api", "architecture", "specifications", "design"):
        d = docs_dir / subdir
        if d.exists():
            artifact_files.extend(d.glob("*.md"))

    # Domain slug is everything before the last "-<type>" suffix.
    # e.g. "weather-widget-api-contracts.md" → "weather-widget"
    type_suffixes = (
        "-api-contracts",
        "-architecture",
        "-data-models",
        "-interface-contracts",
        "-design",
    )
    domains: set[str] = set()
    for f in artifact_files:
        stem = f.stem
        for suffix in type_suffixes:
            if stem.endswith(suffix):
                domains.add(stem[: -len(suffix)])
                break
        else:
            # Fallback: use the whole stem as the domain slug
            domains.add(stem)

    return {
        "pass": len(domains) >= 2,
        "count": len(domains),
        "domains": sorted(domains),
        "artifact_files": [
            str(f.relative_to(project_root_path)) for f in artifact_files
        ],
    }


def check_task_responsibility(tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Check whether implementation tasks carry contract-first metadata.

    Looks for ``responsibility`` field on each task OR the
    ``MARCUS_CONTRACT_FIRST`` marker in the task description
    (the persistence fallback added in response to Codex P1).

    Parameters
    ----------
    tasks : List[Dict[str, Any]]
        Task dicts from Marcus project history or state.

    Returns
    -------
    Dict[str, Any]
        ``{"pass": bool, "total_impl": int, "with_responsibility": int,
           "examples": List[Dict]}``
    """
    marker_pattern = re.compile(
        r"<!--\s*MARCUS_CONTRACT_FIRST.*?responsibility:\s*([^\n]+)",
        re.DOTALL,
    )

    impl_tasks = [
        t
        for t in tasks
        if "implement" in (t.get("name", "") or "").lower()
        or "implementation" in (t.get("labels") or [])
    ]

    with_resp: List[Dict[str, Any]] = []
    for t in impl_tasks:
        resp = t.get("responsibility")
        source_context = t.get("source_context") or {}
        sc_resp = source_context.get("responsibility")
        description = t.get("description") or ""
        marker_match = marker_pattern.search(description)

        if resp or sc_resp or marker_match:
            resolved = resp or sc_resp
            if not resolved and marker_match:
                resolved = marker_match.group(1).strip()
            with_resp.append(
                {
                    "name": t.get("name"),
                    "responsibility": resolved,
                    "source": (
                        "direct"
                        if resp
                        else "source_context" if sc_resp else "description_marker"
                    ),
                }
            )

    return {
        "pass": len(with_resp) > 0 and len(with_resp) == len(impl_tasks),
        "total_impl": len(impl_tasks),
        "with_responsibility": len(with_resp),
        "examples": with_resp[:5],
    }


def check_agent_prompt_contract_layer(
    instructions_text: str,
) -> Dict[str, Any]:
    """
    Check that agent instructions contain the CONTRACT RESPONSIBILITY layer.

    This closes the last gap left by Codex P1: we know the
    responsibility metadata is persisted (invariant 2) and the
    integration preamble fires (invariant 3), but those checks read
    state directly — neither proves the metadata reaches an agent.

    ``build_tiered_instructions`` Layer 1.3 is supposed to add a
    ``CONTRACT RESPONSIBILITY`` section to the returned instructions
    when ``_parse_contract_metadata`` resolves a non-empty
    responsibility via any of its three fallback paths. If that
    section is absent, either:

    1. ``_parse_contract_metadata`` isn't resolving responsibility
       for the task the agent happened to pick up, OR
    2. Layer 1.3 isn't firing for some other reason (ordering bug,
       label filter, etc.), OR
    3. ``generate_task_instructions`` is short-circuiting to a
       fallback path that skips the tiered layer builder.

    Any of those breaks contract-first in practice even though the
    data is technically present in state.

    Parameters
    ----------
    instructions_text : str
        The ``instructions`` field returned by ``request_next_task``.

    Returns
    -------
    Dict[str, Any]
        ``{"pass": bool, "has_layer": bool, "has_contract_file": bool,
           "excerpt": str}``
    """
    if not instructions_text:
        return {
            "pass": False,
            "has_layer": False,
            "has_contract_file": False,
            "excerpt": "",
            "error": "instructions field is empty",
        }

    has_layer = "CONTRACT RESPONSIBILITY" in instructions_text
    has_contract_file = (
        "Contract file:" in instructions_text or ".md" in instructions_text
    )
    has_read_directive = (
        "Read" in instructions_text and "before" in instructions_text.lower()
    )

    # Find the layer section and extract ~600 chars for the report
    excerpt = ""
    if has_layer:
        idx = instructions_text.find("CONTRACT RESPONSIBILITY")
        excerpt = instructions_text[idx : idx + 600]

    return {
        "pass": has_layer and has_contract_file and has_read_directive,
        "has_layer": has_layer,
        "has_contract_file": has_contract_file,
        "has_read_directive": has_read_directive,
        "excerpt": excerpt,
    }


def check_contract_cross_file_consistency(
    project_root_path: Path,
) -> Dict[str, Any]:
    """
    Check no field has contradictory types across contract files.

    Per-domain contracts are supposed to scope to their own domain
    and reference other domains by name only. If an LLM prompt fails
    to enforce that scope, multiple contract files end up describing
    the same shared field (e.g. ``time.lastUpdated``) with different
    types in each file. Agents assigned one file each will then
    produce incompatible code — the exact silent-drift failure mode
    contract-first decomposition is supposed to prevent.

    This check parses each interface-contracts.md, extracts
    ``field_name (type)`` patterns, and cross-references them across
    files. Any field name appearing in ≥2 files with ≠ types is a
    contradiction.

    The regex catches two common markdown conventions:
    - bullet form: ``- fieldName (type) — description``
    - tree form:   ``├── fieldName (type) — description``

    Heuristic, not perfect. It will miss contradictions in prose form
    and it will flag benign duplicates where the two files use slightly
    different type vocabulary for the same concept (e.g. ``string`` vs
    ``ISO 8601 string``). The goal is to catch the obvious scope bugs
    before Experiment 4 burns agent credits, not to be an exhaustive
    type checker.

    Parameters
    ----------
    project_root_path : Path
        Project root where Phase A wrote its artifacts.

    Returns
    -------
    Dict[str, Any]
        ``{"pass": bool, "contradictions": List[Dict], "total_fields": int,
           "unique_fields": int, "files_scanned": int}``
    """
    spec_dir = project_root_path / "docs" / "specifications"
    if not spec_dir.exists():
        return {
            "pass": False,
            "contradictions": [],
            "total_fields": 0,
            "unique_fields": 0,
            "files_scanned": 0,
            "error": f"specifications/ not found at {spec_dir}",
        }

    contract_files = list(spec_dir.glob("*-interface-contracts.md"))
    if len(contract_files) < 2:
        # Can't have contradictions across fewer than 2 files
        return {
            "pass": True,
            "contradictions": [],
            "total_fields": 0,
            "unique_fields": 0,
            "files_scanned": len(contract_files),
            "note": "fewer than 2 contract files; nothing to cross-check",
        }

    # Strict pattern: only match real type annotations. Requires
    # either a primitive type keyword (string/number/boolean/object/
    # array) or a recognizable shape like "ISO 8601" inside the
    # parentheses, OR a type-like first token that isn't an English
    # word. This eliminates false positives where prose in
    # parentheses (e.g. "(on initialization)", "(for rendering)")
    # was being captured as a "type".
    type_like_pattern = re.compile(
        r"[-*]\s+`?(\w[\w.]*)`?\s*\(\s*("
        r"(?:string|number|boolean|integer|float|object|array|"
        r"date|datetime|json|null|void|bigint)"
        r"(?:\s*\|\s*(?:string|number|boolean|null))*"
        r"(?:[^)]*)"
        r")\s*\)",
        re.IGNORECASE,
    )

    # field_name -> {file_path: type_str}
    field_types: Dict[str, Dict[str, str]] = {}
    total_fields = 0

    # Skip identifiers that are CamelCase type names (interface/class
    # references, not fields) and obviously-not-a-field tokens.
    skip_canonicals = {
        "id",
        "string",
        "number",
        "boolean",
        "yes",
        "no",
        "true",
        "false",
        "null",
        "none",
    }

    for contract_file in contract_files:
        content = contract_file.read_text()
        relative_name = contract_file.name

        for match in type_like_pattern.finditer(content):
            field_name = match.group(1).strip()
            type_str = match.group(2).strip()
            total_fields += 1

            # Normalize compound field names: `weather.temperature`
            # and `temperature` collide when they refer to the same
            # concept. Use the last dotted segment as the canonical
            # key, but keep the full path in the report.
            canonical = field_name.split(".")[-1].lower()
            if (
                len(canonical) < 3
                or canonical in skip_canonicals
                # Skip CamelCase type/interface names like WeatherWidget
                or (
                    field_name[0].isupper() and any(c.isupper() for c in field_name[1:])
                )
            ):
                continue

            field_types.setdefault(canonical, {})
            field_types[canonical][relative_name] = type_str

    contradictions: List[Dict[str, Any]] = []
    for field_name, file_type_map in field_types.items():
        if len(file_type_map) < 2:
            continue
        # Normalize types for comparison (strip whitespace,
        # collapse synonyms loosely)
        type_set = {_normalize_type(t) for t in file_type_map.values()}
        if len(type_set) > 1:
            contradictions.append(
                {
                    "field": field_name,
                    "types_by_file": file_type_map,
                }
            )

    return {
        "pass": len(contradictions) == 0,
        "contradictions": contradictions,
        "total_fields": total_fields,
        "unique_fields": len(field_types),
        "files_scanned": len(contract_files),
    }


def _normalize_type(type_str: str) -> str:
    """
    Normalize a type string for cross-file comparison.

    Collapses whitespace, strips markdown formatting, strips common
    qualifiers (required, optional, nullable), and maps common
    synonyms to canonical types. Deliberately lenient: the goal is
    to catch ``ISO 8601 string`` vs ``Date object`` (a real
    contradiction), not ``string`` vs ``string, required``
    (stylistic variation on the same type).
    """
    t = type_str.lower().strip().strip("`")
    t = re.sub(r"\s+", " ", t)

    # Normalize union syntax: "X or Y" → "X | Y"
    t = re.sub(r"\bor\b", "|", t)
    # Collapse spaces around union pipes
    t = re.sub(r"\s*\|\s*", "|", t)

    # Strip common qualifiers that describe optionality, not type
    qualifiers = [
        ", required",
        ", optional",
        ", nullable",
        " required",
        " optional",
        " nullable",
    ]
    for qual in qualifiers:
        t = t.replace(qual, "")
    t = t.strip().rstrip(",").strip()

    # Strip descriptive tails after a comma: "string, IANA timezone
    # identifier" → "string". Keep only the primary type token.
    # Apply cautiously — only strip if the head is a recognized type.
    head_types = {
        "string",
        "number",
        "boolean",
        "integer",
        "float",
        "object",
        "array",
        "date",
        "datetime",
        "null",
    }
    if "," in t:
        head = t.split(",", 1)[0].strip()
        if head in head_types:
            t = head

    # Collapse common string subtypes to "string"
    string_synonyms = [
        "iso 8601 string",
        "iso8601 string",
        "iso string",
        "iso 8601",
        "text",
    ]
    for syn in string_synonyms:
        if syn in t:
            return "string"

    # Collapse number subtypes
    if any(
        x in t
        for x in [
            "unix timestamp",
            "milliseconds",
            "millisecond",
            "seconds",
            " ms",
        ]
    ):
        return "number"

    # Collapse common date-like types
    if t in {"date", "datetime", "date object"}:
        return "date"

    return t


def check_integration_preamble(tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Check that integration verification task has CONTRACT-FIRST preamble.

    When contract-first is active, ``IntegrationTaskGenerator``
    prepends a ``CONTRACT-FIRST PROJECT`` block to the task
    description instructing the integration agent to treat the
    contract as authoritative.

    Parameters
    ----------
    tasks : List[Dict[str, Any]]
        Task dicts from Marcus project history or state.

    Returns
    -------
    Dict[str, Any]
        ``{"pass": bool, "has_preamble": bool, "description_excerpt": str}``
    """
    integration_tasks = [
        t
        for t in tasks
        if "integration" in (t.get("labels") or [])
        or "integration verification" in (t.get("name", "") or "").lower()
    ]
    if not integration_tasks:
        return {
            "pass": False,
            "has_preamble": False,
            "error": "No integration task found on the board",
        }

    task = integration_tasks[0]
    description = task.get("description") or ""
    has_preamble = "CONTRACT-FIRST PROJECT" in description

    return {
        "pass": has_preamble,
        "has_preamble": has_preamble,
        "description_excerpt": description[:500],
        "task_id": task.get("id"),
        "task_name": task.get("name"),
    }


# --------------------------------------------------------------------------
# Main smoke test
# --------------------------------------------------------------------------


async def main() -> int:
    """Run the smoke test. Returns 0 on pass, 1 on fail."""
    print("\n" + "=" * 70)
    print("🔬 GH-320 Experiment 4 — Contract-first smoke test")
    print("=" * 70)
    print(f"\n  Project name: {PROJECT_NAME}")
    print(f"  Project root: {PROJECT_ROOT}")
    print(f"  Marcus URL:   {MARCUS_URL}")
    print()

    # Create project_root ahead of time so log_artifact's
    # project_root_path.exists() check passes.
    Path(PROJECT_ROOT).mkdir(parents=True, exist_ok=True)

    client = Inspector(connection_type="http")

    try:
        async with client.connect(url=MARCUS_URL) as session:
            # Authenticate as admin
            print("🔐 Authenticating as admin...")
            await session.call_tool(
                "authenticate",
                arguments={
                    "client_id": "gh320-smoke",
                    "client_type": "admin",
                    "role": "admin",
                    "metadata": {"test_mode": True, "experiment": "gh320_smoke"},
                },
            )
            print("✅ Authenticated")

            # Create project with contract_first enabled
            print("\n📝 Creating project with MARCUS_DECOMPOSER=contract_first...")
            create_result = await session.call_tool(
                "create_project",
                arguments={
                    "description": PROJECT_DESCRIPTION,
                    "project_name": PROJECT_NAME,
                    "options": {
                        "mode": "new_project",
                        "decomposer": "contract_first",
                        "project_root": PROJECT_ROOT,
                        "complexity": "prototype",
                        "agent_count": 2,
                    },
                },
            )
            create_data = _extract_result_data(create_result)
            if not create_data.get("success") and not create_data.get("result", {}).get(
                "success"
            ):
                print("❌ create_project failed")
                print(json.dumps(create_data, indent=2))
                return 1

            # Unwrap Marcus's double-nested result envelope
            result_body = create_data.get("result", create_data)
            project_id = result_body.get("project_id")
            tasks_created = result_body.get("tasks_created", 0)
            print(f"✅ Project created: id={project_id}, tasks_created={tasks_created}")

            # Wait for Phase A (background design content + contract
            # generation). Phase A runs as an ensure_future closure
            # after create_project returns — we need to poll until
            # the artifact files land on disk.
            print("\n⏳ Waiting for Phase A (up to 120s)...")
            artifact_dir = Path(PROJECT_ROOT) / "docs"
            deadline = time.time() + 120
            while time.time() < deadline:
                if artifact_dir.exists() and any(artifact_dir.rglob("*.md")):
                    # Give Phase A a few more seconds to finish all
                    # 4-5 LLM calls for the full artifact set and the
                    # scaffold generation.
                    await asyncio.sleep(10)
                    break
                await asyncio.sleep(5)
            else:
                print("⚠️  Phase A timed out (no artifacts in 120s)")

            # ---- Invariant 1: domain count ----
            print("\n" + "-" * 70)
            print("🧪 Invariant 1: domain count >= 2")
            print("-" * 70)
            domain_check = check_domain_count(Path(PROJECT_ROOT))
            print(f"  Pass: {domain_check['pass']}")
            print(f"  Count: {domain_check['count']}")
            print(f"  Domains: {domain_check['domains']}")
            if "artifact_files" in domain_check:
                print("  Artifact files:")
                for f in domain_check["artifact_files"]:
                    print(f"    - {f}")
            if "error" in domain_check:
                print(f"  Error: {domain_check['error']}")

            # Query task state by calling get_task_context for each
            # task_id from the create_project response. project_history
            # is empty for fresh projects — task state lives on the
            # kanban board and the get_task_context MCP tool surfaces
            # it (including source_context, description with embedded
            # marker, and contract-first metadata).
            print("\n📊 Fetching task details via get_task_context...")
            task_ids = result_body.get("task_ids", [])
            print(f"  create_project returned {len(task_ids)} task_ids")

            tasks: List[Dict[str, Any]] = []
            for task_id in task_ids:
                ctx_result = await session.call_tool(
                    "get_task_context",
                    arguments={"task_id": task_id},
                )
                ctx_data = _extract_result_data(ctx_result)
                # get_task_context returns:
                # {"success": True, "context": {...}} where context has
                # the task dict shape. But we need the full task
                # including name and source_context, which lives on
                # the kanban state object not in get_task_context.
                # As a fallback, pull the context dict and synthesize
                # a task-like dict.
                ctx = ctx_data.get("context") or ctx_data.get("result", {}).get(
                    "context", {}
                )
                # ctx contains artifacts, decisions, dependencies —
                # NOT the task's own fields. For this smoke test we
                # rely on the kanban state being queryable via
                # list_projects on the same board.
                tasks.append(
                    {
                        "id": task_id,
                        "context": ctx,
                    }
                )

            # Alternative: pull tasks by querying the SQLite kanban
            # directly since we're on localhost and know the provider.
            # project_id + board_id are in the create_project result.
            print(
                "\n  (get_task_context returns dependency context, not "
                "task fields — reading kanban DB for task records)"
            )
            tasks = _read_sqlite_tasks_for_project(project_id)
            print(f"  Loaded {len(tasks)} tasks from kanban.db")

            # ---- Invariant 2: Task.responsibility set on impl tasks ----
            print("\n" + "-" * 70)
            print("🧪 Invariant 2: implementation tasks carry contract-first metadata")
            print("-" * 70)
            resp_check = check_task_responsibility(tasks)
            print(f"  Pass: {resp_check['pass']}")
            print(f"  Total impl tasks: {resp_check['total_impl']}")
            print(f"  With responsibility: {resp_check['with_responsibility']}")
            if resp_check["examples"]:
                print("  Examples:")
                for ex in resp_check["examples"]:
                    print(
                        f"    - {ex['name']}: {ex['responsibility']} "
                        f"(source={ex['source']})"
                    )

            # ---- Invariant 3: integration task has contract preamble ----
            print("\n" + "-" * 70)
            print("🧪 Invariant 3: integration task has CONTRACT-FIRST preamble")
            print("-" * 70)
            int_check = check_integration_preamble(tasks)
            print(f"  Pass: {int_check['pass']}")
            print(f"  Has preamble: {int_check.get('has_preamble', False)}")
            if "error" in int_check:
                print(f"  Error: {int_check['error']}")
            if "description_excerpt" in int_check:
                print("  Description excerpt (first 500 chars):")
                excerpt = int_check["description_excerpt"]
                for line in excerpt.split("\n")[:15]:
                    print(f"    {line}")

            # ---- Invariant 4: Agent prompt actually surfaces the
            # CONTRACT RESPONSIBILITY layer ----
            #
            # Register a smoke-test agent and call request_next_task.
            # Unlike invariants 2 and 3 which read state directly,
            # this exercises the full instruction-building pipeline
            # an agent actually hits. Closes Codex P1 end-to-end.
            print("\n" + "-" * 70)
            print("🧪 Invariant 4: agent prompt contains CONTRACT RESPONSIBILITY")
            print("-" * 70)
            agent_id = f"smoke-agent-{int(time.time())}"
            print(f"  Registering test agent: {agent_id}")
            await session.call_tool(
                "register_agent",
                arguments={
                    "agent_id": agent_id,
                    "name": "Smoke Test Agent",
                    "role": "Developer",
                    "skills": ["typescript", "react", "nodejs"],
                },
            )

            print(f"  Calling request_next_task for {agent_id}")
            task_result = await session.call_tool(
                "request_next_task",
                arguments={"agent_id": agent_id},
            )
            task_data = _extract_result_data(task_result)
            task_body = task_data.get("result", task_data)

            # request_next_task may return {"success": True, "task": {...},
            # "instructions": "..."} or nested under "result"
            instructions_text = (
                task_body.get("instructions")
                or task_body.get("task", {}).get("instructions")
                or ""
            )
            assigned_task = task_body.get("task") or {}
            assigned_name = assigned_task.get("name", "<unknown>")
            print(f"  Task assigned: {assigned_name}")
            print(f"  Instructions length: {len(instructions_text)} chars")

            prompt_check = check_agent_prompt_contract_layer(instructions_text)
            print(f"  Pass: {prompt_check['pass']}")
            print(f"  Has CONTRACT RESPONSIBILITY layer: {prompt_check['has_layer']}")
            print(
                f"  Has contract file reference: "
                f"{prompt_check['has_contract_file']}"
            )
            print(
                f"  Has read-before-code directive: "
                f"{prompt_check['has_read_directive']}"
            )
            if "error" in prompt_check:
                print(f"  Error: {prompt_check['error']}")
            if prompt_check["excerpt"]:
                print("  Layer excerpt:")
                for line in prompt_check["excerpt"].split("\n")[:20]:
                    print(f"    {line}")

            # ---- Invariant 5: no cross-file type contradictions ----
            #
            # Per-domain contract files must not redefine fields
            # owned by other domains. When the LLM prompt fails to
            # scope per-domain, the same shared field (e.g.
            # ``time.lastUpdated``) appears in multiple files with
            # contradictory types. Agents assigned one file each
            # then produce mutually-incompatible code. Kaia flagged
            # this on 2026-04-11 as the last unverified pre-flight
            # check — prompt scope clamp shipped in the same PR.
            print("\n" + "-" * 70)
            print("🧪 Invariant 5: no cross-file type contradictions")
            print("-" * 70)
            consistency_check = check_contract_cross_file_consistency(
                Path(PROJECT_ROOT)
            )
            print(f"  Pass: {consistency_check['pass']}")
            print(f"  Files scanned: {consistency_check['files_scanned']}")
            print(f"  Total fields parsed: {consistency_check['total_fields']}")
            print(f"  Unique field names: {consistency_check['unique_fields']}")
            print(f"  Contradictions: {len(consistency_check['contradictions'])}")
            if "error" in consistency_check:
                print(f"  Error: {consistency_check['error']}")
            if "note" in consistency_check:
                print(f"  Note: {consistency_check['note']}")
            if consistency_check["contradictions"]:
                print("  Contradictory fields (first 5):")
                for c in consistency_check["contradictions"][:5]:
                    print(f"    - {c['field']}:")
                    for fname, type_str in c["types_by_file"].items():
                        print(f"        {fname}: {type_str}")

            # ---- Summary ----
            print("\n" + "=" * 70)
            print("📋 Summary")
            print("=" * 70)
            invariants = {
                "Domain count >= 2": domain_check["pass"],
                "Impl tasks have responsibility": resp_check["pass"],
                "Integration task has preamble": int_check["pass"],
                "Agent prompt contains CONTRACT RESPONSIBILITY": prompt_check["pass"],
                "No cross-file type contradictions": consistency_check["pass"],
            }
            for name, passed in invariants.items():
                icon = "✅" if passed else "❌"
                print(f"  {icon} {name}")

            all_pass = all(invariants.values())
            print()
            if all_pass:
                print("🎉 All invariants hold. Pipeline is wired correctly.")
                print("    Real Experiment 4 (2-agent run) can proceed.")
                return 0
            print("⚠️  One or more invariants failed.")
            print("    PR #327 contract-first path needs investigation")
            print("    before running the full Experiment 4.")
            return 1

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
