"""
Utility functions for Marcus MCP server
"""

import json
from enum import Enum
from datetime import datetime
from typing import Any


class MarcusJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for Marcus objects that handles enums and datetimes"""
    
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            # Handle dataclasses and other objects with __dict__
            return obj.__dict__
        return super().default(obj)


def serialize_for_mcp(data: Any) -> Any:
    """
    Serialize data for MCP response, handling enums and dataclasses.
    
    This ensures that enums (like RiskLevel, Priority) are converted to their
    string values and datetimes are converted to ISO format strings.
    """
    return json.loads(json.dumps(data, cls=MarcusJSONEncoder))


def safe_serialize_task(task: Any) -> dict:
    """Safely serialize a Task object for MCP response"""
    if not task:
        return None
        
    return {
        "id": task.id,
        "name": task.name,
        "description": task.description,
        "priority": task.priority.value if hasattr(task.priority, 'value') else str(task.priority),
        "status": task.status.value if hasattr(task.status, 'value') else str(task.status),
        "estimated_hours": task.estimated_hours,
        "dependencies": task.dependencies or [],
        "labels": task.labels or [],
        "assigned_to": task.assigned_to,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        "due_date": task.due_date.isoformat() if task.due_date else None
    }