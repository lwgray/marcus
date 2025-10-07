# Implementation Plan: AI-First Task Descriptions

## Goal

Remove template noise from task descriptions while preserving Design/Implement/Test methodology.

**Current:** Task descriptions are 80% generic template, 20% AI content (buried at end)

**Target:** Task descriptions are 100% AI-generated content, methodology enforced through task structure

---

## Problem Summary

### What Users See Now (Planka Board)

```
Task: Design User Authentication

Description: Create architectural design and documentation for web application.
Research security requirements, create user flow diagrams, document authentication
patterns and session management approach. Plan security protocols and define user
account lifecycle. Deliverables: authentication flow diagrams, security
documentation, and API specifications. Goal: secure user access.

Specific requirement: Users must be able to register, log in, and log out of the
application using JWT tokens with 24-hour expiration and email verification...
```

**Problems:**
- First 400 characters are generic template
- Actual requirement buried after generic boilerplate
- User can't quickly see WHAT this task is for
- Details often truncated

### What Users Should See

```
Task: Design User Authentication

Description: Users must be able to register, log in, and log out of the
application using JWT tokens with 24-hour expiration and email verification.
```

**Benefits:**
- ✅ Immediately clear WHAT to build
- ✅ Specific details prominent, not buried
- ✅ AI-generated content preserved
- ✅ No template noise

---

## Solution Design

### Principle

**Separate WHAT from HOW:**
- **Task Description** = WHAT to build (AI content, no templates)
- **Task Name/Labels** = Phase identifier (Design/Implement/Test)
- **Agent Instructions** = HOW to approach (methodology guidance)

### Architecture

```
User Input
    ↓
AI Analysis (expands to detailed requirements)
    ↓
Task Creation
    ├─→ Name: "Design User Authentication" (methodology)
    ├─→ Description: AI requirement (clean)
    ├─→ Labels: ["type:design"] (methodology)
    └─→ Dependencies: [] (phase ordering)
    ↓
Agent Instructions (when assigned)
    └─→ Add Design/Implement/Test methodology guidance
```

---

## Implementation Steps

### Phase 1: Clean Up Task Descriptions (Core Fix)

#### 1.1 Modify `_generate_detailed_task`

**File:** `src/ai/advanced/prd/advanced_parser.py`
**Lines:** 598-654
**Changes:**

```python
async def _generate_detailed_task(
    self, task_id, epic_id, analysis, constraints, sequence
):
    """Generate task using AI description directly."""

    # Extract task type from task_id
    task_type = self._extract_task_type(task_id)  # "design", "implement", "test"

    # Find matching requirement from AI analysis
    relevant_req = self._find_matching_requirement(task_id, analysis)

    if relevant_req:
        # ✅ USE AI DESCRIPTION DIRECTLY
        base_description = relevant_req["description"]
        task_name = relevant_req["name"]

        # Add minimal phase prefix to description (optional)
        if task_type == "design":
            description = f"Design: {base_description}"
        elif task_type == "implement":
            description = f"Implement: {base_description}"
        elif task_type == "test":
            description = f"Test: {base_description}"
        else:
            description = base_description

    else:
        # Fallback for tasks without matching requirement
        description = f"{task_type.title()} {task_id.replace('_', ' ')}"
        task_name = task_id.replace("_", " ").title()

    # Create task
    task = Task(
        id=task_id,
        name=f"{task_type.title()} {task_name}",  # "Design User Authentication"
        description=description,  # ✅ Clean AI content
        # ... rest of task creation
    )

    return task
```

**Impact:**
- Task descriptions become clean AI content
- No template boilerplate
- Preserves all AI-analyzed requirements

#### 1.2 Remove Template Generation Functions (Optional)

**File:** `src/ai/advanced/prd/advanced_parser.py`
**Lines:** 1358-1650
**Action:** Can delete or simplify these functions

- `_generate_design_task`
- `_generate_implementation_task`
- `_generate_testing_task`
- `_generate_generic_task`

**Or** keep as fallback when no AI requirement matches.

**Recommendation:** Keep simplified versions as fallback only.

#### 1.3 Add Helper Methods

```python
def _extract_task_type(self, task_id: str) -> str:
    """Extract task type from task_id."""
    if "design" in task_id.lower():
        return "design"
    elif "implement" in task_id.lower():
        return "implement"
    elif "test" in task_id.lower():
        return "test"
    else:
        return "feature"

def _find_matching_requirement(
    self, task_id: str, analysis: PRDAnalysis
) -> Optional[Dict[str, Any]]:
    """Find the functional requirement that matches this task."""
    # Extract feature from task_id
    # e.g., "task_user_authentication_design" -> "user_authentication"
    feature_id = self._extract_feature_id(task_id)

    # Find matching requirement
    for req in analysis.functional_requirements:
        req_id = req.get("id", "").replace("-", "_")
        if req_id == feature_id:
            return req

    return None
```

---

### Phase 2: Enhance Agent Instructions (Methodology)

#### 2.1 Update AI Instruction Prompt

**File:** `src/integrations/ai_analysis_engine.py`
**Lines:** 148-181
**Changes:**

```python
"task_instructions": """You are Marcus, coordinating a development project.

TASK DATA:
{task}

AGENT DATA:
{agent}

The task description contains the AI-determined REQUIREMENT.
Your job is to add METHODOLOGY GUIDANCE based on the task type.

CRITICAL: Start with the requirement, then add appropriate phase guidance.

For DESIGN tasks:
Structure:
1. Requirement (from task.description)
2. Design approach:
   - Create architecture diagrams
   - Define API specifications
   - Document security/technical approach
   - Specify data models
3. Deliverables checklist
4. Next phase info

For IMPLEMENTATION tasks:
Structure:
1. Requirement (from task.description)
2. Implementation approach:
   - Review design specifications
   - Build core functionality
   - Write tests alongside code
   - Follow coding standards
3. Deliverables checklist
4. Integration notes

For TESTING tasks:
Structure:
1. Requirement (from task.description)
2. Testing approach:
   - Test happy paths
   - Test edge cases
   - Test error scenarios
   - Achieve 80%+ coverage
3. Deliverables checklist
4. Quality gates

Format as clear, actionable markdown.
START WITH THE REQUIREMENT - make it prominent!
Add phase guidance AFTER the requirement.
"""
```

**Impact:**
- AI instructions will put requirement FIRST
- Add methodology guidance appropriate to phase
- Keep Design/Implement/Test structure clear

#### 2.2 Update Fallback Templates

**File:** `src/integrations/ai_analysis_engine.py`
**Lines:** 527-568
**Changes:**

Make fallback templates start with task description:

```python
if task_type == "design":
    implementation_steps = f"""2. **Design Approach**
   Based on the requirement: "{task.description[:100]}..."

   Create:
   - Architecture diagrams showing the design
   - API specifications for the feature
   - Security/technical documentation
   - Data model definitions"""
```

**Impact:**
- Even fallback templates reference the actual requirement
- Less generic
- Requirement stays prominent

---

### Phase 3: Testing & Validation

#### 3.1 Update Preview Script

**File:** `scripts/preview_project_plan.py`
**Changes:** Already works, will show cleaner descriptions automatically

**Test:**
```bash
python scripts/preview_project_plan.py "Build todo app with JWT auth" "todo"
cat data/diagnostics/project_preview.md
```

**Expected:** Task descriptions should be AI requirements, not template boilerplate

#### 3.2 Update Diagnostic Script

**File:** `scripts/diagnose_task_descriptions.py`
**Changes:** None needed, will show improved descriptions

**Test:**
```bash
# After creating project
python scripts/diagnose_task_descriptions.py
```

**Expected:** No more mismatches between names and descriptions

#### 3.3 Create Comparison Test

**New File:** `scripts/compare_old_vs_new_descriptions.py`

```python
"""Compare old template-based vs new AI-first descriptions."""

import asyncio
from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser, ProjectConstraints

async def compare():
    parser = AdvancedPRDParser()
    constraints = ProjectConstraints(team_size=1, deployment_target='local')

    description = "Build a todo app with JWT authentication, CRUD operations, and filtering"

    result = await parser.parse_prd_to_tasks(description, constraints)

    print("NEW AI-FIRST DESCRIPTIONS:")
    print("=" * 80)
    for task in result.tasks[:5]:
        print(f"\nTask: {task.name}")
        print(f"Description: {task.description}")
        print()

        # Check if clean (no template boilerplate)
        template_markers = [
            "Create architectural design",
            "Develop responsive UI components",
            "Research security requirements"
        ]

        has_template = any(marker in task.description for marker in template_markers)

        if has_template:
            print("  ❌ Still has template boilerplate")
        else:
            print("  ✅ Clean AI description")

asyncio.run(compare())
```

---

### Phase 4: Documentation Updates

#### 4.1 Update User-Facing Docs

**Files to Update:**
- `README.md` - Mention clean task descriptions
- `docs/user-guide.md` - Explain task structure
- `docs/task-descriptions.md` - Document new format

#### 4.2 Update Developer Docs

**Files to Update:**
- `docs/architecture/task-generation.md` - Document new flow
- `docs/diagrams/task-description-flow.md` - Update diagram
- `CONTRIBUTING.md` - Note changes for contributors

---

## Testing Plan

### Unit Tests

**New File:** `tests/unit/ai/test_clean_task_descriptions.py`

```python
"""Test that task descriptions use AI content without templates."""

import pytest
from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser

@pytest.mark.asyncio
async def test_design_task_uses_ai_description():
    """Design tasks should use AI requirement, not template."""
    parser = AdvancedPRDParser()

    # Mock AI analysis with specific requirement
    analysis = create_mock_analysis(
        requirement="Users must register, login, and logout"
    )

    task = await parser._generate_detailed_task(
        "task_user_auth_design", "epic_auth", analysis, constraints, 1
    )

    # Should contain AI requirement
    assert "register" in task.description.lower()
    assert "login" in task.description.lower()
    assert "logout" in task.description.lower()

    # Should NOT contain template boilerplate
    assert "Create architectural design" not in task.description
    assert "Research security requirements" not in task.description

@pytest.mark.asyncio
async def test_implementation_task_uses_ai_description():
    """Implementation tasks should use AI requirement, not template."""
    # Similar test for implementation tasks
    pass

@pytest.mark.asyncio
async def test_test_task_uses_ai_description():
    """Test tasks should use AI requirement, not template."""
    # Similar test for test tasks
    pass
```

### Integration Tests

**New File:** `tests/integration/test_end_to_end_descriptions.py`

```python
"""Test full flow from user input to clean descriptions."""

@pytest.mark.asyncio
async def test_detailed_input_preserves_specifics():
    """Detailed user input should appear in task descriptions."""
    parser = AdvancedPRDParser()

    detailed_input = """
    Build todo app with:
    - JWT tokens with 24-hour expiration
    - Email verification on registration
    - Dark mode toggle
    - Drag-and-drop reordering
    """

    result = await parser.parse_prd_to_tasks(detailed_input, constraints)

    # Find auth task
    auth_task = next(t for t in result.tasks if "auth" in t.name.lower())

    # Should contain specific details
    assert "JWT" in auth_task.description
    assert "24-hour" in auth_task.description
    assert "email verification" in auth_task.description

    # Should NOT be buried in template
    # (Check it appears in first 200 chars)
    assert "JWT" in auth_task.description[:200]
```

### Manual Testing

```bash
# Test 1: Short description
python scripts/preview_project_plan.py "Build a todo app" "todo"
# Verify: Descriptions are clean and clear

# Test 2: Detailed description
python scripts/preview_project_plan.py "Build todo app with JWT auth (24-hour expiration), email verification, dark mode, drag-and-drop" "todo-detailed"
# Verify: All details appear prominently in descriptions

# Test 3: Create real project
mcp__marcus__create_project(
    description="Build a todo app with authentication",
    project_name="test-todo"
)
# Verify in Planka: Task descriptions are readable and specific
```

---

## Rollback Plan

If issues arise, changes can be reverted easily:

### Quick Rollback

**Option 1:** Git revert
```bash
git revert <commit-hash>
```

**Option 2:** Feature flag (add before implementing)

```python
# In advanced_parser.py
USE_AI_FIRST_DESCRIPTIONS = os.getenv("USE_AI_FIRST_DESCRIPTIONS", "false").lower() == "true"

if USE_AI_FIRST_DESCRIPTIONS:
    # New clean description approach
    description = relevant_req["description"]
else:
    # Old template approach
    enhanced_details = await self._enhance_task_with_ai(...)
    description = enhanced_details.get("description", "")
```

---

## Success Metrics

### Quantitative

1. **Description clarity:** <50 characters to first specific detail (vs >400 now)
2. **Detail preservation:** >80% of user-provided details visible (vs ~40% now)
3. **Template ratio:** <20% template content in descriptions (vs 80% now)

### Qualitative

1. **User feedback:** Can users quickly understand what each task is for?
2. **Agent effectiveness:** Do agents produce correct implementations?
3. **Readability:** Are task descriptions easier to read in Planka?

### Test Coverage

- Unit tests: >80% coverage for modified functions
- Integration tests: Full flow from input to task creation
- Manual testing: Real projects with various complexity levels

---

## Timeline Estimate

- **Phase 1 (Core Fix):** 4-6 hours
  - Modify `_generate_detailed_task`: 2 hours
  - Add helper methods: 1 hour
  - Test basic functionality: 1-2 hours
  - Fix any issues: 1 hour

- **Phase 2 (Instructions):** 2-3 hours
  - Update AI prompt: 1 hour
  - Update fallback templates: 30 min
  - Test instruction generation: 1-1.5 hours

- **Phase 3 (Testing):** 3-4 hours
  - Write unit tests: 1.5 hours
  - Write integration tests: 1 hour
  - Manual testing: 1-1.5 hours

- **Phase 4 (Documentation):** 2 hours
  - Update docs: 1.5 hours
  - Review and polish: 30 min

**Total:** 11-15 hours

---

## Risk Assessment

### Low Risk

- **Methodology preserved:** Task names, labels, dependencies unchanged
- **Isolated changes:** Only affects task description generation
- **Easy rollback:** Can revert or use feature flag
- **Backward compatible:** Existing projects unaffected

### Potential Issues

1. **Missing requirements:** Some tasks might not match AI requirements
   - **Mitigation:** Keep simplified templates as fallback

2. **Description too short:** Some AI descriptions might be very brief
   - **Mitigation:** Validate minimum description length, expand if needed

3. **Agent confusion:** Agents might miss methodology guidance
   - **Mitigation:** Enhanced instructions make methodology clear

---

## Dependencies

### Required

- None - all changes are self-contained

### Optional

- AI provider configured (for enhanced instructions)
- If AI unavailable, fallback templates still work

---

## Next Steps

1. **Review this plan** - Get approval on approach
2. **Create feature branch** - `feature/ai-first-descriptions`
3. **Implement Phase 1** - Core description cleanup
4. **Test thoroughly** - Verify clean descriptions work
5. **Implement Phase 2** - Enhanced instructions
6. **Full testing** - Unit + integration + manual
7. **Documentation** - Update all relevant docs
8. **Create PR** - With before/after examples
9. **Deploy** - Merge to main after approval

---

## Appendix: Example Before/After

### Before (Current)

```
Task: Design User Authentication

Description: Create detailed UI/UX design for frontend application. Include
component hierarchy, design system, responsive layouts, and user interaction
patterns. Focus on achieving: Increase user engagement through an intuitive and
secure todo app. Define accessibility standards and usability requirements.
Specific requirement: Users must be able to register, log in, and log out of
the application using JWT tokens with 24-hour expiration and email verification...
```

**Analysis:**
- Word count: 72 words
- Template content: 57 words (79%)
- AI content: 15 words (21%)
- First specific detail: Position 401 (character count)

### After (Proposed)

```
Task: Design User Authentication

Description: Users must be able to register, log in, and log out of the
application using JWT tokens with 24-hour expiration and email verification.
```

**Analysis:**
- Word count: 24 words
- Template content: 0 words (0%)
- AI content: 24 words (100%)
- First specific detail: Position 0 (character count)

**Improvement:**
- 3x shorter
- 100% meaningful content
- Instantly clear what to build
- All details prominent
