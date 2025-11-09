# Phase 2 Post-Project Analysis - User Guide

## Overview

Phase 2 provides AI-powered analysis of completed projects to understand **why** things went wrong and generate actionable insights. This guide shows how to use the Phase 2 analysis tools via the Marcus MCP server.

## Quick Start

### Running Analysis via MCP

The Marcus MCP server exposes 5 tools for post-project analysis:

1. **`analyze_project`** - Run complete analysis on a project
2. **`get_requirement_divergence`** - Analyze how implementation diverged from requirements
3. **`get_decision_impacts`** - Trace how decisions cascaded through the project
4. **`get_instruction_quality`** - Evaluate clarity and completeness of task instructions
5. **`get_failure_diagnoses`** - Diagnose why tasks failed

### Example: Complete Project Analysis

```python
# Via MCP client
result = await mcp_client.call_tool(
    "analyze_project",
    {
        "project_id": "my-web-app-2024",
        "scope": {
            "requirement_divergence": True,
            "decision_impact": True,
            "instruction_quality": True,
            "failure_diagnosis": True
        }
    }
)
```

**Output Structure:**
```json
{
  "success": true,
  "project_id": "my-web-app-2024",
  "analysis_timestamp": "2025-11-09T10:30:00Z",
  "summary": "Executive summary of project analysis...",
  "requirement_divergences": [...],
  "decision_impacts": [...],
  "instruction_quality_issues": [...],
  "failure_diagnoses": [...],
  "metadata": {
    "tasks_analyzed": 12,
    "decisions_analyzed": 8,
    "failed_tasks": 2
  }
}
```

## Analysis Modules

### 1. Requirement Divergence Analyzer

**Purpose:** Detect when implementation doesn't match the original requirements

**Use Case:** You specified OAuth2 authentication but the agent implemented username/password instead.

**Example:**

```python
result = await mcp_client.call_tool(
    "get_requirement_divergence",
    {
        "project_id": "auth-system-2024",
        "task_ids": ["task-auth-implement"]  # Optional: analyze specific tasks
    }
)
```

**Real Example Output (from integration tests):**

Task: "Implement user authentication"
- Original requirement: "Build authentication system using OAuth2 with Google provider"
- Actual implementation: Used JWT tokens instead
- Fidelity Score: 0.65 (moderate divergence)
- Divergences found:
  - **MAJOR**: OAuth2 sessions → JWT tokens
    - Citation: Decision dec-001 at 2025-11-01 10:00
    - Impact: "Changed from stateless OAuth2 to session-based JWT"
  - **MINOR**: No Google provider integration
    - Citation: Task implementation artifact
    - Impact: "Users cannot sign in with Google accounts"

**Recommendations:**
- Clarify if OAuth2 is required or if JWT is acceptable
- If OAuth2 is required, reimplement authentication flow
- Add approval checkpoint for decisions that change authentication strategy

**Output Schema:**
```python
{
  "task_id": "task-auth-implement",
  "fidelity_score": 0.65,  # 0.0 = complete divergence, 1.0 = perfect match
  "divergences": [
    {
      "requirement": "OAuth2 with Google provider",
      "implementation": "JWT token authentication",
      "severity": "major",  # critical | major | minor
      "impact": "Changed authentication model",
      "citation": "Decision dec-001 at 2025-11-01 10:00"
    }
  ],
  "recommendations": [...]
}
```

### 2. Decision Impact Tracer

**Purpose:** Understand how architectural decisions cascaded through the project

**Use Case:** You decided to use Redis for sessions, but it caused unexpected test failures.

**Example:**

```python
result = await mcp_client.call_tool(
    "get_decision_impacts",
    {
        "project_id": "session-store-2024",
        "decision_ids": ["dec-redis"]  # Optional: analyze specific decisions
    }
)
```

**Real Example Output (from integration tests):**

Decision: "Use JWT tokens instead of OAuth2 sessions"
- Made at: 2025-11-01 10:00
- Confidence: 0.8
- Rationale: "JWT tokens are stateless and easier to scale"

**Impact Chains:**
1. **Direct impacts:**
   - Task "Implement authentication" - Switched to JWT implementation
   - Task "Create user dashboard" - Had to validate JWT tokens

2. **Indirect impacts (depth 2):**
   - Task "Data export" - Needed to handle JWT in async processes
   - Performance: Reduced database load (no session queries)

3. **Unexpected impacts:**
   - Task "Create user dashboard" expected OAuth tokens
   - Anticipated: "Minor changes to token validation"
   - Actual: "Required complete rewrite of auth middleware" (severity: major)

**Recommendations:**
- Document decision impact scope before implementation
- Consider cascading effects on dependent tasks
- Set up impact review checkpoints for high-impact decisions

**Output Schema:**
```python
{
  "decision_id": "dec-redis",
  "impact_chains": [
    {
      "decision_summary": "Use Redis for session storage",
      "direct_impacts": ["task-session-impl", "task-logout-impl"],
      "indirect_impacts": ["task-load-test"],
      "depth": 2,
      "citation": "Decision dec-redis at 2025-11-02 11:00"
    }
  ],
  "unexpected_impacts": [
    {
      "affected_task": "task-logout-impl",
      "anticipated": "Straightforward implementation",
      "actual_impact": "Required Redis setup in test environment",
      "severity": "moderate"
    }
  ],
  "recommendations": [...]
}
```

### 3. Instruction Quality Analyzer

**Purpose:** Evaluate if task instructions were clear and complete enough

**Use Case:** A task took 4x longer than estimated because requirements were vague.

**Example:**

```python
result = await mcp_client.call_tool(
    "get_instruction_quality",
    {
        "project_id": "notification-system-2024",
        "task_ids": ["task-notification-impl"]
    }
)
```

**Real Example Output (from integration tests):**

Task: "Add authentication"
- Original description: "Users should be able to log in to the system"
- Estimated: 4 hours
- Actual: 16 hours (4x overrun)

**Quality Scores:**
- Clarity: 0.3/1.0 (poor)
- Completeness: 0.2/1.0 (very poor)
- Specificity: 0.25/1.0 (poor)
- Overall: 0.25/1.0

**Ambiguity Issues Found:**
1. **CRITICAL**: Authentication method not specified
   - Evidence: Agent asked "OAuth, JWT, or sessions?"
   - Consequence: 2 hours spent researching options
   - Citation: Clarification log 2025-11-01 10:30

2. **MAJOR**: User data schema unclear
   - Evidence: Agent asked "What fields to collect?"
   - Consequence: Database schema designed twice
   - Citation: Clarification log 2025-11-01 10:35

3. **MAJOR**: Password requirements undefined
   - Evidence: Agent asked "Complexity rules?"
   - Consequence: 1 hour implementing arbitrary rules
   - Citation: Clarification log 2025-11-01 10:40

**Correlation with Delays:**
The 4x time overrun directly correlates with poor instruction quality. Agent spent 6+ hours asking clarifying questions.

**Recommendations:**
- Specify authentication method explicitly (OAuth2, JWT, username/password)
- Define user data schema upfront
- Document password complexity requirements
- Add acceptance criteria checklist to task templates

**Output Schema:**
```python
{
  "task_id": "task-notification-impl",
  "quality_scores": {
    "clarity": 0.3,
    "completeness": 0.2,
    "specificity": 0.25,
    "overall": 0.25
  },
  "ambiguity_issues": [
    {
      "aspect": "Authentication method",
      "evidence": "Agent asked multiple clarifying questions",
      "consequence": "2 hours delay",
      "severity": "critical"  # critical | major | minor
    }
  ],
  "recommendations": [...]
}
```

### 4. Failure Diagnosis Generator

**Purpose:** Understand why tasks failed and how to prevent similar failures

**Use Case:** A database migration task failed after 8 hours of work.

**Example:**

```python
result = await mcp_client.call_tool(
    "get_failure_diagnoses",
    {
        "project_id": "db-migration-2024",
        "task_ids": ["task-migration-failed"]  # Analyzes only failed tasks
    }
)
```

**Real Example Output (from integration tests):**

Task: "Migrate from REST to GraphQL API"
- Status: Failed
- Estimated: 80 hours
- Actual: 160 hours (100% overrun before failure)

**Failure Causes:**

1. **TECHNICAL** (root cause):
   - Root Cause: "N+1 query problem causing 1000+ database queries"
   - Contributing Factors:
     - No database query optimization in design
     - Performance testing done with small dataset (100 users vs 100k production)
   - Evidence: Error logs showing query timeouts
   - Citation: Task error log 2025-10-25 15:30

2. **REQUIREMENTS** (contributing):
   - Root Cause: "Breaking API changes not communicated to client teams"
   - Contributing Factors:
     - No API versioning strategy
     - Mobile team not consulted
   - Evidence: 50% of mobile users experienced crashes
   - Citation: Production incident report

3. **PROCESS** (contributing):
   - Root Cause: "Deployed to production without canary release"
   - Contributing Factors:
     - Over-confidence in test coverage (only 30% coverage)
     - No rollback plan documented
   - Evidence: Decision dec-002 "Deploy without canary"
   - Citation: Decision log 2025-10-20 14:00

**Prevention Strategies:**

1. **HIGH PRIORITY**, Medium Effort:
   - Strategy: "Implement database query monitoring and optimization review"
   - Rationale: "Would have caught N+1 queries before production"

2. **HIGH PRIORITY**, Low Effort:
   - Strategy: "Require API versioning for all breaking changes"
   - Rationale: "Allows gradual migration, prevents breaking existing clients"

3. **MEDIUM PRIORITY**, High Effort:
   - Strategy: "Set up canary deployment pipeline"
   - Rationale: "Limits blast radius of failures to small percentage of users"

**Lessons Learned:**
- Performance testing must use production-scale datasets
- Breaking changes require explicit communication to all stakeholders
- High-impact deployments need gradual rollout strategies

**Output Schema:**
```python
{
  "task_id": "task-migration-failed",
  "failure_causes": [
    {
      "category": "technical",  # technical | requirements | process | communication
      "root_cause": "N+1 query problem",
      "contributing_factors": ["No query optimization", "Small test dataset"],
      "evidence": "Error logs showing 1000+ queries",
      "citation": "Task error log 2025-10-25 15:30"
    }
  ],
  "prevention_strategies": [
    {
      "strategy": "Implement query monitoring",
      "rationale": "Would catch performance issues early",
      "effort": "medium",  # low | medium | high
      "priority": "high"   # low | medium | high
    }
  ],
  "lessons_learned": [...]
}
```

## Running Integration Tests

The Phase 2 analyzers have comprehensive integration tests that make real Claude API calls.

### Prerequisites

1. Valid Claude API key in `config_marcus.json`:
```json
{
  "ai_provider": "anthropic",
  "anthropic": {
    "api_key": "sk-ant-..."  # pragma: allowlist secret
  }
}
```

2. Install test dependencies:
```bash
pip install -e ".[test]"
```

### Running Tests

**Run all Phase 2 integration tests:**
```bash
pytest tests/integration/analysis/ -v -m integration
```

**Run specific analyzer tests:**
```bash
# Requirement Divergence Analyzer
pytest tests/integration/analysis/test_requirement_divergence_live.py -v -m integration

# Decision Impact Tracer
pytest tests/integration/analysis/test_decision_impact_tracer_live.py -v -m integration

# Instruction Quality Analyzer
pytest tests/integration/analysis/test_instruction_quality_live.py -v -m integration

# Failure Diagnosis Generator
pytest tests/integration/analysis/test_failure_diagnosis_live.py -v -m integration

# Complete PostProjectAnalyzer
pytest tests/integration/analysis/test_post_project_analyzer_live.py -v -m integration
```

**Manual inspection tests (shows full LLM output):**
```bash
# See complete analysis output for review
pytest tests/integration/analysis/test_post_project_analyzer_live.py::test_manual_inspection_live -v -s
pytest tests/integration/analysis/test_failure_diagnosis_live.py::test_manual_inspection_failure_diagnosis_live -v -s
pytest tests/integration/analysis/test_instruction_quality_live.py::test_manual_inspection_instruction_quality_live -v -s
```

### Test Coverage

All integration tests verify:
- ✅ LLM outputs have valid structure and schemas
- ✅ Citations include task/decision IDs and timestamps
- ✅ Severity levels are valid ("critical", "major", "minor")
- ✅ Scores are in valid ranges (0.0 to 1.0)
- ✅ Progress callbacks work correctly
- ✅ Analysis handles edge cases (minimal data, complex failures)

## Advanced Usage

### Selective Analysis

Run only specific analyzers to save time and API costs:

```python
# Only analyze requirement divergence
result = await mcp_client.call_tool(
    "analyze_project",
    {
        "project_id": "my-project",
        "scope": {
            "requirement_divergence": True,
            "decision_impact": False,
            "instruction_quality": False,
            "failure_diagnosis": False
        }
    }
)
```

### Progress Tracking

For long-running analyses, use progress callbacks:

```python
async def progress_callback(event):
    print(f"{event.operation}: {event.message} ({event.current}/{event.total})")

analyzer = PostProjectAnalyzer()
analysis = await analyzer.analyze_project(
    project_id="large-project",
    tasks=tasks,
    decisions=decisions,
    progress_callback=progress_callback
)
```

Output:
```
requirement_divergence: Analyzing task 1 of 50 (1/50)
requirement_divergence: Analyzing task 2 of 50 (2/50)
...
decision_impact: Tracing decision dec-001 (1/20)
...
```

### Filtering Results

Analyze specific tasks or decisions:

```python
# Only analyze specific tasks
result = await mcp_client.call_tool(
    "get_requirement_divergence",
    {
        "project_id": "my-project",
        "task_ids": ["task-001", "task-005", "task-012"]
    }
)

# Only analyze specific decisions
result = await mcp_client.call_tool(
    "get_decision_impacts",
    {
        "project_id": "my-project",
        "decision_ids": ["dec-redis", "dec-graphql"]
    }
)
```

## Best Practices

### 1. Always Review Raw Data

The LLM provides interpretations, but always verify against raw data:

```python
for divergence in result["requirement_divergences"]:
    print("Task:", divergence["task_id"])
    print("Fidelity:", divergence["fidelity_score"])

    # Review each divergence
    for div in divergence["divergences"]:
        print(f"  Severity: {div['severity']}")
        print(f"  Requirement: {div['requirement']}")
        print(f"  Implementation: {div['implementation']}")
        print(f"  Citation: {div['citation']}")  # Verify this exists!
```

### 2. Use Citations to Verify Claims

Every analysis includes citations. Use them to validate the LLM's reasoning:

```python
# Good: Citation with specific reference
"Citation: Decision dec-001 at 2025-11-01 10:00 - 'Use JWT tokens'"

# Bad: No citation
"The agent decided to use JWT tokens"  # Can't verify!
```

### 3. Focus on High-Severity Issues First

Prioritize issues by severity:

```python
critical_divergences = [
    div for analysis in result["requirement_divergences"]
    for div in analysis["divergences"]
    if div["severity"] == "critical"
]

print(f"Found {len(critical_divergences)} critical divergences to address")
```

### 4. Track Prevention Strategies

Failure diagnoses include prevention strategies - track and implement them:

```python
high_priority_strategies = [
    strat for diagnosis in result["failure_diagnoses"]
    for strat in diagnosis["prevention_strategies"]
    if strat["priority"] == "high"
]

for strategy in high_priority_strategies:
    print(f"[{strategy['effort']} effort] {strategy['strategy']}")
    print(f"  Why: {strategy['rationale']}")
```

## Troubleshooting

### Analysis Returns Empty Results

**Problem:** `requirement_divergences: []`

**Solutions:**
1. Check that project has task history: `context.project_history.conversations`
2. Verify tasks have required fields: `task_id`, `name`, `description`, `status`
3. Ensure project context exists in state: `state._project_contexts.get(project_id)`

### LLM Analysis Seems Wrong

**Problem:** Fidelity score doesn't match your understanding

**Remember:**
- LLM makes its own interpretation - don't over-constrain it
- Check citations to understand the LLM's reasoning
- Verify raw data is complete and accurate
- LLM may catch divergences you missed!

### API Rate Limits

**Problem:** "Rate limit exceeded" errors

**Solutions:**
1. Analyze fewer tasks at once (use `task_ids` parameter)
2. Run selective analysis (disable some analyzers in `scope`)
3. Increase delay between API calls in `AIEngine` configuration

### Test Failures

**Problem:** Integration tests fail

**Common causes:**
1. Missing/invalid API key in `config_marcus.json`
2. Overly prescriptive assertions (expecting exact LLM output)
3. Network issues (Claude API unavailable)

**Fix overly prescriptive tests:**
```python
# Bad: Expects exact score
assert analysis.fidelity_score == 0.85

# Good: Validates range
assert 0.0 <= analysis.fidelity_score <= 1.0
```

## What's Next?

After running Phase 2 analysis:

1. **Review the summary** - Start with the executive summary
2. **Address critical issues** - Fix critical divergences and failures first
3. **Learn from patterns** - Look for recurring instruction quality issues
4. **Update processes** - Implement prevention strategies
5. **Document learnings** - Share insights with team

Phase 3 (coming next) will provide a web UI (Cato) for interactive exploration of analysis results.

## Reference

### All MCP Tools

| Tool | Purpose | Required Args | Optional Args |
|------|---------|---------------|---------------|
| `analyze_project` | Complete analysis | `project_id` | `scope` |
| `get_requirement_divergence` | Divergence only | `project_id` | `task_ids` |
| `get_decision_impacts` | Decision impacts only | `project_id` | `decision_ids` |
| `get_instruction_quality` | Instruction quality only | `project_id` | `task_ids` |
| `get_failure_diagnoses` | Failure diagnosis only | `project_id` | `task_ids` |

### Analysis Data Models

See `src/analysis/post_project_analyzer.py` for complete data models:
- `PostProjectAnalysis` - Complete analysis result
- `RequirementDivergenceAnalysis` - Divergence analysis
- `DecisionImpactAnalysis` - Decision impact analysis
- `InstructionQualityAnalysis` - Instruction quality analysis
- `FailureDiagnosis` - Failure diagnosis

### Integration Test Files

All integration tests in `tests/integration/analysis/`:
- `test_requirement_divergence_live.py` - Requirement divergence tests
- `test_decision_impact_tracer_live.py` - Decision impact tests
- `test_instruction_quality_live.py` - Instruction quality tests
- `test_failure_diagnosis_live.py` - Failure diagnosis tests
- `test_post_project_analyzer_live.py` - Complete analyzer tests
