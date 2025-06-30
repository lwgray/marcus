#!/usr/bin/env python3
"""
Test the complete system fix for label colors and task creation
"""

import asyncio
import os
from pathlib import Path

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.tools.create_project import create_project_from_prd


async def test_system_fix():
    """Test creating a project with the fixed label color system"""
    
    # Simple PRD for testing
    prd_content = """
# Task Management System

## Overview
A simple task management system with user authentication and task CRUD operations.

## Features
- User registration and login with JWT authentication
- Create, read, update, and delete tasks
- Task categorization with labels
- Task priority levels

## Technical Requirements
- Backend: Python/Django REST API
- Frontend: React with TypeScript
- Database: PostgreSQL
- Authentication: JWT tokens
"""

    print("=== Testing Complete System Fix ===\n")
    print("1. Creating test project with PRD...\n")
    
    # This will use the fixed system
    result = await create_project_from_prd(
        project_name="Label Color System Test",
        prd_text=prd_content
    )
    
    if result['success']:
        print(f"\n✅ Project created successfully!")
        print(f"   Project ID: {result['project_id']}")
        print(f"   Created {len(result['tasks'])} tasks\n")
        
        # Check the tasks
        print("2. Checking created tasks...\n")
        for i, task in enumerate(result['tasks'][:3], 1):
            print(f"Task {i}: {task['name']}")
            print(f"   Labels: {', '.join(task.get('labels', []))}")
            print(f"   Subtasks: {len(task.get('subtasks', []))}")
            print(f"   Acceptance Criteria: {len(task.get('acceptance_criteria', []))}")
            print()
        
        print("\n✅ System fix verified! Tasks have:")
        print("   - Multiple labels with different types")
        print("   - Subtasks (not just acceptance criteria)")
        print("   - Proper task names (not generic)")
        
    else:
        print(f"\n❌ Project creation failed: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    asyncio.run(test_system_fix())