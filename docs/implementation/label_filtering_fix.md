# Label Filtering Fix - Implementation Complete

## Summary

Fixed critical issue where kanban-mcp returns ALL board labels for every card, causing validation system to incorrectly skip implementation tasks.

**Status**: ✅ **COMPLETE** - Code implemented, tested, committed
**Next Step**: Run new project to verify end-to-end functionality

---

## Problem Statement

### Symptom
When checking Simple Calculator v6 logs, discovered that ALL board labels were being applied to every task:

```
VALIDATION GATE: Task 1678679806473930297 (Implement Basic Arithmetic Operations) -
labels=['P0: Critical', 'design', 'readme_documentation', 'implement', 'calculator',
'architecture', 'P1: High', 'P2: Medium', 'P3: Low', 'Bug', 'Feature', 'Enhancement',
'documentation', 'Blocked', 'Needs Info', 'Ready'], should_validate=False
```

Task has `implement` label (should validate) but also has `design` label. Since task filter checks exclusion labels FIRST, validation was skipped.

### Root Cause

kanban-mcp's `getCardDetails` action returns ALL board labels, not filtered to card's assigned labels:

**File**: `/Users/lwgray/dev/kanban-mcp/tools/card-details.ts` (lines 87-92)
```typescript
const labels = await getLabels(boardId);

// Filter to just the labels assigned to this card
// Note: We need to get the labelIds from the card's data
// This might require additional API calls or data structure knowledge
// For now, we'll return all labels for the board
```

The TODO comment confirms this is a known limitation in kanban-mcp.

---

## Solution Design

### Card Structure Discovery

Cards have a `labelIds` field indicating which labels are assigned:

```json
{
  "id": "card_1",
  "name": "Test Card",
  "labelIds": ["l1", "l3"],  // <- Only these labels assigned
  "labels": [
    {"id": "l1", "name": "implementation"},
    {"id": "l2", "name": "design"},       // <- ALL board labels
    {"id": "l3", "name": "documentation"}
  ]
}
```

### Filtering Logic

Marcus now filters labels client-side using the `labelIds` array:

```python
if "labels" in card_details:
    all_labels = card_details["labels"]
    card_label_ids = card.get("labelIds", [])

    # Filter to only labels assigned to this card
    if card_label_ids:
        filtered_labels = [
            label
            for label in all_labels
            if label.get("id") in card_label_ids
        ]
        card["labels"] = filtered_labels
    else:
        # No labelIds means no labels assigned
        card["labels"] = []
```

**Edge Cases Handled**:
1. Card has no `labelIds` field → empty labels
2. Card has empty `labelIds` array → empty labels
3. `get_details` call fails → empty labels (existing behavior)
4. Card has multiple `labelIds` → filter to only those labels

---

## Implementation Details

### Files Modified

1. **src/integrations/kanban_client.py** (lines 443-464, 621-642)
   - Modified `get_available_tasks()` method
   - Modified `get_all_tasks()` method
   - Added filtering logic after `get_details` call
   - Both methods use identical filtering logic

2. **tests/unit/integrations/test_kanban_label_fetch.py**
   - Completely rewrote all 6 tests to reflect new behavior
   - Tests now mock `get_details` returning ALL board labels
   - Verify Marcus correctly filters based on `labelIds`
   - Added 2 new edge case tests

### Test Coverage

**6 Tests - All Passing**:

1. `test_get_available_tasks_filters_labels_by_label_ids`
   - Mock: card with `labelIds: ["l1"]`, get_details returns 3 labels
   - Verify: task only has "implementation" (l1), not "design" or "documentation"

2. `test_get_all_tasks_filters_multiple_labels`
   - Mock: card with `labelIds: ["l1", "l2"]`, get_details returns 4 labels
   - Verify: task only has "backend" and "api", not "frontend" or "design"

3. `test_handles_card_without_label_ids`
   - Mock: card with NO `labelIds` field, get_details returns labels
   - Verify: task has empty labels (no crash)

4. `test_handles_empty_label_ids_array`
   - Mock: card with `labelIds: []`, get_details returns labels
   - Verify: task has empty labels

5. `test_handles_get_details_exception`
   - Mock: `get_details` raises exception
   - Verify: task has empty labels (graceful degradation)

6. `test_handles_multiple_cards_with_different_label_ids`
   - Mock: 2 cards, both get ALL board labels from `get_details`
   - Card A has `labelIds: ["l1"]`, Card B has `labelIds: ["l2"]`
   - Verify: Card A gets only "frontend", Card B gets only "backend"

---

## Test Results

```bash
# Run tests
$ python -m pytest tests/unit/integrations/test_kanban_label_fetch.py -v
============================= test session starts ==============================
collected 6 items

test_get_available_tasks_filters_labels_by_label_ids PASSED [ 16%]
test_get_all_tasks_filters_multiple_labels PASSED [ 33%]
test_handles_card_without_label_ids PASSED [ 50%]
test_handles_empty_label_ids_array PASSED [ 66%]
test_handles_get_details_exception PASSED [ 83%]
test_handles_multiple_cards_with_different_label_ids PASSED [100%]

============================== 6 passed in 0.05s ===============================

# Code quality checks
✅ mypy - no issues
✅ black - formatted
✅ isort - imports sorted
✅ flake8 - no issues (fixed line length)
✅ pydocstyle - docstrings valid
✅ bandit - no security issues
```

---

## Commit History

### First Commit: Label Retrieval Fix
**Commit**: `4818bac`
**Message**: "fix(labels): fetch labels via get_details for each card"

This commit added the `get_details` call to retrieve labels from kanban-mcp. However, it did NOT filter the labels, so ALL board labels were still being returned.

### Second Commit: Label Filtering Fix
**Commit**: `915799d`
**Message**: "feat(labels): filter labels based on card's labelIds array"

This commit adds the filtering logic to only include labels whose IDs are in the card's `labelIds` array, solving the root cause.

---

## Expected Impact

### Before Fix
```
Task: "Implement Basic Arithmetic Operations"
Labels: ['P0: Critical', 'design', 'readme_documentation', 'implement', ...]
Validation: SKIPPED (has 'design' exclusion label)
Result: ❌ Implementation task not validated
```

### After Fix
```
Task: "Implement Basic Arithmetic Operations"
Labels: ['implement', 'P0: Critical']  # Only assigned labels
Validation: RUN (has 'implement', no exclusion labels)
Result: ✅ Implementation task validated against acceptance criteria
```

### Validation System Now Works Correctly
- Implementation tasks (with `implement` label) will be validated
- Design tasks (with `design` label only) will be skipped
- Mixed tasks won't incorrectly get ALL board labels
- Each task only gets its specifically assigned labels

---

## Verification Plan

To verify the fix works end-to-end:

1. **Run a new test project** (e.g., "Simple Calculator v7")
2. **Check logs** for validation gate messages
3. **Expected behavior**:
   - Design tasks: `labels=['design', 'P0: Critical']` → validation skipped ✅
   - Implementation tasks: `labels=['implement', 'P0: Critical']` → validation runs ✅
   - NO tasks should have ALL 15+ board labels

4. **Check validation execution**:
   - At least one implementation task should trigger validation
   - Should see log messages about source file discovery
   - Should see validation pass/fail results

---

## Related Issues

- **Issue #170**: Feature Completeness Validation System
- **Simple Calculator v6**: Project where issue was discovered
- **kanban-mcp TODO**: Upstream issue in kanban-mcp needs eventual fix

---

## Future Considerations

### Upstream Fix in kanban-mcp
Eventually, kanban-mcp should filter labels server-side:

```typescript
// In kanban-mcp/tools/card-details.ts
const allLabels = await getLabels(boardId);
const cardLabelIds = card.labelIds || [];

// Filter to only assigned labels
const assignedLabels = allLabels.filter(label =>
  cardLabelIds.includes(label.id)
);

return {
  ...card,
  labels: assignedLabels  // Filtered, not all board labels
};
```

**Benefits**:
- Reduced network payload (fewer labels sent)
- Marcus code becomes simpler (no client-side filtering)
- Consistent behavior across all kanban-mcp users

**Until then**: Marcus's client-side filtering works correctly.

---

## Documentation Updates

- [x] Created this implementation document
- [x] Updated test file with comprehensive docstrings
- [x] Added inline comments explaining filtering logic
- [x] Commit messages explain problem, solution, and impact

---

## Checklist

- [x] Problem identified and root cause found
- [x] Solution designed and implemented
- [x] Unit tests written (6 tests, all passing)
- [x] Code quality checks passing (mypy, black, isort, flake8)
- [x] Changes committed with detailed commit message
- [x] Documentation created
- [ ] **End-to-end verification** (run new project to confirm)

---

**Status**: Ready for end-to-end verification with new test project.
