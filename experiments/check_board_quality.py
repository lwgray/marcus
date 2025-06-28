#!/usr/bin/env python3
"""
Check board quality using Marcus standards
"""

import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.quality.board_quality_validator import BoardQualityValidator, QualityLevel
from src.integrations.kanban_factory import KanbanFactory
from src.core.models import Task, TaskStatus, Priority
from dotenv import load_dotenv
import os


def print_quality_report(report):
    """Pretty print quality report"""
    print("\n" + "="*60)
    print("📊 BOARD QUALITY REPORT")
    print("="*60)
    
    # Overall score
    score_emoji = {
        QualityLevel.POOR: "🔴",
        QualityLevel.BASIC: "🟡", 
        QualityLevel.GOOD: "🟢",
        QualityLevel.EXCELLENT: "🌟"
    }
    
    print(f"\nOverall Score: {report.score:.2f}/1.00 {score_emoji[report.level]} {report.level.value.upper()}")
    
    # Metrics
    print("\n📈 Metrics:")
    print(f"  - Total tasks: {report.metrics['total_tasks']}")
    print(f"  - Description coverage: {report.metrics['description_coverage']:.0%}")
    print(f"  - Label coverage: {report.metrics['label_coverage']:.0%}")
    print(f"  - Estimate coverage: {report.metrics['estimate_coverage']:.0%}")
    print(f"  - Tasks with dependencies: {report.metrics['tasks_with_dependencies']}")
    print(f"  - Average labels per task: {report.metrics['average_labels_per_task']:.1f}")
    
    # Issues by severity
    errors = [i for i in report.issues if i.severity == "error"]
    warnings = [i for i in report.issues if i.severity == "warning"]
    info = [i for i in report.issues if i.severity == "info"]
    
    if errors:
        print(f"\n❌ Critical Issues ({len(errors)}):")
        for issue in errors[:5]:  # Show first 5
            print(f"  - {issue.message}")
            print(f"    💡 {issue.suggestion}")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more")
    
    if warnings:
        print(f"\n⚠️  Warnings ({len(warnings)}):")
        for issue in warnings[:3]:
            print(f"  - {issue.message}")
        if len(warnings) > 3:
            print(f"  ... and {len(warnings) - 3} more")
    
    # Suggestions
    if report.suggestions:
        print("\n💡 Top Suggestions:")
        for i, suggestion in enumerate(report.suggestions[:5], 1):
            print(f"  {i}. {suggestion}")
    
    # Summary
    print("\n" + "-"*60)
    if report.level == QualityLevel.EXCELLENT:
        print("🎉 Excellent board quality! Keep up the great work!")
    elif report.level == QualityLevel.GOOD:
        print("✅ Good board quality. A few improvements would make it excellent.")
    elif report.level == QualityLevel.BASIC:
        print("📈 Basic quality. Significant improvements needed for better project tracking.")
    else:
        print("🚨 Poor board quality. Critical improvements needed for effective project management.")


async def check_current_board():
    """Check quality of current board"""
    # Load environment
    load_dotenv()
    provider = os.getenv('KANBAN_PROVIDER', 'planka')
    
    print(f"🔍 Checking {provider} board quality...")
    
    # Get kanban client
    kanban_client = KanbanFactory.create(provider)
    
    # Get all tasks
    try:
        tasks = await kanban_client.get_available_tasks()
        print(f"✓ Found {len(tasks)} tasks")
        
        # Run quality validation
        validator = BoardQualityValidator()
        report = validator.validate_board(tasks)
        
        # Print report
        print_quality_report(report)
        
        # Save detailed report
        print("\n📄 Full report saved to: board_quality_report.json")
        
        import json
        with open("board_quality_report.json", "w") as f:
            report_dict = {
                "score": report.score,
                "level": report.level.value,
                "metrics": report.metrics,
                "issues": [
                    {
                        "task_id": i.task_id,
                        "type": i.issue_type,
                        "severity": i.severity,
                        "message": i.message,
                        "suggestion": i.suggestion
                    }
                    for i in report.issues
                ],
                "suggestions": report.suggestions
            }
            json.dump(report_dict, f, indent=2)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return


def demo_quality_levels():
    """Demo different quality levels"""
    print("\n" + "="*60)
    print("📚 QUALITY LEVEL EXAMPLES")
    print("="*60)
    
    # Poor quality task
    poor_task = Task(
        id="1",
        name="Fix bug",
        description="",
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        assigned_to=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        due_date=None,
        estimated_hours=0,
        actual_hours=0,
        labels=[],
        dependencies=[]
    )
    
    # Basic quality task
    basic_task = Task(
        id="2",
        name="Implement user authentication",
        description="Add login functionality",
        status=TaskStatus.TODO,
        priority=Priority.HIGH,
        assigned_to=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        due_date=None,
        estimated_hours=0,
        actual_hours=0,
        labels=["backend"],
        dependencies=[]
    )
    
    # Good quality task
    good_task = Task(
        id="3",
        name="Create REST API for user management",
        description="Implement RESTful endpoints for user CRUD operations with proper validation and error handling. Should support pagination and filtering.",
        status=TaskStatus.TODO,
        priority=Priority.HIGH,
        assigned_to=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        due_date=None,
        estimated_hours=8,
        actual_hours=0,
        labels=["component:backend", "type:feature", "skill:nodejs"],
        dependencies=["1", "2"]
    )
    
    # Excellent quality task
    excellent_task = Task(
        id="4",
        name="Implement JWT authentication with refresh tokens",
        description="""
        Create a secure JWT-based authentication system with the following requirements:
        - Access tokens valid for 15 minutes
        - Refresh tokens valid for 7 days with rotation
        - Secure token storage recommendations for frontend
        - Rate limiting on auth endpoints
        
        Acceptance Criteria:
        - [ ] POST /auth/login returns access and refresh tokens
        - [ ] POST /auth/refresh rotates refresh token
        - [ ] POST /auth/logout invalidates refresh token
        - [ ] All endpoints have proper error responses
        - [ ] Unit tests achieve 90% coverage
        - [ ] Security audit passed
        """,
        status=TaskStatus.TODO,
        priority=Priority.URGENT,
        assigned_to=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        due_date=None,
        estimated_hours=16,
        actual_hours=0,
        labels=["phase:core", "component:backend", "type:feature", "skill:nodejs", "security:critical"],
        dependencies=["3"]
    )
    
    # Validate each
    validator = BoardQualityValidator()
    
    for task, expected_level in [
        (poor_task, "POOR"),
        (basic_task, "BASIC"),
        (good_task, "GOOD"),
        (excellent_task, "EXCELLENT")
    ]:
        score, issues = validator.validate_task(task)
        print(f"\n{expected_level} Quality Example:")
        print(f"  Task: {task.title}")
        print(f"  Score: {score:.2f}")
        print(f"  Issues: {len(issues)}")
        if issues:
            print(f"  Main issue: {issues[0].message}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo_quality_levels()
    else:
        asyncio.run(check_current_board())