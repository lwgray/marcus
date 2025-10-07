# AI-First Task Descriptions

**Status:** ✅ Implemented (Phase 1-3 Complete)
**Version:** 1.0
**Last Updated:** 2025-10-06

## Overview

Marcus now generates clean, AI-first task descriptions that preserve user specifics instead of using template boilerplate. This improvement results in more readable, actionable tasks that agents can execute with better context.

## The Problem (Before)

Previously, task descriptions were 80% template boilerplate and 20% actual requirements:

```markdown
### Task: Design User Authentication

**Description:**
Research and design architecture for web application. Create documentation
defining approach, patterns, and specifications. Plan component structure and
integration points. Deliverables: design documentation, architectural diagrams,
and technical specifications. Goal: Increase user engagement by providing a
simple, secure todo app.

[400+ chars of generic template]

Specific requirement: Users should be able to register, login, and logout
using JWT tokens that expire after 24 hours.
```

### Issues:
- ❌ Generic templates obscure actual requirements
- ❌ User specifics ("24 hours", "JWT") buried at the end
- ❌ Descriptions too long (500-600 chars)
- ❌ Poor signal-to-noise ratio for agents

## The Solution (After)

Task descriptions now use clean, AI-generated content directly:

```markdown
### Task: Design User Authentication

**Description:**
Users should be able to register, login, and logout using JWT tokens that
expire after 24 hours.
```

### Benefits:
- ✅ Clean, concise descriptions (< 200 chars)
- ✅ User specifics front and center
- ✅ Agents get clear, actionable requirements
- ✅ Better readability on task boards

## How It Works

### Architecture

```
User Input
  ↓
AI Analysis (parse_prd_to_tasks)
  ↓
Functional/Non-Functional Requirements
  ↓
Task Generation (_generate_detailed_task)
  ↓
Match Requirement (_find_matching_requirement)
  ↓
Use AI Description Directly ✅
  (no template overlay)
```

### Key Components

1. **`_extract_task_type(task_id)`**
   - Extracts "design", "implement", or "test" from task ID
   - Example: `task_user_login_design` → `"design"`

2. **`_find_matching_requirement(task_id, analysis)`**
   - Matches task to its AI-generated requirement
   - Handles both functional and non-functional requirements
   - Example: `task_user_login_design` → User Login requirement

3. **`_generate_task_labels(task_type, feature_name, analysis)`**
   - Generates labels to preserve methodology
   - Adds technology/domain labels (api, auth, database, etc.)
   - Example: `["design", "authentication", "user-management"]`

### Methodology Preservation

The Design/Implement/Test methodology is preserved through:

**Task Names:**
- "Design User Authentication"
- "Implement User Authentication"
- "Test User Authentication"

**Labels:**
- `design`, `implement`, `test`
- Technology: `api`, `database`, `frontend`
- Domain: `authentication`, `user-management`

**Dependencies:**
- Design → Implement → Test dependency chain
- Automatically inferred by AI

## Examples

### Example 1: Simple Todo App

**User Input:**
```
Build a todo app with user login using JWT tokens that expire after 24 hours
```

**Generated Tasks:**

| Task Name | Description |
|-----------|-------------|
| Design User Registration | Allow users to register with an email and password. |
| Implement User Registration | Allow users to register with an email and password. |
| Design User Login | Enable users to log in using their registered email and password, receiving a JWT token upon successful authentication. |
| Implement JWT Token Expiration | Ensure JWT tokens expire after 24 hours from issue. |

### Example 2: E-Commerce Platform

**User Input:**
```
Build an e-commerce platform with:
- User authentication using OAuth2
- Product catalog with search and filtering
- Shopping cart with real-time updates
- Payment processing via Stripe
```

**Generated Tasks:**

| Task Name | Description |
|-----------|-------------|
| Design OAuth2 Authentication | Implement user authentication using OAuth2 protocol for secure login. |
| Implement Product Search | Enable users to search products by name, category, and price range. |
| Design Shopping Cart | Create real-time shopping cart that updates instantly when users add/remove items. |
| Implement Stripe Payment | Integrate Stripe for secure payment processing with card validation. |

## Before/After Comparison

### Before (Template-Based)

```
Task: Implement User Authentication
Priority: medium
Estimated: 16 hours

Description:
Build core functionality for web application. Implement business logic, data
processing, user interfaces, and system integrations. Using: Use JWT for
authentication, Token expiration: 24 hours. Include proper error handling,
logging, and performance optimization. Addresses requirement: Users should be
able to register, login, and logout using JWT tokens that expire after 24 hours.

[500+ chars total, 80% template boilerplate]
```

### After (AI-First)

```
Task: Implement User Authentication
Priority: medium
Estimated: 16 hours

Description:
Users should be able to register, login, and logout using JWT tokens that
expire after 24 hours.

[120 chars total, 100% relevant content]
```

## Technical Implementation

### Code Location

**File:** `src/ai/advanced/prd/advanced_parser.py`

**Key Method:** `_generate_detailed_task()`

```python
async def _generate_detailed_task(
    self, task_id, epic_id, analysis, constraints, sequence
) -> Task:
    """Generate a detailed task using AI descriptions directly."""

    # Extract task type (design/implement/test)
    task_type = self._extract_task_type(task_id)

    # Find matching AI requirement
    relevant_req = self._find_matching_requirement(task_id, analysis)

    if relevant_req:
        # ✅ USE AI DESCRIPTION DIRECTLY (no templates!)
        description = relevant_req.get("description", "")
        feature_name = relevant_req.get("name", "")
        task_name = f"{task_type.title()} {feature_name}"
    else:
        # Fallback to template approach if no match
        ...

    # Generate labels for methodology
    labels = self._generate_task_labels(task_type, feature_name, analysis)

    return Task(
        name=task_name,
        description=description,  # Clean AI content!
        labels=labels,
        ...
    )
```

### Fallback Behavior

If no AI requirement matches (edge case):
- Falls back to original template-based approach
- Logs warning for debugging
- Ensures system continues to function

## Testing

### Test Coverage

**Unit Tests (19 tests):**
- `test_extract_task_type`: 5 tests
- `test_find_matching_requirement`: 5 tests
- `test_generate_task_labels`: 6 tests
- Integration scenarios: 3 tests

**Integration Tests (7 tests):**
- Clean descriptions verification
- User specifics preservation
- Description conciseness
- Methodology preservation
- Complex project handling
- Priority assignment

**Results:**
- ✅ All 26 tests pass
- ✅ Unit tests: 0.17s
- ✅ Integration tests: 78s

### Running Tests

```bash
# Unit tests only
pytest tests/unit/ai/test_advanced_parser_ai_first.py -v

# Integration tests
pytest tests/integration/e2e/test_ai_first_descriptions.py -v

# All AI-first tests
pytest -k "ai_first" -v
```

## Migration Guide

### For Users

No changes required! The AI-first descriptions work automatically when you create projects:

```python
# Using MCP
await mcp__marcus__create_project(
    description="Your project description here",
    project_name="MyProject"
)

# Using direct API
result = await parser.parse_prd_to_tasks(description, constraints)
```

### For Developers

If you're modifying task generation:

1. **Requirement Format:** Ensure AI requirements have `id`, `name`, and `description` fields
2. **Task ID Format:** Use `task_{requirement_id}_{phase}` or `nfr_task_{requirement_id}`
3. **Labels:** Call `_generate_task_labels()` to preserve methodology

## Performance

### Metrics

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Avg Description Length | 520 chars | 180 chars | -65% |
| Template Boilerplate | 80% | 0% | -100% |
| User Specifics Visible | Bottom | Top | ✅ |
| Agent Clarity | Medium | High | ✅ |

### AI Calls

No additional AI calls required! Uses existing PRD analysis.

## Future Enhancements

### Planned

- [ ] Phase 4: Documentation updates (in progress)
- [ ] Add subtasks and acceptance criteria to Task model
- [ ] Support for custom description templates per project type
- [ ] Multi-language description support

### Ideas

- AI-generated acceptance criteria in descriptions
- Task description quality scoring
- Auto-summarization for long requirements

## Related

- **Implementation Plan:** `docs/specifications/implementation-plan-ai-first-descriptions.md`
- **GitHub Issue:** #57
- **PR:** feature/task-description branch
- **Original Analysis:** `docs/diagrams/the-real-problem.md`

## Support

For questions or issues:
- Review test examples in `tests/unit/ai/test_advanced_parser_ai_first.py`
- Check integration tests for real-world scenarios
- See `scripts/preview_project_plan.py` for preview tool
