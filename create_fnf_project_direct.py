#!/usr/bin/env python3
"""
Create Friday Night Funkin' project directly with predefined tasks
"""

import asyncio
from datetime import datetime
from pathlib import Path

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.integrations.kanban_client_with_create import KanbanClientWithCreate


async def create_fnf_project():
    """Create Friday Night Funkin' project with comprehensive tasks"""
    
    print("Creating Friday Night Funkin' Clone project...")
    print("=" * 60)
    
    # Initialize kanban client
    client = KanbanClientWithCreate()
    
    # Define tasks for the FNF clone project
    tasks = [
        # Core Architecture
        {
            "name": "Setup project architecture and development environment",
            "description": "Initialize HTML5 game project with Canvas API setup, folder structure, and development tools",
            "priority": "high",
            "labels": ["type:setup", "skill:fullstack", "component:infrastructure"],
            "estimated_hours": 6,
            "subtasks": [
                "Create HTML5 project structure",
                "Setup Canvas rendering context",
                "Configure development server",
                "Initialize git repository",
                "Setup build tools and asset pipeline"
            ],
            "acceptance_criteria": [
                "Project runs locally with canvas element",
                "Asset loading system in place",
                "Development server with hot reload"
            ]
        },
        {
            "name": "Implement game state management system",
            "description": "Create core game state manager for handling menus, gameplay, pause, and game over states",
            "priority": "high",
            "labels": ["type:feature", "skill:frontend", "component:game-engine"],
            "estimated_hours": 12,
            "subtasks": [
                "Design state machine architecture",
                "Implement state transition system",
                "Create base state class",
                "Add menu, gameplay, and pause states",
                "Handle state persistence"
            ],
            "acceptance_criteria": [
                "Smooth transitions between game states",
                "State data properly maintained",
                "Clean state cleanup on transitions"
            ]
        },
        {
            "name": "Build rhythm game input system",
            "description": "Create precise input handling for arrow keys with timing windows and input buffering",
            "priority": "high",
            "labels": ["type:feature", "skill:frontend", "component:gameplay"],
            "estimated_hours": 16,
            "subtasks": [
                "Implement keyboard event listeners",
                "Create input timing windows (perfect, good, bad, miss)",
                "Add input buffering for better feel",
                "Handle simultaneous key presses",
                "Create visual input feedback"
            ],
            "acceptance_criteria": [
                "Responsive input detection",
                "Accurate timing windows",
                "No dropped inputs during gameplay"
            ]
        },
        {
            "name": "Develop note scrolling and generation system",
            "description": "Create the note highway system with scrolling arrows synced to beat maps",
            "priority": "high",
            "labels": ["type:feature", "skill:frontend", "component:gameplay"],
            "estimated_hours": 20,
            "subtasks": [
                "Design note data structure",
                "Implement note spawning from beat maps",
                "Create smooth note scrolling",
                "Add note recycling for performance",
                "Sync notes to music timing"
            ],
            "acceptance_criteria": [
                "Notes scroll smoothly at all speeds",
                "Perfect sync with music beats",
                "No performance issues with many notes"
            ]
        },
        {
            "name": "Implement music synchronization engine",
            "description": "Build Web Audio API based music system with precise beat tracking and sync",
            "priority": "high",
            "labels": ["type:feature", "skill:frontend", "component:audio"],
            "estimated_hours": 18,
            "subtasks": [
                "Setup Web Audio API context",
                "Implement audio loading and buffering",
                "Create beat tracking system",
                "Add audio playback controls",
                "Sync visual elements to audio time"
            ],
            "acceptance_criteria": [
                "Audio plays without latency",
                "Beat tracking stays in sync",
                "Smooth audio transitions"
            ]
        },
        {
            "name": "Create character animation system",
            "description": "Build sprite-based animation system for player and opponent characters",
            "priority": "medium",
            "labels": ["type:feature", "skill:frontend", "component:graphics"],
            "estimated_hours": 24,
            "subtasks": [
                "Design animation state machine",
                "Implement sprite sheet loader",
                "Create idle animations",
                "Add singing animations per arrow",
                "Implement miss/fail animations",
                "Add animation blending"
            ],
            "acceptance_criteria": [
                "Smooth character animations",
                "Animations sync with inputs",
                "No animation glitches"
            ]
        },
        {
            "name": "Build health and scoring system",
            "description": "Implement health bar mechanics and scoring with combo multipliers",
            "priority": "medium",
            "labels": ["type:feature", "skill:frontend", "component:gameplay"],
            "estimated_hours": 14,
            "subtasks": [
                "Create health bar UI component",
                "Implement health gain/loss logic",
                "Build scoring algorithm",
                "Add combo system",
                "Create score display UI",
                "Add high score persistence"
            ],
            "acceptance_criteria": [
                "Health responds to hits/misses",
                "Score calculation is accurate",
                "Combos work correctly"
            ]
        },
        {
            "name": "Develop opponent AI system",
            "description": "Create AI that plays opponent notes automatically with configurable accuracy",
            "priority": "medium",
            "labels": ["type:feature", "skill:frontend", "component:ai"],
            "estimated_hours": 12,
            "subtasks": [
                "Parse opponent note patterns",
                "Implement auto-play logic",
                "Add accuracy variance for realism",
                "Sync AI with animations",
                "Handle special opponent patterns"
            ],
            "acceptance_criteria": [
                "AI plays notes on time",
                "Looks natural and synced",
                "Difficulty affects AI accuracy"
            ]
        },
        {
            "name": "Create menu and UI system",
            "description": "Build main menu, song selection, options, and pause menus",
            "priority": "medium",
            "labels": ["type:feature", "skill:frontend", "component:ui"],
            "estimated_hours": 16,
            "subtasks": [
                "Design menu layout and flow",
                "Create main menu screen",
                "Build song selection interface",
                "Add options/settings menu",
                "Implement pause menu",
                "Add menu transitions"
            ],
            "acceptance_criteria": [
                "Intuitive menu navigation",
                "All options functional",
                "Smooth menu transitions"
            ]
        },
        {
            "name": "Implement difficulty system",
            "description": "Create Easy, Normal, and Hard modes with different note patterns",
            "priority": "medium",
            "labels": ["type:feature", "skill:frontend", "component:gameplay"],
            "estimated_hours": 10,
            "subtasks": [
                "Design difficulty parameters",
                "Create note pattern generators",
                "Adjust timing windows per difficulty",
                "Modify health loss/gain rates",
                "Add difficulty selection UI"
            ],
            "acceptance_criteria": [
                "Each difficulty feels distinct",
                "Proper progression in challenge",
                "Settings save between sessions"
            ]
        },
        {
            "name": "Create first playable song",
            "description": "Implement first complete song with all difficulties and patterns",
            "priority": "medium",
            "labels": ["type:content", "skill:frontend", "component:songs"],
            "estimated_hours": 12,
            "subtasks": [
                "Create beat map for song",
                "Design note patterns for each difficulty",
                "Add background and stage graphics",
                "Implement song-specific animations",
                "Test and balance gameplay"
            ],
            "acceptance_criteria": [
                "Song plays from start to finish",
                "All difficulties completable",
                "Feels fun and challenging"
            ]
        },
        {
            "name": "Add visual effects and polish",
            "description": "Implement particle effects, screen shakes, and visual feedback",
            "priority": "low",
            "labels": ["type:enhancement", "skill:frontend", "component:graphics"],
            "estimated_hours": 14,
            "subtasks": [
                "Create hit particle effects",
                "Add screen shake on misses",
                "Implement note hit animations",
                "Add UI transition effects",
                "Create combo visual feedback"
            ],
            "acceptance_criteria": [
                "Effects enhance gameplay feel",
                "No performance impact",
                "Effects are configurable"
            ]
        },
        {
            "name": "Implement responsive design",
            "description": "Make game playable on different screen sizes and orientations",
            "priority": "low",
            "labels": ["type:feature", "skill:frontend", "component:ui"],
            "estimated_hours": 10,
            "subtasks": [
                "Create responsive canvas scaling",
                "Adjust UI for different ratios",
                "Handle window resize events",
                "Test on various devices",
                "Add fullscreen support"
            ],
            "acceptance_criteria": [
                "Game scales properly",
                "UI remains usable at all sizes",
                "No visual artifacts"
            ]
        },
        {
            "name": "Create remaining songs",
            "description": "Implement 2 additional songs with unique patterns and themes",
            "priority": "low",
            "labels": ["type:content", "skill:frontend", "component:songs"],
            "estimated_hours": 20,
            "subtasks": [
                "Create beat maps for each song",
                "Design unique note patterns",
                "Add variety in BPM and style",
                "Create song-specific visuals",
                "Balance difficulty progression"
            ],
            "acceptance_criteria": [
                "Each song feels unique",
                "Consistent quality across songs",
                "Good difficulty curve"
            ]
        },
        {
            "name": "Testing and bug fixes",
            "description": "Comprehensive testing and bug fixing across all systems",
            "priority": "low",
            "labels": ["type:testing", "skill:fullstack", "component:quality"],
            "estimated_hours": 16,
            "subtasks": [
                "Test input responsiveness",
                "Verify audio sync accuracy",
                "Check performance optimization",
                "Fix animation glitches",
                "Browser compatibility testing"
            ],
            "acceptance_criteria": [
                "No game-breaking bugs",
                "Consistent 60 FPS",
                "Works in major browsers"
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
    print(f"   Estimated hours: {sum(t.get('estimated_hours', 0) for t in tasks)}")
    print(f"\n🎮 Your Friday Night Funkin' Clone project is ready on the kanban board!")
    
    return created_tasks


if __name__ == "__main__":
    asyncio.run(create_fnf_project())