#!/usr/bin/env python3
"""
Simple demo showing the concept of NLP project creation on boards
"""

import json
from datetime import datetime

def demo_nlp_to_board():
    """Demonstrate how NLP creates tasks that appear on boards"""
    
    print("🎯 Natural Language → Kanban Board Demo")
    print("="*60)
    
    # Step 1: Natural Language Input
    print("\n📝 Step 1: User provides natural language description")
    print("-"*40)
    description = """
    "I need a todo app with:
    - User accounts and login
    - Create, edit, delete todos  
    - Mark todos as complete
    - Filter by status"
    """
    print(description)
    
    # Step 2: AI Parsing
    print("\n🤖 Step 2: AI parses into structured tasks")
    print("-"*40)
    
    # Simulated AI output
    parsed_tasks = [
        {
            "phase": "Backend Setup",
            "tasks": [
                {"title": "Set up Node.js project structure", "labels": ["backend", "setup"]},
                {"title": "Implement user authentication API", "labels": ["backend", "auth"]},
                {"title": "Create todo CRUD endpoints", "labels": ["backend", "api"]}
            ]
        },
        {
            "phase": "Frontend Development",
            "tasks": [
                {"title": "Create React app with routing", "labels": ["frontend", "setup"]},
                {"title": "Build login/register components", "labels": ["frontend", "auth"]},
                {"title": "Implement todo list UI", "labels": ["frontend", "ui"]}
            ]
        },
        {
            "phase": "Testing & Deployment",
            "tasks": [
                {"title": "Write API tests", "labels": ["testing", "backend"]},
                {"title": "Write frontend tests", "labels": ["testing", "frontend"]},
                {"title": "Deploy to production", "labels": ["deployment"], "depends_on": ["all_tests"]}
            ]
        }
    ]
    
    print("✓ AI identified 3 phases with 9 total tasks")
    for phase in parsed_tasks:
        print(f"\n  {phase['phase']}:")
        for task in phase['tasks']:
            print(f"    - {task['title']}")
    
    # Step 3: Safety Checks
    print("\n🛡️ Step 3: Marcus applies safety checks")
    print("-"*40)
    print("✓ Deployment task depends on all tests")
    print("✓ No premature production changes")
    print("✓ Dependencies properly mapped")
    
    # Step 4: Board Creation
    print("\n📋 Step 4: Tasks appear on Kanban board")
    print("-"*40)
    
    # Show what the board would look like
    board_columns = {
        "Backlog": [],
        "To Do": [],
        "In Progress": [],
        "Done": []
    }
    
    # All tasks start in Backlog
    task_id = 1
    for phase in parsed_tasks:
        for task in phase['tasks']:
            board_columns["Backlog"].append({
                "id": f"TASK-{task_id}",
                "title": task['title'],
                "labels": task.get('labels', []),
                "created": datetime.now().isoformat()
            })
            task_id += 1
    
    print("\nKanban Board State:")
    for column, tasks in board_columns.items():
        print(f"\n  {column} ({len(tasks)} tasks):")
        for task in tasks[:3]:  # Show first 3
            print(f"    [{task['id']}] {task['title']}")
            if task['labels']:
                print(f"         Labels: {', '.join(task['labels'])}")
        if len(tasks) > 3:
            print(f"    ... and {len(tasks) - 3} more")
    
    # Step 5: Integration Tests
    print("\n✅ Step 5: Integration tests verify tasks on board")
    print("-"*40)
    print("The integration tests we created check:")
    print("  1. Tasks actually appear on Planka/GitHub board")
    print("  2. Task count matches what was created")
    print("  3. Labels and properties are preserved")
    print("  4. Dependencies are properly set")
    
    # Summary
    print("\n" + "="*60)
    print("🎉 Summary: Natural Language → Real Kanban Tasks")
    print("="*60)
    print("\n1. User describes project in plain English")
    print("2. Marcus AI parses into structured tasks")
    print("3. Safety checks prevent deployment disasters") 
    print("4. Tasks created on actual Kanban board")
    print("5. Integration tests verify everything works")
    
    print("\n📁 Test Files:")
    print("  - tests/test_nlp_board_integration.py (pytest)")
    print("  - tests/test_integration_nlp_board.py (detailed)")
    print("  - experiments/nlp_standalone_test.py (quick test)")

if __name__ == "__main__":
    demo_nlp_to_board()