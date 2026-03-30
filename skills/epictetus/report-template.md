# Code Audit Report: [Project Name]

**Date**: [YYYY-MM-DD]
**Auditor**: Epictetus v1.1
**Project Type**: [type]
**Skill Lens**: [lens applied]
**Inferred Contributors**: [N] ([confidence]: [evidence summary])
**Process Evidence**: [Available — tmux session `<name>` | Not available — code-only audit]

## Executive Summary
[2-3 sentences: what it is, overall quality, biggest concern]

## Scores

| Dimension | Weight | Score | Grade | Justification |
|-----------|--------|-------|-------|---------------|
| Architecture & Design | % | /5 | | [one-line with file:line citation] |
| Code Quality & Craftsmanship | % | /5 | | |
| Correctness & Reliability | % | /5 | | |
| Completeness | % | /5 | | |
| Testing | % | /5 | | |
| Documentation & Spec Fidelity | % | /5 | | |
| Security | % | /5 | | |
| Performance & Efficiency | % | /5 | | |
| Maintainability & Extensibility | % | /5 | | |
| **Weighted Total** | **100%** | **/5** | | |

## Authorship Cohesiveness

**Verdict**: [Distinctly Multi-Author | Mildly Varied | Suspiciously Uniform | Jarringly Inconsistent]

### Style Profiles

| Signal | Agent 1 | Agent 2 | ... | Divergent? |
|--------|---------|---------|-----|------------|
| Naming conventions | | | | Yes/No |
| Comment style | | | | Yes/No |
| Error handling | | | | Yes/No |
| Whitespace/formatting | | | | Yes/No |
| Abstraction preferences | | | | Yes/No |
| Variable declarations | | | | Yes/No |
| Control flow | | | | Yes/No |
| Import organization | | | | Yes/No |
| Function structure | | | | Yes/No |
| Defensive coding | | | | Yes/No |

**Divergent signals**: [count]/10
**Examples**: [cite specific file:line comparisons]
**Assessment**: [What this means for multi-agent value on this project]

## Critical Issues

| # | Severity | File | Line | Description |
|---|----------|------|------|-------------|
| | critical/major | | | |

## Notable Strengths
[What was done well — reinforce good patterns with file:line references]

## Ghost Code & Dead Weight

| Item | Location | Type | Impact |
|------|----------|------|--------|
| | file:line | ghost method / ghost spec / misleading doc / dead import | |

## Process Evidence (if --session provided)

### Evidence Sources

| Source | Available | Details |
|--------|-----------|---------|
| Marcus API (`/api/tasks/{id}/conversation`) | yes/no | [N tasks retrieved, M timeline events] or [reason unavailable] |
| tmux session logs | yes/no | [N panes captured, M panes skipped] |

### API vs Log Discrepancies

| Agent | Task | API Says | Log Shows | Finding |
|-------|------|----------|-----------|---------|
| | | [structured event] | [raw log evidence] | [what this reveals] |

### Instruction Quality Assessment

| Factor | Rating | Evidence |
|--------|--------|---------|
| Task descriptions | clear/ambiguous/missing/contradictory | [quote instruction + agent interpretation] |
| Success criteria | clear/ambiguous/missing/contradictory | |
| Dependency info | clear/ambiguous/missing/contradictory | |
| Scope boundaries | clear/ambiguous/missing/contradictory | |
| Technical constraints | clear/ambiguous/missing/contradictory | |

### Key Process Findings

| # | Agent | Tmux Log Line | What Happened | Impact on Score |
|---|-------|---------------|---------------|-----------------|
| | | ~line N | [description of process signal] | [which dimension affected, how] |

### Agent Interview Responses

| Agent | Questions Asked | Key Revelations | Contradicts Log? |
|-------|---------------|-----------------|------------------|
| | [count] | [summary of what we learned] | yes/no |

### Root Cause Attribution

| Problem | Code Evidence | Process Evidence | Root Cause | Blame |
|---------|-------------|-----------------|------------|-------|
| [bug/issue] | file:line | tmux log / interview | bad spec / bad execution / bad coordination | spec / agent / both |

## Agent/Developer Grades

| Agent | Task | Score | Grade | Spec Adherence | Ghost Code? | Net Contribution | Process Modifier | Feedback |
|-------|------|-------|-------|----------------|-------------|------------------|------------------|----------|
| | | /5 | | full/partial/ignored/n/a | yes/no | high/med/low/negative | [+/-0.5 reason] or n/a | |

## Cross-Agent Issues
[Contradictions, duplicated work, integration gaps, spec drift cascades]

## Coordination Effectiveness

**Score**: [/5] ([grade])

### Parallelization Analysis

| Metric | Value | Assessment |
|--------|-------|------------|
| Agents available | | |
| Agents that produced work | | 🔴/🟡/🟢 |
| Max theoretical parallelism (from DAG) | | |
| Actual parallel tasks observed | | 🔴/🟡/🟢 |
| Time wasted (retries, idle, trust prompts) | | |

### Dependency Chain Analysis

- Critical path length: [N tasks]
- Max parallel width: [N tasks could run simultaneously]
- Could parallelism improve? [YES/NO — explain]
- DAG shape: [linear chain / diamond / wide fan-out / balanced tree]

### Agent Utilization

| Agent | Tasks Completed | Active Time | Idle Time | Idle Reason |
|-------|----------------|-------------|-----------|-------------|
| | | | | [dependency blocked / retry loop / trust prompt / no tasks / lease bug] |

### Coordination Failures

| Failure | Duration | Root Cause | Fixable? |
|---------|----------|------------|----------|
| | | [linear deps / lease bug / trust prompt / task stuck / retry loop] | Yes/No — [how] |

## Recommendations

### Project-Specific Fixes
Fixes that apply only to this project's codebase.

| Priority | Scope | Category | Effort | Description |
|----------|-------|----------|--------|-------------|
| 1 | project | bug_fix / testing / dead_code_removal / doc_fix / refactor / security / performance | trivial / small / medium / large | |

### Global Marcus Ecosystem Improvements
Changes to Marcus itself — task templates, coordination patterns, instruction
quality, default configurations — so future experiments don't repeat these problems.

| Priority | Scope | Category | Effort | Description |
|----------|-------|----------|--------|-------------|
| 1 | global | instruction_quality / coordination / task_templates / agent_defaults / guardrails / observability / process | trivial / small / medium / large | |

### Both (Project + Global)
Issues found in this project that reveal systemic Marcus problems.
Fix the project AND fix Marcus so it doesn't happen again.

| Priority | Scope | Category | Effort | Description |
|----------|-------|----------|--------|-------------|
| 1 | both | [category] | trivial / small / medium / large | [what to fix locally] + [what to change in Marcus] |
