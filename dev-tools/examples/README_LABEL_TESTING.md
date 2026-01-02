# Label Filtering Test Scripts

Quick tests to verify label filtering is working correctly without running a full 30-minute project.

## Test Scripts

### 1. Direct KanbanClient Test (FASTEST - Recommended)

**File**: `test_kanban_labels_direct.py`

**Speed**: ~5 seconds

**What it does**:
- Directly creates a KanbanClient instance
- Fetches tasks from the current board
- Analyzes label counts to verify filtering

**Prerequisites**:
- Marcus must be running (to use Planka MCP server)
- A project must be loaded with tasks
- Environment variables must be set (PLANKA_BOARD_ID, etc.)

**Usage**:
```bash
# Make sure Marcus is running
cd /Users/lwgray/dev/marcus
python dev-tools/examples/test_kanban_labels_direct.py
```

**Expected Output** (if working correctly):
```
✅ SUCCESS: Label filtering is working correctly!
   All tasks have 1-10 labels (properly filtered)
```

**Error Indicators**:
- ⚠️  Tasks have NO labels → labelIds not being read correctly
- ❌ Tasks have >10 labels → Filtering not working (ALL board labels)

---

### 2. HTTP Connection Test (More Complete)

**File**: `test_label_filtering.py`

**Speed**: ~10-15 seconds

**What it does**:
- Connects to running Marcus HTTP server
- Authenticates as admin
- Requests a task (triggers full task assignment flow)
- Analyzes labels on the received task

**Prerequisites**:
- Marcus running in HTTP mode (`--http` flag)
- A project loaded with available tasks

**Usage**:
```bash
# Make sure Marcus is running with --http
python dev-tools/examples/test_label_filtering.py
```

**Expected Output** (if working correctly):
```
✅ SUCCESS: Label filtering is working correctly!
```

---

## Interpreting Results

### ✅ Success (Label Filtering Working)
```
Task: Implement Basic Arithmetic Operations
   Labels: ['implement', 'P0: Critical']
   Label count: 2
   ✅ OK: Task has 2 labels
```

Each task has 1-10 labels (only its assigned labels).

### ❌ Failure: Empty Labels
```
Task: Implement Basic Arithmetic Operations
   Labels: []
   Label count: 0
   ⚠️  WARNING: Task has NO labels
```

**Problem**: `labelIds` not being read from `card_details`

**Fix**: Check that code uses `card_details.get("labelIds")` not `card.get("labelIds")`

### ❌ Failure: ALL Board Labels
```
Task: Implement Basic Arithmetic Operations
   Labels: ['P0: Critical', 'design', 'readme_documentation', 'implement',
            'calculator', 'architecture', 'P1: High', 'P2: Medium',
            'P3: Low', 'Bug', 'Feature', 'Enhancement', 'documentation',
            'Blocked', 'Needs Info', 'Ready']
   Label count: 16
   ❌ ERROR: Task has 16 labels (ALL board labels - filtering NOT working!)
```

**Problem**: Label filtering logic not working

**Fix**: Verify filtering code in `kanban_client.py` lines 454-468

---

## Troubleshooting

### Error: "No board_id configured"
```bash
# Check environment variables
echo $PLANKA_BOARD_ID
echo $PLANKA_PROJECT_ID

# If not set, Marcus should set them when a project is loaded
# Try running with Marcus's environment
```

### Error: "No tasks found on board"
```bash
# Make sure a project is loaded
# Option 1: Load existing project via Marcus UI
# Option 2: Create test project via create_project MCP tool
```

### Error: Connection refused
```bash
# Make sure Marcus is running
ps aux | grep marcus

# Restart Marcus if needed
cd /Users/lwgray/dev/marcus
python -m src.marcus_mcp.server --http
```

---

## When to Use Each Test

**Use Direct Test** (`test_kanban_labels_direct.py`):
- ✅ Fastest (5 seconds)
- ✅ Tests the exact code that was fixed
- ✅ Clear pass/fail output
- ❌ Requires Marcus to be running (for MCP server)

**Use HTTP Test** (`test_label_filtering.py`):
- ✅ Tests full task assignment flow
- ✅ Verifies labels reach the agent
- ❌ Slower (10-15 seconds)
- ❌ More complex setup

**Use Full Project**:
- ✅ Tests complete end-to-end workflow
- ✅ Tests validation system integration
- ❌ Very slow (30 minutes)
- ❌ Only use for final verification

---

## Quick Reference

```bash
# Fastest test (5 seconds)
python dev-tools/examples/test_kanban_labels_direct.py

# More complete test (10-15 seconds)
python dev-tools/examples/test_label_filtering.py

# Full project test (30 minutes - use sparingly)
# Create project via Marcus UI or create_project tool
```

---

## Expected Timeline for Verification

1. **First Fix** (commit 915799d): Label filtering added
   - Result: ALL board labels still returned
   - Issue: Used `card.get("labelIds")` instead of `card_details.get("labelIds")`

2. **Second Fix** (commit 6797f6e): labelIds source corrected
   - Result: Should work! (needs verification)
   - Run: `python dev-tools/examples/test_kanban_labels_direct.py`

3. **Expected Result**: ✅ Tasks have 1-10 labels each (properly filtered)
