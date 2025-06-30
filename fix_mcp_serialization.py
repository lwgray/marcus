#!/usr/bin/env python3
"""
Fix MCP serialization issues for RiskLevel and initialization
"""

import json
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime

# Create a JSON encoder that handles enums and dataclasses
class MarcusJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for Marcus objects"""
    
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            # Handle dataclasses and other objects with __dict__
            return obj.__dict__
        return super().default(obj)


def serialize_for_mcp(data):
    """Serialize data for MCP response, handling enums and dataclasses"""
    return json.loads(json.dumps(data, cls=MarcusJSONEncoder))


# Test the serialization
if __name__ == "__main__":
    from src.core.models import RiskLevel, Priority, TaskStatus
    
    # Test enum serialization
    test_data = {
        "success": True,
        "task": {
            "priority": Priority.HIGH,
            "status": TaskStatus.TODO,
            "risk_level": RiskLevel.MEDIUM
        },
        "timestamp": datetime.now()
    }
    
    print("Original data:")
    print(test_data)
    
    print("\nSerialized data:")
    serialized = serialize_for_mcp(test_data)
    print(serialized)
    
    print("\nJSON string:")
    print(json.dumps(serialized, indent=2))