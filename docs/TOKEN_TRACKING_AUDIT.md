# Token Tracking Audit & Implementation Plan

**Date**: 2025-01-11
**Status**: ⚠️ **INCOMPLETE** - Token tracking infrastructure exists but is not being used for all LLM calls
**Priority**: HIGH - Need accurate cost tracking for all AI operations

---

## Executive Summary

**Good News**:
- ✅ Token tracking infrastructure exists (`TokenTracker`, `AIUsageMiddleware`)
- ✅ Middleware design is solid and ready to use

**Bad News**:
- ❌ **AnthropicProvider doesn't return token counts** from API responses
- ❌ **LLMAbstraction instances are NOT wrapped** by middleware in most places
- ❌ **Analysis AI calls (Phase 3) are NOT tracked**
- ❌ **Project creation AI calls are NOT tracked**

**Impact**: We're currently **blind to 90%+ of token usage**.

---

## Current State Analysis

### What EXISTS (Infrastructure)

#### 1. TokenTracker Class (`src/cost_tracking/token_tracker.py`)
**Purpose**: Track token usage per project with real-time cost monitoring

**Features**:
- Per-project token tracking
- Real-time spend rate calculation (tokens/hour)
- Cost projections
- Token usage history
- Anomaly detection (spending spikes)
- Persistence to `data/token_usage.json`

**Status**: ✅ Implemented, ❌ Not being used

#### 2. AIUsageMiddleware (`src/cost_tracking/ai_usage_middleware.py`)
**Purpose**: Intercept AI provider calls to track token usage

**Features**:
- `@track_ai_usage` decorator for AI methods
- `wrap_ai_provider()` to wrap entire provider instances
- `track_project_tokens()` context manager
- Automatic token extraction from responses
- Logging for significant usage (>1000 tokens)

**Status**: ✅ Implemented, ⚠️ Partially used

### What's USING Token Tracking

#### ✅ AIAnalysisEngine (Partially)
**Location**: `src/integrations/ai_analysis_engine.py`
**Usage**: Unknown (found import but need to verify usage)

#### ✅ MarcusServer (Wraps ai_engine only)
**Location**: `src/marcus_mcp/server.py` (line 601)
```python
self.ai_engine = ai_usage_middleware.wrap_ai_provider(self.ai_engine)
```
**Coverage**: Only wraps `ai_engine`, misses LLM providers

### What's NOT USING Token Tracking

#### ❌ AnthropicProvider
**Location**: `src/ai/providers/anthropic_provider.py`
**Problem**: Discards token usage data from API response

**Current code** (line 432-436):
```python
response = await self.client.post(f"{self.base_url}/messages", json=payload)
response.raise_for_status()

data = response.json()
return str(data["content"][0]["text"])  # ❌ Throws away usage data
```

**Anthropic API Response Structure**:
```json
{
  "id": "msg_...",
  "type": "message",
  "role": "assistant",
  "content": [{"type": "text", "text": "..."}],
  "model": "claude-3-haiku-20240307",
  "stop_reason": "end_turn",
  "usage": {
    "input_tokens": 123,
    "output_tokens": 456
  }
}
```

**Impact**: **CRITICAL** - All Anthropic calls lose token data

#### ❌ LLMAbstraction
**Location**: `src/ai/providers/llm_abstraction.py`
**Problem**: Instantiated in multiple places but NOT wrapped

**Unwrapped Instances Found**:
1. `src/ai/advanced/prd/advanced_parser.py:94`
   - **Impact**: Project creation tokens NOT tracked

2. `src/ai/enrichment/intelligent_enricher.py:70`
   - **Impact**: Task enrichment tokens NOT tracked

3. `src/ai/core/ai_engine.py:295`
   - **Impact**: Core AI operations NOT tracked

4. `src/analysis/ai_engine.py:176`
   - **Impact**: Post-project analysis tokens NOT tracked
   - **Severity**: HIGH - Analysis uses 100k+ tokens per medium project

5. `src/integrations/ai_analysis_engine.py:1630`
   - **Impact**: Integration analysis NOT tracked

#### ❌ Post-Project Analysis (Phase 3)
**Location**: `src/analysis/post_project_analyzer.py`
**AI Operations**:
- Requirement divergence analysis (per task)
- Decision impact tracing (per decision)
- Instruction quality assessment (per task)
- Failure diagnosis (per failed task)
- Task redundancy detection (entire project)

**Token Estimate**: 20k-400k tokens per analysis
**Status**: ❌ NOT tracked

---

## Token Tracking Gaps Summary

| Component | Token Usage | Tracked? | Priority |
|-----------|-------------|----------|----------|
| **AnthropicProvider** | High (all calls) | ❌ NO | CRITICAL |
| **Project Creation** | Medium (5k tokens) | ❌ NO | HIGH |
| **Post-Project Analysis** | Very High (20k-400k) | ❌ NO | CRITICAL |
| **Task Enrichment** | Medium (1-2k/task) | ❌ NO | MEDIUM |
| **Core AI Engine** | Medium | ⚠️ Partial | HIGH |
| **Integration Analysis** | Low | ❌ NO | LOW |

**Current Coverage**: ~10% of token usage tracked
**Target Coverage**: 95%+ of token usage tracked

---

## Implementation Plan

### Phase 1: Fix AnthropicProvider (CRITICAL)
**Priority**: P0 - Blocks all other tracking
**Effort**: 1-2 hours

**Changes Needed**:

**File**: `src/ai/providers/anthropic_provider.py`

```python
# BEFORE (line 432-436):
data = response.json()
return str(data["content"][0]["text"])

# AFTER:
data = response.json()
return {
    "text": str(data["content"][0]["text"]),
    "usage": data.get("usage", {}),
    "model": data.get("model", self.model),
}
```

**Impact**: All callers of `_call_claude()` need to handle dict response instead of string.

**Affected Methods** (need updates):
- `analyze_task()` - line 87
- `infer_dependencies()` - line 121
- `generate_enhanced_description()` - line 146
- `estimate_effort()` - line 171
- `analyze_blocker()` - line 203
- `complete()` - line 410

**Pattern for updates**:
```python
# BEFORE:
response = await self._call_claude(prompt)
return self._parse_task_analysis_response(response)

# AFTER:
response_data = await self._call_claude(prompt)
result = self._parse_task_analysis_response(response_data["text"])
# Token tracking happens in _call_claude via middleware
return result
```

### Phase 2: Wrap All LLM Provider Instances
**Priority**: P0
**Effort**: 2-3 hours

**Strategy**: Create a factory function that ensures all LLM instances are wrapped.

**New File**: `src/ai/providers/llm_factory.py`
```python
"""
LLM Provider Factory with automatic token tracking.
"""
from src.ai.providers.llm_abstraction import LLMAbstraction
from src.cost_tracking.ai_usage_middleware import ai_usage_middleware


def create_llm_client(track_tokens: bool = True) -> LLMAbstraction:
    """
    Create an LLM client with optional token tracking.

    Parameters
    ----------
    track_tokens : bool
        Whether to wrap with token tracking middleware (default True)

    Returns
    -------
    LLMAbstraction
        Configured LLM client, wrapped if track_tokens=True
    """
    client = LLMAbstraction()

    if track_tokens:
        client = ai_usage_middleware.wrap_ai_provider(client)

    return client
```

**Changes Required**:
1. Replace all `LLMAbstraction()` with `create_llm_client()`
2. Update imports

**Files to Update** (5 files):
1. `src/ai/advanced/prd/advanced_parser.py:94`
2. `src/ai/enrichment/intelligent_enricher.py:70`
3. `src/ai/core/ai_engine.py:295`
4. `src/analysis/ai_engine.py:176`
5. `src/integrations/ai_analysis_engine.py:1630`

**Example**:
```python
# BEFORE:
from src.ai.providers.llm_abstraction import LLMAbstraction
self.llm_client = LLMAbstraction()

# AFTER:
from src.ai.providers.llm_factory import create_llm_client
self.llm_client = create_llm_client()
```

### Phase 3: Add Project Context to Analysis
**Priority**: P1
**Effort**: 1 hour

**File**: `src/analysis/post_project_analyzer.py`

Wrap analysis calls with project context:

```python
from src.cost_tracking.ai_usage_middleware import track_project_tokens

async def analyze_project(
    self,
    project_id: str,
    history: ProjectHistory,
    scope: AnalysisScope,
    progress_callback: Optional[Callable] = None
) -> ProjectAnalysisResult:
    """Analyze project with token tracking."""

    # Set project context for token tracking
    with track_project_tokens(project_id, agent_id="analyzer"):
        # All AI calls in analysis will be tracked to this project
        result = await self._perform_analysis(
            history, scope, progress_callback
        )

    return result
```

### Phase 4: Add Token Usage to MCP Tool Responses
**Priority**: P2
**Effort**: 2 hours

**Enhancement**: Return token usage stats in MCP tool responses

**Example** (create_project tool):
```python
{
    "success": True,
    "project_id": "proj_123",
    "board_id": "board_456",
    "tasks_created": 10,
    "token_usage": {
        "total_tokens": 5234,
        "cost": 0.0067,
        "breakdown": {
            "project_parsing": 1200,
            "task_generation": 3500,
            "subtask_decomposition": 534
        }
    }
}
```

### Phase 5: Create Token Usage Dashboard/Report
**Priority**: P3
**Effort**: 4 hours

**New File**: `src/cost_tracking/usage_report.py`

```python
"""Generate token usage reports."""

async def generate_usage_report(
    project_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Generate comprehensive token usage report.

    Returns
    -------
    Dict with:
    - Total tokens and cost
    - Breakdown by project
    - Breakdown by operation type
    - Spend rate trends
    - Cost projections
    - Recommendations (e.g., "switch to Haiku to save 60%")
    """
    pass
```

**CLI Command**:
```bash
# View usage for all projects
marcus tokens report

# View usage for specific project
marcus tokens report --project proj_123

# View usage for date range
marcus tokens report --start 2025-01-01 --end 2025-01-31
```

---

## Testing Strategy

### Unit Tests Needed

**File**: `tests/unit/cost_tracking/test_anthropic_token_extraction.py`
```python
"""Test that AnthropicProvider returns token usage."""

async def test_call_claude_returns_usage():
    """Test _call_claude returns usage data."""
    provider = AnthropicProvider()
    response = await provider._call_claude("Test prompt")

    assert isinstance(response, dict)
    assert "text" in response
    assert "usage" in response
    assert "input_tokens" in response["usage"]
    assert "output_tokens" in response["usage"]
```

**File**: `tests/integration/cost_tracking/test_end_to_end_tracking.py`
```python
"""Test end-to-end token tracking."""

async def test_project_creation_tracks_tokens():
    """Test that create_project tracks all token usage."""
    # Create project
    result = await create_project(
        description="Build a TODO app",
        project_name="Test Project"
    )

    # Check token usage was tracked
    stats = token_tracker.get_project_stats(result["project_id"])
    assert stats["total_tokens"] > 0
    assert stats["total_cost"] > 0
```

### Manual Verification Checklist

After implementation:
- [ ] Create a test project → Check `data/token_usage.json` has data
- [ ] Run post-project analysis → Verify tokens tracked
- [ ] Check `~/.marcus/logs/` for usage logs
- [ ] Verify costs match Anthropic's usage dashboard
- [ ] Test with Ollama (should show $0 cost)

---

## Success Criteria

### Coverage Goals
- ✅ 95%+ of LLM calls tracked
- ✅ Project creation fully tracked
- ✅ Post-project analysis fully tracked
- ✅ All providers return token counts
- ✅ Token data persisted to disk

### Accuracy Goals
- ✅ Token counts match provider dashboards (±5%)
- ✅ Cost calculations accurate for all providers
- ✅ Project-level attribution 100% accurate

### UX Goals
- ✅ Token usage visible in MCP tool responses
- ✅ CLI command for usage reports
- ✅ Alerts for unusual spend spikes
- ✅ Cost projections for in-progress projects

---

## Cost Comparison (After Full Tracking)

Once tracking is complete, we'll have accurate data for:

| Scenario | Expected Tokens | Expected Cost (Haiku) |
|----------|-----------------|----------------------|
| Create small project (10 tasks) | 5,000 | $0.006 |
| Create medium project (50 tasks) | 15,000 | $0.019 |
| Post-analysis (medium project) | 100,000 | $0.095 |
| Daily development usage | 200,000 | $0.19 |
| Monthly development usage | 4,000,000 | $3.80 |

**Note**: These are estimates. Actual tracking will give us real numbers.

---

## Timeline

| Phase | Effort | Priority | Dependencies |
|-------|--------|----------|--------------|
| Phase 1: Fix AnthropicProvider | 2 hours | P0 | None |
| Phase 2: Wrap all LLM instances | 3 hours | P0 | Phase 1 |
| Phase 3: Analysis context | 1 hour | P1 | Phase 2 |
| Phase 4: MCP response enhancement | 2 hours | P2 | Phase 2 |
| Phase 5: Usage dashboard | 4 hours | P3 | All phases |
| **Total** | **12 hours** | **~2 days** | - |

---

## Next Steps

1. **Immediate** (P0):
   - [ ] Fix AnthropicProvider to return token counts
   - [ ] Update all callers to handle dict response
   - [ ] Test with a simple project creation

2. **Short-term** (P0):
   - [ ] Create LLM factory with automatic wrapping
   - [ ] Replace all LLMAbstraction() instantiations
   - [ ] Verify all providers return token counts

3. **Medium-term** (P1-P2):
   - [ ] Add project context to analysis
   - [ ] Enhance MCP responses with token usage
   - [ ] Write integration tests

4. **Long-term** (P3):
   - [ ] Build usage dashboard/CLI
   - [ ] Add cost optimization recommendations
   - [ ] Create monthly usage reports

---

## References

- **TokenTracker**: `src/cost_tracking/token_tracker.py`
- **Middleware**: `src/cost_tracking/ai_usage_middleware.py`
- **AnthropicProvider**: `src/ai/providers/anthropic_provider.py`
- **LLMAbstraction**: `src/ai/providers/llm_abstraction.py`
- **Anthropic API Docs**: https://docs.anthropic.com/claude/reference/messages_post

---

**Status**: Ready for implementation
**Owner**: TBD
**Created**: 2025-01-11
