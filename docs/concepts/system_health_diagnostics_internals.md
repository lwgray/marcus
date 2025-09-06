# System Health & Diagnostics: Marcus Monitoring Intelligence
## Internal Systems Architecture Deep Dive

Marcus's System Health & Diagnostics tools are **sophisticated monitoring and diagnostic systems** that provide real-time visibility into system health, assignment integrity, and operational effectiveness. These aren't simple ping checks - they're comprehensive health intelligence systems that monitor system connectivity, validate assignment consistency, assess Kanban board health, and provide deep diagnostic insights for maintaining optimal Marcus coordination effectiveness.

---

## 🎯 **System Overview**

```
System Health & Diagnostics Architecture
        ↓
Multi-Layer Health Intelligence
        ↓
┌─────────────────┬─────────────────┬─────────────────┐
│ System          │ Assignment      │ Board Health    │
│ Connectivity    │ Health          │ Monitoring      │
│ & Status        │ Monitoring      │ & Validation    │
└─────────────────┴─────────────────┴─────────────────┘
        ↓                ↓                ↓
┌─────────────────┬─────────────────┬─────────────────┐
│ Health Metrics  │ Consistency     │ Integration     │
│ & Analytics     │ Validation      │ Diagnostics     │
└─────────────────┴─────────────────┴─────────────────┘
        ↓
Proactive Health Management & System Optimization
```

**Core Purpose**: Transform system monitoring from reactive problem detection to proactive health intelligence that prevents coordination failures and optimizes system performance.

---

## 🏗️ **Core Diagnostic Tools**

### **Tool 1: System Connectivity & Status (`ping`)**
**File**: `src/marcus_mcp/tools/system.py` - `ping` function
**Purpose**: Advanced system connectivity verification with health diagnostics

```python
async def ping(echo: str, state: Any) -> Dict[str, Any]:
    """
    Check Marcus status and connectivity with enhanced health diagnostics.

    Extended health check endpoint that verifies the Marcus system
    is online and responsive. Can echo back a message and provide
    detailed system health information.

    Special echo commands:
    - "health": Return detailed health information
    - "cleanup": Force cleanup of stuck task assignments
    - "reset": Clear all pending assignments (use with caution)
    """
```

#### **What Happens During a Ping:**

**Stage 1: Client Type Detection & Context Analysis**
```python
# Intelligent client identification
client_type = "unknown"
if echo:
    echo_lower = echo.lower()
    if "seneca" in echo_lower:
        client_type = "seneca"
    elif "claude" in echo_lower or "desktop" in echo_lower:
        client_type = "claude_desktop"

# Context-aware response customization
client_context = {
    "seneca": {
        "capabilities": ["advanced_ai_analysis", "workflow_optimization"],
        "preferred_response_format": "detailed_technical",
        "monitoring_needs": "performance_metrics"
    },
    "claude_desktop": {
        "capabilities": ["task_management", "project_coordination"],
        "preferred_response_format": "user_friendly",
        "monitoring_needs": "status_overview"
    }
}
```

**Stage 2: System Health Assessment**
```python
if echo and echo.lower() == "health":
    health_data = await _get_comprehensive_health_diagnostics(state)

    system_health = {
        "core_systems": {
            "marcus_core": "operational",
            "memory_system": await _check_memory_system_health(state),
            "ai_engine": await _check_ai_engine_health(state),
            "communication_hub": await _check_communication_health(state)
        },
        "integration_health": {
            "kanban_connectivity": await _check_kanban_health(state),
            "database_connectivity": await _check_database_health(state),
            "external_apis": await _check_external_api_health(state)
        },
        "performance_metrics": {
            "response_time": await _measure_system_response_time(),
            "memory_usage": await _get_memory_utilization(),
            "active_connections": await _count_active_connections(),
            "queue_depths": await _analyze_queue_depths(state)
        }
    }
```

**Stage 3: Advanced Diagnostic Commands**
```python
if echo and echo.lower() == "cleanup":
    # Force cleanup of stuck assignments
    cleanup_results = await _force_assignment_cleanup(state)

    return {
        "status": "cleanup_completed",
        "assignments_cleared": cleanup_results.cleared_count,
        "stuck_tasks_resolved": cleanup_results.resolved_tasks,
        "system_health": "restored",
        "cleanup_summary": cleanup_results.summary
    }

elif echo and echo.lower() == "reset":
    # Emergency reset (use with caution)
    reset_results = await _emergency_system_reset(state)

    return {
        "status": "system_reset_completed",
        "warning": "All pending assignments cleared",
        "assignments_cleared": reset_results.total_cleared,
        "system_state": "reset_to_clean_slate",
        "requires_reinitialization": True
    }
```

### **Tool 2: Assignment Health Monitoring (`check_assignment_health`)**
**Purpose**: Comprehensive assignment system integrity verification

```python
async def check_assignment_health(state: Any) -> Dict[str, Any]:
    """
    Monitor assignment system health and detect integrity issues.

    Comprehensive health check that validates:
    - Assignment-lease consistency
    - Task status synchronization
    - Agent assignment conflicts
    - Orphaned assignments detection
    - Performance health metrics
    """
```

#### **Assignment Health Analysis Workflow:**

**Stage 1: Assignment-Lease Consistency Validation**
```python
async def _validate_assignment_lease_consistency(state: Any) -> Dict[str, Any]:
    """
    Check consistency between assignments and their leases

    Identifies:
    - Assignments without active leases
    - Expired leases with active assignments
    - Lease renewal failures
    - Assignment state mismatches
    """

    consistency_issues = []

    # Get all active assignments
    active_assignments = state.assignment_persistence.get_all_assignments()

    # Check each assignment's lease status
    for agent_id, assignment in active_assignments.items():
        lease_status = await state.assignment_lease_manager.get_lease_status(
            assignment.task_id
        )

        # Detect consistency issues
        if not lease_status:
            consistency_issues.append({
                "type": "missing_lease",
                "agent_id": agent_id,
                "task_id": assignment.task_id,
                "severity": "high",
                "impact": "Assignment may become stuck without lease management"
            })

        elif lease_status.status == "expired" and assignment.status == "active":
            consistency_issues.append({
                "type": "expired_lease_active_assignment",
                "agent_id": agent_id,
                "task_id": assignment.task_id,
                "lease_expired": lease_status.expired_at,
                "severity": "critical",
                "impact": "Task may be stuck with unresponsive agent"
            })

    return {
        "consistency_score": 1.0 - (len(consistency_issues) / max(len(active_assignments), 1)),
        "issues_detected": len(consistency_issues),
        "issues": consistency_issues,
        "health_status": "healthy" if len(consistency_issues) == 0 else "issues_detected"
    }
```

**Stage 2: Task Status Synchronization Check**
```python
async def _validate_task_status_sync(state: Any) -> Dict[str, Any]:
    """
    Ensure task status consistency between Marcus and Kanban systems

    Validates:
    - Marcus internal task status vs Kanban board status
    - Assignment records vs actual task assignments
    - Task completion status synchronization
    - Dependency status accuracy
    """

    sync_issues = []

    # Compare Marcus state with Kanban state
    marcus_tasks = {task.id: task for task in state.project_tasks}

    for task_id, marcus_task in marcus_tasks.items():
        try:
            kanban_task = await state.kanban_client.get_task_by_id(task_id)

            # Check status synchronization
            if marcus_task.status != kanban_task.status:
                sync_issues.append({
                    "type": "status_mismatch",
                    "task_id": task_id,
                    "marcus_status": marcus_task.status,
                    "kanban_status": kanban_task.status,
                    "severity": "medium",
                    "auto_fixable": True
                })

            # Check assignment synchronization
            marcus_assigned = marcus_task.assigned_to
            kanban_assigned = kanban_task.assigned_to

            if marcus_assigned != kanban_assigned:
                sync_issues.append({
                    "type": "assignment_mismatch",
                    "task_id": task_id,
                    "marcus_assigned": marcus_assigned,
                    "kanban_assigned": kanban_assigned,
                    "severity": "high",
                    "requires_resolution": True
                })

        except Exception as e:
            sync_issues.append({
                "type": "sync_error",
                "task_id": task_id,
                "error": str(e),
                "severity": "critical",
                "requires_investigation": True
            })

    return {
        "sync_health_score": 1.0 - (len(sync_issues) / max(len(marcus_tasks), 1)),
        "sync_issues": sync_issues,
        "auto_fixable_issues": len([i for i in sync_issues if i.get("auto_fixable")]),
        "critical_issues": len([i for i in sync_issues if i.get("severity") == "critical"])
    }
```

**Stage 3: Orphaned Assignment Detection**
```python
async def _detect_orphaned_assignments(state: Any) -> Dict[str, Any]:
    """
    Identify assignments that have become orphaned or stuck

    Detects:
    - Assignments to offline/unresponsive agents
    - Tasks assigned but not in agent's active task list
    - Long-running assignments without progress
    - Circular assignment dependencies
    """

    orphaned_assignments = []

    # Check for assignments to inactive agents
    active_assignments = state.assignment_persistence.get_all_assignments()

    for agent_id, assignment in active_assignments.items():
        # Check agent responsiveness
        agent_status = state.agent_status.get(agent_id)

        if not agent_status:
            orphaned_assignments.append({
                "type": "unknown_agent",
                "agent_id": agent_id,
                "task_id": assignment.task_id,
                "assigned_at": assignment.assigned_at,
                "severity": "high",
                "recovery_action": "reassign_to_available_agent"
            })

        elif agent_status.last_activity:
            time_since_activity = datetime.now() - agent_status.last_activity

            if time_since_activity > timedelta(hours=6):
                orphaned_assignments.append({
                    "type": "unresponsive_agent",
                    "agent_id": agent_id,
                    "task_id": assignment.task_id,
                    "last_activity": agent_status.last_activity,
                    "hours_since_activity": time_since_activity.total_seconds() / 3600,
                    "severity": "medium",
                    "recovery_action": "check_agent_status_or_reassign"
                })

        # Check for assignments without progress
        if assignment.progress_percentage == 0:
            assignment_age = datetime.now() - assignment.assigned_at

            if assignment_age > timedelta(hours=4):
                orphaned_assignments.append({
                    "type": "stalled_assignment",
                    "agent_id": agent_id,
                    "task_id": assignment.task_id,
                    "assigned_duration": assignment_age.total_seconds() / 3600,
                    "severity": "medium",
                    "recovery_action": "contact_agent_or_provide_support"
                })

    return {
        "orphaned_count": len(orphaned_assignments),
        "orphaned_assignments": orphaned_assignments,
        "recovery_actions_needed": len([a for a in orphaned_assignments if "recovery_action" in a]),
        "immediate_attention_required": len([a for a in orphaned_assignments if a.get("severity") == "high"])
    }
```

### **Tool 3: Board Health Monitoring (`check_board_health`)**
**Purpose**: Kanban board health and integration diagnostics

```python
async def check_board_health(state: Any) -> Dict[str, Any]:
    """
    Monitor Kanban board health and integration status.

    Comprehensive board health analysis including:
    - Board connectivity and responsiveness
    - Data consistency and synchronization
    - Performance metrics and bottlenecks
    - Integration health with Marcus systems
    """
```

#### **Board Health Analysis Workflow:**

**Stage 1: Connectivity & Performance Assessment**
```python
async def _assess_board_connectivity(state: Any) -> Dict[str, Any]:
    """
    Test board connectivity and measure performance metrics

    Tests:
    - API endpoint responsiveness
    - Authentication status
    - Request/response latency
    - Rate limiting status
    - Error rates and patterns
    """

    connectivity_results = {
        "connection_status": "unknown",
        "response_times": {},
        "error_rates": {},
        "authentication_valid": False
    }

    try:
        # Test basic connectivity
        start_time = datetime.now()
        board_info = await state.kanban_client.get_board_info()
        response_time = (datetime.now() - start_time).total_seconds()

        connectivity_results.update({
            "connection_status": "connected",
            "board_info": board_info,
            "basic_response_time": response_time,
            "authentication_valid": True
        })

        # Test various operations for performance profiling
        operations = {
            "get_tasks": lambda: state.kanban_client.get_tasks(),
            "get_columns": lambda: state.kanban_client.get_columns(),
            "get_labels": lambda: state.kanban_client.get_labels()
        }

        for op_name, operation in operations.items():
            try:
                start_time = datetime.now()
                await operation()
                op_response_time = (datetime.now() - start_time).total_seconds()
                connectivity_results["response_times"][op_name] = op_response_time
                connectivity_results["error_rates"][op_name] = 0.0

            except Exception as e:
                connectivity_results["response_times"][op_name] = "timeout"
                connectivity_results["error_rates"][op_name] = 1.0
                connectivity_results[f"{op_name}_error"] = str(e)

    except Exception as e:
        connectivity_results.update({
            "connection_status": "failed",
            "connection_error": str(e),
            "authentication_valid": False
        })

    return connectivity_results
```

**Stage 2: Data Consistency Validation**
```python
async def _validate_board_data_consistency(state: Any) -> Dict[str, Any]:
    """
    Validate data consistency between board and Marcus expectations

    Validates:
    - Task count consistency
    - Column structure matches expectations
    - Label system completeness
    - Assignment data accuracy
    """

    consistency_results = {
        "data_consistency_score": 1.0,
        "issues_detected": [],
        "validation_summary": {}
    }

    # Validate task count consistency
    marcus_task_count = len(state.project_tasks)
    try:
        board_tasks = await state.kanban_client.get_tasks()
        board_task_count = len(board_tasks)

        task_count_variance = abs(marcus_task_count - board_task_count)

        if task_count_variance > 0:
            consistency_results["issues_detected"].append({
                "type": "task_count_mismatch",
                "marcus_tasks": marcus_task_count,
                "board_tasks": board_task_count,
                "variance": task_count_variance,
                "severity": "medium" if task_count_variance <= 3 else "high"
            })

        consistency_results["validation_summary"]["task_count_check"] = {
            "passed": task_count_variance == 0,
            "marcus_count": marcus_task_count,
            "board_count": board_task_count
        }

    except Exception as e:
        consistency_results["issues_detected"].append({
            "type": "task_validation_error",
            "error": str(e),
            "severity": "critical"
        })

    # Validate column structure
    try:
        expected_columns = ["TODO", "IN_PROGRESS", "TESTING", "DONE", "BLOCKED"]
        board_columns = await state.kanban_client.get_columns()
        board_column_names = [col.name for col in board_columns]

        missing_columns = set(expected_columns) - set(board_column_names)
        extra_columns = set(board_column_names) - set(expected_columns)

        if missing_columns or extra_columns:
            consistency_results["issues_detected"].append({
                "type": "column_structure_mismatch",
                "missing_columns": list(missing_columns),
                "extra_columns": list(extra_columns),
                "severity": "medium"
            })

        consistency_results["validation_summary"]["column_structure_check"] = {
            "passed": len(missing_columns) == 0 and len(extra_columns) == 0,
            "expected": expected_columns,
            "actual": board_column_names
        }

    except Exception as e:
        consistency_results["issues_detected"].append({
            "type": "column_validation_error",
            "error": str(e),
            "severity": "high"
        })

    # Calculate overall consistency score
    total_issues = len(consistency_results["issues_detected"])
    critical_issues = len([i for i in consistency_results["issues_detected"] if i.get("severity") == "critical"])

    if critical_issues > 0:
        consistency_results["data_consistency_score"] = 0.3
    elif total_issues > 0:
        consistency_results["data_consistency_score"] = max(0.5, 1.0 - (total_issues * 0.1))

    return consistency_results
```

---

## 📊 **Advanced Health Intelligence**

### **Health Metrics Aggregation**
```python
class SystemHealthAggregator:
    """Aggregates health metrics across all diagnostic tools"""

    async def generate_comprehensive_health_report(
        self,
        state: Any
    ) -> Dict[str, Any]:
        """
        Generate comprehensive system health report

        Combines:
        - System connectivity and performance
        - Assignment system integrity
        - Board health and synchronization
        - Predictive health indicators
        """

        # Gather health data from all diagnostic tools
        ping_health = await self._get_system_health_metrics(state)
        assignment_health = await check_assignment_health(state)
        board_health = await check_board_health(state)

        # Calculate overall system health score
        overall_health_score = self._calculate_overall_health_score(
            ping_health, assignment_health, board_health
        )

        # Generate health recommendations
        recommendations = self._generate_health_recommendations(
            ping_health, assignment_health, board_health
        )

        return {
            "overall_health_score": overall_health_score,
            "health_grade": self._score_to_grade(overall_health_score),
            "system_components": {
                "core_system": ping_health,
                "assignment_system": assignment_health,
                "board_integration": board_health
            },
            "critical_issues": self._identify_critical_issues(
                ping_health, assignment_health, board_health
            ),
            "performance_metrics": self._aggregate_performance_metrics(
                ping_health, assignment_health, board_health
            ),
            "recommendations": recommendations,
            "next_health_check": datetime.now() + timedelta(hours=1),
            "health_trend": self._analyze_health_trend(state)
        }

    def _calculate_overall_health_score(
        self,
        ping_health: Dict[str, Any],
        assignment_health: Dict[str, Any],
        board_health: Dict[str, Any]
    ) -> float:
        """Calculate weighted overall health score"""

        weights = {
            "system_connectivity": 0.25,
            "assignment_consistency": 0.35,  # Critical for coordination
            "board_integration": 0.25,
            "performance_metrics": 0.15
        }

        scores = {
            "system_connectivity": ping_health.get("connectivity_score", 1.0),
            "assignment_consistency": assignment_health.get("consistency_score", 1.0),
            "board_integration": board_health.get("integration_score", 1.0),
            "performance_metrics": self._calculate_performance_score(ping_health, board_health)
        }

        weighted_score = sum(
            scores[component] * weights[component]
            for component in weights
        )

        return round(weighted_score, 3)
```

### **Proactive Health Management**
```python
class ProactiveHealthManager:
    """Manages proactive health monitoring and issue prevention"""

    async def identify_health_degradation_patterns(
        self,
        state: Any
    ) -> List[HealthDegradationPattern]:
        """
        Identify patterns that indicate health degradation

        Monitors:
        - Increasing response times
        - Growing assignment inconsistencies
        - Declining board synchronization
        - Resource utilization trends
        """

        patterns = []

        # Analyze response time trends
        recent_response_times = await self._get_recent_response_times(state)
        if self._shows_degradation_trend(recent_response_times):
            patterns.append(HealthDegradationPattern(
                type="performance_degradation",
                severity="medium",
                description="System response times showing upward trend",
                predicted_impact="Coordination delays may increase",
                recommended_action="Investigate resource utilization and optimize"
            ))

        # Analyze assignment consistency trends
        assignment_health_history = await self._get_assignment_health_history(state)
        if self._shows_consistency_degradation(assignment_health_history):
            patterns.append(HealthDegradationPattern(
                type="assignment_consistency_degradation",
                severity="high",
                description="Assignment-lease consistency declining",
                predicted_impact="Risk of stuck tasks and coordination failures",
                recommended_action="Run assignment cleanup and validate lease management"
            ))

        return patterns

    async def execute_proactive_maintenance(
        self,
        state: Any,
        maintenance_type: str = "routine"
    ) -> Dict[str, Any]:
        """
        Execute proactive maintenance based on health analysis

        Maintenance types:
        - routine: Regular optimization and cleanup
        - targeted: Address specific identified issues
        - emergency: Respond to critical health degradation
        """

        maintenance_results = {
            "maintenance_type": maintenance_type,
            "actions_taken": [],
            "issues_resolved": [],
            "performance_improvements": {}
        }

        if maintenance_type in ["routine", "targeted"]:
            # Clean up expired assignments
            cleanup_results = await self._cleanup_expired_assignments(state)
            maintenance_results["actions_taken"].append("expired_assignment_cleanup")
            maintenance_results["issues_resolved"].extend(cleanup_results.resolved_issues)

            # Synchronize task states
            sync_results = await self._synchronize_task_states(state)
            maintenance_results["actions_taken"].append("task_state_synchronization")
            maintenance_results["performance_improvements"]["sync_accuracy"] = sync_results.improvement_score

            # Optimize memory usage
            memory_optimization = await self._optimize_memory_usage(state)
            maintenance_results["actions_taken"].append("memory_optimization")
            maintenance_results["performance_improvements"]["memory_efficiency"] = memory_optimization.efficiency_gain

        return maintenance_results
```

---

## 🔍 **Integration Points**

### **With Assignment System**
```python
async def validate_assignment_system_health(
    assignment_persistence: AssignmentPersistence,
    lease_manager: AssignmentLeaseManager
) -> Dict[str, Any]:
    """
    Deep validation of assignment system health

    Checks:
    - Assignment persistence integrity
    - Lease management effectiveness
    - Assignment-task synchronization
    - Performance bottlenecks
    """
```

### **With Monitoring Systems**
```python
async def integrate_with_monitoring(
    health_data: Dict[str, Any],
    monitoring_system: MonitoringSystem
) -> None:
    """
    Feed health data into monitoring systems

    Provides:
    - Real-time health metrics
    - Alert triggers for degradation
    - Performance trend analysis
    - Predictive maintenance signals
    """
```

---

## 🎯 **Key Capabilities**

### **1. Comprehensive Health Visibility**
System health tools provide complete visibility into Marcus coordination health:

- **System Connectivity**: Real-time status of all Marcus components
- **Assignment Integrity**: Deep validation of task assignment consistency
- **Board Health**: Kanban integration health and performance
- **Performance Monitoring**: Response times, throughput, and resource utilization

### **2. Proactive Issue Detection**
Advanced diagnostics identify problems before they impact coordination:

- **Degradation Pattern Recognition**: Identifies trends indicating health decline
- **Predictive Maintenance**: Proactive optimization before issues occur
- **Consistency Validation**: Prevents data synchronization problems
- **Performance Optimization**: Maintains optimal system responsiveness

### **3. Automated Recovery & Maintenance**
Intelligent recovery mechanisms maintain system health:

- **Automatic Cleanup**: Removes stuck assignments and expired leases
- **State Synchronization**: Maintains consistency between systems
- **Emergency Recovery**: Rapid response to critical health issues
- **Performance Tuning**: Continuous optimization of system performance

---

## 🎯 **System Impact**

### **Without Health & Diagnostics**
- Coordination failures discovered only after impact
- Manual detection of system inconsistencies
- Reactive response to performance degradation
- Limited visibility into system health trends
- No proactive maintenance or optimization

### **With Health & Diagnostics**
- **Proactive Health Management**: Issues identified and resolved before impact
- **Comprehensive System Visibility**: Complete insight into coordination health
- **Automated Maintenance**: Self-healing capabilities maintain optimal performance
- **Predictive Intelligence**: Trend analysis prevents future problems
- **Continuous Optimization**: System performance continuously improved

---

## 🎯 **Key Takeaway**

The System Health & Diagnostics tools transform Marcus from a coordination system that fails unpredictably into a **self-monitoring, self-healing coordination intelligence** with comprehensive health visibility, proactive issue detection, and automated maintenance capabilities.

These tools ensure that Marcus coordination remains reliable, performant, and resilient, providing the foundation for trustworthy multi-agent project management at scale.
