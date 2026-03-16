# PRD Requirement Filtering System

## Overview

The PRD Requirement Filtering System determines which extracted requirements are included in the final project plan based on **prompt specificity** and **complexity mode**. This system balances user intent preservation with AI-guided scope management.

## System Purpose

**Primary Goals:**
1. **Respect explicit user requirements** (don't filter what users explicitly ask for)
2. **Prevent scope creep** in AI-generated features (apply intelligent filtering)
3. **Align task count with team capacity** (prototype, standard, enterprise modes)

## Architecture

### Component Location

**Primary Implementation:**
- `src/ai/advanced/prd/advanced_parser.py`
  - `_detect_prompt_specificity()` (lines 3950-4009)
  - `_filter_requirements_by_size()` (lines 3862-3930)

**Related Components:**
- `src/ai/advanced/prd/prd_analyzer.py` - Extracts requirements from PRD
- `src/integrations/nlp_tools.py` - Uses filtered requirements for project creation

### Data Flow

```
User PRD
    ↓
PRD Analyzer (extracts requirements)
    ↓
Specificity Detector (explicit vs guided)
    ↓
    ├─→ [Explicit Mode] → Keep ALL requirements
    │
    └─→ [Guided Mode] → Filter by complexity
            ↓
        Filtered Requirements
            ↓
        Task Generation
```

## Specificity Detection

### Algorithm

The system analyzes the PRD content to determine if the user provided:
- **Explicit requirements:** Specific, numbered/bulleted list of features
- **Guided requirements:** Open-ended description for AI interpretation

### Detection Criteria

**Explicit Mode Triggers:**
1. **Pattern matching:** Keywords like "create these", "these tools:", "requirements:"
2. **List structure:** ≥3 numbered items (1., 2., 3.) or bulleted items (-, *, •)

**Guided Mode Default:**
If neither pattern matching nor list structure criteria are met, defaults to guided mode.

### Implementation

```python
def _detect_prompt_specificity(self, prd_content: str) -> str:
    """
    Detect if user provided explicit requirements or open-ended description.

    Parameters
    ----------
    prd_content : str
        The raw PRD text from the user

    Returns
    -------
    str
        "explicit" if user listed specific requirements
        "guided" if open-ended description
    """
    content_lower = prd_content.lower()

    # Check for explicit pattern keywords
    explicit_patterns = [
        "create these",
        "create the following",
        "these tools:",
        "these features:",
        "requirements:",
        "must have:",
        "should include:",
        "needs to have:",
    ]

    has_explicit_pattern = any(
        pattern in content_lower for pattern in explicit_patterns
    )

    # Count list-formatted lines
    lines = prd_content.split("\n")
    list_lines = sum(
        1
        for line in lines
        if line.strip().startswith(("-", "*", "•"))
        or (
            len(line.strip()) > 0
            and line.strip()[0].isdigit()
            and "." in line[:5]
        )
    )

    # Decision logic
    has_list_structure = list_lines >= 3

    if has_explicit_pattern or has_list_structure:
        return "explicit"
    else:
        return "guided"
```

### Edge Cases

**Threshold Choice (≥3 items):**
- **Rationale:** 1-2 items could be examples, not exhaustive lists
- **3+ items:** Strong signal of explicit enumeration

**Mixed Mode:**
- If PRD contains both explicit patterns AND open-ended text, explicit mode takes precedence
- Example: "Create these 3 tools: ... Also make it scalable" → Explicit mode

## Requirement Filtering

### Filtering Rules

| Mode | Specificity | Filtering Behavior |
|------|-------------|-------------------|
| Any | Explicit | **NO FILTERING** - Keep all requirements |
| Prototype | Guided | Keep first 2 requirements |
| Standard | Guided | Keep 3-5 requirements (team size dependent) |
| Enterprise | Guided | Keep all requirements |

### Implementation

```python
def _filter_requirements_by_size(
    self,
    requirements: List[Dict[str, Any]],
    project_size: str,
    team_size: int,
    prd_content: str,
) -> List[Dict[str, Any]]:
    """
    Filter functional requirements based on project size and team capacity.

    Parameters
    ----------
    requirements : List[Dict[str, Any]]
        Extracted functional requirements from PRD
    project_size : str
        Complexity mode: prototype, standard, enterprise
    team_size : int
        Number of agents/developers (affects standard mode)
    prd_content : str
        Original PRD text for specificity detection

    Returns
    -------
    List[Dict[str, Any]]
        Filtered requirements (or all if explicit mode)
    """
    original_count = len(requirements)

    # Detect if user provided explicit requirements
    specificity = self._detect_prompt_specificity(prd_content)

    if specificity == "explicit":
        # User explicitly listed requirements - keep ALL
        logger.info(
            f"User provided explicit requirements ({original_count} items), "
            f"keeping all regardless of project_size={project_size}"
        )
        return requirements  # NO FILTERING

    # Guided mode - AI features, apply capacity filtering
    if project_size in ["prototype", "mvp"]:
        # Minimal viable product - only core features
        filtered = requirements[:2]
    elif project_size in ["standard", "small", "medium"]:
        # Moderate scope - team capacity dependent
        max_reqs = min(len(requirements), max(3, team_size))
        filtered = requirements[:max_reqs]
    else:
        # Enterprise - comprehensive scope
        filtered = requirements

    logger.info(
        f"Filtered requirements from {original_count} to {len(filtered)} "
        f"for project_size={project_size}, team_size={team_size}"
    )

    return filtered
```

### Filtering Strategy

**Ordering Matters:**
Requirements are filtered by taking the **first N** items, so the ordering from PRD analysis is critical:
1. Core functional requirements (highest priority)
2. Enhanced features (medium priority)
3. Nice-to-have features (lowest priority)

The PRD analyzer uses AI to prioritize requirements before filtering occurs.

## Complexity Mode Semantics

### Dual Interpretation

The complexity mode has **different meanings** depending on specificity:

**Explicit Mode:**
- Complexity = **Quality/Detail Level**
- Prototype: Basic implementation of all explicit requirements
- Standard: Full implementation with moderate testing
- Enterprise: Comprehensive implementation with extensive testing/docs

**Guided Mode:**
- Complexity = **Scope Limiter**
- Prototype: Minimal feature set (2 features)
- Standard: Moderate feature set (3-5 features)
- Enterprise: Full feature set (all AI-extracted features)

### Empirical Task Counts

**Explicit Mode:**
```
Tasks ≈ (# explicit requirements) × 2.3-2.7

Examples:
  5 explicit tools → 12-14 tasks
  10 explicit tools → 23-27 tasks
```

**Guided Mode:**
```
Prototype:  ≈ 4-6 tasks
Standard:   ≈ 6-10 tasks
Enterprise: ≈ 10+ tasks
```

## Integration Points

### Input (PRD Analysis)

**From:** `src/ai/advanced/prd/prd_analyzer.py`

**Data Structure:**
```python
{
    "functional_requirements": [
        {
            "name": "User Authentication",
            "description": "...",
            "priority": "high",
            "complexity": "medium"
        },
        # ... more requirements
    ],
    "integration_requirements": [
        # Infrastructure, glue code, assembly requirements
    ]
}
```

**Note:** Only `functional_requirements` are filtered. Integration requirements are kept separately.

### Output (Task Generation)

**To:** `src/integrations/nlp_tools.py` → `NaturalLanguageProjectCreator`

**Filtered Requirements:**
```python
filtered_requirements = [
    # Subset of functional_requirements based on filtering rules
]

# Integration requirements added back
all_requirements = filtered_requirements + integration_requirements
```

## Validation and Testing

### Unit Tests

**Location:** `tests/unit/ai/test_prd_complexity_detection.py`

**Coverage:**
- Specificity detection accuracy
- Filtering behavior per complexity mode
- Edge cases (threshold boundaries, mixed content)

### Integration Tests

**Location:** `tests/integration/project_creation/test_create_project_regressions.py`

**Coverage:**
- End-to-end project creation with explicit requirements
- End-to-end project creation with guided requirements
- Complexity parameter propagation

### E2E Tests

**Location:** `dev-tools/examples/test_requirement_filtering.py`

**Scenarios:**
1. Prototype with 10 explicit tools → All 10 kept
2. Standard with 10 explicit tools → All 10 kept
3. Prototype with guided description → 2 features extracted
4. Standard with guided description → 3-5 features extracted

## Common Issues and Solutions

### Issue 1: Unexpected Filtering

**Symptom:** User lists 5 tools, but only 2 are created

**Diagnosis:**
- Check if list has ≥3 items (threshold)
- Check if explicit patterns are present
- Check PRD formatting (indentation can break detection)

**Solution:** Use numbered list (1., 2., 3.) with ≥3 items

### Issue 2: Too Many Tasks in Prototype

**Symptom:** Prototype mode creates 20+ tasks

**Diagnosis:**
- User provided explicit requirements (detected as explicit mode)
- All explicit requirements were kept
- Each requirement expanded to multiple tasks

**Solution:** This is expected behavior. Use guided mode for scope limiting.

### Issue 3: Keyword Matching Failure (Historical)

**Symptom:** Integration requirements not extracted during validator retries

**Root Cause:** Previous implementation used keyword matching to classify requirements as integration vs component. Vocabulary mismatch caused failures.

**Solution:** Removed keyword matching. Integration requirements now separated during PRD analysis, not during filtering.

## Performance Characteristics

**Time Complexity:**
- Specificity detection: O(n) where n = PRD length
- Filtering: O(m) where m = requirement count
- Overall: O(n + m) - linear

**Space Complexity:**
- O(m) for storing requirements

**Typical Performance:**
- Specificity detection: <10ms
- Filtering: <1ms
- Total overhead: <15ms per project creation

## Future Enhancements

### Planned Improvements

1. **Smart Requirement Bundling**
   - Group related explicit requirements into composite tasks
   - Reduce task explosion for large explicit lists

2. **Adaptive Thresholds**
   - Learn optimal filtering thresholds from project success rates
   - Adjust based on team velocity data

3. **Multi-Phase Filtering**
   - Phase 1: Core requirements (always included)
   - Phase 2: Enhanced features (complexity dependent)
   - Phase 3: Nice-to-have (enterprise only)

4. **User Feedback Loop**
   - Allow users to mark requirements as "must-have" vs "nice-to-have"
   - Improve detection accuracy based on user corrections

## Related Documentation

- **[Explicit vs Guided Requirements Concept](../../concepts/explicit-vs-guided-requirements.md)**
- **[PRD Analysis System](./prd-analysis-system.md)**
- **[Natural Language Project Creation](../project-management/38-natural-language-project-creation.md)**
- **[Hierarchical Task Decomposition](../project-management/54-hierarchical-task-decomposition.md)**

## Change History

| Date | Change | Reason |
|------|--------|--------|
| 2025-12-22 | Removed keyword matching filter | Vocabulary mismatch caused validator failures |
| 2025-12-22 | Added E2E test suite | Validate explicit vs guided behavior |
| 2025-12-22 | Created CLI testing tool | Easier manual testing of filtering |
