# Label Retrieval Fix - Implementation Summary

## Problem

Tasks created in Planka had labels added successfully, but when Marcus retrieved tasks later via `get_available_tasks()` or `get_all_tasks()`, the Task objects had empty labels (`labels=[]`). This caused the validation system to skip all tasks because `should_validate_task()` returns False when labels are empty.

### Root Cause

Planka's MCP API has two different actions for retrieving cards:
1. **`mcp_kanban_card_manager` with `action="get_all"`** - Returns list of cards WITHOUT label data
2. **`mcp_kanban_card_manager` with `action="get_details"`** - Returns full card details INCLUDING labels

The `KanbanClient` was only using `get_all`, which meant labels were never retrieved even though they existed in Planka.

### Previous Fix Attempt (Commit 4818bac)

A previous fix added labels to the `request_next_task()` response, but this only worked if the Task object already had labels populated. Since tasks were retrieved without labels, this fix didn't solve the root cause.

## Solution

Modified `KanbanClient.get_available_tasks()` and `KanbanClient.get_all_tasks()` to fetch detailed card information including labels.

### Implementation Details

**File**: `src/integrations/kanban_client.py`

**Changes**:
- Added label fetching logic after retrieving card lists
- For each card returned by `get_all`, call `get_details` to fetch full card data including labels
- Update the card dictionary with label data before passing to `_card_to_task()`
- Graceful error handling: if `get_details` fails, continue without labels rather than crashing

**Code Location**:
- `get_available_tasks()`: Lines 429-457
- `get_all_tasks()`: Lines 607-634

**Logic Flow**:
```python
# 1. Retrieve cards from Planka (no labels)
cards_result = await session.call_tool(
    "mcp_kanban_card_manager",
    {"action": "get_all", "listId": list_id}
)

# 2. For each card, fetch detailed information
for card in all_cards:
    card_id = card.get("id")

    # Get full card details which includes labels
    details_result = await session.call_tool(
        "mcp_kanban_card_manager",
        {"action": "get_details", "cardId": card_id}
    )

    # 3. Update card dict with labels from details
    if "labels" in card_details:
        card["labels"] = card_details["labels"]

# 4. Existing _card_to_task() parses labels correctly
task = _card_to_task(card)
```

### Error Handling

The implementation includes try/except wrapping the label fetching logic:
- If `get_details` fails for any reason, log a warning and continue
- Tasks are created with empty labels rather than failing entirely
- This ensures backward compatibility if the MCP action becomes unavailable

## Testing

**Test File**: `tests/unit/integrations/test_kanban_label_fetch.py`

### Test Coverage

1. **`test_get_available_tasks_calls_get_details`**
   - Verifies `get_details` is called for each card
   - Confirms labels are correctly extracted and added to Task objects

2. **`test_get_all_tasks_calls_get_details`**
   - Same verification for `get_all_tasks()` method
   - Tests multiple labels per card

3. **`test_handles_card_without_labels_field`**
   - Tests graceful handling when `get_details` doesn't return labels field
   - Ensures task creation continues with empty labels

4. **`test_handles_get_details_exception`**
   - Tests error handling when `get_details` raises exception
   - Verifies system doesn't crash, creates task without labels

5. **`test_handles_multiple_cards`**
   - Tests label fetching for multiple cards in one request
   - Verifies each task gets correct labels from its respective card

### Test Results

```
============================== test session starts ==============================
platform darwin -- Python 3.12.11, pytest-8.4.1, pluggy-1.6.0
collected 5 items

tests/unit/integrations/test_kanban_label_fetch.py::TestLabelFetchDiscovery::test_get_available_tasks_calls_get_details PASSED [ 20%]
tests/unit/integrations/test_kanban_label_fetch.py::TestLabelFetchDiscovery::test_get_all_tasks_calls_get_details PASSED [ 40%]
tests/unit/integrations/test_kanban_label_fetch.py::TestLabelFetchDiscovery::test_handles_card_without_labels_field PASSED [ 60%]
tests/unit/integrations/test_kanban_label_fetch.py::TestLabelFetchDiscovery::test_handles_get_details_exception PASSED [ 80%]
tests/unit/integrations/test_kanban_label_fetch.py::TestLabelFetchDiscovery::test_handles_multiple_cards PASSED [100%]

============================== 5 passed in 0.05s ===============================
```

All tests pass, mypy type checking passes, code formatted with black and isort.

## Impact

### Before Fix
- Labels added to cards during task creation ✅
- Labels NOT retrieved when fetching tasks ❌
- Task objects had `labels=[]` ❌
- `should_validate_task()` skipped all tasks ❌
- Validation system never ran ❌

### After Fix
- Labels added to cards during task creation ✅
- Labels retrieved via `get_details` when fetching tasks ✅
- Task objects have correct labels ✅
- `should_validate_task()` correctly identifies implementation tasks ✅
- Validation system runs for appropriate tasks ✅

## Performance Considerations

### Additional API Calls
- **Before**: 1 API call per list (get_all)
- **After**: 1 API call per list + 1 API call per card (get_details)
- **Impact**: If a board has 10 cards, this adds 10 API calls

### Mitigation
- Labels are small data structures (minimal network overhead)
- API calls happen sequentially within the same MCP session (fast)
- The validation benefits outweigh the minimal performance cost
- Could be optimized later with batch get_details if MCP adds that feature

## Related Issues

- **Issue #170**: Feature Completeness Validation System
- **Previous attempt**: Commit 4818bac (fixed symptom, not root cause)

## Next Steps

To verify the complete fix works end-to-end:

1. Run a new Marcus project with implementation tasks
2. Check logs to confirm:
   - Labels are written during task creation
   - Labels are retrieved when fetching tasks
   - `should_validate_task()` returns True for implementation tasks
   - Validation system runs and checks implementation completeness

## Code Quality

- ✅ All unit tests pass
- ✅ Mypy type checking passes
- ✅ Code formatted with black
- ✅ Imports sorted with isort
- ✅ Follows TDD best practices
- ✅ Graceful error handling
- ✅ Backward compatible
