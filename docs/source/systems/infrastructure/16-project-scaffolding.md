# Project Scaffolding

## Status

| Field | Value |
|-------|-------|
| Status | Implemented |
| Version | 1.0 |
| Date | 2026-04-03 |

## Problem

With git worktree isolation (#250), each agent gets its own worktree
branched from main. But if there's no project structure on main, both
agents independently scaffold the same project — package manifest, build
config, entry point, shared types. This creates:

- **Duplicated work** — both agents spend tokens on identical scaffolding
- **Guaranteed merge conflicts** — on every shared file (package.json,
  main.tsx, App.tsx, tsconfig.json)
- **Negative efficiency** — two agents scaffolding + resolving conflicts
  is slower than one agent doing everything

This is Finding 5 from GH-301: isolation without shared infrastructure
creates more waste than no isolation at all.

## Solution

Phase A.5 — after design artifact generation (Phase A) and before task
board creation. Marcus reads the architecture document it just produced
and generates the project scaffold via one LLM call.

The scaffold is committed to main. When worktrees are created, they
inherit the scaffold. Agents start with a working project structure
and only write their component code.

## What the Scaffold Contains

The LLM determines the right scaffold based on the architecture document.
Marcus does not hardcode what goes in the scaffold — the project can be
anything (React dashboard, Python pipeline, Rust game, MCP server).

Typical scaffold includes:

- **Package manifest** — package.json, pyproject.toml, Cargo.toml, etc.
- **Build configuration** — tsconfig, vite.config, eslint, etc.
- **Entry point** — main.tsx, main.py, main.rs, etc.
- **App shell** — base component that imports/renders child components
- **Shared configuration** — .gitignore, .env.example, etc.
- **Empty placeholder files** — one per implementation task

### Placeholder Files

Each implementation task gets an empty file at the path the architecture
document specifies. The file contains only a comment:

```
// TimeWidget — implementation task for agent
```

This serves as a territorial marker. When an agent opens its worktree
and sees `src/components/TimeWidget.tsx` exists, it knows that file is
its responsibility. When it sees `src/components/WeatherWidget.tsx` also
exists, it knows that belongs to another agent's task.

No function stubs. No exports. No implementation code. Just the file
and a comment. The agent decides everything about how to implement it.

## Pipeline Position

```
Phase A:     Design artifacts (architecture, API, data models)
Phase A.5:   Project scaffold ← THIS
             Committed to main via git add + git commit
Board:       Tasks created on kanban
Worktrees:   Branch from main HEAD (inherits design + scaffold)
Workers:     Start with working project structure
```

## How It Works

`_generate_project_scaffold()` in `src/integrations/nlp_tools.py`:

1. Reads the architecture document from `design_content`
2. Builds a list of implementation task names from `safe_tasks`
3. Sends both to the LLM with `_SCAFFOLD_PROMPT`
4. LLM returns a JSON array of `{path, content}` file objects
5. Each file is written to `project_root` (implementation/ on main)
6. Files are committed to main via `git add -A && git commit`

The LLM prompt instructs:
- Generate shared infrastructure files for the project type
- Create one empty placeholder file per implementation task
- No function stubs or implementation code in placeholders
- File paths should match the architecture document's conventions

## Graceful Degradation

If the LLM call fails or returns unparseable JSON, scaffolding is
skipped. Agents scaffold independently (the old behavior). This is
logged as a warning but does not block project creation.

## Implementation Files

| File | Function |
|------|----------|
| `src/integrations/nlp_tools.py` | `_generate_project_scaffold()` and `_SCAFFOLD_PROMPT` |
| `src/integrations/nlp_tools.py` | Wired in Phase A block after `_generate_design_content()` |

## Related

- #250 — Git worktree isolation (scaffolding prevents duplicated work)
- #297 — Design autocomplete (scaffold reads the architecture doc)
- #300 — Per-component design artifacts (includes scaffolding)
- #301 — Four findings (Finding 5: isolation without shared infrastructure)

## See Also

- [15-git-worktree-isolation.md](15-git-worktree-isolation.md) — worktree lifecycle
- [52-design-autocomplete.md](../coordination/52-design-autocomplete.md) — Phase A
