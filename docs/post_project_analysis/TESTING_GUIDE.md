# Testing Guide: Phase 2 Analysis Engine

This guide shows you how to test the Phase 2 analysis modules both with unit tests (fast, no API calls) and integration tests (real LLM calls).

## Quick Start

### 1. Unit Tests (Fast, No API Required)

Unit tests use mocked AI responses, so they're fast and don't require API keys:

```bash
# Test all Phase 2 components
pytest tests/unit/analysis/ -v

# Test specific analyzer
pytest tests/unit/analysis/analyzers/test_requirement_divergence.py -v

# Test with coverage
pytest tests/unit/analysis/ --cov=src/analysis --cov-report=term-missing
```

**Benefits:**
- Fast (runs in ~0.2 seconds)
- No API keys needed
- No cost
- Great for TDD and rapid iteration

### 2. Integration Tests (Real AI Calls)

Integration tests use actual LLM calls to verify the analyzers work with real AI:

```bash
# Run integration tests (requires API key)
pytest tests/integration/analysis/test_requirement_divergence_live.py -v -m integration

# Run specific test
pytest tests/integration/analysis/test_requirement_divergence_live.py::TestRequirementDivergenceWithRealAI::test_detect_critical_divergence_oauth_to_jwt -v -m integration
```

**Prerequisites:**
1. Valid API key in `config_marcus.json`:
   ```json
   {
     "ai": {
       "enabled": true,
       "provider": "anthropic",
       "anthropic_api_key": "sk-ant-your-real-key-here"  // pragma: allowlist secret
     }
   }
   ```

2. Or set environment variable:
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-your-real-key-here"  # pragma: allowlist secret
   ```

**Benefits:**
- Tests real LLM behavior
- Validates prompt quality
- Ensures actual analysis works
- Catches prompt engineering issues

**Costs:**
- Uses real API tokens (~$0.01-0.05 per test)
- Takes 5-10 seconds per test

### 3. Manual Testing (Interactive)

For hands-on testing with your own scenarios:

```bash
# Run the manual test function
python tests/integration/analysis/test_requirement_divergence_live.py
```

This will:
1. Create a sample task (password reset with email skipped)
2. Run real LLM analysis
3. Print detailed results with progress updates
4. Show fidelity score, divergences, and recommendations

**Example Output:**
```
======================================================================
MANUAL TEST: Requirement Divergence Analyzer
======================================================================

Running analysis...
  [10/100] Building prompt...
  [20/100] Calling LLM...
  [80/100] Parsing response...
  [100/100] Complete

======================================================================
RESULTS
======================================================================

Fidelity Score: 35%
Divergences: 1

1. [MAJOR]
   Required: User enters email, receives reset link via email
   Got: Generates reset token, stores in DB, email sending is TODO
   Impact: Users cannot actually reset passwords - no email sent

Recommendations:
1. Implement email service integration
2. Add proper error handling for email failures
3. Consider temporary workaround (admin manual reset)
```

## Test Scenarios

### Scenario 1: Critical Divergence (OAuth → JWT)

From the Phase 2 spec example:

```python
# Task required OAuth2 with GitHub
task.description = "Implement OAuth2 authentication using GitHub provider..."

# But implementation used JWT instead
decision.what = "Use JWT authentication instead of OAuth2"
artifact.description = "POST /login endpoint with username/password, returns JWT"

# Expected result:
# - Fidelity score: 0.1-0.3 (critical divergence)
# - Severity: critical
# - Impact: Users cannot login with GitHub accounts
```

**Run this test:**
```bash
pytest tests/integration/analysis/test_requirement_divergence_live.py::TestRequirementDivergenceWithRealAI::test_detect_critical_divergence_oauth_to_jwt -v -m integration
```

### Scenario 2: Perfect Match

Implementation exactly matches requirements:

```python
# Task: Add logout endpoint
task.description = "POST /logout that invalidates session, returns 200 OK"

# Implementation: Exactly as specified
artifact.description = "POST /logout invalidates token, returns 200 OK"

# Expected result:
# - Fidelity score: 0.9-1.0 (perfect match)
# - Divergences: 0 or only minor
```

**Run this test:**
```bash
pytest tests/integration/analysis/test_requirement_divergence_live.py::TestRequirementDivergenceWithRealAI::test_detect_perfect_match -v -m integration
```

### Scenario 3: Minor Divergence

Working alternative approach:

```python
# Task: Use regex for email validation
task.description = "Add email validation using regex pattern"

# Implementation: Used library instead
decision.what = "Use email-validator library instead of regex"
decision.why = "More robust, handles edge cases"

# Expected result:
# - Fidelity score: 0.7-0.9 (minor divergence)
# - Severity: minor
# - Impact: Works better than requested
```

**Run this test:**
```bash
pytest tests/integration/analysis/test_requirement_divergence_live.py::TestRequirementDivergenceWithRealAI::test_detect_minor_divergence -v -m integration
```

## Custom Test Scenarios

### Create Your Own Test

```python
import asyncio
from datetime import datetime, timezone
from src.analysis.analyzers.requirement_divergence import RequirementDivergenceAnalyzer
from src.analysis.aggregator import TaskHistory
from src.core.project_history import Decision, ArtifactMetadata

async def my_test():
    analyzer = RequirementDivergenceAnalyzer()

    # Define your task
    task = TaskHistory(
        task_id="my-task",
        name="Your feature name",
        description="Your detailed requirement...",
        status="completed",
        estimated_hours=4.0,
        actual_hours=5.0,
    )

    # Define decisions made
    decisions = [
        Decision(
            decision_id="dec-001",
            task_id="my-task",
            agent_id="agent-1",
            timestamp=datetime.now(timezone.utc),
            what="What decision was made",
            why="Why it was made",
            impact="major",
            affected_tasks=[],
            confidence=0.8,
        )
    ]

    # Define implementation artifacts
    artifacts = [
        ArtifactMetadata(
            artifact_id="art-001",
            task_id="my-task",
            agent_id="agent-1",
            timestamp=datetime.now(timezone.utc),
            artifact_type="code",
            filename="implementation.py",
            relative_path="src/implementation.py",
            absolute_path="/project/src/implementation.py",
            description="Detailed description of what was implemented...",
            file_size_bytes=1024,
            sha256_hash="abc123",
        )
    ]

    # Run analysis
    analysis = await analyzer.analyze_task(
        task=task,
        decisions=decisions,
        artifacts=artifacts,
    )

    # Print results
    print(f"Fidelity: {analysis.fidelity_score:.2%}")
    for div in analysis.divergences:
        print(f"[{div.severity}] {div.impact}")

# Run it
asyncio.run(my_test())
```

## Debugging Tips

### 1. Check API Key

```bash
# Verify API key is loaded
python -c "from src.config.config_loader import get_config; c=get_config(); print('API key:', c.get('ai', {}).get('anthropic_api_key', 'NOT SET')[:20] + '...')"
```

### 2. Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now run your test - you'll see detailed logs
analyzer = RequirementDivergenceAnalyzer()
# ... rest of test
```

### 3. Inspect Raw LLM Response

```python
analysis = await analyzer.analyze_task(...)

# See what LLM actually returned
print("Raw LLM Response:")
print(analysis.llm_interpretation)

# See parsed JSON
print("\nParsed Result:")
import json
print(json.dumps(analysis.raw_data, indent=2))
```

### 4. Test Prompt Quality

The prompt is built from a template. To see what's actually sent to the LLM:

```python
analyzer = RequirementDivergenceAnalyzer()

# Get the template
template = analyzer.build_prompt_template()
print(template)

# Format with your data
context = {
    "task_description": "Your task...",
    "decisions": analyzer.format_decisions(decisions),
    "artifacts": analyzer.format_artifacts(artifacts),
    # ... other fields
}

prompt = template.format(**context)
print("\n=== ACTUAL PROMPT SENT TO LLM ===")
print(prompt)
```

## Continuous Testing

### Run Before Committing

```bash
# Quick unit tests
pytest tests/unit/analysis/ -v

# Full validation (if you have API key and time)
pytest tests/unit/analysis/ tests/integration/analysis/ -v -m "not integration or integration"
```

### CI/CD Integration

In your CI pipeline:

```yaml
# Only run unit tests (fast, no API key needed)
- name: Unit Tests
  run: pytest tests/unit/analysis/ -v

# Optional: Integration tests (only if API key available)
- name: Integration Tests
  if: env.ANTHROPIC_API_KEY != ''
  run: pytest tests/integration/analysis/ -v -m integration
```

## Expected Behavior

### What Should Pass
- ✅ Unit tests should always pass (they use mocks)
- ✅ Integration tests with valid API key should pass
- ✅ Manual tests should produce reasonable analysis

### What's Normal
- ⚠️ LLM responses vary slightly between runs (it's probabilistic)
- ⚠️ Integration tests take 5-10 seconds per test
- ⚠️ Fidelity scores might not be exactly same each time

### What's a Problem
- ❌ Unit tests failing (indicates code regression)
- ❌ Integration tests timing out (check API key / network)
- ❌ Fidelity scores wildly wrong (e.g., 1.0 for obvious divergence)
- ❌ Missing citations in divergences
- ❌ Empty recommendations

## Cost Estimation

Integration tests use real API tokens:

- **Per test:** ~2,000-4,000 tokens (~$0.01-0.02)
- **Full integration suite:** ~$0.05-0.10
- **Development session:** ~$0.50-1.00 (if running frequently)

**Tip:** Use unit tests for rapid iteration, integration tests for validation before merging.
