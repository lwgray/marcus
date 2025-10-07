# GitHub Issue: Clean AI-First Task Descriptions

## Title

Remove template boilerplate from task descriptions while preserving Design/Implement/Test methodology

---

## Labels

`enhancement`, `task-generation`, `user-experience`, `priority:high`

---

## Issue Description

### Problem

Task descriptions are currently 80% generic template boilerplate and only 20% AI-generated content (buried at the end). This makes it hard for users to quickly understand what a task is actually for.

**Example - Current state:**
```
Task: Design User Authentication

Description: Create architectural design and documentation for web application.
Research security requirements, create user flow diagrams, document authentication
patterns and session management approach. Plan security protocols and define user
account lifecycle. Deliverables: authentication flow diagrams, security
documentation, and API specifications. Goal: secure user access.

Specific requirement: Users must be able to register, log in, and log out of
the application using JWT tokens with 24-hour expiration...
```

**Problems:**
- First 400 characters are generic ("Create architectural design...")
- Actual requirement buried after boilerplate
- Specific details (JWT, 24-hour, email verification) often truncated
- User can't quickly scan tasks in Planka to understand project

---

### Proposed Solution

**Put AI-generated requirements FIRST, keep methodology in structure:**

```
Task: Design User Authentication

Description: Users must be able to register, log in, and log out of the
application using JWT tokens with 24-hour expiration and email verification.
```

**Benefits:**
- ✅ Immediately clear what to build
- ✅ Specific details prominent, not buried
- ✅ AI content preserved (currently gets truncated)
- ✅ Design/Implement/Test methodology still enforced via task names, labels, and instructions

---

## Current vs Proposed

### Metric Comparison

| Metric | Current | Proposed | Improvement |
|--------|---------|----------|-------------|
| Avg description length | 500 chars | 150 chars | 70% shorter |
| Template content | 80% | 0% | All meaningful |
| Position of first detail | Char 401 | Char 0 | Immediately visible |
| Detail preservation | ~40% | >80% | 2x better |
| User comprehension | Scan 400+ chars | Scan <150 chars | 3x faster |

### Test Results

When given detailed input:
```
Build a todo app with:
- JWT tokens with 24-hour expiration
- Email verification on registration
- Priority levels (low/medium/high)
- Archive after 30 days
- Dark mode toggle
- Keyboard shortcuts (Ctrl+N)
```

**Current:** Only 40% of details preserved (JWT, email verification, dark mode)
**Proposed:** >80% of details preserved (all major features)

---

## Technical Details

### Files to Modify

**Primary:**
- `src/ai/advanced/prd/advanced_parser.py` (lines 598-654, 1358-1650)
  - Modify `_generate_detailed_task()` to use AI descriptions directly
  - Remove/simplify template generation functions

**Secondary:**
- `src/integrations/ai_analysis_engine.py` (lines 148-181, 527-568)
  - Update AI prompt to put requirements first
  - Enhance fallback templates to reference actual requirement

### Methodology Preservation

The Design/Implement/Test pattern is **already enforced** in:
1. ✅ Task names ("Design X", "Implement X", "Test X")
2. ✅ Task labels (`type:design`, `type:implementation`, `type:testing`)
3. ✅ Task dependencies (Test depends on Implement depends on Design)
4. ✅ Agent instructions (AI guidance based on task type)

**No changes needed** to these mechanisms - they will continue to work.

---

## Implementation Plan

### Phase 1: Core Fix (4-6 hours)

**Task:** Clean up task description generation

```python
# In advanced_parser.py:_generate_detailed_task()

# OLD:
enhanced_details = await self._enhance_task_with_ai(...)
description = enhanced_details.get("description", "")  # Template + AI appended

# NEW:
relevant_req = self._find_matching_requirement(task_id, analysis)
description = relevant_req["description"]  # Pure AI content
```

**Deliverables:**
- [ ] Modified `_generate_detailed_task()` function
- [ ] Helper method `_find_matching_requirement()`
- [ ] Helper method `_extract_task_type()`
- [ ] Unit tests for clean descriptions

### Phase 2: Enhanced Instructions (2-3 hours)

**Task:** Ensure agent instructions provide methodology guidance

```python
# In ai_analysis_engine.py:task_instructions prompt

# NEW PROMPT:
"START WITH THE REQUIREMENT (from task.description).
Then add phase-appropriate guidance:
- DESIGN: Create diagrams, specs, documentation
- IMPLEMENT: Build code, write tests, follow standards
- TEST: Test scenarios, edge cases, coverage"
```

**Deliverables:**
- [ ] Updated AI instruction prompt
- [ ] Updated fallback instruction templates
- [ ] Tests for instruction generation

### Phase 3: Testing (3-4 hours)

**Deliverables:**
- [ ] Unit tests: `test_clean_task_descriptions.py`
- [ ] Integration tests: `test_end_to_end_descriptions.py`
- [ ] Manual testing with preview script
- [ ] Real project creation and validation

### Phase 4: Documentation (2 hours)

**Deliverables:**
- [ ] Updated architecture docs
- [ ] Updated user guide
- [ ] Updated flow diagrams
- [ ] Before/after examples

**Total:** 11-15 hours

---

## Testing Strategy

### Automated Tests

```python
# Unit test
async def test_design_task_uses_ai_description():
    """Design tasks should use AI requirement, not template."""
    task = await parser._generate_detailed_task(...)

    # Should contain AI requirement
    assert "register" in task.description.lower()

    # Should NOT contain template boilerplate
    assert "Create architectural design" not in task.description

# Integration test
async def test_detailed_input_preserves_specifics():
    """Detailed user input should appear in task descriptions."""
    result = await parser.parse_prd_to_tasks("Build todo with JWT 24-hour tokens...")

    auth_task = next(t for t in result.tasks if "auth" in t.name.lower())

    # Specific details should be visible early (not buried)
    assert "JWT" in auth_task.description[:200]
    assert "24-hour" in auth_task.description[:200]
```

### Manual Testing

```bash
# Test 1: Preview with short description
python scripts/preview_project_plan.py "Build a todo app with authentication" "todo"

# Expected: Clean descriptions, all AI content visible

# Test 2: Preview with detailed description
python scripts/preview_project_plan.py "Build todo app with JWT tokens (24-hour expiration), email verification, dark mode toggle, drag-and-drop reordering" "todo-detailed"

# Expected: All specific details prominent in descriptions, not truncated

# Test 3: Create real project
mcp__marcus__create_project(
    description="Build a blog with markdown support, authentication, and comments",
    project_name="test-blog"
)

# Expected: Task descriptions in Planka are clear and specific
```

---

## Success Criteria

### Must Have
- [ ] Task descriptions use AI content directly (no template boilerplate)
- [ ] Specific user details appear prominently (not buried or truncated)
- [ ] Design/Implement/Test methodology still enforced
- [ ] All existing tests pass
- [ ] New tests added with >80% coverage

### Should Have
- [ ] Task descriptions <200 characters on average (vs 500+ now)
- [ ] >80% of user-provided details preserved (vs 40% now)
- [ ] Agent instructions clearly explain methodology

### Nice to Have
- [ ] Feature flag for gradual rollout
- [ ] Metrics dashboard showing description quality
- [ ] User feedback mechanism

---

## Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Some tasks don't match AI requirements | Medium | Low | Keep simplified templates as fallback |
| AI descriptions too brief | Low | Medium | Validate min length, expand if needed |
| Agents miss methodology guidance | Medium | Low | Enhanced instructions make it clear |
| Backward compatibility issues | Low | Low | Only affects new projects |

---

## Rollback Plan

If issues arise:

**Option 1:** Git revert
```bash
git revert <commit-hash>
```

**Option 2:** Feature flag (implement before changes)
```python
USE_AI_FIRST_DESCRIPTIONS = os.getenv("USE_AI_FIRST_DESCRIPTIONS", "false")

if USE_AI_FIRST_DESCRIPTIONS == "true":
    # New clean approach
else:
    # Old template approach
```

---

## Dependencies

- None (self-contained changes)
- Optional: AI provider configured for enhanced instructions (fallback works without)

---

## Related Issues

- #XXX - Task description quality improvements
- #XXX - AI-generated content preservation
- #XXX - User experience in Planka board view

---

## Documentation

**Full implementation plan:** `docs/specifications/implementation-plan-ai-first-descriptions.md`

**Analysis documents:**
- `docs/diagrams/task-description-flow.md` - Current flow with problems highlighted
- `docs/diagrams/the-real-problem.md` - Evidence of template override issue
- `docs/diagrams/detail-preservation-test-results.md` - Test results showing 60% detail loss
- `docs/diagrams/how-context-preserved.md` - How agents still build correctly
- `docs/diagrams/instruction-generation-explained.md` - How instructions are templated

---

## Example: Before and After

### Before (Current)

**What user provides:**
```
Build a todo app with JWT authentication (24-hour expiration),
email verification, and dark mode toggle
```

**What appears in Planka:**
```
Task: Design User Authentication

Description: Create detailed UI/UX design for frontend application. Include
component hierarchy, design system, responsive layouts, and user interaction
patterns. Focus on achieving: Increase user engagement through an intuitive and
secure todo app. Define accessibility standards and usability requirements.
Specific requirement: Users must be able to register using their email and
password, and receive an email for verificati...
                                                                              ^^^
                                                                         TRUNCATED
```

**Analysis:**
- Generic template: 400 characters (first thing you see)
- Your details: Buried at character 401, then truncated
- JWT, 24-hour, email verification: Lost in truncation
- User must read 400+ chars to find actual requirement

### After (Proposed)

**What user provides:**
```
Build a todo app with JWT authentication (24-hour expiration),
email verification, and dark mode toggle
```

**What appears in Planka:**
```
Task: Design User Authentication

Description: Users must be able to register and login using JWT tokens
with 24-hour expiration and email verification.
```

**Analysis:**
- No template boilerplate: 0 characters
- Your details: First thing you see
- JWT, 24-hour, email verification: All visible
- User scans <100 chars to understand task

**Improvement:**
- ✅ 3x shorter
- ✅ 100% meaningful content
- ✅ Instantly clear
- ✅ No truncation

---

## Questions to Resolve

1. Should we add minimal phase prefix? ("Design: {requirement}" vs just "{requirement}")
2. Feature flag for gradual rollout or direct deployment?
3. Minimum description length validation? (expand if <50 chars)
4. Keep old template functions as fallback or remove entirely?

---

## Acceptance Criteria

### Code Quality
- [ ] All modified functions have docstrings
- [ ] Code follows project style guide
- [ ] No pylint/mypy errors
- [ ] Test coverage >80% for new/modified code

### Functionality
- [ ] Task descriptions use AI content directly
- [ ] No template boilerplate in descriptions
- [ ] User details preserved and prominent
- [ ] Design/Implement/Test methodology enforced

### Testing
- [ ] Unit tests pass (new and existing)
- [ ] Integration tests pass
- [ ] Manual testing successful
- [ ] Preview script shows clean descriptions

### Documentation
- [ ] Architecture docs updated
- [ ] User guide updated
- [ ] Code comments clear
- [ ] CHANGELOG.md entry added

---

## Timeline

- **Review & Approval:** 1-2 days
- **Implementation:** 2-3 days (11-15 hours)
- **Testing & Fixes:** 1 day
- **Documentation:** 0.5 day
- **PR Review:** 1-2 days

**Total:** ~5-8 days

---

## Assignees

- **Primary:** @lwgray
- **Reviewer:** TBD
- **QA:** TBD

---

## Checklist

### Before Starting
- [ ] Review implementation plan
- [ ] Discuss any questions with team
- [ ] Create feature branch `feature/ai-first-descriptions`
- [ ] Set up tracking issue

### During Implementation
- [ ] Follow TDD (write tests first)
- [ ] Commit regularly with clear messages
- [ ] Document as you go
- [ ] Test after each major change

### Before PR
- [ ] All tests passing
- [ ] Documentation updated
- [ ] CHANGELOG entry added
- [ ] Before/after examples included
- [ ] Self-review completed

### PR Review
- [ ] Code review by peer
- [ ] Manual testing by reviewer
- [ ] All feedback addressed
- [ ] Approved by maintainer

### After Merge
- [ ] Monitor for issues
- [ ] Update documentation site
- [ ] Announce in release notes
- [ ] Close related issues

---

## Notes

This change significantly improves user experience by making task descriptions clear and actionable, while maintaining the proven Design/Implement/Test methodology that ensures quality and coordination.

The implementation is low-risk because:
1. Methodology enforcement is unchanged (names, labels, dependencies)
2. Changes are isolated to description generation
3. Easy rollback available
4. Backward compatible (existing projects unaffected)

Expected impact:
- Users can scan tasks 3x faster
- Details are preserved 2x better
- Onboarding is easier (clear task descriptions)
- Agent effectiveness maintained (methodology in instructions)
