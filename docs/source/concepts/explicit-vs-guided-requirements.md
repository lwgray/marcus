# Explicit vs Guided Requirements

## Overview

Marcus uses **two distinct modes** for handling user requirements during project creation: **Explicit Mode** and **Guided Mode**. Understanding these modes is critical for predicting project scope and task count.

## The Two Modes

### Explicit Mode

**When Activated:**
- User provides numbered lists (1., 2., 3., ...)
- User provides bulleted lists (-, *, •)
- User uses explicit phrases: "create these", "these tools:", "requirements:"
- **Trigger threshold:** ≥3 list items in any of the above formats

**Behavior:**
- **Bypasses ALL complexity-based filtering**
- Respects user's explicit intent 100%
- Keeps ALL user-specified requirements regardless of complexity mode
- Still applies AI enhancement for support tasks (design, testing, infrastructure)

**Example:**
```
PRD: "Create an MCP server with these 10 tools:
1. ping - Test connectivity
2. echo - Echo messages
3. get_time - Get timestamp
... (7 more tools)"

Prototype mode → 23 tasks (all 10 tools + support tasks)
Standard mode  → 27 tasks (all 10 tools + support tasks)
```

**Rationale:** If a user explicitly lists 10 requirements, filtering them down to 2-3 would violate their explicit request. The complexity mode becomes a **quality/detail** setting, not a quantity limiter.

### Guided Mode

**When Activated:**
- Open-ended descriptions
- No numbered/bulleted lists
- Descriptive language like "build", "create a system for"

**Behavior:**
- **Applies complexity-based filtering**
- AI extracts features from description
- Requirements filtered by team capacity
  - **Prototype:** Keep first 2 functional requirements
  - **Standard:** Keep 3-5 requirements (team size dependent)
  - **Enterprise:** Keep all AI-extracted requirements

**Example:**
```
PRD: "Build an MCP server for managing utilities and tools"

Prototype mode → 6 tasks (2 features + support tasks)
Standard mode  → 8 tasks (3-5 features + support tasks)
```

**Rationale:** For open-ended descriptions, the AI generates features based on best practices. Without user constraints, filtering prevents scope creep. Complexity mode acts as a **scope limiter**.

## Detection Logic

### Implementation Location
[src/ai/advanced/prd/advanced_parser.py:3950-4009](../../src/ai/advanced/prd/advanced_parser.py)

### Detection Algorithm

```python
def _detect_prompt_specificity(self, prd_content: str) -> str:
    """
    Detect if user provided explicit requirements or open-ended description.

    Returns "explicit" or "guided"
    """
    # Step 1: Check for explicit patterns
    explicit_patterns = [
        "create these",
        "create the following",
        "these tools:",
        "these features:",
        "requirements:",
        # ... more patterns
    ]

    has_explicit_pattern = any(
        pattern in prd_content.lower()
        for pattern in explicit_patterns
    )

    # Step 2: Count list-formatted lines
    list_lines = sum(
        1
        for line in lines
        if line.strip().startswith(("-", "*", "•"))
        or (line.strip()[0].isdigit() and "." in line[:5])
    )

    # Step 3: Determine mode
    has_list_structure = list_lines >= 3

    if has_explicit_pattern or has_list_structure:
        return "explicit"  # User knows what they want - keep ALL
    else:
        return "guided"    # AI-driven - apply filtering
```

## Filtering Behavior

### Implementation Location
[src/ai/advanced/prd/advanced_parser.py:3862-3930](../../src/ai/advanced/prd/advanced_parser.py)

### Filtering Algorithm

```python
def _filter_requirements_by_size(
    self,
    requirements: List[Dict[str, Any]],
    project_size: str,
    team_size: int,
    prd_content: str,
) -> List[Dict[str, Any]]:
    """Filter functional requirements based on project size and team capacity."""

    # Detect mode
    specificity = self._detect_prompt_specificity(prd_content)

    if specificity == "explicit":
        # User explicitly listed requirements - keep ALL
        return requirements  # NO FILTERING

    # Guided mode - apply capacity filtering
    if project_size in ["prototype", "mvp"]:
        filtered = requirements[:2]  # Only keep first 2
    elif project_size in ["standard", "small", "medium"]:
        max_reqs = min(len(requirements), max(3, team_size))
        filtered = requirements[:max_reqs]
    else:
        filtered = requirements  # Enterprise - keep all

    return filtered
```

## Empirical Test Results

### Explicit Mode Test Results

| Complexity | PRD Type | Requirements | Tasks Created | Breakdown |
|-----------|----------|--------------|---------------|-----------|
| Prototype | 10 numbered tools | All 10 kept | 23 | 6 design, 8 impl, 7 test, 2 infra |
| Standard  | 10 numbered tools | All 10 kept | 27 | 4 design, 12 impl, 9 test, 2 infra |
| Enterprise | 5 numbered tools | All 5 kept | 18 | Mixed |

**Observation:** Explicit requirements bypass filtering completely. Task count scales with number of explicit requirements.

### Guided Mode Test Results

| Complexity | PRD Type | Requirements | Tasks Created | Breakdown |
|-----------|----------|--------------|---------------|-----------|
| Prototype | Open-ended | 2 features (filtered) | 6 | 1 design, 2 impl, 1 test, 1 doc, 1 infra |
| Standard  | Open-ended | 3-5 features (filtered) | 8 | 2 design, 2 impl, 3 test, 1 doc |

**Observation:** Guided mode applies complexity filtering. Task count limited by complexity mode regardless of AI-extracted feature count.

## Task Count Formula

### Explicit Mode
```
Tasks = (# of explicit requirements) × (design + impl + test + infra factors)
      ≈ (# of requirements) × 2.3-2.7 expansion factor
```

### Guided Mode
```
Prototype:  ≈ 4-6 tasks  (2 features + support)
Standard:   ≈ 6-10 tasks (3-5 features + support)
Enterprise: ≈ 10+ tasks  (all features + support)
```

## Design Philosophy

### User Intent Preservation (Explicit Mode)
When a user says "Create these 10 tools", they **explicitly want 10 tools**. Filtering them down to 2-3 would violate their explicit request and undermine trust.

### AI-Guided Scope Management (Guided Mode)
For open-ended descriptions like "Build a task manager", the AI extracts features based on best practices. Without explicit user constraints, filtering prevents scope creep and ensures deliverable projects.

## Best Practices

### For Users

**When you want specific features:**
```markdown
✅ GOOD (Explicit Mode):
Create these 5 tools:
1. Authentication system
2. User profile management
3. Dashboard
4. Reporting
5. Notifications

Result: All 5 will be included
```

**When you want AI to determine scope:**
```markdown
✅ GOOD (Guided Mode):
Build a user management system with authentication and profiles

Prototype: 2 core features selected by AI
Standard:  3-5 features selected by AI
Enterprise: All features selected by AI
```

### For Developers

**Testing Explicit Mode:**
```bash
python dev-tools/examples/create_test_project.py prototype \
    "Create these tools: 1. ping 2. echo 3. time"
```

**Testing Guided Mode:**
```bash
python dev-tools/examples/create_test_project.py prototype \
    "Build an MCP server for utilities"
```

## Common Misconceptions

### ❌ Misconception 1
"Prototype mode always creates ≤3 tasks"

**Reality:** Only in guided mode. Explicit mode respects user's full list.

### ❌ Misconception 2
"Complexity mode controls scope"

**Reality:** Only in guided mode. In explicit mode, it controls quality/detail level.

### ❌ Misconception 3
"The system ignores my numbered list in prototype mode"

**Reality:** Numbered lists (≥3 items) trigger explicit mode, which **keeps all items**.

## Related Systems

- **[PRD Analysis](../systems/intelligence/prd-analysis.md):** How requirements are extracted
- **[Task Decomposition](../systems/project-management/54-hierarchical-task-decomposition.md):** How requirements become tasks
- **[Complexity Modes](../systems/project-management/38-natural-language-project-creation.md):** Definition of prototype/standard/enterprise

## Testing

See E2E test suite: `dev-tools/examples/test_requirement_filtering.py`

## Implementation History

- **Original Design:** Simple filtering by project size
- **Keyword Matching Approach (REMOVED):** Attempted to classify requirements by keywords (failed due to vocabulary mismatch)
- **Current Design:** Specificity detection + conditional filtering
