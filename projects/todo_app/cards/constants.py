"""
Constants and configuration for Todo App cards.
"""

# Label color mapping for Planka
LABEL_COLORS = {
    "Feature": "lagoon-blue",
    "Frontend": "pink-tulip",
    "Backend": "berry-red",
    "Database": "pumpkin-orange",
    "Testing": "bright-moss",
    "Bug": "red-burgundy",
    "High Priority": "midnight-blue",
    "Enhancement": "sunny-grass",
    "Documentation": "light-mud",
    "Security": "tank-green",
    "DevOps": "antique-blue",
    "Performance": "coral-green",
    "UI/UX": "light-orange",
    "API": "wet-moss",
    "Infrastructure": "desert-sand",
}

# Default configuration
DEFAULT_TIME_ESTIMATE = 8  # hours
DEFAULT_PRIORITY = "medium"
DEFAULT_DUE_DAYS = 7
MAX_SUBTASKS_PER_CARD = 10