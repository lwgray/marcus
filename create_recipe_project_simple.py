#!/usr/bin/env python3
"""
Create the Smart Recipe Manager project with predefined tasks
"""

import asyncio
from datetime import datetime
from pathlib import Path

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.integrations.kanban_client_with_create import KanbanClientWithCreate


async def create_recipe_project():
    """Create the Smart Recipe Manager project with predefined tasks"""
    
    print("Creating Smart Recipe Manager project...")
    print("=" * 60)
    
    # Initialize kanban client
    client = KanbanClientWithCreate()
    
    # Define tasks for the recipe manager project
    tasks = [
        {
            "name": "Setup project infrastructure and development environment",
            "description": "Initialize the project with React, TypeScript, Node.js, and PostgreSQL. Setup development tools and project structure.",
            "priority": "high",
            "labels": ["type:setup", "skill:fullstack", "component:infrastructure"],
            "estimated_hours": 8,
            "subtasks": [
                "Initialize React app with TypeScript",
                "Setup Node.js/Express backend",
                "Configure PostgreSQL database",
                "Setup development environment and tools",
                "Configure ESLint and Prettier"
            ],
            "acceptance_criteria": [
                "Project runs locally with hot reload",
                "Database connection established",
                "Basic folder structure in place"
            ]
        },
        {
            "name": "Design and implement database schema",
            "description": "Create PostgreSQL schema for users, recipes, ingredients, meal plans, and shopping lists.",
            "priority": "high",
            "labels": ["type:design", "skill:backend", "component:database"],
            "estimated_hours": 12,
            "subtasks": [
                "Design users table with authentication fields",
                "Create recipes table with relationships",
                "Design ingredients and recipe_ingredients tables",
                "Create meal_plans and shopping_lists tables",
                "Setup database migrations"
            ],
            "acceptance_criteria": [
                "All tables created with proper relationships",
                "Foreign keys and constraints in place",
                "Migration scripts ready"
            ]
        },
        {
            "name": "Implement user authentication system",
            "description": "Build JWT-based authentication with registration, login, and protected routes.",
            "priority": "high",
            "labels": ["type:feature", "skill:backend", "component:authentication"],
            "estimated_hours": 16,
            "subtasks": [
                "Create user registration endpoint",
                "Implement login with JWT generation",
                "Setup password hashing with bcrypt",
                "Create authentication middleware",
                "Implement refresh token mechanism"
            ],
            "acceptance_criteria": [
                "Users can register and login",
                "JWT tokens properly generated and validated",
                "Protected routes require authentication"
            ]
        },
        {
            "name": "Build recipe CRUD operations API",
            "description": "Create REST API endpoints for creating, reading, updating, and deleting recipes.",
            "priority": "high",
            "labels": ["type:feature", "skill:backend", "component:api"],
            "estimated_hours": 20,
            "subtasks": [
                "Create POST /api/recipes endpoint",
                "Implement GET /api/recipes with pagination",
                "Build PUT /api/recipes/:id endpoint",
                "Create DELETE /api/recipes/:id endpoint",
                "Add ingredient management to recipes"
            ],
            "acceptance_criteria": [
                "All CRUD operations working",
                "Proper validation on inputs",
                "Only recipe owners can edit/delete"
            ]
        },
        {
            "name": "Create React UI for recipe management",
            "description": "Build frontend components for displaying and managing recipes.",
            "priority": "medium",
            "labels": ["type:feature", "skill:frontend", "component:ui"],
            "estimated_hours": 24,
            "subtasks": [
                "Create recipe list component with cards",
                "Build recipe detail view",
                "Implement recipe form for add/edit",
                "Add ingredient input with autocomplete",
                "Create recipe search and filter UI"
            ],
            "acceptance_criteria": [
                "Responsive recipe cards display",
                "Forms validate before submission",
                "Search updates results in real-time"
            ]
        },
        {
            "name": "Implement meal planning calendar",
            "description": "Create drag-and-drop calendar interface for weekly meal planning.",
            "priority": "medium",
            "labels": ["type:feature", "skill:frontend", "component:calendar"],
            "estimated_hours": 20,
            "subtasks": [
                "Build calendar grid component",
                "Implement drag-and-drop functionality",
                "Create meal slot components",
                "Add ability to assign recipes to days",
                "Save meal plans to database"
            ],
            "acceptance_criteria": [
                "Calendar shows current week by default",
                "Recipes can be dragged to calendar slots",
                "Meal plans persist after refresh"
            ]
        },
        {
            "name": "Build shopping list generator",
            "description": "Automatically generate shopping lists from selected meal plans.",
            "priority": "medium",
            "labels": ["type:feature", "skill:backend", "component:shopping"],
            "estimated_hours": 16,
            "subtasks": [
                "Create algorithm to aggregate ingredients",
                "Combine quantities for same ingredients",
                "Group items by category",
                "Generate printable shopping list",
                "Add ability to check off items"
            ],
            "acceptance_criteria": [
                "Ingredients properly aggregated",
                "Quantities correctly combined",
                "List can be exported/printed"
            ]
        },
        {
            "name": "Add recipe scaling functionality",
            "description": "Allow users to scale recipes up or down based on number of servings.",
            "priority": "low",
            "labels": ["type:feature", "skill:frontend", "component:recipes"],
            "estimated_hours": 12,
            "subtasks": [
                "Add serving size selector to recipes",
                "Implement ingredient scaling logic",
                "Handle fractional measurements",
                "Update UI to show scaled amounts",
                "Save preferred serving sizes"
            ],
            "acceptance_criteria": [
                "Ingredients scale proportionally",
                "Fractions display user-friendly",
                "Scaling persists per recipe"
            ]
        },
        {
            "name": "Integrate nutritional information",
            "description": "Add nutritional data tracking and display for recipes.",
            "priority": "low",
            "labels": ["type:feature", "skill:backend", "component:nutrition"],
            "estimated_hours": 16,
            "subtasks": [
                "Research nutrition API options",
                "Integrate nutrition data API",
                "Calculate recipe nutrition totals",
                "Display nutrition per serving",
                "Add dietary restriction filters"
            ],
            "acceptance_criteria": [
                "Nutrition data displayed per recipe",
                "Calculations accurate per serving",
                "Can filter by dietary restrictions"
            ]
        },
        {
            "name": "Implement search and filtering",
            "description": "Build advanced search with filters for ingredients, dietary restrictions, and more.",
            "priority": "medium",
            "labels": ["type:feature", "skill:fullstack", "component:search"],
            "estimated_hours": 14,
            "subtasks": [
                "Create search API with query parameters",
                "Implement ingredient-based search",
                "Add dietary restriction filters",
                "Build search UI with filters",
                "Add search result pagination"
            ],
            "acceptance_criteria": [
                "Search returns relevant results",
                "Multiple filters can be combined",
                "Results paginated properly"
            ]
        }
    ]
    
    # Create all tasks
    created_tasks = []
    for i, task_data in enumerate(tasks, 1):
        print(f"\n[{i}/{len(tasks)}] Creating: {task_data['name']}")
        try:
            task = await client.create_task(task_data)
            created_tasks.append(task)
            print(f"   ✅ Created with {len(task_data.get('labels', []))} labels")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
    
    print(f"\n{'='*60}")
    print(f"✅ Project created successfully!")
    print(f"   Total tasks: {len(created_tasks)}")
    print(f"\n🎉 Your Smart Recipe Manager project is ready on the kanban board!")
    
    return created_tasks


if __name__ == "__main__":
    asyncio.run(create_recipe_project())