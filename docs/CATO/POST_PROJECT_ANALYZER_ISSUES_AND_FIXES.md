# Post-Project Analyzer Issues and Fixes

## Executive Summary

Several issues were found in the post-project analysis pipeline that prevent accurate reporting in CATO:

1. **Duration showing as 0**: Project duration not calculated from task timestamps
2. **"Invalid date" errors**: Analysis timestamp not properly formatted
3. **Task redundancy showing "No data"**: Redundancy score = 0 but no explanation
4. **Artifacts not reporting**: Total artifacts = 0 when artifacts were created
5. **Lack of actionable insights**: Scores displayed without interpretation or recommendations

## Root Cause Analysis

### Issue 1: Project Duration = 0

**Location**: `src/analysis/query_api.py:get_project_summary()`

**Problem**: The function doesn't calculate project duration from task timestamps. It relies on `project_duration_hours` from the snapshot, but this field may not exist or may be 0.

**Root Cause**:
```python
# Line ~560 in query_api.py
"project_duration_hours": snapshot.project_duration_hours if snapshot else 0.0,
```

This assumes the snapshot has `project_duration_hours`, but:
- Snapshots may not include this field
- Field may be 0 if project just started
- No fallback to calculate from task timestamps

**Fix Required**:
```python
def _calculate_project_duration(self, tasks: list[TaskHistory]) -> float:
    """Calculate project duration from task timestamps."""
    if not tasks:
        return 0.0

    # Find earliest start and latest completion
    start_times = [t.started_at for t in tasks if t.started_at]
    end_times = [t.completed_at for t in tasks if t.completed_at]

    if not start_times or not end_times:
        return 0.0

    earliest = min(start_times)
    latest = max(end_times)
    duration = (latest - earliest).total_seconds() / 3600  # Convert to hours
    return duration
```

### Issue 2: "Analysis Generated Invalid Date"

**Location**: CATO's `RetrospectiveDashboard.tsx:66`

**Problem**:
```typescript
<p className="analysis-timestamp">
  Analysis generated: {new Date(analysis_timestamp).toLocaleString()}
</p>
```

**Root Cause**: The `analysis_timestamp` from the API may be:
1. Missing entirely (when Phase 2 fails)
2. Not in ISO format
3. Timezone-naive (no 'Z' suffix)

**API Response** (from `api.py:1032`):
```python
result.update({
    "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
    # ...
})
```

This should work, but CATO needs better error handling.

**Fix Required**:
1. Ensure all timestamps from Marcus include timezone
2. Add fallback in CATO for invalid timestamps:
```typescript
const formatTimestamp = (timestamp: string | undefined) => {
  if (!timestamp) return 'N/A';
  try {
    return new Date(timestamp).toLocaleString();
  } catch {
    return 'Invalid date';
  }
};
```

### Issue 3: Task Redundancy "No Data Available"

**Location**: `src/analysis/analyzers/task_redundancy.py` and CATO display

**Problem**: The redundancy analyzer runs but produces:
- `redundancy_score = 0`
- `redundant_pairs = []`
- `total_time_wasted = 0`

But CATO's `TaskRedundancyView.tsx` shows "No task redundancy data available" instead of showing "0 redundancy detected" (which is valid).

**Root Cause**:
1. **Data Collection**: Redundancy analyzer expects `conversations` but gets empty list:
   ```python
   # post_project_analyzer.py:338
   task_redundancy_analysis = await self.redundancy_analyzer.analyze_project(
       tasks=tasks,
       conversations=[],  # TODO: Extract conversations from history
       progress_callback=progress_callback,
   )
   ```

2. **UI Logic**: CATO checks if `task_redundancy` is null/undefined instead of checking if it has data:
   ```typescript
   if (!historicalAnalysis?.task_redundancy) {
     return <div>No task redundancy data available</div>;
   }
   ```

**Fix Required**:
1. Pass conversations to the analyzer:
   ```python
   task_redundancy_analysis = await self.redundancy_analyzer.analyze_project(
       tasks=tasks,
       conversations=history.timeline,  # Use timeline events as conversations
       progress_callback=progress_callback,
   )
   ```

2. Update CATO to show zero redundancy as a positive result:
   ```typescript
   if (!task_redundancy || task_redundancy.redundancy_score === undefined) {
     return <div>No task redundancy data available</div>;
   }

   // Show zero redundancy as valid result
   if (task_redundancy.redundancy_score === 0) {
     return (
       <div className="zero-redundancy">
         <h3>✅ No Redundancy Detected</h3>
         <p>All tasks were unique with no duplicate work.</p>
       </div>
     );
   }
   ```

### Issue 4: Artifacts Not Reporting (Showing 0)

**Location**: `src/analysis/aggregator.py` and `src/core/project_history.py`

**Problem**: Even when artifacts are created via `log_artifact()`, the summary shows `total_artifacts: 0`.

**Root Causes**:
1. **Filtering Issue**: Artifacts are being filtered out during aggregation
   ```python
   # aggregator.py:378-383
   tasks = self._build_task_histories(
       filtered_outcomes,  # Only outcomes from conversations
       decisions,
       artifacts,  # All artifacts passed here
       conversations,
       filtered_events,
       task_metadata,
   )
   ```

   The `artifacts` are passed to `_build_task_histories()`, but only artifacts matching `task_id` in `task_histories` are included.

2. **Task ID Mismatch**: Artifacts created with `task_id` that doesn't exist in conversations won't be counted.

**Investigation Needed**:
- Check if artifacts in SQLite have matching task_ids
- Verify task_ids in conversation logs match artifact task_ids
- Check if artifact count comes from `history.artifacts` or `task_histories[].artifacts_produced`

**Fix Required**:
```python
# In get_project_summary(), count all artifacts regardless of task matching
async def get_project_summary(self, project_id: str) -> dict[str, Any]:
    history = await self.get_project_history(project_id)

    # Count ALL artifacts from persistence, not just those in task_histories
    total_artifacts = len(history.artifacts)  # Use full artifact list

    return {
        # ...
        "total_artifacts": total_artifacts,
        # ...
    }
```

## What Each Analyzer Measures

### 1. Requirement Divergence Analyzer (`requirement_divergence.py`)

**What it measures**:
- **Fidelity Score** (0.0-1.0): How closely implementation matches original requirements
  - 1.0 = Perfect match
  - 0.7-0.9 = Minor deviations
  - 0.4-0.7 = Significant divergence
  - < 0.4 = Major divergence (critical issues)

**How it works**:
- Compares task descriptions (requirements) with decisions, artifacts, and outcomes
- Uses LLM to semantically analyze if implementation matches intent
- Identifies specific divergences with citations

**What to look for**:
- **Fidelity < 0.7**: Review divergences for critical issues
- **Severity = "critical"**: Core functionality changed from requirements
- **Divergence patterns**: Repeated issues across multiple tasks suggest unclear requirements

**Actionable insights**:
- Improve requirement specificity
- Add acceptance criteria to tasks
- Flag architectural decision that cause divergence

### 2. Decision Impact Tracer (`decision_impact_tracer.py`)

**What it measures**:
- **Impact Chains**: How decisions affect downstream tasks
- **Unexpected Impacts**: Decisions that had unintended consequences
- **Depth**: How far decision ripples propagated (1 = direct, 2+ = indirect)

**How it works**:
- Builds dependency graph from `affected_tasks` in decisions
- Traces decision propagation through task dependencies
- Identifies decisions that impacted more tasks than anticipated

**What to look for**:
- **Depth > 3**: Decision had far-reaching consequences
- **Unexpected impacts**: Decision affected tasks not listed in `affected_tasks`
- **High-impact decisions**: Single decision affecting many tasks

**Actionable insights**:
- Document high-impact decisions better
- Add "anticipated impacts" field when logging decisions
- Review unexpected impacts for architectural issues

### 3. Instruction Quality Analyzer (`instruction_quality.py`)

**What it measures**:
- **Clarity** (0.0-1.0): How unambiguous instructions were
- **Completeness** (0.0-1.0): Whether all necessary info was provided
- **Specificity** (0.0-1.0): How specific vs vague requirements were
- **Overall** (0.0-1.0): Weighted average of all dimensions

**How it works**:
- Analyzes task descriptions for ambiguities
- Correlates instruction quality with:
  - Time variance (actual vs estimated)
  - Clarifications requested during execution
  - Implementation notes mentioning confusion

**What to look for**:
- **Overall < 0.6**: Instructions need significant improvement
- **Clarity < 0.5**: Ambiguous phrasing causing confusion
- **Completeness < 0.5**: Missing critical information
- **Time variance > 2.0**: Task took 2x longer than estimated (often due to unclear instructions)

**Actionable insights**:
- Use templates for task descriptions
- Add examples to ambiguous requirements
- Include "Definition of Done" criteria
- Specify constraints and assumptions upfront

### 4. Failure Diagnosis Generator (`failure_diagnosis.py`)

**What it measures**:
- **Failure Causes**: Root causes categorized (technical, requirements, communication, etc.)
- **Contributing Factors**: Secondary factors that exacerbated the failure
- **Prevention Strategies**: Specific actions to prevent recurrence

**How it works**:
- Only runs on `failed` tasks
- Analyzes error logs, blockers, and context
- Uses LLM to identify root causes and prevention strategies

**What to look for**:
- **Category patterns**: Repeated failure categories suggest systemic issues
  - Multiple "requirements" failures → Need better requirement gathering
  - Multiple "technical" failures → Need better task decomposition
  - Multiple "communication" failures → Need better agent coordination
- **High-effort prevention**: Strategies marked "high effort" need prioritization
- **High-priority recommendations**: Focus on these first

**Actionable insights**:
- Address systemic issues (patterns across multiple failures)
- Implement prevention strategies in order of priority
- Update task templates to avoid common pitfalls

### 5. Task Redundancy Analyzer (`task_redundancy.py`)

**What it measures**:
- **Redundancy Score** (0.0-1.0): Overall project redundancy
  - 0.0 = No redundancy
  - 0.1-0.2 = Acceptable overlap
  - 0.3-0.5 = Significant redundancy (needs attention)
  - > 0.5 = Excessive redundancy (major inefficiency)
- **Redundant Pairs**: Specific task pairs doing duplicate work
- **Overlap Score** (per pair): How much work overlaps (1.0 = complete duplicate)
- **Time Wasted**: Hours spent on redundant work
- **Over-decomposition**: Whether Enterprise mode broke down tasks unnecessarily

**How it works**:
- Compares task descriptions to find similar goals
- Identifies "quick completions" (< 30 seconds) suggesting work already done
- Analyzes conversations for mentions of "already completed", "duplicate", etc.
- Recommends appropriate complexity mode

**What to look for**:
- **Redundancy > 0.3**: Significant waste that needs addressing
- **Quick completions > 30% of tasks**: Strong sign of over-decomposition
- **Recommended complexity != current**: Switch to suggested mode
- **Time wasted > 5 hours**: Major efficiency loss

**Actionable insights**:
- **If redundancy > 0.3 + recommended = "prototype"**: Use prototype mode for simpler projects
- **If redundancy > 0.3 + recommended = "standard"**: Enterprise mode is over-decomposing
- **Review redundant pairs**: Merge similar tasks or clarify distinction
- **Quick completions**: Agent assigned tasks for already-completed work

## Adding Actionable Recommendations

Each analyzer already includes `recommendations: list[str]` in its output, but these are often generic. Here's how to improve them:

### Pattern-Based Recommendations

**Requirement Divergence**:
```python
recommendations = []

# Pattern 1: High divergence across multiple tasks
if avg_fidelity < 0.6:
    recommendations.append(
        "⚠️ CRITICAL: Multiple tasks show significant divergence. "
        "ACTION: Hold requirements review session before next project."
    )

# Pattern 2: Repeated severity="critical" divergences
critical_count = sum(1 for d in divergences if d.severity == "critical")
if critical_count > 2:
    recommendations.append(
        f"🚨 {critical_count} critical divergences detected. "
        f"ACTION: Implement acceptance criteria in all task descriptions."
    )

# Pattern 3: Specific divergence types
for div in divergences:
    if "auth" in div.requirement.lower():
        recommendations.append(
            "🔐 Authentication changed from requirements. "
            "ACTION: Document security architecture decisions explicitly."
        )
```

**Instruction Quality**:
```python
recommendations = []

# Pattern 1: Low clarity → Add examples
if quality_scores.clarity < 0.5:
    recommendations.append(
        "💡 Instructions are ambiguous. "
        "ACTION: Add concrete examples to task descriptions."
    )

# Pattern 2: Low completeness → Use templates
if quality_scores.completeness < 0.5:
    recommendations.append(
        "📋 Instructions are incomplete. "
        "ACTION: Use task template with: Goal, Context, Constraints, Definition of Done."
    )

# Pattern 3: High time variance → Improve estimates
if time_variance > 2.0:
    recommendations.append(
        f"⏱️ Task took {time_variance:.1f}x longer than estimated. "
        f"ACTION: Break down tasks with >4 hour estimates."
    )
```

**Task Redundancy**:
```python
recommendations = []

# Pattern 1: Over-decomposition
if redundancy_score > 0.3 and recommended_complexity == "prototype":
    recommendations.append(
        f"🎯 Reduce task breakdown. "
        f"ACTION: Switch to '{recommended_complexity}' mode "
        f"(current redundancy: {redundancy_score:.1%}, wasted: {total_time_wasted:.1f}h)"
    )

# Pattern 2: Specific redundant pairs
for pair in redundant_pairs[:3]:  # Top 3
    recommendations.append(
        f"🔄 Tasks '{pair.task_1_name}' and '{pair.task_2_name}' are {pair.overlap_score:.0%} redundant. "
        f"ACTION: Merge or clarify distinction (saves {pair.time_wasted:.1f}h)."
    )

# Pattern 3: Quick completions
if quick_completion_rate > 0.3:
    recommendations.append(
        f"⚡ {quick_completion_rate:.0%} of tasks completed in <30s. "
        f"ACTION: Check if work was already done before assigning tasks."
    )
```

### Contextual Recommendations

Add context from project phase:

```python
# Early project (< 25% complete)
if completion_rate < 0.25:
    recommendations.append(
        "🌱 Early stage project. Recommendation: Focus on architecture decisions now "
        "to avoid costly changes later."
    )

# Mid project (25-75%)
elif completion_rate < 0.75:
    recommendations.append(
        "🏗️ Mid-stage project. Recommendation: Lock down requirements now "
        "to prevent scope creep."
    )

# Late project (> 75%)
else:
    recommendations.append(
        "🏁 Final stage. Recommendation: Focus on documentation and knowledge transfer "
        "for next project retrospective."
    )
```

### Cross-Analyzer Recommendations

In `post_project_analyzer.py:_generate_summary()`, add cross-cutting insights:

```python
def _generate_enhanced_recommendations(
    self,
    requirement_divergences,
    instruction_quality_issues,
    task_redundancy,
) -> list[str]:
    """Generate recommendations that span multiple analyzers."""
    recommendations = []

    # Pattern: Low fidelity + Low instruction quality = Poor requirements
    avg_fidelity = sum(d.fidelity_score for d in requirement_divergences) / len(requirement_divergences)
    avg_instruction_quality = sum(i.quality_scores.overall for i in instruction_quality_issues) / len(instruction_quality_issues)

    if avg_fidelity < 0.7 and avg_instruction_quality < 0.6:
        recommendations.append(
            "🎯 ROOT CAUSE: Poor requirements quality leading to divergent implementations. "
            "ACTION: Implement requirements review checklist before task creation."
        )

    # Pattern: High redundancy + Low instruction quality = Unclear task boundaries
    if task_redundancy and task_redundancy.redundancy_score > 0.3 and avg_instruction_quality < 0.6:
        recommendations.append(
            "🔄 ROOT CAUSE: Unclear task boundaries causing duplicate work. "
            "ACTION: Add 'Scope' section to task template defining what's IN and OUT of scope."
        )

    return recommendations
```

## Testing Plan

### Test 1: Duration Calculation
```python
# Create test project with known duration
tasks = [
    TaskHistory(
        task_id="task1",
        started_at=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
        completed_at=datetime(2025, 1, 1, 11, 30, 0, tzinfo=timezone.utc),
        # ... other fields
    ),
    TaskHistory(
        task_id="task2",
        started_at=datetime(2025, 1, 1, 11, 0, 0, tzinfo=timezone.utc),
        completed_at=datetime(2025, 1, 1, 13, 0, 0, tzinfo=timezone.utc),
        # ... other fields
    ),
]

# Expected duration: 10:00 - 13:00 = 3 hours
summary = await query_api.get_project_summary("test_proj")
assert summary["project_duration_hours"] == 3.0
```

### Test 2: Artifact Counting
```python
# Create project with known artifacts
# 1. Create artifacts via log_artifact()
# 2. Run aggregator
# 3. Verify count matches

summary = await query_api.get_project_summary("test_proj")
assert summary["total_artifacts"] == expected_count
```

### Test 3: Zero Redundancy
```python
# Create project with no redundant tasks
analysis = await redundancy_analyzer.analyze_project(
    tasks=unique_tasks,
    conversations=[],
)

# Verify zero redundancy is reported correctly
assert analysis.redundancy_score == 0.0
assert len(analysis.redundant_pairs) == 0
assert analysis.total_time_wasted == 0.0
assert analysis.recommended_complexity == "enterprise"  # No over-decomposition
```

### Test 4: Timestamp Formatting
```python
# Ensure all timestamps are ISO format with timezone
summary = await query_api.get_project_summary("test_proj")

# Parse timestamp to verify format
timestamp = datetime.fromisoformat(summary["analysis_timestamp"])
assert timestamp.tzinfo is not None  # Must have timezone
```

## Implementation Priority

1. **[HIGH] Fix project duration calculation** - Blocking metric
2. **[HIGH] Fix artifact counting** - Data integrity issue
3. **[MEDIUM] Add zero-redundancy display** - UX improvement
4. **[MEDIUM] Fix timestamp formatting** - UX bug
5. **[MEDIUM] Add enhanced recommendations** - Value add
6. **[LOW] Add cross-analyzer recommendations** - Nice to have

## Next Steps

1. Create unit tests for each fix (TDD)
2. Implement fixes in order of priority
3. Test with real project data
4. Update CATO UI to handle edge cases
5. Document analyzer interpretations in user-facing docs
