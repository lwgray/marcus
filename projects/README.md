# PM Agent Projects

This directory contains example projects and templates that can be created using PM Agent with Planka boards.

## Available Projects

### 1. Todo App (`todo_app/`)
A comprehensive Todo application development project with:
- 17 development cards covering full stack development
- Three levels of detail (comprehensive, moderate, minimal)
- Complete documentation including API specs and database schemas
- Interactive menu for easy project creation

## Project Structure

Each project folder contains:
- Card creation scripts with varying detail levels
- JSON configuration files defining the project structure
- Documentation and specifications
- Interactive menu for easy setup

## Usage

To use any project:

1. Navigate to the project directory:
   ```bash
   cd projects/todo_app
   ```

2. Run the interactive menu:
   ```bash
   python create_todo_cards_menu.py
   ```

3. Or run specific scripts directly:
   ```bash
   python create_all_todo_app_cards.py    # Comprehensive
   python create_moderate_todo_cards_v2.py # Moderate
   python create_minimal_todo_cards_v2.py  # Minimal
   ```

## Adding New Projects

To add a new project:

1. Create a new directory under `projects/`
2. Add your card definition JSON file
3. Create card creation scripts (use todo_app as a template)
4. Add project-specific documentation
5. Create a README.md for your project

## Requirements

- Planka running at `http://localhost:3333`
- kanban-mcp server installed
- "Task Master Test" project in Planka
- Python 3.8+
