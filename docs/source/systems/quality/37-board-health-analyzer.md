# 37. Board Health Analyzer System

## Executive Summary

The Board Health Analyzer System is a sophisticated diagnostic tool that identifies six critical board health issues: skill mismatches, circular dependencies, bottlenecks, chain blocks, stale tasks, and workload imbalances. It provides both real-time analysis through MCP tools and comprehensive health reports with actionable recommendations for resolving detected issues.

## System Architecture

### Core Components

The Board Health Analyzer consists of:

```
Board Health Analyzer Architecture
├── board_health_analyzer.py (Core Analysis)
│   ├── BoardHealthAnalyzer (Main analyzer class)
│   ├── BoardHealthIssue (Issue data structure)
│   ├── IssueSeverity (LOW, MEDIUM, HIGH, CRITICAL)
│   └── Six Analysis Methods:
│       ├── _analyze_skill_mismatches()
│       ├── _analyze_circular_dependencies()
│       ├── _analyze_bottlenecks()
│       ├── _analyze_chain_blocks()
│       ├── _analyze_stale_tasks()
│       └── _analyze_workload_balance()
└── board_health.py (MCP Tool Integration)
    ├── check_board_health (Full health analysis)
    └── check_task_dependencies (Dependency graph)
```

### Analysis Flow

```
Board State (Tasks + Agents)
            │
            ▼
    Load Board Data
            │
            ├─► Skill Analysis ──────► Mismatches Found
            │
            ├─► Dependency Graph ────► Circular Deps
            │
            ├─► Column Analysis ─────► Bottlenecks
            │
            ├─► Chain Detection ─────► Blocked Chains
            │
            ├─► Time Analysis ───────► Stale Tasks
            │
            └─► Workload Check ──────► Imbalances
                        │
                        ▼
                 Aggregate Issues
                        │
                        ▼
                Generate Recommendations
                        │
                        ▼
                  Health Report
```

## Core Health Issues Detected

### 1. Skill Mismatches

Detects when required skills aren't available:

```python
def _analyze_skill_mismatches(
    self,
    tasks: List[Task],
    agents: List[WorkerAgent]
) -> List[BoardHealthIssue]:
    """Analyze tasks that require skills not available in team"""
    issues = []

    # Collect all available skills
    available_skills = set()
    for agent in agents:
        if agent.status == WorkerStatus.ACTIVE:
            available_skills.update(skill.lower() for skill in agent.skills)

    # Check each TODO/BLOCKED task
    for task in tasks:
        if task.status in [TaskStatus.TODO, TaskStatus.BLOCKED]:
            if hasattr(task, 'required_skills') and task.required_skills:
                missing = set(s.lower() for s in task.required_skills) - available_skills
                if missing:
                    issues.append(BoardHealthIssue(
                        type="skill_mismatch",
                        severity=IssueSeverity.HIGH,
                        title="Missing Required Skills",
                        description=f"Task '{task.title}' requires {missing} but no active agents have these skills",
                        affected_tasks=[task.id],
                        recommendations=[
                            f"Find agents with skills: {', '.join(missing)}",
                            "Consider training existing agents",
                            "Break down task to use available skills"
                        ]
                    ))

    return issues
```

### 2. Circular Dependencies

Detects dependency cycles using DFS:

```python
def _analyze_circular_dependencies(
    self,
    tasks: List[Task]
) -> List[BoardHealthIssue]:
    """Detect circular dependencies in task graph"""
    # Build dependency graph
    graph: Dict[str, List[str]] = {}
    task_map = {task.id: task for task in tasks}

    for task in tasks:
        if hasattr(task, 'dependencies') and task.dependencies:
            graph[task.id] = task.dependencies
        else:
            graph[task.id] = []

    # Find cycles using DFS
    cycles = []
    visited = set()
    rec_stack = set()

    def dfs(node: str, path: List[str]) -> None:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, []):
            if neighbor in rec_stack:
                # Found cycle
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:]
                cycles.append(cycle)
            elif neighbor not in visited and neighbor in task_map:
                dfs(neighbor, path.copy())

        rec_stack.remove(node)

    # Check all nodes
    for task_id in graph:
        if task_id not in visited:
            dfs(task_id, [])

    # Create issues for cycles
    if cycles:
        return [BoardHealthIssue(
            type="circular_dependency",
            severity=IssueSeverity.CRITICAL,
            title=f"Circular Dependency Detected",
            description=f"Tasks form a dependency cycle: {' → '.join(cycle + [cycle[0]])}",
            affected_tasks=cycle,
            recommendations=[
                "Break the cycle by removing one dependency",
                "Restructure tasks to eliminate circular references",
                "Consider merging related tasks"
            ]
        ) for cycle in cycles]

    return []
```

### 3. Bottleneck Detection

Identifies columns with too many tasks:

```python
def _analyze_bottlenecks(self, tasks: List[Task]) -> List[BoardHealthIssue]:
    """Identify bottlenecks in the workflow"""
    issues = []

    # Count tasks by status
    status_counts = {}
    for task in tasks:
        status = task.status.value if hasattr(task.status, 'value') else str(task.status)
        status_counts[status] = status_counts.get(status, 0) + 1

    # Thresholds for bottlenecks
    thresholds = {
        'TODO': 20,
        'IN_PROGRESS': 10,
        'BLOCKED': 5,
        'IN_REVIEW': 8
    }

    for status, count in status_counts.items():
        threshold = thresholds.get(status.upper(), 15)
        if count > threshold:
            severity = IssueSeverity.HIGH if count > threshold * 1.5 else IssueSeverity.MEDIUM

            issues.append(BoardHealthIssue(
                type="bottleneck",
                severity=severity,
                title=f"Bottleneck in {status}",
                description=f"{count} tasks in {status} (threshold: {threshold})",
                affected_tasks=[t.id for t in tasks if str(t.status).upper() == status.upper()],
                recommendations=[
                    f"Review and prioritize {status} tasks",
                    "Assign more resources to this stage",
                    "Identify and remove blockers",
                    "Consider work-in-progress limits"
                ]
            ))

    return issues
```

## Additional Health Checks

### 4. Chain Block Detection

Finds chains of blocked dependencies:

```python
def _analyze_chain_blocks(self, tasks: List[Task]) -> List[BoardHealthIssue]:
    """Find chains where blocked tasks block other tasks"""
    issues = []
    task_map = {task.id: task for task in tasks}

    # Find blocked tasks that have dependents
    blocked_tasks = [t for t in tasks if t.status == TaskStatus.BLOCKED]

    for blocked_task in blocked_tasks:
        # Find tasks depending on this blocked task
        dependent_tasks = [
            t for t in tasks
            if hasattr(t, 'dependencies') and
            blocked_task.id in t.dependencies
        ]

        if dependent_tasks:
            chain_length = 1 + len(dependent_tasks)
            severity = IssueSeverity.HIGH if chain_length > 3 else IssueSeverity.MEDIUM

            issues.append(BoardHealthIssue(
                type="chain_block",
                severity=severity,
                title=f"Blocked Task Creating Chain",
                description=(
                    f"Blocked task '{blocked_task.title}' is blocking "
                    f"{len(dependent_tasks)} other tasks"
                ),
                affected_tasks=[blocked_task.id] + [t.id for t in dependent_tasks],
                recommendations=[
                    f"Prioritize unblocking '{blocked_task.title}'",
                    "Consider alternative approaches for dependent tasks",
                    "Review if dependencies can be relaxed"
                ]
            ))

    return issues
```

### 5. Stale Task Detection

Identifies tasks that haven't been updated:

```python
def _analyze_stale_tasks(self, tasks: List[Task]) -> List[BoardHealthIssue]:
    """Find tasks that haven't been updated recently"""
    issues = []
    now = datetime.now()

    # Thresholds by status
    staleness_thresholds = {
        TaskStatus.IN_PROGRESS: timedelta(days=3),
        TaskStatus.IN_REVIEW: timedelta(days=2),
        TaskStatus.BLOCKED: timedelta(days=7),
        TaskStatus.TODO: timedelta(days=14)
    }

    stale_tasks = []
    for task in tasks:
        if task.status == TaskStatus.DONE:
            continue

        threshold = staleness_thresholds.get(task.status, timedelta(days=7))
        last_update = task.updated_at if hasattr(task, 'updated_at') else task.created_at

        if now - last_update > threshold:
            stale_tasks.append((task, now - last_update))

    if stale_tasks:
        stale_tasks.sort(key=lambda x: x[1], reverse=True)

        description_parts = []
        for task, age in stale_tasks[:5]:  # Show top 5
            age_days = age.days
            description_parts.append(f"• '{task.title}' ({age_days} days old)")

        issues.append(BoardHealthIssue(
            type="stale_tasks",
            severity=IssueSeverity.MEDIUM,
            title=f"{len(stale_tasks)} Stale Tasks Detected",
            description="\n".join(description_parts),
            affected_tasks=[t[0].id for t in stale_tasks],
            recommendations=[
                "Review and update stale tasks",
                "Close tasks that are no longer relevant",
                "Reassign tasks that are stuck",
                "Add progress updates to active tasks"
            ]
        ))

    return issues
```

### 6. Workload Balance Analysis

Checks for uneven task distribution:

```python
def _analyze_workload_balance(
    self,
    tasks: List[Task],
    agents: List[WorkerAgent]
) -> List[BoardHealthIssue]:
    """Analyze if workload is balanced across agents"""
    issues = []

    # Count tasks per agent
    agent_task_count = {}
    for agent in agents:
        if agent.status == WorkerStatus.ACTIVE:
            agent_task_count[agent.id] = 0

    # Count assigned tasks
    for task in tasks:
        if task.status == TaskStatus.IN_PROGRESS and task.assigned_to:
            if task.assigned_to in agent_task_count:
                agent_task_count[task.assigned_to] += 1

    if not agent_task_count:
        return issues

    # Calculate statistics
    counts = list(agent_task_count.values())
    avg_tasks = sum(counts) / len(counts) if counts else 0
    max_tasks = max(counts) if counts else 0
    min_tasks = min(counts) if counts else 0

    # Check for imbalance
    if max_tasks > avg_tasks * 2 and max_tasks >= 3:
        overloaded = [aid for aid, count in agent_task_count.items() if count == max_tasks]
        underutilized = [aid for aid, count in agent_task_count.items() if count <= 1]

        issues.append(BoardHealthIssue(
            type="workload_imbalance",
            severity=IssueSeverity.MEDIUM,
            title="Uneven Workload Distribution",
            description=(
                f"Some agents have {max_tasks} tasks while others have {min_tasks}. "
                f"Average is {avg_tasks:.1f} tasks per agent."
            ),
            affected_tasks=[],
            recommendations=[
                f"Reassign tasks from overloaded agents: {', '.join(overloaded)}",
                f"Utilize available agents: {', '.join(underutilized)}",
                "Review task assignment algorithm",
                "Consider agent skills when distributing tasks"
            ]
        ))

    return issues
```

## Issue Data Structure

```python
@dataclass
class BoardHealthIssue:
    """Represents a health issue found during board analysis"""
    type: str  # skill_mismatch, circular_dependency, etc.
    severity: IssueSeverity
    title: str
    description: str
    affected_tasks: List[str]
    affected_agents: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class IssueSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
```

## MCP Tool Integration

### check_board_health Tool

Provides comprehensive board analysis:

```python
async def check_board_health(
    kanban_client: KanbanInterface,
    agent_manager: AgentManager
) -> Dict[str, Any]:
    """Analyze board health and return issues with recommendations"""

    # Get current board state
    tasks = await kanban_client.get_all_tasks()
    agents = agent_manager.get_all_agents()

    # Run analysis
    analyzer = BoardHealthAnalyzer()
    issues = analyzer.analyze_board_health(tasks, agents)

    # Format response
    return {
        "healthy": len(issues) == 0,
        "issue_count": len(issues),
        "critical_issues": sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL),
        "issues": [
            {
                "type": issue.type,
                "severity": issue.severity.value,
                "title": issue.title,
                "description": issue.description,
                "affected_tasks": issue.affected_tasks,
                "recommendations": issue.recommendations
            }
            for issue in issues
        ],
        "summary": _generate_health_summary(issues)
    }
```

### check_task_dependencies Tool

Analyzes task dependency graph:

```python
async def check_task_dependencies(
    task_id: str,
    kanban_client: KanbanInterface
) -> Dict[str, Any]:
    """Check dependencies for a specific task"""

    tasks = await kanban_client.get_all_tasks()
    task_map = {t.id: t for t in tasks}

    if task_id not in task_map:
        raise ValueError(f"Task {task_id} not found")

    target_task = task_map[task_id]

    # Build dependency information
    dependencies = {
        "direct_dependencies": [],
        "direct_dependents": [],
        "transitive_dependencies": [],
        "transitive_dependents": [],
        "is_blocked": False,
        "blocking_tasks": [],
        "is_part_of_cycle": False,
        "cycle_tasks": []
    }

    # Analyze dependencies
    # ... (implementation details)

    return dependencies
```

## Real-World Examples

### Example 1: Circular Dependency Detection

```bash
$ check_board_health

🚑 CRITICAL: Circular Dependency Detected
Tasks form a dependency cycle: task-123 → task-456 → task-789 → task-123

Recommendations:
• Break the cycle by removing one dependency
• Restructure tasks to eliminate circular references
• Consider merging related tasks
```

### Example 2: Skill Mismatch Alert

```bash
$ check_board_health

⚠️  HIGH: Missing Required Skills
Task 'Implement OAuth2' requires {'oauth', 'security'} but no active agents have these skills

Recommendations:
• Find agents with skills: oauth, security
• Consider training existing agents
• Break down task to use available skills
```

### Example 3: Bottleneck Warning

```bash
$ check_board_health

⚠️  HIGH: Bottleneck in IN_REVIEW
18 tasks in IN_REVIEW (threshold: 8)

Recommendations:
• Review and prioritize IN_REVIEW tasks
• Assign more resources to this stage
• Identify and remove blockers
• Consider work-in-progress limits
```

## Implementation Details

### Complete Analysis Method

```python
class BoardHealthAnalyzer:
    """Analyzes Kanban board health and identifies issues"""

    def analyze_board_health(
        self,
        tasks: List[Task],
        agents: List[WorkerAgent]
    ) -> List[BoardHealthIssue]:
        """Run all health checks and return issues"""
        all_issues = []

        # Run all analysis methods
        all_issues.extend(self._analyze_skill_mismatches(tasks, agents))
        all_issues.extend(self._analyze_circular_dependencies(tasks))
        all_issues.extend(self._analyze_bottlenecks(tasks))
        all_issues.extend(self._analyze_chain_blocks(tasks))
        all_issues.extend(self._analyze_stale_tasks(tasks))
        all_issues.extend(self._analyze_workload_balance(tasks, agents))

        # Sort by severity
        severity_order = {
            IssueSeverity.CRITICAL: 0,
            IssueSeverity.HIGH: 1,
            IssueSeverity.MEDIUM: 2,
            IssueSeverity.LOW: 3
        }

        all_issues.sort(key=lambda x: severity_order[x.severity])

        return all_issues
```

### Summary Generation

```python
def _generate_health_summary(issues: List[BoardHealthIssue]) -> str:
    """Generate a human-readable summary of board health"""
    if not issues:
        return "🎉 Board is healthy! No issues detected."

    summary_parts = []

    # Count by severity
    severity_counts = {}
    for issue in issues:
        severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1

    # Build summary
    if IssueSeverity.CRITICAL in severity_counts:
        summary_parts.append(
            f"🚑 {severity_counts[IssueSeverity.CRITICAL]} CRITICAL issues"
        )
    if IssueSeverity.HIGH in severity_counts:
        summary_parts.append(
            f"⚠️  {severity_counts[IssueSeverity.HIGH]} HIGH priority issues"
        )
    if IssueSeverity.MEDIUM in severity_counts:
        summary_parts.append(
            f"🟡 {severity_counts[IssueSeverity.MEDIUM]} MEDIUM priority issues"
        )
    if IssueSeverity.LOW in severity_counts:
        summary_parts.append(
            f"🟢 {severity_counts[IssueSeverity.LOW]} LOW priority issues"
        )

    return " | ".join(summary_parts)
```

## Configuration

### Analysis Thresholds

Configurable in `config_marcus.json`:

```json
{
  "board_health": {
    "enabled": true,
    "bottleneck_thresholds": {
      "TODO": 20,
      "IN_PROGRESS": 10,
      "BLOCKED": 5,
      "IN_REVIEW": 8
    },
    "staleness_days": {
      "IN_PROGRESS": 3,
      "IN_REVIEW": 2,
      "BLOCKED": 7,
      "TODO": 14
    },
    "workload_imbalance_factor": 2.0,
    "min_tasks_for_imbalance_check": 3
  }
}
```

## Pros and Cons

### Advantages

1. **Comprehensive Detection**: Covers 6 major types of board issues
2. **Actionable Insights**: Each issue comes with specific recommendations
3. **Severity Ranking**: Prioritizes issues by impact
4. **Dependency Analysis**: Detects complex circular dependencies
5. **Resource Optimization**: Identifies skill gaps and workload imbalances
6. **Easy Integration**: Simple MCP tool interface
7. **Real-Time Analysis**: On-demand health checks

### Disadvantages

1. **Static Thresholds**: Fixed limits may not suit all projects
2. **No Historical Tracking**: Doesn't track health trends over time
3. **Limited Context**: May miss project-specific nuances
4. **Manual Invocation**: Requires explicit tool calls
5. **No Auto-Remediation**: Provides recommendations but doesn't fix issues

## Why This Approach

The focused issue detection approach was chosen because:

1. **Specific Problems**: Targets known pain points in Kanban boards
2. **Actionable Results**: Each issue has clear remediation steps
3. **Quick Analysis**: Fast execution for real-time feedback
4. **Developer-Friendly**: Clear categories match developer mental models
5. **Integration**: Works seamlessly with existing Marcus workflow
6. **Practical Focus**: Addresses real problems teams face daily

## Usage Examples

### Basic Health Check

```python
# From MCP client
result = await client.call_tool(
    "check_board_health",
    {}
)

if not result["healthy"]:
    print(f"Found {result['issue_count']} issues:")
    for issue in result["issues"]:
        print(f"- [{issue['severity']}] {issue['title']}")
```

### Dependency Analysis

```python
# Check specific task dependencies
result = await client.call_tool(
    "check_task_dependencies",
    {"task_id": "task-123"}
)

if result["is_blocked"]:
    print(f"Task is blocked by: {result['blocking_tasks']}")

if result["is_part_of_cycle"]:
    print(f"WARNING: Task is in a dependency cycle with: {result['cycle_tasks']}")
```

### Automated Health Monitoring

```python
# Set up periodic health checks
async def monitor_board_health():
    while True:
        result = await client.call_tool("check_board_health", {})

        critical_count = result["critical_issues"]
        if critical_count > 0:
            # Send alert
            await notify_team(
                f"CRITICAL: {critical_count} critical board health issues detected!"
            )

        await asyncio.sleep(300)  # Check every 5 minutes
```

## Integration with Other Systems

### Assignment Lease System

Health analyzer can detect stuck tasks from lease data:

```python
# Detect tasks with too many lease renewals
if hasattr(state, 'lease_manager'):
    lease_stats = state.lease_manager.get_statistics()
    if lease_stats['stuck_tasks'] > 0:
        issues.append(BoardHealthIssue(
            type="stuck_tasks_from_leases",
            severity=IssueSeverity.HIGH,
            title=f"{lease_stats['stuck_tasks']} Stuck Tasks (Lease System)",
            description="Tasks have been renewed too many times",
            recommendations=["Review stuck tasks", "Consider reassignment"]
        ))
```

### Assignment Monitor

Integrates with assignment monitor for orphan detection:

```python
# Check for orphaned assignments
if hasattr(state, 'assignment_monitor'):
    health = await state.assignment_monitor.check_assignment_health()
    if not health['healthy']:
        for issue in health['issues']:
            if issue['type'] == 'orphaned_assignments':
                # Add to board health issues
                ...
```

## Future Enhancements

### Short-term Improvements

1. **Auto-Remediation**: Automatically fix simple issues (e.g., unblock tasks)
2. **Health Trends**: Track health over time for pattern detection
3. **Custom Checks**: Allow project-specific health checks
4. **Integration API**: Webhook notifications for critical issues

### Long-term Vision

1. **Predictive Analysis**: Forecast future bottlenecks
2. **AI Recommendations**: ML-based suggestion improvements
3. **Team Analytics**: Correlate health with team performance
4. **Automated Workflows**: Trigger actions based on health status

## Conclusion

The Board Health Analyzer System provides Marcus with targeted diagnostic capabilities that identify and help resolve six critical board health issues. By analyzing skill mismatches, circular dependencies, bottlenecks, chain blocks, stale tasks, and workload imbalances, the system helps teams maintain healthy, efficient Kanban boards.

The analyzer's practical focus on real-world problems, combined with actionable recommendations for each issue type, makes it an essential tool for project managers and team leads. Its integration as simple MCP tools ensures easy access for both human users and AI agents, enabling proactive board management and preventing common workflow problems before they impact project delivery.
