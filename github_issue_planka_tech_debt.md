# Remove Legacy Planka Class - Technical Debt

## Summary
The codebase contains two implementations of the Planka kanban integration:
1. `Planka` (legacy) - `/src/integrations/providers/planka.py`
2. `PlankaKanban` (current) - `/src/integrations/providers/planka_kanban.py`

The legacy `Planka` class should be removed as it causes bugs and confusion.

## Problem Description

### Current Issues
- **Bug**: Tasks don't move to "In Progress" column when assigned (fixed in #93f6280 by switching to PlankaKanban)
- **Confusion**: Two classes with similar names but different behavior
- **Maintenance burden**: Need to maintain two implementations
- **Inconsistent behavior**: `Planka` has incomplete status update logic

### Technical Details

The legacy `Planka` class has flawed `update_task` logic:
```python
async def update_task(self, task_id: str, updates: Dict[str, Any]) -> Task:
    if "status" in updates:
        status = updates["status"]
        if status == TaskStatus.IN_PROGRESS:
            # Only moves if BOTH status AND assigned_to are present
            if "assigned_to" in updates:
                await self.client.assign_task(task_id, updates["assigned_to"])
```

This means tasks only move to "In Progress" when both conditions are met, not when just updating status.

The `PlankaKanban` class correctly handles this:
```python
async def update_task(self, task_id: str, updates: Dict[str, Any]) -> Task:
    if "status" in updates:
        # Maps status to column and moves task
        status_to_column = {
            TaskStatus.IN_PROGRESS: "in progress",
            # ...
        }
        if status in status_to_column:
            await self.move_task_to_column(task_id, status_to_column[status])
```

## Proposed Solution

1. **Remove** `/src/integrations/providers/planka.py`
2. **Update imports** - Change any remaining imports from `Planka` to `PlankaKanban`
3. **Rename** `PlankaKanban` to `Planka` for consistency (optional)
4. **Update tests** to ensure they use the correct implementation

## Impact
- **Fixes**: Prevents future bugs from using wrong implementation
- **Simplifies**: One clear implementation for Planka integration
- **Improves**: Code maintainability and clarity

## Migration Steps
1. Ensure all code uses `PlankaKanban` (already done in KanbanFactory)
2. Search for any remaining imports of the legacy `Planka` class
3. Update tests if needed
4. Delete the legacy file
5. Consider renaming `PlankaKanban` → `Planka` for simplicity

## Testing
- Verify task assignment moves tasks to "In Progress"
- Verify all status transitions work correctly
- Run integration tests for Planka provider