# Archived Documentation

These documents reflect prior plans that have been superseded by the
2026-04 documentation triage. They are preserved here for historical
reference and so that links in older PRs/issues continue to resolve.
**Do not treat any of these as current guidance.**

For the current state of Marcus, see:

- [`ROADMAP.md`](../../ROADMAP.md) — current shipped state and active phases
- [`docs/Playbook.md`](../Playbook.md) — long-term vision (with 2026-04 triage notes at the top)
- [`docs/DEVELOPMENT_GUIDE.md`](../DEVELOPMENT_GUIDE.md) — fresh developer onboarding guide
- [`docs/MVP_CATO_ALIGNMENT_EVALUATION.md`](../MVP_CATO_ALIGNMENT_EVALUATION.md) — re-evaluation of the original Cato bundling plan

## What's in here and why

| Archived file | Why archived |
|---|---|
| `DEVELOPMENT_GUIDE_2025_12_8wk_plan.md` | Original 8-week curriculum-style guide. Most week-by-week milestones either shipped, were dropped, or were punted to the proposed Marcus Studio desktop app (#443). Replaced by the much shorter active `docs/DEVELOPMENT_GUIDE.md`. |
| `UNIFIED_MASTER_IMPLEMENTATION_PLAN_2025_12_13wk_plan.md` | Original 13-week plan. Already self-marked superseded; finally moved out of the active doc tree during the 2026-04 triage. |
| `MASTER_IMPLEMENTATION_ORDER_2025_12_13wk_plan.md` | Original ordering rationale (Phase 3 → MVP → Cato MCP). Already self-marked superseded; moved here. |
| `MVP_IMPLEMENTATION_PLAN_2025_12.md` | Companion to the 13-week plan. Same supersession. |
| `WEEK_1_PLAN_2025_12.md` through `WEEK_6_PLAN_2025_12.md` (incl. `WEEK_5_5_PLAN_2025_12.md`) | Per-week instructions for the original 8-week plan. The Week 4–6 Cato bundling work was dropped 2026-04; Week 1–3 milestones shipped (in different shapes). The per-week step-by-step is no longer the recommended onboarding path. |
| `CATO_MCP_INTEGRATION_PLAN_2025_12.md` | Original Cato bundling plan (Weeks 4–7 of the 8-week plan). The git submodule + unified install + 6-tab dashboard work was dropped 2026-04. Cato remains a sibling product; any future "unified surface" work belongs in Marcus Studio (#443). |

## Bug-fix logs and design references

The following files **remain in `docs/implementation/`** because they are
historical bug-fix logs or active design references that don't belong in
the archive:

- `docs/implementation/issue_170_complete_resolution.md`
- `docs/implementation/label_filtering_fix.md`
- `docs/implementation/label_retrieval_fix.md`
- `docs/implementation/workspace-isolation-and-feature-context.md` (design reference; Feature-entity work itself is deferred)

## Other archived material

The 2026-04 triage also affected:

- `docs/CATO/CATO_UX_ANALYSIS_AND_RECOMMENDATIONS.md` — UX work deferred per triage item 2.7. Kept in place with a deferral banner instead of being archived.
- `docs/CATO/CATO_FIXES_SUMMARY.md` — historical fix log, untouched.
- `docs/CATO/ANALYZER_INTERPRETATION_GUIDE.md` — operational guide, untouched.
