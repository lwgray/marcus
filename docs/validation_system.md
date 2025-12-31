# Feature Completeness Validation System

## Overview

The Feature Completeness Validation System is Marcus's built-in quality gate that prevents incomplete implementations from being marked as complete. It validates implementation tasks against their acceptance criteria before allowing task completion.

**Problem Solved**: In previous Marcus versions, agents could mark tasks as "completed" even when features were missing, partially implemented, or contained placeholder code. This led to issues like empty files, missing integrations, and incomplete features making it into the codebase.

**Solution**: Automatic validation that:
- Discovers source code by scanning the project directory
- Verifies each acceptance criterion has working code evidence
- Provides specific remediation guidance when validation fails
- Creates blockers only when agents get stuck in retry loops

## Key Concepts

### 1. Source Code Discovery

**How It Works**: Instead of relying on agents to report what they built, Marcus automatically discovers implementation files by scanning the project directory.

**Discovery Process**:
1. Get `project_root` from workspace manager or logged artifacts
2. Recursively scan directory for source files (`.py`, `.js`, `.html`, `.css`, etc.)
3. Filter out non-implementation directories (`docs/`, `node_modules/`, `.git/`, etc.)
4. Read complete file contents to verify features
5. Detect empty files (0 bytes) and placeholder code (TODO, FIXME, etc.)

**Why This Matters**: Agents create source files during implementation but don't always log them as artifacts. Discovery ensures Marcus validates what was actually built, not just what was documented.

### 2. Validation Scope

**What Gets Validated**:
- **Implementation tasks**: Tasks labeled with `implement`, `build`, `create`, `develop`
- Tasks with `completion_criteria` defined (acceptance criteria)

**What Gets Skipped**:
- **Design tasks**: Labeled with `design`, `plan`, `architecture`
- **Testing tasks**: QA and testing work
- **Documentation tasks**: Writing docs
- Tasks without completion criteria

**Task Filter**: `should_validate_task()` in [task_filter.py](../src/ai/validation/task_filter.py) determines eligibility.

### 3. Evidence Gathering

**Three Types of Evidence**:

1. **Source Files** (discovered automatically):
   - Complete file content (up to 1MB per file)
   - File size metadata (catches empty files)
   - Placeholder detection (TODO, FIXME, NotImplementedError)
   - File modification time (for optimization)

2. **Design Artifacts** (logged via `log_artifact()`):
   - API specifications
   - Architecture docs
   - Design documents
   - Provide context for what SHOULD be built

3. **Decisions** (retrieved via `get_task_context()`):
   - Architectural choices from this task
   - Decisions from dependency tasks (e.g., design phase)
   - Decisions from sibling tasks (parallel work)
   - Provide context for WHY certain choices were made

**Evidence Bundle**: All three types packaged as `WorkEvidence` for AI validation.

### 4. Criterion-by-Criterion Validation

**AI Validation Prompt**:
```
TASK: Implement warranty form
DESCRIPTION: Create HTML form with validation

ACCEPTANCE CRITERIA (ALL must be met):
1. Form includes fields for name, email, phone
2. Fields are properly validated
3. Professional CSS styling applied

EVIDENCE - DISCOVERED SOURCE FILES:
Source File: warranty-form.html (3200 bytes)
  Content: <form>...</form>

Source File: validation.js (2400 bytes)
  Content: function validateEmail(email) {...}

Source File: styles.css (4800 bytes)
  Content: .form-container {...}

YOUR JOB: For EACH acceptance criterion, verify it was FULLY implemented in SOURCE CODE.
```

**Validation Rules**:
- ✅ **PASS** only if ALL criteria have working code
- ❌ **FAIL** if ANY criterion lacks implementation
- ❌ **FAIL** if source code contains TODO/FIXME for required features
- ❌ **FAIL** if source files are empty (0 bytes)
- ❌ **FAIL** if obvious integrations missing (e.g., form exists but validation.js has no functions)

### 5. Hybrid Remediation Strategy

**Two-Tier Failure Handling**:

#### First Failure: Return Response
- Task stays `IN_PROGRESS`
- Agent receives specific issues with remediation
- Agent can fix and retry completion
- **Goal**: Give agent a chance to fix issues autonomously

**Example Response**:
```json
{
  "success": false,
  "status": "validation_failed",
  "issues": [
    {
      "severity": "critical",
      "issue": "Phone number validation not implemented",
      "evidence": "Code has <input name='phone'> but validation.js has no validatePhone()",
      "remediation": "Add validatePhone() to check format /^\\d{3}-\\d{3}-\\d{4}$/",
      "criterion": "Fields are properly validated"
    }
  ],
  "message": "Task did not pass validation. Fix issues and retry completion."
}
```

#### Retry with Same Issues: Create Blocker
- Detected via issue fingerprinting (MD5 hash of severity + criterion + issue)
- Marcus creates blocker with detailed remediation
- Agent sees blocker guidance and decides next steps
- **Goal**: Escalate when agent is stuck in a loop

**Blocker Format**:
```
🚫 VALIDATION BLOCKER - REPEATED FAILURES

You've attempted to complete this task multiple times with the same issues.
This suggests you may be stuck. Please carefully review the issues below:

1. ❌ Phone number validation not implemented
   SEVERITY: CRITICAL
   EVIDENCE: Code has <input name='phone'> but no validatePhone()
   REMEDIATION: Add validatePhone() to check format /^\\d{3}-\\d{3}-\\d{4}$/
   CRITERION: Fields are properly validated

IMPORTANT:
- READ the remediation carefully - it tells you EXACTLY what to fix
- Don't rebuild everything - fix the SPECIFIC issues listed above
- If you're unsure, ask for help understanding the requirements
```

### 6. Issue Fingerprinting

**Purpose**: Detect when agent retries with identical issues (stuck in loop).

**Fingerprint Calculation**:
```python
def get_fingerprint(self) -> str:
    """Generate stable fingerprint for issue comparison."""
    content = f"{self.severity.value}|{self.criterion}|{self.issue}"
    return hashlib.md5(content.encode()).hexdigest()
```

**Why Not Include Evidence/Remediation**: These may change slightly between runs (e.g., file sizes update), but the core issue remains the same. Fingerprint focuses on WHAT is missing, not HOW it's described.

**Retry Detection**:
```python
# First attempt
tracker.record_attempt(task_id, validation_result_1)

# Second attempt
is_retry = tracker.is_retry_with_same_issues(task_id, validation_result_2)
# Returns True if fingerprints match (same issues)
```

### 7. Context Isolation

**LLM Separation**: WorkAnalyzer has its own dedicated LLM instance separate from Marcus's task coordination LLM.

**Why This Matters**:
- **Marcus LLM**: Focused on task assignment, dependency inference, agent coordination
- **Validation LLM**: Focused on code analysis, feature completeness

**Benefits**:
- Validation prompts don't pollute Marcus's coordination context
- Each LLM maintains independent conversation history
- Different system prompts for different purposes
- Prevents validation details from affecting task assignment decisions

## System Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│ report_task_progress(agent_id, task_id, status="completed") │
└─────────────────────────────────────────────────────────────┘
                         │
                         ↓
             ┌─────────────────────┐
             │ should_validate_task │  ← Task Filter
             │ (Implementation?)    │
             └─────────────────────┘
                         │
                         ↓ YES
             ┌─────────────────────────┐
             │ _validate_task_completion │
             └─────────────────────────┘
                         │
                         ↓
             ┌───────────────────────────┐
             │ WorkAnalyzer.gather_evidence │
             │ • Discover source files      │
             │ • Get design artifacts       │
             │ • Retrieve decisions         │
             └───────────────────────────┘
                         │
                         ↓
             ┌───────────────────────────────────┐
             │ WorkAnalyzer.validate_implementation │
             │ • Build AI prompt                    │
             │ • Call dedicated validation LLM      │
             │ • Parse response                     │
             └───────────────────────────────────┘
                         │
           ┌─────────────┴──────────────┐
           ↓                            ↓
      VALIDATION                  VALIDATION
       PASSED                      FAILED
           ↓                            ↓
    Mark task DONE        ┌──────────────────────┐
                         │ RetryTracker.record   │
                         │ Is retry with same?   │
                         └──────────────────────┘
                                  │
                    ┌─────────────┴──────────────┐
                    ↓                            ↓
              First Failure              Retry with Same Issues
                    ↓                            ↓
        Return failure response      Create blocker with
        (agent can retry)             detailed remediation
```

### File Structure

```
src/ai/validation/
├── __init__.py
├── validation_models.py      # Data structures (ValidationResult, WorkEvidence, etc.)
├── work_analyzer.py          # Core validation engine
├── retry_tracker.py          # Retry detection and fingerprinting
└── task_filter.py            # Task eligibility filter

src/marcus_mcp/tools/task.py
├── _validate_task_completion()      # Helper: Run validation
├── _handle_validation_failure()     # Helper: Hybrid remediation
└── _format_blocker_description()    # Helper: Format blocker text
```

### Integration Points

**Entry Point**: `report_task_progress()` in [task.py:1360-1383](../src/marcus_mcp/tools/task.py#L1360-L1383)

```python
# VALIDATION GATE
if status == "completed":
    task = next((t for t in state.project_tasks if t.id == task_id), None)

    if task and should_validate_task(task):
        try:
            validation_result = await _validate_task_completion(
                task, agent_id, state
            )

            if not validation_result.passed:
                return await _handle_validation_failure(
                    task, agent_id, validation_result, state
                )
        except Exception as e:
            logger.error(f"Validation system error: {e}")
            # Allow completion on validation system failure
```

**Module-Level Singletons**:
```python
# Lazy initialization for validation components
_work_analyzer: Optional[Any] = None
_retry_tracker: Optional[Any] = None
```

**Lazy Imports** (to avoid circular dependencies):
```python
# Import validation modules inside functions
from src.ai.validation.work_analyzer import WorkAnalyzer
from src.ai.validation.retry_tracker import RetryTracker
```

## Usage Examples

### Example 1: Warranty Form Implementation

**Task**:
- Name: Implement warranty form
- Labels: `implement`, `frontend`
- Acceptance Criteria:
  1. Form includes fields for name, email, phone
  2. Fields are properly validated
  3. Professional CSS styling applied

**Agent Implementation** (incomplete - missing phone validation):
```bash
# Agent creates files
warranty-form.html   # Has all 3 input fields
validation.js        # validateEmail() only (NO validatePhone!)
styles.css           # Basic styling
```

**Validation Process**:
1. Marcus discovers 3 source files
2. Reads complete contents
3. AI analyzes against criteria:
   - ✅ Criterion 1: All fields present in HTML
   - ❌ Criterion 2: Phone validation missing in JS
   - ✅ Criterion 3: CSS styling exists

**Validation Result** (FAIL):
```json
{
  "success": false,
  "status": "validation_failed",
  "issues": [
    {
      "severity": "critical",
      "issue": "Phone number validation not implemented",
      "evidence": "Code has <input name='phone'> but validation.js has no validatePhone()",
      "remediation": "Add validatePhone() to check format /^\\d{3}-\\d{3}-\\d{4}$/",
      "criterion": "Fields are properly validated"
    }
  ]
}
```

**Agent Fixes**:
```javascript
// Agent adds to validation.js
function validatePhone(phone) {
  return /^\d{3}-\d{3}-\d{4}$/.test(phone);
}
```

**Agent Retries**: Reports "completed" again → Validation **PASSES** → Task marked DONE ✅

### Example 2: Empty File Detection (Minesweeper Audio Bug)

**Task**:
- Name: Add audio feedback to Minesweeper
- Acceptance Criteria:
  1. Click sound on cell reveal
  2. Win sound on game completion
  3. Loss sound on mine click

**Agent Implementation** (empty audio files):
```bash
# Agent creates files
audio/click.mp3   # 0 bytes (EMPTY!)
audio/win.mp3     # 0 bytes (EMPTY!)
audio/loss.mp3    # 0 bytes (EMPTY!)
game.js           # Has audio playback code
```

**Validation Process**:
1. Marcus discovers 4 files
2. Detects 3 empty files (size_bytes == 0)
3. AI fails validation:

**Validation Result** (FAIL):
```json
{
  "success": false,
  "status": "validation_failed",
  "issues": [
    {
      "severity": "critical",
      "issue": "Empty audio files - no sound will play",
      "evidence": "audio/click.mp3 is 0 bytes, audio/win.mp3 is 0 bytes, audio/loss.mp3 is 0 bytes",
      "remediation": "Add actual audio content or use placeholder sounds from asset library",
      "criterion": "Audio feedback on actions"
    }
  ]
}
```

**Outcome**: Agent must provide actual audio files or use placeholders before task can complete.

### Example 3: Retry Detection (Stuck Agent)

**Attempt 1** (validation fails):
- Issue: "validatePhone() not implemented"
- Response: Return failure with remediation

**Attempt 2** (same issue - agent didn't fix it):
- Issue: "validatePhone() not implemented" (SAME fingerprint)
- Response: Create blocker with meta-analysis

**Blocker Created**:
```
🚫 VALIDATION BLOCKER - REPEATED FAILURES

You've attempted to complete this task 2 times with the same issues.

1. ❌ validatePhone() not implemented
   SEVERITY: CRITICAL
   EVIDENCE: validation.js still has no validatePhone() function
   REMEDIATION: Add function validatePhone(phone) { return /^\d{3}-\d{3}-\d{4}$/.test(phone); }
   CRITERION: Fields are properly validated

PATTERN DETECTED: You keep submitting without fixing the specific issue.
- Attempt 1: validation.js had no validatePhone()
- Attempt 2: validation.js STILL has no validatePhone()

YOU ARE STUCK because the remediation clearly states what's missing.
The ONLY issue is: validation.js needs a validatePhone() function.
Don't rebuild everything - just add the ONE missing function.
```

## Configuration

### File Extensions (Source Code Discovery)

Configured in [work_analyzer.py:44-66](../src/ai/validation/work_analyzer.py#L44-L66):

```python
SOURCE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx",
    ".java", ".go", ".rs", ".c", ".cpp",
    ".h", ".hpp", ".cs", ".rb", ".php",
    ".swift", ".kt", ".html", ".css",
    ".scss", ".less",
}
```

**Add new extension**:
```python
SOURCE_EXTENSIONS = {..., ".vue"}  # Add Vue files
```

### Excluded Directories

Configured in [work_analyzer.py:68-85](../src/ai/validation/work_analyzer.py#L68-L85):

```python
EXCLUDE_DIRS = {
    "docs",          # Design artifacts (not implementation)
    "node_modules",  # Dependencies
    ".git",          # Version control
    "__pycache__",   # Python cache
    "venv", ".venv", # Python virtual environments
    "build", "dist", # Build artifacts
}
```

**Add new exclusion**:
```python
EXCLUDE_DIRS = {..., ".terraform"}  # Ignore Terraform state
```

### Placeholder Patterns

Configured in [work_analyzer.py:87-97](../src/ai/validation/work_analyzer.py#L87-L97):

```python
PLACEHOLDER_PATTERNS = {
    "TODO", "FIXME", "HACK", "XXX",
    "NotImplementedError",
    "pass  # TODO",
    "throw new Error('Not implemented')",
    "unimplemented!()",  # Rust
}
```

**Add custom pattern**:
```python
PLACEHOLDER_PATTERNS = {..., "STUB"}
```

### Retry Tracking

Configured in [retry_tracker.py:30-39](../src/ai/validation/retry_tracker.py#L30-L39):

```python
def __init__(self, cleanup_hours: int = 24) -> None:
    """Initialize retry tracker.

    Parameters
    ----------
    cleanup_hours : int
        Hours after which old attempts are cleaned up
    """
    self._cleanup_threshold = timedelta(hours=cleanup_hours)
```

**Adjust cleanup threshold**:
```python
tracker = RetryTracker(cleanup_hours=48)  # Keep history for 2 days
```

## Testing

### Test Coverage

**Current Coverage**: 85.07% (exceeds 80% requirement)

Coverage by module:
- `validation_models.py`: 93.65%
- `retry_tracker.py`: 84.78%
- `work_analyzer.py`: 84.29%
- `task_filter.py`: 66.67%
- `task_completeness_validator.py`: 82.61%

### Running Tests

**Full validation test suite**:
```bash
pytest tests/unit/ai/validation/ tests/integration/validation/ -v
```

**With coverage**:
```bash
pytest tests/unit/ai/validation/ tests/integration/validation/ \
  --cov=src/ai/validation --cov-report=term-missing
```

**Specific test file**:
```bash
pytest tests/integration/validation/test_validation_workflow.py -v
```

### Test Structure

**Unit Tests** ([tests/unit/ai/validation/](../tests/unit/ai/validation/)):
- `test_work_analyzer.py`: Source discovery, AI validation
- `test_retry_tracker.py`: Fingerprinting, retry detection
- `test_task_completeness_validator.py`: Legacy validator tests

**Integration Tests** ([tests/integration/validation/](../tests/integration/validation/)):
- `test_validation_workflow.py`: End-to-end validation workflow

**Key Integration Tests**:
1. Validation passes for complete implementation
2. Validation fails for missing features
3. Validation skipped for design tasks
4. Blocker created on retry with same issues
5. No blocker when agent fixes issues between retries

## Troubleshooting

### Validation System Errors

**Problem**: Validation fails with error instead of validating

**Check**:
```bash
# Check Marcus logs
tail -f ~/.marcus/logs/marcus.log | grep validation
```

**Common Causes**:
1. **Circular import**: Fixed with lazy imports in task.py
2. **Missing project_root**: Ensure workspace manager configured
3. **LLM API error**: Check AI provider credentials

**Graceful Degradation**: If validation system fails, task completion proceeds (logged as error).

### False Positives (Validation Fails When It Shouldn't)

**Problem**: AI incorrectly marks complete implementation as incomplete

**Debug**:
```python
# In work_analyzer.py, add logging before AI call
logger.info(f"Validation prompt:\n{task_prompt}")
logger.info(f"AI response:\n{ai_response}")
```

**Common Causes**:
1. **Empty discovered files**: Check file reading logic
2. **AI misunderstood criteria**: Refine acceptance criteria
3. **Missing context**: Ensure decisions are being retrieved

**Fix**: Adjust AI system prompt or acceptance criteria to be more specific.

### False Negatives (Validation Passes When It Shouldn't)

**Problem**: AI marks incomplete implementation as complete

**Debug**:
```python
# Check what evidence was gathered
logger.info(f"Source files discovered: {len(evidence.source_files)}")
for sf in evidence.source_files:
    logger.info(f"  - {sf.relative_path}: {sf.size_bytes} bytes")
```

**Common Causes**:
1. **Too lenient criteria**: Make acceptance criteria more specific
2. **Placeholder detection missed**: Add pattern to PLACEHOLDER_PATTERNS
3. **AI hallucination**: AI claims code exists when it doesn't

**Fix**: Make acceptance criteria more explicit about required code patterns.

### Retry Detection Not Working

**Problem**: Agent gets multiple chances with same issues (no blocker created)

**Debug**:
```python
# In retry_tracker.py
logger.info(f"Last fingerprints: {last_fingerprints}")
logger.info(f"Current fingerprints: {current_fingerprints}")
logger.info(f"Match: {last_fingerprints == current_fingerprints}")
```

**Common Causes**:
1. **Issue wording changes**: Fingerprint includes issue text
2. **Severity changes**: Fingerprint includes severity
3. **Tracker not persisted**: Singletons reset between runs

**Fix**: Ensure issue text and severity are stable across validation runs.

## Performance Optimization

### File Discovery Optimization

**Problem**: Scanning large projects is slow

**Strategy 1: Modification Time Filter**
```python
# Only scan files modified since task assignment
task_assigned_time = task.assigned_at
recent_threshold = task_assigned_time - timedelta(hours=1)

for file in files:
    mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
    if mod_time < recent_threshold:
        continue  # Skip - not modified during task
```

**Strategy 2: Smart Filtering**
- Already excludes `node_modules/`, `docs/`, etc.
- Only reads source file extensions
- Typically reduces 500+ files to 5-20 relevant files

**Strategy 3: Content Size Limits**
```python
if size_bytes > 1_000_000:  # 1MB limit
    content = file_path.read_text()[:100000]  # First 100KB
    content += "\n\n[FILE TRUNCATED - Too large]"
```

### LLM Cost Optimization

**Problem**: AI validation costs add up

**Optimization 1: Skip Validation for Design Tasks**
- `should_validate_task()` filters out non-implementation work
- Saves ~50% of validation calls

**Optimization 2: Smart Context Truncation**
- Only first 2KB of each source file shown to AI
- Full content still validated, but prompt is smaller

**Optimization 3: Batch Validation** (future enhancement)
- Could validate multiple tasks in single LLM call
- Not currently implemented

## Future Enhancements

### Planned Features

1. **Visual Testing Integration**
   - Use Puppeteer for UI validation
   - Screenshot comparison
   - Interaction testing

2. **Code Quality Metrics**
   - Cyclomatic complexity
   - Code coverage requirements
   - Security vulnerability scanning

3. **Dual LLM Voting** (Worker Disputes)
   - Agent can contest validation
   - Two additional LLMs analyze
   - Majority vote wins

4. **Persistent Retry Tracking**
   - Store attempt history in database
   - Survive Marcus restarts
   - Cross-session retry detection

5. **Custom Validation Rules**
   - User-defined validators
   - Project-specific checks
   - Domain-specific rules

### Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Adding new validation checks
- Extending evidence sources
- Improving AI prompts
- Writing tests

## References

- **GitHub Issue**: [#170 - Feature Completeness Validation System](https://github.com/lwgray/marcus/issues/170)
- **Implementation Plan**: [playful-hopping-pillow.md](../.claude/plans/playful-hopping-pillow.md)
- **Source Code**: [src/ai/validation/](../src/ai/validation/)
- **Tests**: [tests/unit/ai/validation/](../tests/unit/ai/validation/), [tests/integration/validation/](../tests/integration/validation/)
