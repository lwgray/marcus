"""
Database schema and initialization for Simple Todo App
"""

import os
import sqlite3


def init_db():
    """Initialize the SQLite database with todos table"""
    db_path = os.path.join(os.path.dirname(__file__), "todos.db")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create todos table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            completed BOOLEAN DEFAULT FALSE,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    conn.commit()
    conn.close()
    print(f"Database initialized at {db_path}")


def get_db_connection():
    """Get a database connection"""
    db_path = os.path.join(os.path.dirname(__file__), "todos.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # This allows dict-like access to rows
    return conn


if __name__ == "__main__":
    init_db()
