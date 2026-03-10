# Interactive Project Management Tool

An interactive CLI tool for managing (bulk deleting or retaining) projects from your Planka board.

## Features

- **Interactive Selection**: Choose projects to delete or keep using an easy-to-use interface
- **Flexible Selection Syntax**: Select projects using numbers, ranges, or combinations
- **Two Modes**:
  - **Delete Mode**: Select which projects to delete
  - **Keep Mode**: Select which projects to keep (deletes all others)
- **Safety Features**:
  - Preview selection before deletion
  - Shows project details (boards count)
  - Requires explicit confirmation (`DELETE`) before proceeding
  - Cannot accidentally delete without confirmation

## Usage

### Basic Usage

```bash
python dev-tools/utilities/manage_projects_interactive.py
```

### Requirements

- Planka must be running and accessible
- `config_marcus.json` must be configured with Planka credentials
- `kanban-mcp` must be installed (automatically detected)

### Selection Syntax

The tool supports multiple ways to select projects:

| Input | Description | Example |
|-------|-------------|---------|
| `5` | Select single project | Selects project #5 |
| `1,3,5` | Select multiple projects | Selects projects #1, #3, and #5 |
| `1-5` | Select range | Selects projects #1, #2, #3, #4, #5 |
| `1-3,7,9-11` | Mixed ranges and numbers | Selects #1, #2, #3, #7, #9, #10, #11 |
| `all` | Select all projects | Selects every project |
| `none` or Enter | Select no projects | Cancels operation |

### Workflow Example

1. **Start the script**:
   ```bash
   python dev-tools/utilities/manage_projects_interactive.py
   ```

2. **View all projects**:
   ```
   📋 Available Projects:
   ======================================================================
     1. Test Project - Main Board
         ID: 1234567890 | 1 board
     2. Production App - Dev Board
         ID: 0987654321 | 2 boards
     3. Archived Project - Old Board
         ID: 1111111111 | 1 board
   ======================================================================
   ```

3. **Choose mode**:
   ```
   🔧 What would you like to do?
     1. Select projects to DELETE
     2. Select projects to KEEP (delete all others)
     3. Exit without changes

   Enter choice (1-3) > 1
   ```

4. **Select projects** (using ranges and numbers):
   ```
   🎯 Select projects to DELETE:
      • Enter numbers: 1,3,5 or ranges: 1-5 or both: 1-3,7,9-11
      • Type 'all' to delete all projects
      • Type 'none' or press Enter to delete none

   Projects to delete > 1,3
   ```

5. **Review selection**:
   ```
   📌 You selected 2 project(s) to delete:
      • Test Project - Main Board
      • Archived Project - Old Board

   ✓ Proceed to delete these projects? (y/n) > y
   ```

6. **Review summary and confirm**:
   ```
   ======================================================================
   📊 SUMMARY
   ======================================================================

   ✅ Projects to KEEP (1):
      • Production App - Dev Board

   ❌ Projects to DELETE (2):
      • Test Project - Main Board (1 boards)
      • Archived Project - Old Board (1 boards)

   ======================================================================

   ⚠️  WARNING: This action cannot be undone!
   You are about to DELETE 2 project(s).

   Type 'DELETE' to confirm (case-sensitive) > DELETE
   ```

7. **Deletion completes**:
   ```
   🗑️  Deleting 2 project(s)...
      ✅ Deleted: Test Project - Main Board
      ✅ Deleted: Archived Project - Old Board

   ======================================================================
   ✅ Successfully deleted 2 project(s)
   🎯 Project management complete!
   ======================================================================
   ```

## Keep Mode Example

If you want to keep only certain projects and delete everything else:

```
Enter choice (1-3) > 2

🎯 Select projects to KEEP:
   • Enter numbers: 1,3,5 or ranges: 1-5 or both: 1-3,7,9-11
   • Type 'all' to keep all projects
   • Type 'none' or press Enter to keep none

Projects to keep > 2

📌 You selected 1 project(s) to keep:
   • Production App - Dev Board

✓ Proceed to keep these projects? (y/n) > y
```

This will delete all projects **except** the ones you selected to keep.

## Safety Features

### Multiple Confirmation Steps

1. **Selection confirmation**: After selecting projects, you must confirm with `y/yes`
2. **Final confirmation**: Before deletion, you must type `DELETE` (case-sensitive)
3. **Summary review**: See exactly what will be kept and deleted before proceeding

### Error Prevention

- Invalid selections show clear error messages
- Can retry selection without restarting
- Press Ctrl+C at any time to abort
- No changes are made until final `DELETE` confirmation

## Configuration

The script automatically loads Planka configuration from `config_marcus.json`:

```json
{
  "planka": {
    "base_url": "http://localhost:3333",
    "email": "your-email@example.com",
    "password": "your-password"  # pragma: allowlist secret
  }
}
```

## Troubleshooting

### "Planka service is not available"

- Ensure Planka is running: `docker ps | grep planka`
- Check the URL in `config_marcus.json`
- Verify you can access Planka in your browser

### "Cannot find kanban-mcp"

Set the `KANBAN_MCP_PATH` environment variable:

```bash
export KANBAN_MCP_PATH=/path/to/kanban-mcp/dist/index.js
python dev-tools/utilities/manage_projects_interactive.py
```

### "config_marcus.json not found"

Create the config file in the project root:

```bash
cd /path/to/marcus
cat > config_marcus.json << 'EOF'
{
  "planka": {
    "base_url": "http://localhost:3333",
    "email": "demo@demo.demo",
    "password": "demo"  # pragma: allowlist secret
  }
}
EOF
```

## Testing

The tool includes comprehensive unit tests:

```bash
# Run tests
python -m pytest tests/unit/dev_tools/test_manage_projects_interactive.py -v

# Check test coverage
python -m pytest tests/unit/dev_tools/test_manage_projects_interactive.py --cov=dev-tools/utilities/manage_projects_interactive
```

## Related Tools

- [delete_all_projects.py](delete_all_projects.py) - Non-interactive bulk deletion (use with caution!)
- [create_fresh_project.py](create_fresh_project.py) - Create new projects

## Notes

- This tool operates directly on your Planka board via the kanban-mcp server
- Deleted projects cannot be recovered unless you have a backup
- Board counts shown include all boards within each project
- The tool automatically detects whether you're running in Docker or locally
