# Subtask Performance Strategy

## Problem Statement

Tasks were completing in 4-8 minutes actual time, but subtasks were also taking 4-8 minutes each, making subtask decomposition 3-5× **slower** than single-agent execution.

### Root Causes Identified

1. **Time Estimation Error**: Tasks estimated at 8-16 hours, actually took 4-8 minutes (60-120× overestimated)
2. **No Time Budgets**: Agents saw "2.0 hours" and paced themselves accordingly
3. **Comprehensive Instructions**: Subtasks received full-task instructions (diagrams, reviews, etc.)
4. **Validation Overhead**: Every task had a validation subtask adding 6 minutes with minimal value
5. **Work Duplication**: Multiple subtasks doing the same work (all creating API + schema + diagrams)

## Phase 1: Current Implementation (Priority Fixes)

### Fix 1: Reality-Based Time Estimates ✅
**File**: `src/ai/advanced/prd/advanced_parser.py`

**Change**: Convert hour-based estimates to minute-based reality:
```python
# OLD:
estimated_hours = 8  # Design tasks

# NEW:
estimated_minutes = 6  # Design tasks: 4-8 minutes reality
estimated_hours = estimated_minutes / 60  # 0.1 hours
```

**Impact**: Entire system now uses realistic time expectations

### Fix 2: Eliminate Validation Subtasks (Prototype Mode) ✅
**File**: `src/marcus_mcp/coordinator/decomposer.py`

**Change**: Skip integration/validation subtasks in prototype mode:
```python
if complexity == "prototype":
    return None  # Don't create validation subtask
```

**Impact**: Saves 6 minutes per task in prototype mode

### Fix 3: Time Budget in Instructions ✅
**File**: `src/marcus_mcp/tools/task.py`

**Change**: Show agents explicit time budget:
```
⏱️ TIME BUDGET: 2 MINUTES
Complexity Mode: PROTOTYPE

PROTOTYPE MODE EXPECTATIONS:
- Detail Level: Quick sketches and bullet points
- Documentation: Brief notes only
- Quality Bar: Good enough to start coding
```

**Impact**: Agents see "2 MINUTES" not "2.0 hours", work faster

### Fix 4: Realistic Subtask Time Guidance ✅
**File**: `src/marcus_mcp/coordinator/decomposer.py`

**Change**: AI gets realistic time examples:
```
Example: For a 6-minute task split into 3 subtasks:
- Subtask 1: 0.033 hours (2 minutes)
- Subtask 2: 0.033 hours (2 minutes)
- Subtask 3: 0.033 hours (2 minutes)
```

**Impact**: AI generates realistic subtask time estimates

## Expected Results (Phase 1)

### Before Phase 1:
```
Design Task: "Design Create Pomodoro Timer"
- 5 subtasks × 6 min each = 30 minutes
- (or 12-18 min with partial parallelization)
- Validation subtask: 6 min overhead

Total: 18-36 minutes per Design task
```

### After Phase 1:
```
Design Task: "Design Create Pomodoro Timer"
Prototype Mode:
- 4 subtasks × 2 min each = 8 minutes (parallel: 2 min)
- No validation subtask
Total: 2-8 minutes per Design task

Standard Mode:
- 4 subtasks × 3 min each = 12 minutes (parallel: 3 min)
- Optional validation: 6 min
Total: 3-18 minutes per Design task
```

**Target Speedup**: 2-6× faster

## Phase 2: Fallback Approach (If Phase 1 Insufficient)

### When to Implement Phase 2

If after Phase 1 implementation, subtasks still take 4-8 minutes (not improving to 1-3 minutes target), implement these additional restrictions:

### Disable Subtasks for Design/Test Tasks

**File**: `src/marcus_mcp/coordinator/decomposer.py`

**Function**: `should_decompose(task: Task)` - Add complexity-aware logic:

```python
def should_decompose(task: Task, complexity: str = "standard") -> bool:
    """Decide whether task should be decomposed into subtasks."""

    # Phase 2: Disable subtasks for certain task types in prototype/standard
    if complexity in ["prototype", "standard"]:
        task_labels = [label.lower() for label in (task.labels or [])]

        # Design tasks complete quickly - don't split
        if "design" in task.name.lower() or "type:design" in task_labels:
            logger.info(f"Skipping decomposition for Design task {task.name} (complexity={complexity})")
            return False

        # Test tasks are naturally integrated - don't split
        if "test" in task.name.lower() or "type:testing" in task_labels:
            logger.info(f"Skipping decomposition for Test task {task.name} (complexity={complexity})")
            return False

    # Original logic for other cases
    if task.estimated_hours < 0.05:  # Less than 3 minutes
        return False

    # ... rest of original logic
```

**Impact**: Design and Test tasks execute as single units in prototype/standard modes

### Expected Results (Phase 2)

```
BRT Demo Project - Phase 2:

Design Tasks (6 tasks):
- No subtasks
- 6 tasks × 6 min = 36 minutes

Test Tasks (6 tasks):
- No subtasks
- 6 tasks × 6 min = 36 minutes

Implementation Tasks (6 tasks):
- Subtasks only if truly independent components
- ~2-3 subtasks per task
- 6 tasks × 2 subtasks × 3 min = 36 minutes (parallel)

Total: ~36-72 minutes (vs 120-180 min currently)
Speedup: 2-5× faster
```

## Complexity-Based Strategy

### Prototype Mode
**Goal**: Maximum speed, minimal overhead

- **Subtasks**: Only for Implementation with clear frontend/backend split
- **Validation**: Disabled (no validation subtasks)
- **Time Budget**: 2-3 minutes per subtask
- **Quality**: "Good enough to start coding"
- **Artifacts**: Sketches, bullet points, minimal docs

### Standard Mode
**Goal**: Balance speed and quality

- **Subtasks**: Implementation tasks only (not Design/Test in Phase 2)
- **Validation**: Optional (disabled in Phase 2, can re-enable if time permits)
- **Time Budget**: 4-6 minutes per subtask
- **Quality**: "Production-ready"
- **Artifacts**: Basic diagrams, structured docs (1-2 pages)

### Enterprise Mode
**Goal**: Quality and compliance over speed

- **Subtasks**: All task types get subtasks
- **Validation**: Required (integration/validation subtasks enabled)
- **Time Budget**: 10-15 minutes per subtask
- **Quality**: "Enterprise-grade with reviews"
- **Artifacts**: Comprehensive diagrams, detailed docs (5+ pages)

## Metrics to Track

### Key Performance Indicators

1. **Average Subtask Completion Time**
   - Target: 2-3 min (prototype), 4-6 min (standard), 10-15 min (enterprise)
   - Current Baseline: 4-8 minutes

2. **Total Project Completion Time**
   - Target: 20-30 min (prototype), 40-60 min (standard), 90-120 min (enterprise)
   - Current Baseline: 120-180 minutes

3. **Subtask vs Parent Task Time Ratio**
   - Target: Subtasks should be faster (parallel execution gains)
   - Current: Equal or slower (3-5× overhead)

### Test Protocol

1. Create BRT Demo project with current changes
2. Measure actual subtask completion times
3. Compare against targets
4. If targets not met → Implement Phase 2
5. Re-test and measure improvements

## Decision Tree

```
Is subtask avg time < 4 minutes?
├─ YES: Phase 1 SUCCESS ✅
│  └─ Monitor and optimize further
└─ NO: Implement Phase 2
   ├─ Disable Design/Test subtasks
   ├─ Test again
   └─ Is subtask avg time < 4 minutes now?
      ├─ YES: Phase 2 SUCCESS ✅
      └─ NO: Consider disabling all subtasks for prototype mode
```

## Rollback Plan

If changes cause issues:

1. **Immediate Rollback**: Revert time estimate changes in `advanced_parser.py`
2. **Partial Rollback**: Keep validation filtering, revert time budgets
3. **Full Rollback**: Git revert to pre-change commit

## Future Enhancements

### Phase 3 (Future): Advanced Optimizations

- **Shared Context Agents**: Reduce overhead by sharing context between subtasks
- **Smart Context Loading**: Load only relevant files per subtask
- **Dependency-Aware Grouping**: Merge sequential subtasks automatically
- **Historical Learning**: Adjust estimates based on actual completion data

---

**Last Updated**: 2025-10-22
**Status**: Phase 1 Implemented, Awaiting Testing
**Next Steps**: Test on BRT Demo project, measure results, decide on Phase 2
