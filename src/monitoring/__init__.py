"""
Marcus Monitoring Module.

This module provides comprehensive project monitoring capabilities for the Marcus
system, including real-time project health tracking, risk assessment, performance
metrics collection, and automated alerting systems.

Key Components
--------------
ProjectMonitor : class
    Core monitoring system that tracks project health, analyzes metrics, and
    identifies potential risks or bottlenecks in real-time.

Monitoring Capabilities
-----------------------
- **Real-time Health Tracking**: Continuous monitoring of project progress,
  task completion rates, and team velocity
- **Risk Assessment**: AI-powered analysis to identify potential project risks
  and recommend mitigation strategies
- **Performance Metrics**: Collection and analysis of key performance indicators
  including velocity, completion rates, and cycle times
- **Automated Alerting**: Detection of stalled tasks, capacity issues, and
  dependency bottlenecks with automated notifications
- **Historical Analysis**: Trend analysis and historical data tracking for
  predictive insights

Usage Example
-------------
>>> from src.monitoring import ProjectMonitor
>>> 
>>> # Initialize the monitoring system
>>> monitor = ProjectMonitor()
>>> 
>>> # Start continuous monitoring
>>> await monitor.start_monitoring()
>>> 
>>> # Get current project state
>>> state = await monitor.get_project_state()
>>> print(f"Project progress: {state.progress_percent}%")
>>> 
>>> # Check for current risks
>>> risks = monitor.get_current_risks()
>>> for risk in risks:
...     print(f"Risk: {risk.description} (Severity: {risk.severity})")

Notes
-----
The monitoring module integrates with the MCP Kanban system and AI analysis
engine to provide comprehensive project oversight. It operates asynchronously
to avoid blocking project workflows while maintaining real-time monitoring
capabilities.

See Also
--------
src.core.models : Project state and risk model definitions
src.integrations.mcp_kanban_client_simple : Kanban board integration
src.integrations.ai_analysis_engine : AI-powered project analysis
"""

from .project_monitor import ProjectMonitor

__all__ = ['ProjectMonitor']