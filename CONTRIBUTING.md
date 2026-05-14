# Contributing to Marcus

Thanks for contributing. This guide is short on purpose. The [README](README.md) covers what Marcus is and how to run it — this file covers the rules for changing it.

---

## TL;DR

1. Fork → branch from `develop` → PR back to `develop` (never `main`).
2. Conventional commit messages (`feat:`, `fix:`, `docs:`...).
3. `pre-commit run --all-files` + `pytest tests/unit/` must pass.
4. New code: NumPy-style docstrings, type hints, ≥80% coverage.

---

## 1. Set up your environment

Follow the [README Quickstart](README.md#get-started) to install Marcus and pick an LLM provider. Then add the dev extras:

```bash
pip install -r requirements-dev.txt
pre-commit install
```

That's it. The SQLite kanban provider is the default — you don't need Docker or Planka unless you want the visual board.

### Free option: Ollama

You can develop without any paid API key. Recommended model:

```bash
# Install Ollama: https://ollama.ai
ollama pull qwen3.5:35b-a3b-coding-nvfp4
```

Point the **planner** at it in `config_marcus.json`:

```json
"ai": {
  "provider": "local",
  "model": "qwen3.5:35b-a3b-coding-nvfp4"
}
```

Then launch each **worker** against the same model:

```bash
ollama launch code --model qwen3.5:35b-a3b-coding-nvfp4
```

Marcus needs both — the planner decomposes the project, workers write the code. On 16GB RAM expect to cap at 1 planner + 2 workers. Smaller machines (8GB) can substitute `qwen2.5-coder:7b` or `deepseek-coder:6.7b`. All Marcus features work with local or cloud models. Full guide: [Setup Local LLM](docs/source/getting-started/setup-local-llm.md).

---

## 2. Branching

Marcus uses a `develop` branch workflow. `main` is protected for releases.

```bash
git remote add upstream https://github.com/lwgray/marcus.git
git checkout develop
git pull upstream develop
git checkout -b fix/<issue-number>     # or feat/<short-name>
```

Open PRs against `develop`. Rebase on `upstream/develop` before pushing if your branch is stale.

---

## 3. Commit messages

[Conventional Commits](https://www.conventionalcommits.org/). Subject ≤ 70 chars. Scope is optional.

```
feat(worker): add exponential backoff for retries
fix(kanban): handle GitHub API rate limits
docs(readme): clarify ollama setup
test(core): cover task dependency resolution
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`.

---

## 4. Code quality

Pre-commit hooks run on every commit: Black, isort, Ruff, MyPy, detect-secrets, YAML/JSON validation.

```bash
pre-commit run --all-files     # everything
mypy src/                      # types only
ruff check --fix src/          # autofix lint
black src/ && isort src/       # format
```

All checks must pass before review.

---

## 5. Tests

```bash
pytest -m unit                                          # fast (CI baseline)
pytest --cov=src --cov-report=html                      # with coverage
pytest tests/unit/core/test_task_manager.py             # one file
```

**Placement** — unit tests go in `tests/unit/{ai,core,mcp,visualization}/`. Anything that needs DB, network, or files goes in `tests/integration/`. Unimplemented features go in `tests/future_features/`. Full rules in [CLAUDE.md](CLAUDE.md#test_writing_instructions).

**Required for new code**: NumPy-style docstrings, type hints, ≥80% coverage, Arrange-Act-Assert, one logical assertion per test, mock all external services in unit tests.

---

## 6. Code style

- PEP 8 + Black (88 char lines)
- Type hints on every public function
- NumPy-style docstrings on every public class/function (see CLAUDE.md)
- Marcus Error Framework for user/agent-facing errors — regular Python exceptions only for internal programming bugs ([details](CLAUDE.md#error_handling_framework))
- Structured logging, no `print()`

---

## 7. Pull requests

Open the PR against `develop`. The template will appear — fill in:

- **What changed and why** (one paragraph is plenty)
- **Issue link** — `Fixes #123`
- **Test plan** — checkboxes the reviewer can run

Reviewers look for: correctness, tests, clarity, performance, security, no regressions. Expect 1–3 rounds of feedback. PRs idle 6 weeks may be closed; you can reopen.

---

## 8. Ways to contribute (not just code)

| Type                 | Example                                                  |
|----------------------|----------------------------------------------------------|
| **Bugs**             | Reproducible repro + environment in the issue            |
| **Features**         | Open a GitHub Discussion first to validate the idea      |
| **Kanban providers** | Jira, Trello, Linear adapters                            |
| **Runners**          | Codex, Gemini, Kimi, AutoGen — see [PROTOCOL.md](PROTOCOL.md) |
| **Docs**             | Tutorials, examples, error-message clarifications        |

Newcomers: filter issues by [`good first issue`](https://github.com/lwgray/marcus/labels/good%20first%20issue) or the sprint label.

---

## 9. Help and community

- [Discord](https://discord.com/channels/1409498120739487859/1409498121456848907) — real-time help
- [GitHub Discussions](https://github.com/lwgray/marcus/discussions) — design questions
- [GitHub Issues](https://github.com/lwgray/marcus/issues) — bugs, features

---

## Reference

- [README](README.md) — what Marcus is, how to run it
- [PROTOCOL.md](PROTOCOL.md) — agent protocol spec
- [ROADMAP.md](ROADMAP.md) — direction
- [CLAUDE.md](CLAUDE.md) — full coding rules (tests, errors, file management, git)
- [Local Development Setup](docs/source/developer/local-development.md)
- [Development Workflow](docs/source/developer/development-workflow.md)
- [Configuration Reference](docs/source/developer/configuration.md)

Every contribution makes Marcus better. Welcome.
