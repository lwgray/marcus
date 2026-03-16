# Activity Tracking vs. Diagnostics

## Core Philosophy

Marcus employs a clear separation between **activity tracking** (recording what happened) and **diagnostics** (analyzing why it happened). This separation improves system maintainability, reduces false assumptions, and provides appropriate information to different audiences.

## The Problem: Everything Mixed Together

### Anti-Pattern: Diagnostic Logging Everywhere

A common mistake in distributed systems is mixing activity tracking with diagnostic analysis:

```python
# ❌ BAD: Mixed concerns
def handle_task_request(agent_id):
    result = find_task_for_agent(agent_id)

    if not result:
        # Logging mixes WHAT with assumed WHY
        if has_dependency_keywords(error):
            logger.critical("DEPENDENCY ISSUE: ...")  # Assumption!
        elif has_busy_keywords(error):
            logger.warning("Agent busy: ...")
        else:
            logger.error("Unknown failure: ...")

        # Diagnostic analysis in logging code
        run_dependency_analysis()  # Wrong place!
        check_agent_skills()        # Wrong place!

    return result
```

**Problems:**
1. **False assumptions:** Keywords don't equal root cause
2. **Mixed audiences:** Operators need different info than agents
3. **Maintenance burden:** Changes require updating multiple locations
4. **Poor separation:** Activity tracking code becomes diagnostic code

## Marcus Solution: Clear Separation

### Two-Layer Design

```
┌─────────────────────────────────────────────────────┐
│                ACTIVITY TRACKING LAYER              │
│  Records: WHAT happened, WHEN, WHO was involved    │
│  Purpose: Index/table of contents for operations   │
│  Audience: Quick overview, correlation              │
│  Example: MCP Tool Logger                           │
│  Location: Conversation logs                        │
└─────────────────────────────────────────────────────┘
                        ↓
         Points to (when needed)
                        ↓
┌─────────────────────────────────────────────────────┐
│                 DIAGNOSTIC LAYER                    │
│  Analyzes: WHY it happened, root cause, context    │
│  Purpose: Deep investigation, problem solving       │
│  Audience: Operators fixing issues                  │
│  Example: Task Diagnostics, Dependency Analyzer     │
│  Location: Python logs, specialized reports         │
└─────────────────────────────────────────────────────┘
```

### Activity Tracking Layer

**Characteristics:**
- **Simple:** Records events as they happen
- **Factual:** No interpretation or analysis
- **Fast:** Minimal processing overhead
- **Consistent:** Same format for all events
- **Indexable:** Easy to search and correlate

**Example: MCP Tool Logger**

```python
# ✅ GOOD: Just record the activity
def log_mcp_tool_response(tool_name, arguments, response):
    """Record WHAT failed and WHEN."""
    if response["success"]:
        logger.debug(f"Tool '{tool_name}' succeeded")
    else:
        logger.warning(
            f"Tool '{tool_name}' returned failure",
            tool_name=tool_name,
            arguments=arguments,
            error=response.get("error"),
            response=response,  # Full context preserved
        )

        # Point to diagnostics (don't run them here!)
        if tool_name == "request_next_task":
            logger.debug("Check Python logs for 'Diagnostic Report'")
```

**Benefits:**
- ✅ No assumptions about cause
- ✅ Consistent WARNING level
- ✅ Full context preserved
- ✅ Fast execution
- ✅ Easy to maintain

### Diagnostic Layer

**Characteristics:**
- **Deep:** Analyzes context and relationships
- **Specialized:** Purpose-built for specific problems
- **Selective:** Only runs when needed
- **Detailed:** Provides actionable insights
- **Separate:** Runs in appropriate context

**Example: Task Diagnostics**

```python
# ✅ GOOD: Separate diagnostic system
async def run_automatic_diagnostics(project_tasks, completed_ids, assigned_ids):
    """
    Deep analysis of WHY tasks can't be assigned.

    Runs automatically when request_next_task fails,
    NOT during every tool call.
    """
    # Collect comprehensive data
    collector = TaskDiagnosticCollector(project_tasks)
    stats = collector.collect_filtering_stats(completed_ids, assigned_ids)

    # Analyze dependencies
    analyzer = DependencyChainAnalyzer(project_tasks)
    dependency_issues = analyzer.analyze_chains()

    # Analyze skills
    skill_mismatches = analyzer.analyze_skill_requirements()

    # Generate actionable report
    report = DiagnosticReportGenerator(
        project_tasks, stats, dependency_issues, skill_mismatches
    )

    # Log to Python logs (separate stream)
    logger.info(f"Diagnostic Report (for operators):\n{report.format()}")

    return report
```

**Benefits:**
- ✅ Accurate root cause analysis
- ✅ Runs in appropriate context
- ✅ Separate log stream
- ✅ Actionable recommendations
- ✅ Purpose-built for problem

## Real-World Example: request_next_task

### The Scenario

Agent calls `request_next_task` → receives `{"success": false, "error": "No suitable tasks available"}`

### Why is it failing? (Multiple possible causes)

1. **All tasks assigned** to other agents
2. **Dependencies blocking** - tasks depend on incomplete work
3. **Skill mismatch** - agent lacks required skills
4. **Circular dependencies** - deadlock in task chain
5. **Tasks filtered** by other criteria (status, priority, etc.)

The MCP response doesn't tell us which!

### Activity Tracking Records WHAT/WHEN

**Conversation Log Entry:**
```json
{
  "timestamp": "2025-01-15T10:35:22.456Z",
  "level": "warning",
  "message": "MCP tool 'request_next_task' returned failure",
  "tool_name": "request_next_task",
  "arguments": {"agent_id": "agent_002"},
  "error": "No suitable tasks available"
}
```

**What we know:**
- ✅ WHAT: request_next_task failed
- ✅ WHEN: 10:35:22 on Jan 15
- ✅ WHO: agent_002
- ❌ WHY: Unknown (need diagnostics)

### Diagnostics Analyze WHY

**Automatic Trigger:**
```python
# In src/marcus_mcp/tools/task.py
if todo_tasks and not assignable_tasks:
    # Activity tracker already logged the failure
    # Now run diagnostics to understand WHY
    diagnostic_report = await run_automatic_diagnostics(...)
```

**Python Log Entry:**
```
2025-01-15 10:35:22,450 INFO - Diagnostic Report (for operators):
=== Task Assignment Diagnostics ===

Total Tasks: 5
TODO Tasks: 3
In Progress: 1
Completed: 1

Filtering Results:
- Started with: 3 TODO tasks
- After dependency filter: 0 tasks ← HERE'S WHY!
- After skill filter: 0 tasks
- After assignment filter: 0 tasks

Dependency Chain Analysis:
- Task "Implement API" (task_456) blocked by incomplete "Setup Database" (task_123)
- Task "Write Tests" (task_789) blocked by incomplete "Implement API" (task_456)

Root Cause: Dependencies blocking
Recommendation: Complete "Setup Database" to unblock chain
```

**Now we know:**
- ✅ WHY: Dependencies blocking
- ✅ WHICH tasks: Specific IDs and names
- ✅ WHAT to do: Complete task_123
- ✅ CONTEXT: Full dependency chain

## Why Mixing is Bad: Real Examples

### Example 1: Keyword-Based Categorization

```python
# ❌ BAD: Activity tracker tries to diagnose
def log_failure(error_msg):
    if "dependency" in error_msg.lower():
        logger.critical("DEPENDENCY ISSUE!")  # Assumption!
        return "dependency_issue"

# Reality:
error_msg = "No suitable tasks available"
# Could be dependency issue, but also could be:
# - All tasks assigned
# - Skill mismatch
# - No tasks exist
# We can't tell from the message!
```

**Problem:** Keyword ≠ Root cause

### Example 2: Wrong Log Level Escalation

```python
# ❌ BAD: Escalate based on keywords
if "blocked by" in error:
    logger.critical("Critical dependency issue!")  # Misleading!
else:
    logger.warning("Normal failure")

# Reality:
# "blocked by" might appear in retry message
# But diagnostic shows: "Actually, all tasks are assigned"
# Operator sees CRITICAL but it's not a dependency issue!
```

**Problem:** False urgency, wasted investigation time

### Example 3: Analysis in Wrong Place

```python
# ❌ BAD: Diagnostic logic in logging code
def log_mcp_failure(tool_name, response):
    logger.warning(f"{tool_name} failed")

    # Diagnostic work in logging layer!
    if tool_name == "request_next_task":
        tasks = get_all_tasks()  # Expensive!
        deps = analyze_dependencies(tasks)  # More expensive!
        logger.info(f"Dependency analysis: {deps}")

# Problems:
# 1. Runs on EVERY failure (wasteful)
# 2. Mixed in logging code (wrong place)
# 3. Duplicate work (diagnostics run elsewhere too)
# 4. Can't leverage existing diagnostic context
```

**Problem:** Wrong layer, duplicate work, performance impact

## Design Principles

### 1. Single Responsibility

**Activity Tracking:**
- Records events
- Preserves context
- Points to diagnostics

**Diagnostics:**
- Analyzes problems
- Determines root cause
- Recommends actions

Don't mix them!

### 2. Appropriate Timing

**Activity Tracking:**
- Runs: Always (low overhead)
- When: During/after operation
- Fast: < 1ms

**Diagnostics:**
- Runs: When needed (selective)
- When: After failure detected
- Thorough: May take seconds

### 3. Correct Audience

**Activity Tracking:**
- **For:** Quick overview, correlation
- **Format:** Structured logs, searchable
- **Location:** Conversation logs (indexed)

**Diagnostics:**
- **For:** Deep investigation
- **Format:** Detailed reports
- **Location:** Python logs (detailed)

### 4. No Assumptions

**Activity Tracking:**
- Records facts only
- No interpretation
- No categorization
- Full context preserved

**Diagnostics:**
- Makes informed analysis
- Uses full system context
- Considers relationships
- Provides evidence

## Practical Benefits

### For Operators

**Quick Investigation:**
```bash
# Step 1: What failed recently?
grep 'returned failure' logs/conversations/marcus_*.log | tail -10

# Step 2: Lots of request_next_task failures?
grep 'request_next_task.*failure' logs/conversations/marcus_*.log | wc -l

# Step 3: Why? Check diagnostics near that time
grep -A 30 'Diagnostic Report' logs/marcus_*.log | tail -50
```

**Benefits:**
- ✅ Fast triage (activity logs)
- ✅ Deep dive when needed (diagnostics)
- ✅ Clear correlation (timestamps)
- ✅ No false assumptions

### For Developers

**Maintainability:**
```python
# Activity tracker: Simple, stable
def log_activity(tool, result):
    """Just record what happened."""
    logger.log(level, message, **context)

# Diagnostics: Complex, evolving
class TaskDiagnostics:
    """Deep analysis, can evolve independently."""
    def analyze_dependencies(self): ...
    def analyze_skills(self): ...
    def generate_report(self): ...
```

**Benefits:**
- ✅ Clear separation of concerns
- ✅ Easy to test independently
- ✅ Can evolve separately
- ✅ Diagnostic complexity doesn't affect logging

### For System Performance

**Efficient Resource Usage:**
```python
# Activity logging: Always on, minimal cost
log_activity()  # < 1ms, always safe

# Diagnostics: Selective, when needed
if failure_needs_investigation:
    run_diagnostics()  # 10-100ms, but selective
```

**Benefits:**
- ✅ Low overhead for activity tracking
- ✅ Expensive analysis only when needed
- ✅ No performance impact on happy path

## Anti-Patterns to Avoid

### ❌ Diagnostic Logic in Activity Tracking

```python
# BAD: Mixing concerns
def log_tool_failure(tool_name, response):
    logger.warning(f"{tool_name} failed")

    # Don't do diagnostic work here!
    if "dependency" in str(response):  # Keyword matching
        category = "dependency_issue"  # Assumption!
        logger.critical("Dependency problem detected!")  # Wrong level!
        analyze_dependencies()  # Wrong place!
```

### ❌ Activity Tracking in Diagnostic Code

```python
# BAD: Diagnostics shouldn't do activity logging
def run_diagnostics():
    # Diagnostic code
    deps = analyze_dependencies()

    # Don't log activity here!
    logger.warning("Tool failed because dependencies")  # Wrong place!

    return report
```

### ❌ Duplicate Information

```python
# BAD: Logging same info in multiple places
def handle_failure():
    # Activity tracker logs it
    log_activity("tool_name", result)

    # Diagnostics also log the failure
    logger.warning("Tool failed")  # Duplicate!

    # Analysis repeats failure details
    report = f"Tool failed because..."  # More duplication!
```

## Implementation Checklist

When building a new feature, ensure clear separation:

### Activity Tracking Implementation

- [ ] Records event occurrence (WHAT/WHEN)
- [ ] Uses consistent log level
- [ ] Preserves full context
- [ ] No interpretation or analysis
- [ ] Fast execution (< 1ms)
- [ ] Points to diagnostics if available
- [ ] Uses conversation logs (or appropriate stream)

### Diagnostic Implementation

- [ ] Runs selectively (when needed)
- [ ] Analyzes root cause (WHY)
- [ ] Provides actionable recommendations
- [ ] Uses full system context
- [ ] Separate log stream (Python logs, reports)
- [ ] Can take time (thorough analysis)
- [ ] Purpose-built for specific problems

## Related Concepts

### Activity Tracking in Marcus

- **MCP Tool Logger** - Tracks MCP tool operations
- **Agent Event Logs** - Tracks agent lifecycle
- **Conversation Logs** - Tracks PM decisions, worker messages

### Diagnostics in Marcus

- **Task Diagnostics** - Analyzes task assignment failures
- **Dependency Analyzer** - Analyzes dependency chains
- **Assignment Monitor** - Detects assignment issues
- **Error Predictor** - Predicts potential failures

### Integration Patterns

- **Hybrid Monitoring** - Activity + diagnostics working together
- **Correlation IDs** - Linking activity to diagnostic reports
- **Layered Logging** - Multiple log streams for different purposes

## Conclusion

The separation between activity tracking and diagnostics is a fundamental design principle in Marcus. It ensures:

1. **Appropriate information** for different audiences
2. **Clear responsibilities** for each component
3. **No false assumptions** about failure causes
4. **Efficient resource usage** (selective expensive analysis)
5. **Maintainability** (concerns evolve independently)

When in doubt:
- **Activity tracking:** Record what happened (facts only)
- **Diagnostics:** Analyze why it happened (when needed)

Never mix them in the same code!
