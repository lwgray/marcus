"""
Simple Todo App with Flask
A basic CRUD application for managing todo items
"""

import os

from database import get_db_connection, init_db
from flask import Flask, flash, redirect, render_template, request, url_for

app = Flask(__name__)
app.secret_key = os.environ.get(
    "SECRET_KEY", "dev-key-change-in-production"
)  # pragma: allowlist secret

# Initialize database on startup
init_db()


@app.route("/")
def index():
    """Display all todos"""
    conn = get_db_connection()
    todos = conn.execute("SELECT * FROM todos ORDER BY created_date DESC").fetchall()
    conn.close()
    return render_template("index.html", todos=todos)


@app.route("/add", methods=["GET", "POST"])
def add_todo():
    """Add a new todo"""
    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]

        if title:
            conn = get_db_connection()
            conn.execute(
                "INSERT INTO todos (title, description) VALUES (?, ?)",
                (title, description),
            )
            conn.commit()
            conn.close()
            flash("Todo added successfully!", "success")
            return redirect(url_for("index"))
        else:
            flash("Title is required!", "error")

    return render_template("add.html")


@app.route("/edit/<int:todo_id>", methods=["GET", "POST"])
def edit_todo(todo_id):
    """Edit an existing todo"""
    conn = get_db_connection()
    todo = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()

    if not todo:
        flash("Todo not found!", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        completed = "completed" in request.form

        if title:
            conn.execute(
                "UPDATE todos SET title = ?, description = ?, "
                "completed = ? WHERE id = ?",
                (title, description, completed, todo_id),
            )
            conn.commit()
            conn.close()
            flash("Todo updated successfully!", "success")
            return redirect(url_for("index"))
        else:
            flash("Title is required!", "error")

    conn.close()
    return render_template("edit.html", todo=todo)


@app.route("/delete/<int:todo_id>")
def delete_todo(todo_id):
    """Delete a todo"""
    conn = get_db_connection()
    conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    conn.commit()
    conn.close()
    flash("Todo deleted successfully!", "success")
    return redirect(url_for("index"))


@app.route("/toggle/<int:todo_id>")
def toggle_todo(todo_id):
    """Toggle todo completed status"""
    conn = get_db_connection()
    todo = conn.execute(
        "SELECT completed FROM todos WHERE id = ?", (todo_id,)
    ).fetchone()

    if todo:
        new_status = not todo["completed"]
        conn.execute(
            "UPDATE todos SET completed = ? WHERE id = ?", (new_status, todo_id)
        )
        conn.commit()
        flash("Todo status updated!", "success")

    conn.close()
    return redirect(url_for("index"))


if __name__ == "__main__":
    # Only use debug=True and bind to all interfaces in development
    debug_mode = os.environ.get("FLASK_ENV") == "development"
    host = "127.0.0.1" if not debug_mode else "0.0.0.0"  # nosec B104
    app.run(debug=debug_mode, host=host, port=5000)
