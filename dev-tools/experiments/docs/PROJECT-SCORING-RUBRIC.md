# Automatic Project Scoring Rubric

## Overview

This rubric provides objective, automated scoring for comparing project implementations (Marcus vs Single Agent).

**Total Points: 100**

---

## Category 1: Functionality (25 points)

### 1.1 Application Runs (10 points)
- **10 pts**: Starts without errors, both endpoints respond correctly
- **7 pts**: Starts but has minor errors or warnings
- **4 pts**: Starts but one endpoint fails
- **0 pts**: Cannot start or crashes immediately

**Automated Test**:
```bash
# Start server in background
python main.py &
sleep 2
# Test both endpoints
curl http://localhost:5000/api/date
curl http://localhost:5000/api/time
# Check response codes and format
```

### 1.2 Tests Exist and Pass (10 points)
- **10 pts**: All tests exist and pass (100% pass rate)
- **7 pts**: Tests exist, 80-99% pass
- **4 pts**: Tests exist, 50-79% pass
- **2 pts**: Tests exist but <50% pass or don't run
- **0 pts**: No tests or tests cannot be executed

**Automated Test**:
```bash
pytest --tb=short -v
# Count: passed/total
```

### 1.3 Test Coverage (5 points)
- **5 pts**: ≥80% coverage
- **4 pts**: 60-79% coverage
- **3 pts**: 40-59% coverage
- **1 pt**: 20-39% coverage
- **0 pts**: <20% or no coverage data

**Automated Test**:
```bash
pytest --cov=. --cov-report=term-missing
# Parse coverage percentage
```

---

## Category 2: Code Quality (20 points)

### 2.1 Static Analysis Score (8 points)
Using pylint or similar tool

- **8 pts**: Score ≥9.0/10
- **6 pts**: Score 7.0-8.9/10
- **4 pts**: Score 5.0-6.9/10
- **2 pts**: Score 3.0-4.9/10
- **0 pts**: Score <3.0/10

**Automated Test**:
```bash
pylint **/*.py --exit-zero
# Parse average score
```

### 2.2 Code Complexity (6 points)
Using radon for cyclomatic complexity

- **6 pts**: Average complexity A (low, 1-5)
- **4 pts**: Average complexity B (moderate, 6-10)
- **2 pts**: Average complexity C (high, 11-20)
- **0 pts**: Average complexity D-F (very high, >20)

**Automated Test**:
```bash
radon cc . -a -s
# Parse average grade
```

### 2.3 Documentation Coverage (6 points)
Percentage of functions/classes with docstrings

- **6 pts**: ≥90% documented
- **4 pts**: 70-89% documented
- **2 pts**: 50-69% documented
- **0 pts**: <50% documented

**Automated Test**:
```bash
interrogate -vv .
# Parse documentation coverage
```

---

## Category 3: Completeness (20 points)

### 3.1 Required Deliverables Present (10 points)

Check for existence of required artifacts:
- API specification document (2 pts)
- Data models (2 pts)
- Endpoint implementations (2 pts)
- Error handling (2 pts)
- Tests (2 pts)

**Automated Test**:
```python
# Check for files matching patterns:
# *spec* or *api* (API docs)
# *model* (data models)
# *endpoint* or *route* or *controller* (endpoints)
# *error* or try/except in code (error handling)
# test_* (tests)
```

### 3.2 No Stub/Placeholder Code (5 points)

- **5 pts**: No TODOs, pass statements, NotImplementedError, or placeholder comments
- **3 pts**: 1-2 minor TODOs in non-critical areas
- **0 pts**: Multiple TODOs or stubs in core functionality

**Automated Test**:
```bash
# Search for patterns:
grep -r "TODO\|FIXME\|XXX\|pass$\|NotImplemented" . --include="*.py"
# Count occurrences
```

### 3.3 All Subtasks Completed (5 points)

- **5 pts**: All 18 tasks/subtasks completed (100%)
- **4 pts**: 16-17 completed (89-94%)
- **3 pts**: 14-15 completed (78-83%)
- **2 pts**: 12-13 completed (67-72%)
- **0 pts**: <12 completed (<67%)

**Manual Verification**: Check against task list

---

## Category 4: Project Structure (15 points)

### 4.1 Logical Organization (8 points)

- **8 pts**: Clear separation (models, controllers, tests, docs in separate dirs)
- **6 pts**: Mostly separated but some mixing
- **4 pts**: Basic structure but inconsistent
- **2 pts**: All files in root directory
- **0 pts**: Chaotic/no structure

**Automated Test**:
```python
# Check for directories:
# - models/ or src/models/
# - tests/ or test/
# - docs/ or documentation/
# - controllers/ or routes/ or api/
# Score based on presence and file counts
```

### 4.2 Appropriate File Count (4 points)

Balance between monolithic and over-fragmented

- **4 pts**: 8-15 files (good balance)
- **3 pts**: 6-7 or 16-20 files
- **2 pts**: 4-5 or 21-25 files
- **1 pt**: 2-3 or >25 files
- **0 pts**: 1 file (everything in one) or >30 files

**Automated Test**:
```bash
find . -name "*.py" -not -path "./.venv/*" -not -path "./.git/*" | wc -l
```

### 4.3 Configuration Separated (3 points)

- **3 pts**: Config in separate file (.env, config.py, settings.py)
- **1 pt**: Config as constants at top of files
- **0 pts**: Hardcoded values throughout

**Automated Test**:
```bash
# Check for config files
ls config.py settings.py .env 2>/dev/null | wc -l
```

---

## Category 5: Documentation (12 points)

### 5.1 PROJECT_SUCCESS.md Exists and Complete (6 points)

- **6 pts**: Comprehensive (how it works, how to run, how to test, troubleshooting)
- **4 pts**: Present but missing 1 section
- **2 pts**: Minimal documentation
- **0 pts**: Missing or just a stub

**Automated Test**:
```python
# Check for file existence and content
# Count sections: "How to Run", "How to Test", "How It Works"
# Check word count (should be >500 words)
```

### 5.2 API Documentation (3 points)

- **3 pts**: Both endpoints fully documented (request/response examples)
- **2 pts**: Documented but missing examples
- **1 pt**: Minimal endpoint documentation
- **0 pts**: No API documentation

**Automated Test**:
```python
# Search for:
# - Endpoint paths (GET /api/date, GET /api/time)
# - Request examples (curl or similar)
# - Response examples (JSON samples)
```

### 5.3 Setup Instructions (3 points)

- **3 pts**: Step-by-step from zero to running
- **2 pts**: Basic instructions but assume knowledge
- **1 pt**: Minimal instructions
- **0 pts**: No setup instructions

**Automated Test**:
```python
# Check for:
# - Dependencies listed (requirements.txt or similar)
# - Installation steps
# - How to start the server
```

---

## Category 6: Usability (8 points)

### 6.1 Single-Command Startup (4 points)

- **4 pts**: `python main.py` or `npm start` or similar single command
- **2 pts**: Requires 2-3 commands (install deps, then run)
- **0 pts**: Complex multi-step startup or unclear

**Manual Test**: Follow documentation

### 6.2 Dependencies Managed (2 points)

- **2 pts**: requirements.txt or package.json or similar
- **1 pt**: Dependencies mentioned in docs but no manifest
- **0 pts**: No dependency information

**Automated Test**:
```bash
ls requirements.txt package.json Pipfile pyproject.toml 2>/dev/null | wc -l
```

### 6.3 Example Requests Provided (2 points)

- **2 pts**: Working example requests/commands for both endpoints
- **1 pt**: Examples for one endpoint or incomplete
- **0 pts**: No examples

**Automated Test**:
```python
# Search docs for curl/http/request examples
# Check for both endpoints
```

---

## Scoring Interpretation

### Total Score Ranges

- **90-100**: Excellent - Production-quality prototype
- **75-89**: Good - Solid implementation with minor issues
- **60-74**: Acceptable - Works but has quality/completeness issues
- **40-59**: Poor - Significant issues or incomplete
- **0-39**: Failing - Non-functional or severely incomplete

### Comparison Metrics

When comparing Marcus vs Single Agent, calculate:

1. **Absolute Score Difference**: `|Marcus_Score - Single_Score|`
2. **Percentage Difference**: `(Difference / Higher_Score) * 100`
3. **Category Breakdown**: Show which categories each approach excelled in
4. **Speed vs Quality Ratio**: `Score / Time_Minutes`

---

## Automated Scoring Script Usage

```bash
# Run the automated scorer
python experiments/score_project.py \
    --project-dir ./datetime-api-marcus \
    --output-file marcus-score.json

python experiments/score_project.py \
    --project-dir ./datetime-api-single-agent \
    --output-file single-agent-score.json

# Compare results
python experiments/compare_scores.py \
    --marcus marcus-score.json \
    --single single-agent-score.json \
    --output comparison-report.md
```

---

## Additional Objective Metrics (Not Scored)

These provide context but aren't part of the 100-point score:

1. **Lines of Code (LOC)**
   - Total lines
   - Code lines (excluding comments/blanks)
   - Comment ratio

2. **File Metrics**
   - Total files created
   - Average lines per file
   - Largest file size

3. **Git Metrics** (if using version control)
   - Number of commits
   - Commit message quality
   - Files changed per commit

4. **Performance Metrics**
   - API response time (ms)
   - Memory usage
   - Startup time

5. **Security Considerations**
   - Hardcoded secrets detected
   - Input validation present
   - Error messages don't leak info

---

## Fair Comparison Guidelines

1. **Same Environment**: Run both on same machine/Python version
2. **Same Time Limit**: If Marcus takes 21 min, give single agent same time limit
3. **Same Prompt**: Use equivalent task descriptions
4. **Blind Scoring**: Score without knowing which is which
5. **Multiple Runs**: Run experiment 3 times, average scores

---

## Example Score Report

```
Project: DateTime API (Marcus)
Total Score: 87/100

Category Breakdown:
- Functionality: 23/25 (92%)
- Code Quality: 16/20 (80%)
- Completeness: 19/20 (95%)
- Project Structure: 13/15 (87%)
- Documentation: 10/12 (83%)
- Usability: 6/8 (75%)

Strengths:
✓ All tests pass (10/10)
✓ No stub code (5/5)
✓ All deliverables present (10/10)

Weaknesses:
✗ Code complexity average B (4/6)
✗ Documentation missing troubleshooting (4/6)

Time: 21.37 minutes
Quality/Time Ratio: 4.07 points/min
```
