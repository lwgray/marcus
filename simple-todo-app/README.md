# Simple Todo App

A basic CRUD todo application built with Flask and SQLite.

## Features

- Create, read, update, and delete todo items
- Mark todos as complete/incomplete
- Simple web interface with Bootstrap styling
- SQLite database for persistence

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python app.py
```

3. Open your browser to `http://localhost:5000`

## Usage

- **View Todos**: Visit the home page to see all todos
- **Add Todo**: Click "Add New Todo" to create a new todo item
- **Edit Todo**: Click "Edit" on any todo to modify it
- **Toggle Status**: Click "Mark Complete/Incomplete" to change todo status
- **Delete Todo**: Click "Delete" to remove a todo (with confirmation)

## Database Schema

The application uses SQLite with a simple `todos` table:

- `id`: Primary key (auto-increment)
- `title`: Todo title (required)
- `description`: Optional description
- `completed`: Boolean status (default: false)
- `created_date`: Timestamp of creation

## Project Structure

```
simple-todo-app/
├── app.py              # Main Flask application
├── database.py         # Database setup and connection
├── requirements.txt    # Python dependencies
├── README.md          # This file
├── templates/         # HTML templates
│   ├── base.html      # Base template
│   ├── index.html     # Todo list view
│   ├── add.html       # Add todo form
│   └── edit.html      # Edit todo form
└── static/           # Static files
    └── style.css     # Custom CSS
```
