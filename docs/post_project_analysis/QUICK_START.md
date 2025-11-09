# Quick Start: Testing Requirement Divergence Analyzer

## 1. Fast Unit Test (No API Key Needed)

```bash
# Run all unit tests
pytest tests/unit/analysis/analyzers/test_requirement_divergence.py -v

# Expected output:
# ✅ 12 tests pass in ~0.1 seconds
```

## 2. Manual Test (Requires API Key)

### Setup API Key

Add to `config_marcus.json`:
```json
{
  "ai": {
    "enabled": true,
    "provider": "anthropic",
    "anthropic_api_key": "sk-ant-YOUR-KEY-HERE"  # pragma: allowlist secret
  }
}
```

Or set environment variable:
```bash
export ANTHROPIC_API_KEY="sk-ant-YOUR-KEY-HERE"  # pragma: allowlist secret
```

### Run Manual Test

```bash
python tests/integration/analysis/test_requirement_divergence_live.py
```

This will analyze a sample task and print:
- Fidelity score
- Detected divergences
- Recommendations
- Progress updates

**Example output:**
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

## 3. Integration Tests (Real AI, Full Scenarios)

```bash
# Run all integration tests
pytest tests/integration/analysis/test_requirement_divergence_live.py -v -m integration

# Run specific scenario
pytest tests/integration/analysis/test_requirement_divergence_live.py::TestRequirementDivergenceWithRealAI::test_detect_critical_divergence_oauth_to_jwt -v -m integration
```

**Available scenarios:**
- `test_detect_critical_divergence_oauth_to_jwt` - OAuth → JWT divergence (from Phase 2 spec)
- `test_detect_perfect_match` - Implementation exactly matches requirements
- `test_detect_minor_divergence` - Working alternative approach

## 4. Create Your Own Test

```python
import asyncio
from datetime import datetime, timezone
from src.analysis.analyzers.requirement_divergence import RequirementDivergenceAnalyzer
from src.analysis.aggregator import TaskHistory
from src.core.project_history import Decision, ArtifactMetadata

async def test_my_scenario():
    analyzer = RequirementDivergenceAnalyzer()

    # Your task
    task = TaskHistory(
        task_id="test-001",
        name="Build login feature",
        description="Implement user login with email and password",
        status="completed",
        estimated_hours=4.0,
        actual_hours=5.0,
    )

    # Decisions made during implementation
    decisions = [
        Decision(
            decision_id="dec-001",
            task_id="test-001",
            agent_id="agent-1",
            timestamp=datetime.now(timezone.utc),
            what="Use bcrypt for password hashing",
            why="Industry standard, well-tested",
            impact="low",
            affected_tasks=[],
            confidence=0.9,
        )
    ]

    # Implementation artifacts
    artifacts = [
        ArtifactMetadata(
            artifact_id="art-001",
            task_id="test-001",
            agent_id="agent-1",
            timestamp=datetime.now(timezone.utc),
            artifact_type="code",
            filename="login.py",
            relative_path="src/auth/login.py",
            absolute_path="/project/src/auth/login.py",
            description="Login endpoint: POST /login with email/password, returns JWT token",
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
    print(f"\nFidelity Score: {analysis.fidelity_score:.2%}")
    print(f"Divergences: {len(analysis.divergences)}")

    for div in analysis.divergences:
        print(f"\n[{div.severity.upper()}]")
        print(f"  Required: {div.requirement}")
        print(f"  Got: {div.implementation}")
        print(f"  Impact: {div.impact}")

    print("\nRecommendations:")
    for rec in analysis.recommendations:
        print(f"  - {rec}")

# Run it
asyncio.run(test_my_scenario())
```

Save as `my_test.py` and run:
```bash
python my_test.py
```

## Troubleshooting

### "No API key" Error
```bash
# Check if key is loaded
python -c "from src.config.config_loader import get_config; print(get_config().get('ai', {}).get('anthropic_api_key', 'NOT SET')[:20])"
```

### API Call Fails
- Check internet connection
- Verify API key is valid
- Check API key hasn't expired
- Try setting `ANTHROPIC_API_KEY` environment variable directly

### Unexpected Results
Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Then run your test
```

## Next Steps

- See [TESTING_GUIDE.md](./TESTING_GUIDE.md) for comprehensive testing documentation
- See [post_project_analysis_PHASE_2.md](./post_project_analysis_PHASE_2.md) for full Phase 2 specification
- Try different scenarios to see how the analyzer handles various divergences
