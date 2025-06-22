# Todo App Card Creators

This directory contains scripts to create Todo App development cards on a Planka board with varying levels of detail.

## Available Scripts

### 1. Comprehensive Cards (`create_all_todo_app_cards.py`)
- **Description**: Creates highly detailed cards with extensive documentation
- **Features**:
  - 2000+ word descriptions per card
  - 12-16 subtasks per card
  - Multiple labels and dependencies
  - Due dates and time estimates
  - Detailed technical requirements
  - Implementation guidelines
  - Best practices documentation

### 2. Moderate Cards (`create_moderate_todo_cards_v2.py`)
- **Description**: Creates cards with practical, focused detail
- **Features**:
  - Concise but informative descriptions
  - 4-6 subtasks per card
  - Key technical points
  - Essential labels
  - Due dates
  - Clear objectives and requirements

### 3. Minimal Cards (`create_minimal_todo_cards_v2.py`)
- **Description**: Creates cards with just the essential information
- **Features**:
  - One-line descriptions
  - 1-2 subtasks per card
  - Only high-priority labels
  - Basic task breakdown

## Interactive Menu

Use `create_todo_cards_menu.py` for an interactive way to choose which level of detail you want:

```bash
python create_todo_cards_menu.py
```

## Prerequisites

1. **Planka Setup**: Ensure Planka is running at `http://localhost:3333`
2. **MCP Server**: The kanban-mcp server must be installed at `/Users/lwgray/dev/kanban-mcp/`
3. **Environment**: Uses demo credentials (demo@demo.demo / demo)
4. **Project**: Requires "Task Master Test" project to exist in Planka

## Usage

### Run Individual Scripts

```bash
# For comprehensive cards
python create_all_todo_app_cards.py

# For moderate detail cards
python create_moderate_todo_cards_v2.py

# For minimal cards
python create_minimal_todo_cards_v2.py
```

### Use Interactive Menu

```bash
python create_todo_cards_menu.py
```

## What Gets Created

All scripts create the same 17 cards for building a Todo App:

1. Set up project structure
2. Design database schema
3. Create Todo model
4. Set up database connection
5. Create API endpoints for CRUD operations
6. Add input validation middleware
7. Implement error handling
8. Create frontend app structure
9. Design UI mockups
10. Build TodoList component
11. Build TodoItem component
12. Build AddTodo form component
13. Implement API client service
14. Connect frontend to backend
15. Add user authentication
16. Write comprehensive tests
17. Deploy to production

## Card Structure

Each card includes:
- **Title**: Clear, action-oriented task name
- **Description**: Varies by detail level
- **Subtasks**: Checklist items (quantity varies by detail level)
- **Labels**: Categorization (Feature, Frontend, Backend, etc.)
- **Due Date**: Timeline for completion
- **Position**: Order in the backlog

## When to Use Each Version

- **Comprehensive**: 
  - New team members who need detailed guidance
  - Complex projects requiring extensive documentation
  - When you need reference documentation
  
- **Moderate**:
  - Experienced teams who need clear objectives
  - Standard projects with known patterns
  - When you want balance between detail and brevity
  
- **Minimal**:
  - Very experienced teams
  - Quick prototypes or MVPs
  - When you just need task tracking

## Notes

- All cards are created in the "Backlog" list
- Existing cards in the Backlog are cleared before creating new ones
- The scripts use the MCP (Model Context Protocol) to communicate with Planka
- Labels must already exist in the Planka board

## Troubleshooting

If you encounter errors:
1. Ensure Planka is running and accessible
2. Check that the kanban-mcp server is properly installed
3. Verify the "Task Master Test" project exists
4. Ensure all required labels exist on the board