# Utilities

Maintenance and setup utilities for managing Marcus projects and boards.

## Tools Overview

| Tool | Purpose | Safety |
|------|---------|--------|
| `clear_board.py` | Clear all tasks from Kanban board | ⚠️ Destructive |
| `delete_all_projects.py` | Remove all Marcus projects | ⚠️ Destructive |
| `create_fresh_project.py` | Create new test project | ✅ Safe |
| `run_through_board.py` | Process tasks through board | ⚠️ Modifies state |
| `setup_marcus_project.sh` | Initial Marcus project setup | ✅ Safe |
| `test_subtask_fixes.sh` | Test subtask handling fixes | ✅ Safe |

## Quick Reference

### Clean Slate
```bash
# Remove all projects and clear board
python delete_all_projects.py
python clear_board.py

# Create fresh test project
python create_fresh_project.py
```

### Setup
```bash
# Initial Marcus setup
./setup_marcus_project.sh

# Test subtask functionality
./test_subtask_fixes.sh
```

## Detailed Tool Documentation

### clear_board.py ⚠️

Removes all tasks from a Kanban board, providing a clean slate for testing.

**⚠️ WARNING**: This is destructive and cannot be undone!

**Features**:
- Removes all tasks from board
- Clears all columns (To Do, In Progress, Done)
- Supports dry-run mode
- Requires confirmation

**Usage**:
```bash
# Dry run (shows what would be deleted)
python clear_board.py --dry-run

# Interactive mode with confirmation
python clear_board.py

# Force clear without confirmation (dangerous!)
python clear_board.py --force

# Clear specific board
python clear_board.py --board-name "Test Board"

# Clear board by ID
python clear_board.py --board-id 12345
```

**Output Example**:
```
=== CLEAR BOARD UTILITY ===
Board: Marcus Development Board
Tasks found: 47

⚠️  This will delete ALL 47 tasks from the board!
This action CANNOT be undone!

Proceed? [yes/no]: yes

Deleting tasks:
  ✓ Deleted task_1: Setup project structure
  ✓ Deleted task_2: Configure database
  ...
  ✓ Deleted task_47: Final deployment

✅ Successfully deleted 47 tasks
Board is now empty
```

**When to Use**:
- Starting fresh experiment
- Cleaning up after failed tests
- Resetting development environment
- Before major project changes

**Best Practices**:
- Always use `--dry-run` first
- Export board state before clearing (if needed)
- Coordinate with team before clearing shared boards
- Consider archiving completed work first

---

### delete_all_projects.py ⚠️

Removes all projects from Marcus, including their tasks and metadata.

**⚠️ WARNING**: This is destructive and cannot be undone!

**Features**:
- Deletes all Marcus projects
- Removes associated tasks
- Cleans up metadata
- Supports dry-run and confirmation

**Usage**:
```bash
# Dry run (shows what would be deleted)
python delete_all_projects.py --dry-run

# Interactive mode with confirmation
python delete_all_projects.py

# Force delete without confirmation (dangerous!)
python delete_all_projects.py --force

# Delete projects matching pattern
python delete_all_projects.py --pattern "test_*"

# Keep specific projects
python delete_all_projects.py --except "Production API"
```

**Output Example**:
```
=== DELETE ALL PROJECTS UTILITY ===
Found 3 projects:
  1. Task Management API (15 tasks)
  2. Calculator Demo (5 tasks)
  3. Test Project (0 tasks)

Total: 3 projects, 20 tasks

⚠️  This will DELETE ALL projects and their tasks!
This action CANNOT be undone!

Proceed? [yes/no]: yes

Deleting projects:
  ✓ Deleted "Task Management API" (15 tasks)
  ✓ Deleted "Calculator Demo" (5 tasks)
  ✓ Deleted "Test Project" (0 tasks)

✅ Successfully deleted 3 projects (20 tasks total)
```

**When to Use**:
- Resetting Marcus completely
- Cleaning up after experiments
- Starting new development cycle
- Removing test projects

**Best Practices**:
- Always use `--dry-run` first
- Backup important projects before deleting
- Verify project names carefully
- Use `--pattern` for targeted deletion
- Coordinate with team on shared instances

---

### create_fresh_project.py ✅

Creates a new test project in Marcus with configurable specifications.

**Features**:
- Quick project creation
- Customizable project specs
- Template support
- Default configurations

**Usage**:
```bash
# Create with default settings
python create_fresh_project.py

# Create with custom name
python create_fresh_project.py --name "My Test Project"

# Use custom spec file
python create_fresh_project.py --spec my_project.md

# Use example template
python create_fresh_project.py --template calculator

# Set complexity level
python create_fresh_project.py --complexity medium

# Choose board provider
python create_fresh_project.py --provider planka
```

**Available Templates**:
- `calculator` - Simple calculator application
- `todo` - Todo list application
- `api` - REST API project
- `fullstack` - Full-stack web app

**Output Example**:
```
=== CREATE FRESH PROJECT ===
Name: My Test Project
Template: calculator
Complexity: simple
Provider: planka

Creating project...
  ✓ Project created: project_id_12345
  ✓ Board created: board_id_67890
  ✓ Tasks generated: 8 tasks
  ✓ Dependencies configured

✅ Project ready!
   Project ID: 12345
   Board URL: https://kanban.example.com/board/67890
   Tasks: 8
   Estimated time: 2-3 hours
```

**When to Use**:
- Testing Marcus functionality
- Experimenting with configurations
- Creating examples or demos
- Quick project prototyping

**Custom Spec File**:
```markdown
# My Project

## Overview
Brief description of what to build

## Features
- Feature 1
- Feature 2

## Technical Stack
- Language: Python
- Framework: FastAPI
- Database: PostgreSQL
```

---

### run_through_board.py ⚠️

Processes tasks through the Kanban board, simulating or executing workflow.

**Features**:
- Simulates task progression
- Can auto-complete tasks
- Tracks task lifecycle
- Generates metrics

**Usage**:
```bash
# Simulate task progression
python run_through_board.py --simulate

# Actually process tasks
python run_through_board.py

# Process specific number of tasks
python run_through_board.py --count 5

# Process until specific task
python run_through_board.py --until task_10

# Auto-complete tasks
python run_through_board.py --auto-complete

# Generate report
python run_through_board.py --report output.json
```

**Output Example**:
```
=== RUN THROUGH BOARD ===
Board: Test Project Board
Tasks available: 12

Processing tasks:
  task_1: Setup project → In Progress → Done (2.3s)
  task_2: Configure DB → In Progress → Done (1.8s)
  task_3: Create models → In Progress → Done (3.1s)
  ...

✅ Processed 5 tasks
   Average time: 2.4s per task
   Success rate: 100%
```

**When to Use**:
- Testing board workflows
- Validating task dependencies
- Generating test data
- Performance testing

---

### setup_marcus_project.sh ✅

Initial setup script for Marcus project environment.

**Features**:
- Installs dependencies
- Configures environment
- Sets up directory structure
- Validates setup

**Usage**:
```bash
# Basic setup
./setup_marcus_project.sh

# Setup with custom Python version
./setup_marcus_project.sh --python python3.11

# Skip dependency installation
./setup_marcus_project.sh --no-deps

# Setup for development
./setup_marcus_project.sh --dev
```

**What It Does**:
1. Creates virtual environment
2. Installs Python dependencies
3. Sets up configuration files
4. Creates necessary directories
5. Validates Marcus installation
6. Configures MCP server

**Output Example**:
```
=== MARCUS PROJECT SETUP ===

[1/6] Creating virtual environment...
  ✓ Virtual environment created at venv/

[2/6] Installing dependencies...
  ✓ Installed core dependencies
  ✓ Installed dev dependencies

[3/6] Setting up configuration...
  ✓ Created .env file
  ✓ Configured MCP server

[4/6] Creating directories...
  ✓ Created logs/
  ✓ Created data/

[5/6] Validating installation...
  ✓ Marcus importable
  ✓ MCP server accessible

[6/6] Final checks...
  ✓ All checks passed

✅ Setup complete!
   Activate environment: source venv/bin/activate
   Run Marcus: python -m marcus
```

**When to Use**:
- First-time Marcus installation
- Setting up development environment
- After cloning repository
- Resetting environment

---

### test_subtask_fixes.sh ✅

Tests subtask handling and fixes in Marcus.

**Features**:
- Validates subtask registration
- Tests dependency resolution
- Checks error handling
- Generates test report

**Usage**:
```bash
# Run all subtask tests
./test_subtask_fixes.sh

# Run specific test suite
./test_subtask_fixes.sh --suite registration

# Verbose output
./test_subtask_fixes.sh --verbose

# Generate report
./test_subtask_fixes.sh --report subtask_report.txt
```

**Test Suites**:
- `registration` - Subtask registration tests
- `dependencies` - Dependency resolution tests
- `lifecycle` - Subtask lifecycle tests
- `errors` - Error handling tests

**Output Example**:
```
=== SUBTASK FIXES TEST SUITE ===

[1/4] Testing subtask registration...
  ✓ Register single subtask
  ✓ Register multiple subtasks
  ✓ Register with dependencies
  ✓ Handle duplicate registration

[2/4] Testing dependency resolution...
  ✓ Simple dependency chain
  ✓ Complex dependency graph
  ✓ Circular dependency detection

[3/4] Testing lifecycle...
  ✓ Subtask creation
  ✓ Subtask assignment
  ✓ Subtask completion
  ✓ Subtask cancellation

[4/4] Testing error handling...
  ✓ Invalid subtask ID
  ✓ Missing dependencies
  ✓ Malformed subtask data

✅ All tests passed (16/16)
```

**When to Use**:
- After modifying subtask code
- Validating fixes
- Regression testing
- Before major releases

## Common Workflows

### Fresh Start Workflow

```bash
# 1. Clean everything
python delete_all_projects.py --dry-run  # Preview
python delete_all_projects.py            # Confirm and delete
python clear_board.py --dry-run          # Preview
python clear_board.py                    # Confirm and clear

# 2. Create fresh project
python create_fresh_project.py --name "Clean Test" --template api

# 3. Verify setup
cd ../diagnostics
python preview_project_plan.py
```

### Development Environment Setup

```bash
# 1. Initial setup
./setup_marcus_project.sh --dev

# 2. Validate subtasks
./test_subtask_fixes.sh

# 3. Create test project
python create_fresh_project.py --template calculator

# 4. Test workflow
python run_through_board.py --simulate
```

### Experiment Preparation

```bash
# 1. Clean slate
python delete_all_projects.py
python clear_board.py

# 2. Create multiple test projects
python create_fresh_project.py --name "Experiment 1" --template api
python create_fresh_project.py --name "Experiment 2" --template fullstack

# 3. Validate
cd ../diagnostics
python preview_project_plan.py
```

## Safety Guidelines

### Before Using Destructive Tools

**ALWAYS**:
1. Run with `--dry-run` first
2. Review what will be deleted
3. Backup important data
4. Coordinate with team
5. Double-check board/project names

**NEVER**:
1. Use `--force` in production
2. Clear shared boards without notice
3. Delete without verification
4. Skip backups for important work

### Confirmation Prompts

Most destructive tools require confirmation:
```
Proceed? [yes/no]:
```

You must type **exactly** `yes` to proceed. Any other input (including `y`, `Yes`, `YES`) will abort.

### Dry Run Mode

Always available for destructive operations:
```bash
--dry-run    # Shows what would happen without doing it
```

## Error Handling

### "Board not found"
- Verify board name/ID is correct
- Check Marcus MCP server connection
- Ensure board exists in Kanban system

### "Permission denied"
- Check credentials in environment
- Verify board access permissions
- Ensure MCP server is running with correct auth

### "Project creation failed"
- Check spec file format
- Verify template exists
- Ensure board provider is available
- Review logs for specific error

## Environment Variables

Required for most utilities:

```bash
# Kanban board configuration
export KANBAN_URL="https://your-kanban.com"
export KANBAN_TOKEN="your_token_here"

# Marcus configuration
export MARCUS_CONFIG_PATH="/path/to/config"
export MARCUS_LOG_LEVEL="INFO"
```

See `example_project_description.txt` for project spec templates.

## Requirements

- Python 3.8+
- Marcus MCP server running
- Kanban board access
- Appropriate permissions for destructive operations
- Bash shell (for .sh scripts)

## Support

For utility issues:
- Check tool-specific `--help` output
- Review error messages carefully
- Ensure environment variables are set
- Verify Marcus MCP server is operational
- See main dev-tools/README.md for general troubleshooting
