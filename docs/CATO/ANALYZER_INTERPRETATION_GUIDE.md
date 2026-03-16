# Post-Project Analyzer Interpretation Guide

This guide explains what each score means and how to use the insights to improve future projects.

## Table of Contents

- [Requirement Fidelity](#requirement-fidelity)
- [Decision Impact](#decision-impact)
- [Instruction Quality](#instruction-quality)
- [Failure Diagnosis](#failure-diagnosis)
- [Task Redundancy](#task-redundancy)
- [Quick Reference](#quick-reference)

---

## Requirement Fidelity

### What It Measures

**Fidelity Score**: How closely the implementation matched the original requirements (0.0 to 1.0).

### Score Interpretation

| Score Range | Meaning | Action Needed |
|-------------|---------|---------------|
| **0.9 - 1.0** | ✅ **Excellent** - Implementation perfectly matches requirements | None - great job! |
| **0.7 - 0.9** | ✅ **Good** - Minor deviations, mostly cosmetic | Review divergences, but acceptable |
| **0.5 - 0.7** | ⚠️ **Fair** - Significant divergence detected | Review all divergences, especially "major" severity |
| **< 0.5** | 🚨 **Poor** - Major divergence from requirements | URGENT: Review all divergences and root causes |

### Understanding Divergence Severity

**Critical Severity**:
- Core functionality changed from requirements
- Could break system or violate constraints
- **Action**: Immediate review and correction or requirement update

**Major Severity**:
- Behavior differs significantly but system still works
- May not meet stakeholder expectations
- **Action**: Assess impact and decide: fix implementation or update requirements

**Minor Severity**:
- Cosmetic differences (UI, naming, formatting)
- Optimizations not specified in requirements
- **Action**: Document for future reference, usually no fix needed

### Common Patterns and What They Mean

**Pattern 1: Fidelity < 0.6 across multiple tasks**
- **Root Cause**: Requirements were unclear or incomplete
- **Fix**: Improve requirement-gathering process
- **Prevention**: Use requirement templates with examples

**Pattern 2: Critical divergences in authentication/security**
- **Root Cause**: Security requirements not explicit
- **Fix**: Add security requirements section to all tasks
- **Prevention**: Security checklist for all new features

**Pattern 3: Multiple "already implemented differently" divergences**
- **Root Cause**: Existing codebase not reviewed before writing requirements
- **Fix**: Codebase discovery phase before requirements
- **Prevention**: Architecture documentation up-to-date

### How to Use This Information

1. **For developers**: Focus on requirements with fidelity < 0.7
2. **For project managers**: Identify patterns across multiple tasks
3. **For next project**:
   - Add examples to requirements showing "what good looks like"
   - Include "Definition of Done" acceptance criteria
   - Review requirements with technical lead before starting

---

## Decision Impact

### What It Measures

**Impact Chains**: How architectural decisions rippled through the project affecting downstream tasks.

**Unexpected Impacts**: Decisions that affected tasks not originally anticipated.

### Metrics Explanation

**Direct Impacts** (depth = 1):
- Tasks directly changed by the decision
- These should match `affected_tasks` when logging decision

**Indirect Impacts** (depth = 2+):
- Tasks affected through dependencies
- Example: Decision on Task A affects Task B, which affects Task C (depth = 2)

**Unexpected Impact Severity**:
- **High**: Decision significantly affected unanticipated tasks
- **Medium**: Minor effects on unanticipated tasks
- **Low**: Negligible impact on unanticipated tasks

### Common Patterns

**Pattern 1: Many unexpected impacts with "High" severity**
- **Root Cause**: Decision made without full dependency analysis
- **Fix**: Create dependency graph before major decisions
- **Prevention**: Use decision template requiring "anticipated impacts" section

**Pattern 2: Depth > 3 for many decisions**
- **Root Cause**: Highly coupled architecture
- **Fix**: Refactor to reduce coupling
- **Prevention**: Design for modularity and loose coupling

**Pattern 3: Low-confidence decisions having high impact**
- **Root Cause**: Critical decision made with insufficient information
- **Fix**: Research more thoroughly before deciding
- **Prevention**: Flag low-confidence decisions for additional review

### How to Use This Information

1. **Review unexpected impacts**: For each decision with unexpected impacts, ask:
   - Why didn't we anticipate this?
   - How can we improve impact analysis next time?

2. **Document high-impact decisions**: Create Architecture Decision Records (ADRs) for:
   - Decisions with > 5 total impacts
   - Decisions with unexpected impacts
   - Any decision with depth > 2

3. **Improve decision logging**: Add required fields:
   - `anticipated_impacts`: List of tasks we expect to be affected
   - `dependency_analysis`: Explicit dependency check
   - `rollback_plan`: How to undo decision if needed

---

## Instruction Quality

### What It Measures

**Quality Dimensions** (each scored 0.0 to 1.0):

- **Clarity**: How unambiguous the instructions were
- **Completeness**: Whether all necessary information was provided
- **Specificity**: How specific vs vague the requirements were
- **Overall**: Weighted average of all dimensions

### Score Interpretation

| Score Range | Meaning | Action Needed |
|-------------|---------|---------------|
| **0.8 - 1.0** | ✅ **Excellent** - Crystal clear instructions | None - use as template for future tasks |
| **0.6 - 0.8** | ✅ **Good** - Minor ambiguities | Review ambiguity issues and improve |
| **0.4 - 0.6** | ⚠️ **Fair** - Significant clarity issues | Major improvement needed |
| **< 0.4** | 🚨 **Poor** - Instructions very unclear | Rewrite using template |

### Dimension-Specific Interpretation

**Low Clarity (< 0.6)**:
- Instructions use vague language ("somehow", "maybe", "probably")
- Contradictory statements
- Ambiguous pronouns ("it", "that thing")
- **Fix**: Rewrite using concrete examples

**Low Completeness (< 0.6)**:
- Missing context (why are we doing this?)
- No constraints specified (performance, security, compatibility)
- No definition of "done"
- **Fix**: Add context section, constraints, and acceptance criteria

**Low Specificity (< 0.6)**:
- Requirements too high-level ("make it better", "improve performance")
- No measurable criteria ("fast", "user-friendly")
- No examples provided
- **Fix**: Add specific metrics and concrete examples

### Correlation with Task Performance

**Time Variance Analysis**:
- **1.0x**: Perfect estimate (instruction quality probably good)
- **1.5x - 2.0x**: Took 50-100% longer (some ambiguities)
- **2.0x - 3.0x**: Took 2-3x longer (significant instruction issues)
- **> 3.0x**: Took 3x+ longer (severe instruction problems OR major unknowns)

**If time variance > 2.0 AND instruction quality < 0.6**:
- **Root Cause**: Unclear instructions caused delays
- **Impact**: Wasted {(actual_hours - estimated_hours)} hours
- **Fix**: Rewrite instructions before assigning similar tasks

**If time variance > 2.0 BUT instruction quality > 0.8**:
- **Root Cause**: Unknown unknowns (not instruction quality issue)
- **Action**: Add discovery phase before estimation

### Ambiguity Issue Severity

**Critical**:
- Ambiguity caused task failure or major rework
- Security/compliance implications
- **Action**: Immediate clarification required

**Major**:
- Ambiguity caused significant delays (> 2 hours)
- Multiple clarifications needed
- **Action**: Update instructions before reuse

**Minor**:
- Small clarifications needed (< 30 minutes)
- Cosmetic ambiguities
- **Action**: Note for improvement

### How to Use This Information

1. **Immediate**: For tasks with overall < 0.6:
   - Review all ambiguity issues
   - Rewrite instructions using template (see below)
   - Re-estimate before assigning

2. **Short-term**: Create instruction template:
   ```markdown
   ## Goal
   What we're trying to achieve (one sentence)

   ## Context
   Why we're doing this and how it fits in

   ## Requirements
   1. Specific requirement with measurable criteria
   2. Another specific requirement

   ## Constraints
   - Performance: Must handle X requests/second
   - Security: Must follow Y standard
   - Compatibility: Must work with Z systems

   ## Examples
   Show concrete examples of success

   ## Definition of Done
   - [ ] Specific, testable criterion
   - [ ] Another testable criterion

   ## Out of Scope
   Explicitly state what's NOT included
   ```

3. **Long-term**: Training and process
   - Train on writing clear instructions
   - Peer review task descriptions before assignment
   - Track instruction quality over time

---

## Failure Diagnosis

### What It Measures

**Failure Causes**: Root causes of task failures, categorized by type.

**Prevention Strategies**: Specific, actionable steps to prevent similar failures.

### Failure Categories

**Technical**:
- Bugs in code, libraries, or infrastructure
- Performance issues
- Integration problems
- **Typical Prevention**: Better testing, code review, spike tasks

**Requirements**:
- Unclear, incomplete, or contradictory requirements
- Changing requirements mid-task
- Missing acceptance criteria
- **Typical Prevention**: Requirements review, stakeholder sign-off, freeze scope

**Communication**:
- Missing information
- Agent misunderstood instructions
- Dependencies not communicated
- **Typical Prevention**: Standup meetings, documentation, explicit handoffs

**Resource**:
- Insufficient time, compute, or access
- Blocked by external dependencies
- Missing credentials or permissions
- **Typical Prevention**: Resource planning, early access requests, buffer time

**Knowledge**:
- Agent lacked required expertise
- Technology unknown to team
- Undocumented legacy system
- **Typical Prevention**: Training, spike tasks, expert consultation, documentation

### Prevention Strategy Priority

**Priority Levels**:
- **High**: Address immediately (affects other tasks)
- **Medium**: Address before next similar task
- **Low**: Nice to have improvement

**Effort Levels**:
- **High**: > 8 hours implementation
- **Medium**: 2-8 hours implementation
- **Low**: < 2 hours implementation

### How to Prioritize Fixes

Use this decision matrix:

| Priority | Effort | Action |
|----------|--------|--------|
| High | Low | **DO IMMEDIATELY** - High impact, low cost |
| High | Medium | **DO SOON** - High impact, worth the cost |
| High | High | **PLAN CAREFULLY** - High impact but expensive, needs planning |
| Medium | Low | **DO WHEN POSSIBLE** - Easy wins |
| Medium | Medium | **EVALUATE ROI** - May or may not be worth it |
| Medium | High | **DEFER** - Not worth the effort |
| Low | Low | **BACKLOG** - Do if bored |
| Low | Medium/High | **DON'T DO** - Waste of resources |

### Common Failure Patterns

**Pattern 1: Multiple "Requirements" failures**
- **Symptom**: 3+ tasks failed due to requirement issues
- **Root Cause**: Systemic requirements gathering problem
- **Fix**: Implement requirements review process
- **Prevention**: Use requirements template and stakeholder sign-off

**Pattern 2: Multiple "Knowledge" failures**
- **Symptom**: Tasks failing because agent lacks expertise
- **Root Cause**: Task assignment doesn't match agent capabilities
- **Fix**: Skills matrix for agent assignment
- **Prevention**: Training plan or expert consultation

**Pattern 3: Multiple "Communication" failures**
- **Symptom**: Tasks failing due to missing information
- **Root Cause**: Poor handoffs between agents
- **Fix**: Explicit handoff protocol (write decision, log artifact, notify)
- **Prevention**: Communication checklist for task completion

### How to Use This Information

1. **Triage failures by category**:
   - Count failures by category
   - Focus on category with most failures (systemic issue)

2. **Implement prevention strategies**:
   - Start with "High Priority + Low Effort"
   - Document implemented strategies
   - Track if they prevent future failures

3. **Create lessons learned**:
   - Document each failure and prevention
   - Share with team
   - Update process documentation

4. **Track metrics over time**:
   - Failure rate by category
   - Prevention strategy effectiveness
   - Cost of failures (wasted hours)

---

## Task Redundancy

### What It Measures

**Redundancy Score**: Overall project redundancy (0.0 to 1.0).

**Redundant Pairs**: Specific pairs of tasks doing duplicate work.

**Time Wasted**: Hours spent on redundant work.

**Over-decomposition**: Whether tasks were broken down unnecessarily (usually from Enterprise mode).

### Score Interpretation

| Score Range | Meaning | Action Needed |
|-------------|---------|---------------|
| **0.0 - 0.1** | ✅ **Excellent** - No redundancy | None - optimal task breakdown |
| **0.1 - 0.2** | ✅ **Good** - Minimal overlap | Acceptable, some overlap is normal |
| **0.2 - 0.3** | ⚠️ **Fair** - Noticeable redundancy | Review redundant pairs, consider merging |
| **0.3 - 0.5** | ⚠️ **Poor** - Significant redundancy | URGENT: Major inefficiency, merge tasks |
| **> 0.5** | 🚨 **Critical** - Excessive redundancy | CRITICAL: Massive waste, switch to prototype mode |

### Redundant Pair Overlap Score

For each pair of redundant tasks:

| Overlap Score | Meaning | Action |
|---------------|---------|--------|
| **0.9 - 1.0** | Complete duplicate | Merge immediately or delete one |
| **0.7 - 0.9** | Substantial overlap | Merge or clearly distinguish |
| **0.5 - 0.7** | Moderate overlap | Consider merging or clarify boundaries |
| **< 0.5** | Minor overlap | Document shared components, OK to keep separate |

### Quick Completion Analysis

**Quick Completion**: Task completed in < 30 seconds.

**Why it matters**: Usually indicates work was already done when task was assigned.

| Quick Completion Rate | Meaning | Action |
|----------------------|---------|--------|
| **< 10%** | Normal | No action needed |
| **10% - 30%** | Moderate over-assignment | Check if tasks were really needed |
| **> 30%** | High over-assignment | Significant waste, improve task assignment process |

### Complexity Mode Recommendations

**Prototype** (simplest):
- Minimal task breakdown
- Entire features as single tasks
- **Use when**: Simple project, clear requirements, small team

**Standard** (balanced):
- Moderate task breakdown
- Features split into 2-4 tasks
- **Use when**: Most projects, medium complexity

**Enterprise** (most detailed):
- Granular task breakdown
- Features split into 5+ tasks
- **Use when**: Complex projects, many dependencies, large team

**If recommended != current mode**:
- **Switch immediately** if redundancy > 0.3
- **Evaluate** if redundancy 0.2-0.3
- **Continue** if redundancy < 0.2

### Common Patterns

**Pattern 1: High redundancy + Quick completions > 30%**
- **Root Cause**: Over-decomposition (Enterprise mode on simple project)
- **Fix**: Switch to {recommended_complexity} mode
- **Impact**: Wasted {total_time_wasted} hours on redundant work

**Pattern 2: Multiple pairs with overlap > 0.8**
- **Root Cause**: Unclear task boundaries
- **Fix**: Add "Scope" section to task template (IN scope vs OUT of scope)
- **Prevention**: Review task list for duplicates before assignment

**Pattern 3: Redundancy in specific area (e.g., "auth tasks")**
- **Root Cause**: Feature breakdown unclear
- **Fix**: Create feature map showing task boundaries
- **Prevention**: Design task breakdown at architecture level

### How to Use This Information

1. **Immediate Actions** (redundancy > 0.3):
   ```
   FOR EACH redundant pair with overlap > 0.7:
     - Review both tasks
     - If same goal: Merge into one task (saves {time_wasted}h)
     - If different goals: Clarify distinction in descriptions

   IF quick_completion_rate > 30%:
     - Switch to {recommended_complexity} mode
     - Review task assignment process
   ```

2. **Process Improvements**:
   - **Add scope boundaries**: Every task should have "IN scope" and "OUT of scope" sections
   - **Review before assignment**: Check for existing tasks that already cover this
   - **Use appropriate complexity**:
     - Simple CRUD app → Prototype mode
     - Standard web app → Standard mode
     - Distributed system → Enterprise mode

3. **Cost-Benefit Analysis**:
   ```
   Time Wasted on Redundancy: {total_time_wasted} hours
   Cost (at $100/hour): ${total_time_wasted * 100}

   Prevention Cost: 1 hour review before task creation
   Breakeven: Prevent 1+ hours of redundancy (ROI: {total_time_wasted}x)
   ```

4. **Long-term Tracking**:
   - Track redundancy score across projects
   - Measure impact of process changes
   - Goal: Keep redundancy < 0.2 consistently

---

## Quick Reference

### Score Interpretation Table

| Analyzer | Score | Excellent | Good | Fair | Poor | Critical |
|----------|-------|-----------|------|------|------|----------|
| **Fidelity** | 0-1 | 0.9-1.0 | 0.7-0.9 | 0.5-0.7 | < 0.5 | - |
| **Instruction Quality** | 0-1 | 0.8-1.0 | 0.6-0.8 | 0.4-0.6 | < 0.4 | - |
| **Redundancy** | 0-1 | 0-0.1 | 0.1-0.2 | 0.2-0.3 | 0.3-0.5 | > 0.5 |
| **Time Variance** | ratio | 1.0x | <1.5x | 1.5-2.0x | 2.0-3.0x | >3.0x |

### Action Priority Matrix

| Metric | Threshold | Priority | Typical Action |
|--------|-----------|----------|----------------|
| Fidelity | < 0.5 | 🚨 URGENT | Review and fix all critical divergences |
| Fidelity | 0.5-0.7 | ⚠️ HIGH | Review major divergences, update requirements |
| Instruction Quality | < 0.4 | 🚨 URGENT | Rewrite all poor instructions |
| Instruction Quality | 0.4-0.6 | ⚠️ HIGH | Improve clarity and completeness |
| Redundancy | > 0.5 | 🚨 URGENT | Switch complexity mode, merge tasks |
| Redundancy | 0.3-0.5 | ⚠️ HIGH | Merge redundant pairs |
| Redundancy | 0.2-0.3 | ⚠️ MEDIUM | Review and consider merging |
| Time Variance | > 3.0x | 🚨 URGENT | Investigate root cause (instructions? unknowns?) |
| Time Variance | 2.0-3.0x | ⚠️ HIGH | Review instructions and estimates |
| Quick Completions | > 30% | 🚨 URGENT | Switch to simpler complexity mode |
| Quick Completions | 10-30% | ⚠️ MEDIUM | Review task assignment process |

### Common Root Causes and Fixes

| Symptom | Likely Root Cause | Fix |
|---------|------------------|-----|
| Low fidelity + Low instruction quality | Poor requirements | Requirements review process |
| High redundancy + Many quick completions | Over-decomposition | Switch to prototype/standard mode |
| Many unexpected decision impacts | Insufficient dependency analysis | Create dependency graph before decisions |
| Multiple requirements failures | Unclear stakeholder needs | Stakeholder interviews + sign-off |
| Multiple communication failures | Poor handoffs | Explicit handoff protocol |
| High time variance + Good instruction quality | Unknown unknowns | Add discovery phase before estimation |
| Low specificity | Vague requirements | Add concrete examples and metrics |
| Multiple knowledge failures | Skills gap | Training plan or expert consultation |

### When to Act

**Act Immediately** (same day):
- Redundancy > 0.5
- Fidelity < 0.5 with critical divergences
- Instruction quality < 0.4
- Multiple high-priority failures

**Act Soon** (this week):
- Redundancy 0.3-0.5
- Fidelity 0.5-0.7
- Instruction quality 0.4-0.6
- Multiple medium-priority failures
- Time variance > 2.0x consistently

**Plan for Next Project**:
- Redundancy 0.2-0.3
- Any patterns across multiple tasks
- Process improvements
- Prevention strategies

**Monitor**:
- Redundancy 0.1-0.2 (acceptable)
- Fidelity 0.7-0.9 (good)
- Instruction quality 0.6-0.8 (good)
- Isolated issues with no pattern
