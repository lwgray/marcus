"""
Audit and usage analytics tools for Marcus.

Provides tools for analyzing audit logs and generating usage reports.
"""

from datetime import datetime, timedelta
from typing import Any, Dict

from mcp.types import Tool

from ..audit import get_audit_logger


async def get_usage_report(
    days: int = 7,
    state: Any = None,
) -> Dict[str, Any]:
    """
    Generate a usage report from audit logs.

    Parameters
    ----------
    days : int
        Number of days to include in report (default: 7)
    state : Any
        Marcus server state

    Returns
    -------
    Dict[str, Any]
        Usage statistics and insights
    """
    audit_logger = get_audit_logger()

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # Get usage statistics
    stats = await audit_logger.get_usage_stats(start_date, end_date)

    # Format report
    report = {
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "days": days,
        },
        "summary": {
            "total_events": stats["total_events"],
            "unique_clients": stats["unique_clients"],
            "errors": stats["errors"],
            "error_rate": (
                f"{(stats['errors'] / stats['total_events'] * 100):.1f}%"
                if stats["total_events"] > 0
                else "0%"
            ),
        },
        "by_client_type": stats["by_client_type"],
        "by_tool": stats["by_tool"],
        "by_event_type": stats["by_event_type"],
    }

    # Add insights
    insights = []

    # Most active client type
    if stats["by_client_type"]:
        most_active = max(stats["by_client_type"].items(), key=lambda x: x[1])
        insights.append(
            f"Most active client type: {most_active[0]} ({most_active[1]} events)"
        )

    # Most used tool
    if stats["by_tool"]:
        most_used = max(stats["by_tool"].items(), key=lambda x: x[1])
        insights.append(f"Most used tool: {most_used[0]} ({most_used[1]} calls)")

    # Error insights
    if stats["errors"] > 10:
        insights.append(f"High error count detected: {stats['errors']} errors")

    report["insights"] = insights

    return report


# Tool definition
USAGE_REPORT_TOOL = Tool(
    name="get_usage_report",
    description="Generate usage statistics and insights from audit logs",
    inputSchema={
        "type": "object",
        "properties": {
            "days": {
                "type": "integer",
                "description": "Number of days to include in report (default: 7)",
                "minimum": 1,
                "maximum": 365,
                "default": 7,
            },
        },
    },
)
