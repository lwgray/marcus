# Roadmap

Marcus is building the coordination layer for the agent era — starting with
orchestration, expanding to domain templates, and scaling to a marketplace.

This roadmap synthesizes our planning documents
([Playbook](docs/Playbook.md), [Development Guide](docs/DEVELOPMENT_GUIDE.md),
[Implementation Plans](docs/implementation/)) and research-driven features from
GitHub issues.

> **Status note (2026-04):** Current shipped release is **v0.3.6**. The
> v0.2.x checklist is now complete and v0.3.x is largely complete — Epictetus
> is integrated, board health monitoring lives in the Cato dashboard, and
> parallel multi-instance experiments shipped on `develop` (the v0.4.0 work).
> The biggest unrepresented gain since this roadmap was last edited is
> **parallel experiment isolation** (per-instance SQLite kanban DBs +
> env-var MCP URLs), which lets multiple independent Marcus instances run
> at once without colliding. See *Phase 1 → v0.4.0-dev* below.

---

## Phase 1: Foundation — *In Progress*

**Goal:** Core coordination works reliably.

### v0.1.1 (2025-10-13) — Initial Release
Started as "PM Agent" in June 2025, rebranded to Marcus in October.
- [x] MCP protocol support (stdio + HTTP transport)
- [x] Planka kanban integration via kanban-mcp
- [x] Agent registration and task assignment
- [x] Workspace isolation (WorkspaceManager)
- [x] Hybrid intelligent coordination system (Phases 1-4)
- [x] NLP tools for natural language project creation
- [x] AI-powered feature analysis
- [x] Board quality validator

### v0.1.2 (2025-10-16) — Scheduling
- [x] CPM (Critical Path Method) scheduling algorithm
- [x] Unified dependency graphs with parallelism calculation
- [x] Optimal agent count recommendation
- [x] Cross-parent dependency wiring
- [x] Race condition prevention in task assignment
- [x] MLflow trace integration for experiments

### v0.1.3 — v0.1.3.1 (2025-10-18 — 2025-10-20) — Stability
- [x] Sweep-line algorithm for correct parallelism
- [x] Tmux-based multi-agent experiment support
- [x] Phase enforcer for cross-feature dependencies
- [x] Subtask assignment and project creation fixes

### v0.2.0 (2026-03-16) — Validation and Intelligence
115 commits. Major release after 5 months of development.
- [x] AI-powered task completeness validation with retry
- [x] Centralized configuration system with environment overrides
- [x] Composition-aware PRD extraction with specificity detection
- [x] Intelligent task pattern selection (prototype/standard/enterprise)
- [x] Constraint propagation through task generation
- [x] Bundled domain-based design tasks
- [x] Soft vs hard dependency support for parallel work
- [x] Post-project analysis: data persistence + LLM-powered analysis (Phase 1+2)
- [x] MLflow tracking for single-agent experiments
- [x] Smart retry with parallel work prioritization
- [x] Enterprise mode with aggressive task decomposition

### v0.2.1 (2026-03-21) — Reliability
- [x] Progressive timeout system with lease recovery
- [x] Structured RecoveryInfo for agent handoffs
- [x] Configurable LLM temperature
- [x] Validation loop bug fix (zero-issue auto-pass)

### v0.2.x (2026-03) — Shipped
- [x] README redesign — manifesto + accurate onboarding (#202, commit 72aea1c4)
- [x] Docker cleanup — infrastructure-only setup (#202)
- [x] Platform architecture + experiment flow diagrams (commit c1140466)
- [x] CLAUDE_API_KEY rename to preserve Claude Code subscription (commit 4e3014ce)
- [ ] Ollama (free LLM) setup verification — provider exists, docs pending
- [ ] OpenAI provider end-to-end testing — provider exists, full E2E pending

### v0.3.x (2026-04, current shipped — v0.3.6) — Mostly Done
- [x] Agent performance metrics and bottleneck detection
      (Epictetus coordination effectiveness analysis, commit 8d1f8b9e / #263)
- [x] Board health monitoring and alerting
      (Quality dashboard in Cato v0.3.0, commit 5f8e54d)
- [x] Auto-terminate agents when experiment completes (#389, commit 1b331117)
- [x] Validation hardening — eliminate criteria hallucinations + BLOCKED
      deadlocks (#421, commit 8e95ca28)
- [x] Coordination/correctness decoupling (commit 4ef01f3a)
- [ ] ~~Unified Cato dashboard bundled with Marcus~~ **DROPPED 2026-04** —
      Cato stays a sibling product. See `MVP_CATO_ALIGNMENT_EVALUATION.md`
      and the proposed Marcus Studio desktop shell (#443) for any future
      "single install" surface.
- [ ] ~~Single install: `pip install marcus && marcus start`~~ **DROPPED 2026-04** —
      depended on the Cato submodule decision above.
- [ ] ~~Real-time event broadcasting (SSE)~~ **DEFERRED 2026-04** —
      Cato continues reading SQLite + Planka directly. SSE rebuilt only
      when Marcus Studio (#443) needs it.
- [ ] ~~Jira kanban provider~~ **DEFERRED 2026-04** — revisit when a real user asks.
- [ ] ~~Linear kanban provider~~ **DEFERRED 2026-04** — same.
- [ ] ~~Trello kanban provider~~ **DEFERRED 2026-04** — same.

### v0.4.0-dev (on `develop` and `feat/parallel-experiment-platform`) — Parallel Experiment Platform

Major architectural addition not in earlier roadmaps. Five-part sprint
that turns Marcus into a parallel-experiment platform: multiple
independent Marcus instances run side-by-side, Epictetus audits run
reliably after every experiment, and a remote-monitoring channel
(Rufus) reports on long-running batches without a desk.

**Shipped:**
- [x] SQLite parallel experiment isolation (commit 0da35ed3, then v0.4.0
      tag in 3c68a97c — version reverted to 0.3.6 in 0e54bfa0 pending more work)
- [x] Env-var driven MCP URLs (per-instance `MARCUS_URL`)
- [x] Per-instance kanban DBs (`db_path` anchored to repo root)
- [x] Spawn-time pretrust race fix (`~/.claude.json` file lock)
- [x] Epictetus phase reporting (commit 420472d9)
- [x] **Track 1 — `asyncio.Lock` fix in `create_project`** (`src/marcus_mcp/tools/nlp.py`):
      serializes concurrent calls so simultaneous project creations no
      longer stall. Tests cover lock existence + serialization behavior.
      Code in; full end-to-end validation still pending.
- [x] **Epictetus reliability**:
      - timeout raised from 30 min → 2 hr
      - Phase 8.5 in the `/epictetus` skill now checks the `MARCUS_DB`
        env var before attempting `import marcus_mcp` —
        Posidonius-spawned audits previously skipped writing to
        `marcus.db` silently (the 5-agent quality score had been
        manually imported as a workaround)
- [x] **Batch pipeline tests** — 6 new tests in Posidonius confirming
      Epictetus fires after every run in a 3-run batch, the pipeline
      reaches `COMPLETED`, and teardown happens in the right order
- [x] **Posidonius Epictetus UI** — phase indicators render in the
      experiment card; backend `/api/experiments/{name}/events`
      endpoint added

**Pending:**
- [ ] v0.4.0 release once dashboard-v98 fixes settle
- [ ] Documentation guide for parallel multi-instance setup
- [ ] Track 1 end-to-end validation under real concurrent load

---

## Next Queue — Post-v0.4.0

The active queue, in order. Anything below is concrete, scoped, and on
the near-term path. Issues exist for each.

### #414 — SQLite migration for all data streams
Replace seven file-based streams (JSONL/JSON under `logs/conversations/`)
with a unified SQLite store. Goal: queryable, multi-root safe, no
full-file scans. **Unblocks Cato multi-path work** and makes Posidonius
multi-instance cleaner. Blocking dependency for several other items.

### #416 — PostHog telemetry (PyCon 2026 sprint)
Opt-in anonymized usage analytics across all Marcus runners (MCP Direct,
`/marcus`, Posidonius). Surfaces in a PostHog dashboard. **PyCon sprint
participants get first pick** — flag this issue before working on it
solo so a sprinter doesn't get blocked.

### #363 — God-files refactor
20 modules exceed 1000 lines (`advanced_parser.py` is 4505 lines). Each
has a subissue with a concrete split plan. Cross-file deduplication
(two `with_retry` implementations, etc.) is bundled in.

### #442 — Track 2: per-session project isolation (deferred post-PyCon)
The real fix for parallel experiments — one Marcus instance on `:4298`
handles N experiments simultaneously, isolated by MCP session ID.
Currently requires N separate Marcus processes on N ports. Blast
radius: **80+ locations across 15+ files**, requires
`contextvars.ContextVar`, threading `session_id` through all 50+ tool
implementations. Deliberately held until after PyCon sprints.

---

## Open Architectural Debt — High Urgency

These surfaced from experiment post-mortems and Kaia architectural
reviews. No fixed order yet; no assigned milestone. Tracked here so
they don't get lost.

### Feature-based contract bleed
`get_task_context` does not label artifacts as `in_scope` vs
`reference_only` at retrieval time. Agents end up consuming the wrong
contracts. Two open design options:
- **Option B** — mode-aware framing (the call site declares its mode;
  the context builder filters by mode)
- **Option C** — explicit `artifact_role` field on artifacts at write
  time

### Foundation task descriptions missing consumption contracts
The design phase produces artifacts, but task descriptions don't tell
downstream agents *how* to consume them. Dashboard-v80 showed agents
correctly built the design system but dependents wired it incorrectly
because the consumption contract wasn't in the task body.

### Decomposer removed integration-wiring tasks
`_create_integration_subtask` was removed citing overhead. The
dashboard-v99 audit proved this causes **hollow products** — each
component passes its unit tests, but the composed result is broken
(no service wiring, no data flow). Restore some form of explicit
integration-wiring step.

---

## Phase 2: Domain Expansion + Build Kits (Months 3-4)

**Goal:** Prove coordination works beyond code. Launch Build Kits.

### Build Kits System
Build Kits (`.mkb` packages) capture completed projects as reusable templates
— source code, architectural decisions, build history, and customization points.

- [ ] `.mkb` file format specification
- [ ] BuildKitPackager — create packages from completed projects
- [ ] BuildKit metadata extractor (auto-detect tech stack)
- [ ] BuildKitCustomizer — intelligent modifications via agents
- [ ] Context injection (Build Kit context -> agent context)
- [ ] CLI: `marcus buildkit create`, `marcus buildkit customize`
- [ ] Build Kit browser in Cato dashboard

### Seed Build Kits
| Kit | Price | Stack |
|-----|-------|-------|
| SaaS Starter | Free | Next.js + Supabase + Stripe |
| E-commerce | Free | React + Node + PostgreSQL |
| Blog/CMS | Free | Markdown-based |
| Todo App | Free | Simple CRUD |
| Dashboard Template | Free | Admin panel |
| API Service | Free | FastAPI REST |
| Real-time Chat | Paid | WebSocket |
| Payment Integration | Paid | Stripe edge cases |
| Multi-tenant B2B | Paid | Tenant isolation |
| Auth System | Paid | OAuth, SSO, MFA |

### Domain Expansion
- [ ] Content creation workflows (podcasts, articles)
- [ ] Research workflows (literature review, data analysis)
- [ ] Marketing workflows (campaigns, copy)

---

## Phase 3: Brownfield + Marketplace Validation (Months 5-6)

**Goal:** Agents work on existing projects. Validate marketplace economics.

### Brownfield Support
- [ ] Project ingestion from existing Git repos
- [ ] RAG-based context retrieval over codebases
- [ ] Safe modification workflows with rollback

### Agent Marketplace
- [ ] Agent registry with capability declarations
- [ ] Agent profile pages with portfolio and reputation
- [ ] Search/filter agents by specialization and rate
- [ ] Hire agent workflow with escrow
- [ ] Star rating and review system

### Payment Infrastructure
- [ ] Stripe Connect integration for creators
- [ ] Checkout flow for Build Kits (one-time, subscription)
- [ ] Escrow system for agent work
- [ ] Platform fee engine (15-20%)
- [ ] Payout processing

---

## Phase 4: Federation Protocol (Months 7-8)

**Goal:** Marcus instances discover each other and share agent networks.

- [ ] Marcus Federation Protocol (MFP) v1.0 specification
- [ ] Instance discovery on network
- [ ] Cross-instance task delegation
- [ ] Reputation portability across instances
- [ ] Payment routing between federated nodes
- [ ] State synchronization protocol

---

## Phase 5: Full Marketplace + Scale (Months 9-12)

**Goal:** Production marketplace with agent labor economy.

- [ ] Full marketplace with agent hiring at scale
- [ ] Enterprise features: RBAC, SSO/SAML, audit logging
- [ ] Multi-project coordination
- [ ] SLA and compliance reporting
- [ ] Enterprise pilot program (10+ organizations)
- [ ] **Plugin architecture with SDK** — *2026-04: rescoped to land much
      earlier, gated on Marcus Studio approval (#443).* Plugin v1
      (manifest-only) in Studio M0–M1; typed SDK in M3+. The Phase 5
      framing here remains as the "GA / public marketplace" milestone
      rather than the introduction of plugins.
- [ ] Horizontal scaling documentation and patterns

---

## Research-Driven Features

These features come from academic research documented in GitHub issues:

| Feature | Issue | Status |
|---------|-------|--------|
| Close the Learning Loop — observation to adaptation | #176 | In progress (Epictetus + research event infra landed) |
| Automated task ordering evaluation framework | #37 | Largely shipped (validation study + #337 hallucination work) |
| Coordination tax experiments (NeurIPS 2026) | n/a | Infrastructure shipped (commit 2801ea6d) |

---

## The Vision

**Open Core Model:**
- Marcus orchestration = **free forever** (MIT)
- Build Kits = mostly free (community-generated)
- Revenue from: cloud hosting, marketplace transactions, enterprise contracts

**Long-term aspirational targets:**
- 1,000+ active users
- 500+ Build Kits
- 100+ specialized agents in marketplace
- 10+ enterprise pilots
- Foundation for the agent labor economy

> *Note (2026-04): These targets remain the long-term commercial vision.
> The internal `docs/Playbook.md` has been rescoped to research-first
> milestones (NeurIPS 2026 coordination-tax submission, validated
> experiments, contributor growth) for the current phase. The
> commercial vision above reactivates when a deliberate commercial
> push begins.*

---

## How to Contribute to the Roadmap

- Join the [Discord](https://discord.com/channels/1409498120739487859/1409498121456848907) to discuss priorities
- Open an [issue](https://github.com/lwgray/marcus/issues) with the
  `enhancement` label
- See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines
- Check [docs/Playbook.md](docs/Playbook.md) for detailed technical specs
  on Build Kits, Marketplace, and Federation
