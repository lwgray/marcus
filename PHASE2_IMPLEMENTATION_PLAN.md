# Phase 2: LLM-Powered Analysis Engine - Implementation Plan

**Branch:** `feature/post-project-analysis-phase2`
**Duration:** 5-7 days
**Dependencies:** Phase 1 complete (✅)
**Target:** LLM analysis engine with 4 modules + helper infrastructure

---

## Executive Summary

Phase 2 builds intelligent analysis on Phase 1's data foundation by:
1. Adding helper functions for pagination and storage
2. Implementing 4 LLM-powered analysis modules
3. Always pairing raw data with LLM interpretations
4. Testing the pipeline (not LLM content)
5. Integrating with Phase 1 query API

**Key Principle:** Build analysis layer ON TOP of Phase 1, don't modify it.

---

## File Structure

```
src/
├── analysis/
│   ├── aggregator.py              # [EXISTS] Phase 1
│   ├── query_api.py               # [EXISTS] Phase 1
│   │
│   ├── helpers.py                 # [NEW] Pagination helpers
│   ├── indexer.py                 # [NEW] Conversation indexer
│   ├── analysis_store.py          # [NEW] Analysis result storage
│   ├── progress.py                # [NEW] Progress reporting
│   │
│   ├── analyzers/
│   │   ├── __init__.py
│   │   ├── base.py                # [NEW] BaseAnalyzer abstract class
│   │   ├── requirement.py         # [NEW] RequirementDivergenceAnalyzer
│   │   ├── decision.py            # [NEW] DecisionImpactTracer
│   │   ├── instruction.py         # [NEW] InstructionQualityAnalyzer
│   │   └── failure.py             # [NEW] FailureDiagnosisGenerator
│   │
│   └── coordinator.py             # [NEW] PostProjectAnalyzer

src/marcus_mcp/tools/
    └── analysis.py                # [NEW] MCP tools for Phase 2

tests/
├── unit/
│   └── analysis/
│       ├── test_helpers.py
│       ├── test_indexer.py
│       ├── test_analysis_store.py
│       ├── test_progress.py
│       └── analyzers/
│           ├── test_requirement_analyzer.py
│           ├── test_decision_tracer.py
│           ├── test_instruction_analyzer.py
│           └── test_failure_diagnoser.py
│
├── integration/
│   └── analysis/
│       ├── test_analysis_pipeline.py
│       └── test_mcp_analysis_tools.py
│
└── fixtures/
    └── golden_examples/
        ├── auth_mismatch_analysis.json
        ├── redis_decision_impact.json
        ├── payment_instruction_quality.json
        └── login_failure_diagnosis.json

examples/
    └── analyze_project_example.py
```

---

## Phase 1: Helper Functions & Infrastructure (Days 1-2)

### 1.1: `src/analysis/helpers.py`

**Purpose:** Auto-paginating async generators

```python
"""
Pagination helpers for Phase 2 analysis modules.

These async generators handle Phase 1's 10,000-item pagination limit
automatically, allowing analysis code to iterate over all items without
manual pagination logic.
"""

from typing import AsyncGenerator, Callable, Optional, Any
from src.core.project_history import Decision, ArtifactMetadata
from src.core.persistence import SQLitePersistence


async def iterate_all_decisions(
    project_id: str,
    persistence: SQLitePersistence,
    task_filter: Optional[Callable[[dict[str, Any]], bool]] = None,
    batch_size: int = 100
) -> AsyncGenerator[Decision, None]:
    """
    Iterate over all decisions for a project with automatic pagination.

    Parameters
    ----------
    project_id : str
        Project identifier
    persistence : SQLitePersistence
        Persistence backend
    task_filter : Optional[Callable]
        Filter function (same as Phase 1)
    batch_size : int
        Number of items per batch (default 100)

    Yields
    ------
    Decision
        Individual decision objects

    Examples
    --------
    >>> async for decision in iterate_all_decisions(project_id, persistence):
    ...     await analyze_decision(decision)
    """
    # Implementation with offset/limit loop


async def iterate_all_artifacts(
    project_id: str,
    persistence: SQLitePersistence,
    task_filter: Optional[Callable[[dict[str, Any]], bool]] = None,
    batch_size: int = 100
) -> AsyncGenerator[ArtifactMetadata, None]:
    """
    Iterate over all artifacts for a project with automatic pagination.

    [Similar signature and docstring as iterate_all_decisions]
    """
    # Implementation with offset/limit loop
```

**Tests:** `tests/unit/analysis/test_helpers.py`
- `test_iterate_all_decisions_empty_project()`
- `test_iterate_all_decisions_single_batch()`
- `test_iterate_all_decisions_multiple_batches()`
- `test_iterate_all_decisions_with_filter()`
- `test_iterate_all_artifacts_*()` (same patterns)

---

### 1.2: `src/analysis/indexer.py`

**Purpose:** SQLite index for conversation logs

```python
"""
Conversation log indexer for fast project-task mapping.

Phase 1 scans all conversation files to extract task IDs. This is slow
for large projects. ConversationIndexer builds a SQLite index for O(1)
lookups.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ConversationIndex:
    """Index entry for conversation log."""

    conversation_id: str
    project_id: str
    task_id: str
    agent_id: str
    timestamp: datetime
    file_path: str
    line_number: int


class ConversationIndexer:
    """
    Build and query SQLite index for conversation logs.

    This is an optimization for Phase 2. Phase 1's linear scan works
    but is slow for 1000+ task projects. The index enables:
    - O(1) lookup of conversations by project/task
    - Fast filtering without full file scan
    - Incremental updates as new conversations arrive
    """

    def __init__(self, persistence: SQLitePersistence):
        self.persistence = persistence
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create conversation_index table if not exists."""
        # CREATE TABLE IF NOT EXISTS conversation_index (...)

    async def index_conversation_file(self, file_path: str) -> int:
        """
        Index a single conversation file.

        Returns number of entries indexed.
        """

    async def rebuild_index(self) -> None:
        """Rebuild entire index from scratch."""

    async def get_conversations_for_project(
        self, project_id: str
    ) -> list[ConversationIndex]:
        """Fast lookup of all conversations for a project."""

    async def get_conversations_for_task(
        self, task_id: str
    ) -> list[ConversationIndex]:
        """Fast lookup of all conversations for a task."""
```

**Tests:** `tests/unit/analysis/test_indexer.py`
- `test_index_single_file()`
- `test_rebuild_index()`
- `test_get_conversations_for_project()`
- `test_incremental_update()`

---

### 1.3: `src/analysis/analysis_store.py`

**Purpose:** SQLite storage for LLM analysis results

```python
"""
Storage for Phase 2 analysis results.

Analysis results are expensive to compute (LLM calls). Store them so:
- Results can be retrieved without re-analysis
- Historical analysis comparisons are possible
- Progress can be tracked
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass
class AnalysisResult:
    """Generic container for analysis outputs."""

    analysis_id: str
    project_id: str
    task_id: Optional[str]  # None for project-level analysis
    analysis_type: str  # "requirement_divergence", "decision_impact", etc.
    timestamp: datetime
    result_data: dict[str, Any]  # The actual analysis output
    llm_model: str  # Which model produced this
    llm_tokens_used: int  # Cost tracking


class AnalysisResultStore:
    """
    Persist and retrieve analysis results.

    Schema:
    - analysis_results table with JSONB result_data column
    - Indexed by project_id, task_id, analysis_type, timestamp
    """

    def __init__(self, persistence: SQLitePersistence):
        self.persistence = persistence
        self._ensure_schema()

    async def save_result(self, result: AnalysisResult) -> None:
        """Store an analysis result."""

    async def get_result(
        self,
        project_id: str,
        task_id: Optional[str],
        analysis_type: str
    ) -> Optional[AnalysisResult]:
        """
        Retrieve most recent analysis result.

        Returns None if no analysis exists.
        """

    async def get_all_results_for_project(
        self, project_id: str
    ) -> list[AnalysisResult]:
        """Get all analysis results for a project."""

    async def clear_results_for_project(self, project_id: str) -> None:
        """Delete all analysis results for a project (for re-analysis)."""
```

**Tests:** `tests/unit/analysis/test_analysis_store.py`
- `test_save_and_retrieve_result()`
- `test_get_nonexistent_result()`
- `test_get_all_results_for_project()`
- `test_clear_results()`

---

### 1.4: `src/analysis/progress.py`

**Purpose:** Real-time progress reporting

```python
"""
Progress reporting for long-running analysis operations.

Analysis can take 30+ seconds for large projects. Emit progress events
so UIs can show status.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional


@dataclass
class ProgressEvent:
    """Progress update event."""

    operation: str  # "analyze_project", "requirement_divergence", etc.
    current: int  # Items processed
    total: int  # Total items
    percentage: float  # 0.0-100.0
    message: str  # Human-readable status
    timestamp: datetime


class ProgressReporter:
    """
    Emit progress events during analysis.

    Usage:
    >>> reporter = ProgressReporter(callback=print_progress)
    >>> reporter.start("Analyzing requirements", total=10)
    >>> for i in range(10):
    ...     reporter.update(i+1, f"Analyzed task {i+1}")
    >>> reporter.complete("Analysis complete")
    """

    def __init__(self, callback: Optional[Callable[[ProgressEvent], None]] = None):
        self.callback = callback
        self.current_operation: Optional[str] = None
        self.total_items: int = 0
        self.current_item: int = 0

    def start(self, operation: str, total: int) -> None:
        """Start tracking an operation."""

    def update(self, current: int, message: str) -> None:
        """Update progress."""

    def complete(self, message: str) -> None:
        """Mark operation complete."""

    def _emit(self, event: ProgressEvent) -> None:
        """Emit event to callback."""
```

**Tests:** `tests/unit/analysis/test_progress.py`
- `test_progress_start_update_complete()`
- `test_progress_percentage_calculation()`
- `test_callback_invocation()`

---

## Phase 2: Analysis Modules (Days 3-5)

### 2.1: Base Analyzer

**File:** `src/analysis/analyzers/base.py`

```python
"""
Base class for all analyzers.

Provides common functionality:
- LLM prompt construction
- Citation extraction
- Schema validation
- Error handling
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
from src.core.ai_engine import AIEngine
from src.analysis.progress import ProgressReporter


class BaseAnalyzer(ABC):
    """Abstract base for all analysis modules."""

    def __init__(
        self,
        ai_engine: AIEngine,
        progress_reporter: Optional[ProgressReporter] = None
    ):
        self.ai = ai_engine
        self.progress = progress_reporter or ProgressReporter()

    @abstractmethod
    async def analyze(self, *args, **kwargs) -> Any:
        """Subclasses implement specific analysis logic."""

    def _validate_citations(self, analysis_result: dict[str, Any]) -> None:
        """
        Ensure all claims have proper citations.

        Raises ValueError if citations are missing or malformed.
        """

    def _extract_confidence(self, llm_response: str) -> float:
        """Parse confidence score from LLM response."""

    async def _call_llm_with_retry(
        self, prompt: str, retries: int = 3
    ) -> str:
        """Call LLM with automatic retry on transient failures."""
```

---

### 2.2: Requirement Divergence Analyzer

**File:** `src/analysis/analyzers/requirement.py`

```python
"""
Requirement Divergence Analyzer.

Compares original task descriptions to implementation artifacts to
identify semantic gaps.
"""

from dataclasses import dataclass
from typing import Optional
from src.analysis.analyzers.base import BaseAnalyzer
from src.analysis.aggregator import TaskHistory


@dataclass
class Divergence:
    """A specific divergence from requirements."""

    requirement: str  # What was required
    implementation: str  # What was actually implemented
    severity: str  # "critical", "major", "minor"
    citation: str  # Line/section reference
    impact: str  # How this affects functionality


@dataclass
class RequirementDivergenceAnalysis:
    """Analysis of how implementation diverged from requirements."""

    task_id: str
    fidelity_score: float  # 0.0-1.0
    divergences: list[Divergence]
    raw_data: dict[str, Any]  # Original task + artifacts
    llm_interpretation: str  # LLM's explanation
    recommendations: list[str]
    confidence: float
    llm_model: str
    tokens_used: int


class RequirementDivergenceAnalyzer(BaseAnalyzer):
    """
    Analyze whether implementation matches requirements.

    Uses LLM to perform semantic comparison (not just text diff).
    """

    async def analyze_task(
        self, task: TaskHistory
    ) -> RequirementDivergenceAnalysis:
        """
        Analyze a single task's requirement fidelity.

        Parameters
        ----------
        task : TaskHistory
            Task with description and artifacts

        Returns
        -------
        RequirementDivergenceAnalysis
            Analysis with fidelity score, divergences, and recommendations
        """

    async def analyze_all_tasks(
        self, project_id: str
    ) -> list[RequirementDivergenceAnalysis]:
        """
        Analyze all tasks in a project.

        Emits progress events via ProgressReporter.
        """

    def _build_prompt(self, task: TaskHistory) -> str:
        """
        Construct LLM prompt for requirement analysis.

        Includes:
        - Original task description
        - Implementation artifacts
        - Architectural decisions
        - Task outcome
        - Output format specification
        """
        return f"""
You are analyzing whether a software implementation matches its original requirements.

ORIGINAL REQUIREMENT:
{task.description}

IMPLEMENTATION:
{self._format_artifacts(task.artifacts)}

ARCHITECTURAL DECISIONS MADE:
{self._format_decisions(task.decisions_made)}

TASK OUTCOME:
Status: {task.outcome.success if task.outcome else "unknown"}
Blockers: {task.outcome.blockers if task.outcome else "none"}

YOUR TASK:
1. Identify any divergences between requirement and implementation
2. For each divergence:
   - Quote the specific requirement text
   - Quote the specific implementation code/design
   - Assess severity: critical (changes core functionality), major
     (changes behavior significantly), minor (cosmetic/optimization)
   - Cite line numbers, decision IDs, timestamps
   - Explain impact on functionality
3. Calculate fidelity score (0.0 = complete divergence, 1.0 = perfect match)
4. Provide actionable recommendations

OUTPUT FORMAT: JSON
{{
  "fidelity_score": 0.0-1.0,
  "divergences": [
    {{
      "requirement": "exact quote",
      "implementation": "exact quote with line ref",
      "severity": "critical|major|minor",
      "citation": "line X, decision dec_uuid_Y at timestamp Z",
      "impact": "description"
    }}
  ],
  "recommendations": ["action 1", "action 2"],
  "confidence": 0.0-1.0,
  "confidence_rationale": "explanation"
}}

Be thorough and cite specific evidence. If implementation matches
requirements, state this clearly and give high fidelity score.
"""
```

**Tests:** `tests/unit/analysis/analyzers/test_requirement_analyzer.py`
- `test_analyze_task_perfect_match()` - Fidelity score 1.0
- `test_analyze_task_critical_divergence()` - OAuth → JWT example
- `test_output_schema_validation()` - JSON structure correct
- `test_citations_present()` - All divergences have citations
- `test_consistency()` - Same input → similar output
- `test_golden_example_auth_mismatch()` - Regression test

**Golden Example:** `tests/fixtures/golden_examples/auth_mismatch_analysis.json`

---

### 2.3: Decision Impact Tracer

**File:** `src/analysis/analyzers/decision.py`

```python
"""
Decision Impact Tracer.

Traces architectural decisions to downstream task outcomes to determine
if decisions caused failures or unexpected consequences.
"""

from dataclasses import dataclass
from src.analysis.analyzers.base import BaseAnalyzer
from src.core.project_history import Decision


@dataclass
class DecisionImpactAnalysis:
    """Analysis of decision's downstream impact."""

    decision_id: str
    decision_was_sound: bool
    affected_tasks_count: int
    success_rate: float  # Of affected tasks
    blockers_caused: list[str]
    unexpected_consequences: list[str]
    raw_data: dict[str, Any]
    llm_interpretation: str
    recommendations: list[str]
    confidence: float


class DecisionImpactTracer(BaseAnalyzer):
    """
    Analyze impact of architectural decisions.

    Determines if decisions led to failures or unexpected consequences.
    """

    async def analyze_decision(
        self, decision: Decision, project_history
    ) -> DecisionImpactAnalysis:
        """Analyze impact of a single decision."""

    async def analyze_all_decisions(
        self, project_id: str
    ) -> list[DecisionImpactAnalysis]:
        """Analyze all decisions in a project."""
```

**LLM Prompt Structure:**
- Decision details (what, why, confidence)
- Affected tasks and their outcomes
- Ask LLM to assess soundness and identify consequences

**Tests:** Similar pattern to requirement analyzer

---

### 2.4: Instruction Quality Analyzer

**File:** `src/analysis/analyzers/instruction.py`

```python
"""
Instruction Quality Analyzer.

Assesses whether task instructions (from get_task_context) were clear,
complete, and actionable.
"""

from dataclasses import dataclass
from src.analysis.analyzers.base import BaseAnalyzer


@dataclass
class InstructionQualityAnalysis:
    """Analysis of instruction clarity and completeness."""

    task_id: str
    clarity_score: float  # 0.0-1.0
    completeness_score: float  # 0.0-1.0
    missing_information: list[str]
    ambiguities: list[str]
    raw_data: dict[str, Any]
    llm_interpretation: str
    improvement_suggestions: list[str]
    confidence: float


class InstructionQualityAnalyzer(BaseAnalyzer):
    """
    Analyze quality of task instructions.

    Identifies missing information and ambiguities that led to blockers.
    """

    async def analyze_task_instructions(
        self, task: TaskHistory
    ) -> InstructionQualityAnalysis:
        """Analyze instructions for a single task."""
```

**LLM Prompt Structure:**
- Instructions received (from task context)
- Task outcome (success/failure, duration, blockers)
- Ask LLM to identify gaps and ambiguities

---

### 2.5: Failure Diagnosis Generator

**File:** `src/analysis/analyzers/failure.py`

```python
"""
Failure Diagnosis Generator.

Generates natural language explanation of why a feature failed, tracing
the complete failure chain.
"""

from dataclasses import dataclass
from src.analysis.analyzers.base import BaseAnalyzer


@dataclass
class FailureDiagnosis:
    """Natural language diagnosis of failure."""

    feature_name: str
    diagnosis: str  # Natural language explanation
    task_chain: list[str]  # Sequence of tasks leading to failure
    root_causes: list[str]  # Specific root causes identified
    raw_evidence: dict[str, Any]  # All supporting data
    recommendations: list[str]
    confidence: float


class FailureDiagnosisGenerator(BaseAnalyzer):
    """
    Generate natural language failure diagnosis.

    Input: "Why doesn't feature X work?"
    Output: Plain English explanation with failure chain.
    """

    async def diagnose_failure(
        self, project_id: str, feature_name: str
    ) -> FailureDiagnosis:
        """
        Diagnose why a feature failed.

        Parameters
        ----------
        project_id : str
            Project identifier
        feature_name : str
            User's description of failing feature (e.g., "login")

        Returns
        -------
        FailureDiagnosis
            Complete diagnosis with failure chain
        """
```

**LLM Prompt Structure:**
- User query ("Why doesn't X work?")
- All related tasks, decisions, artifacts
- Ask LLM to build causal chain and identify root cause

---

## Phase 3: Coordinator & Integration (Day 6)

### 3.1: `src/analysis/coordinator.py`

```python
"""
Post-Project Analysis Coordinator.

Orchestrates all analysis modules and provides unified API.
"""

from src.analysis.query_api import ProjectHistoryQuery
from src.analysis.analyzers.requirement import RequirementDivergenceAnalyzer
from src.analysis.analyzers.decision import DecisionImpactTracer
from src.analysis.analyzers.instruction import InstructionQualityAnalyzer
from src.analysis.analyzers.failure import FailureDiagnosisGenerator
from src.core.ai_engine import AIEngine


class PostProjectAnalyzer:
    """
    Orchestrates all Phase 2 analysis modules.

    This is the main entry point for Phase 2 functionality.
    """

    def __init__(
        self,
        query_api: ProjectHistoryQuery,
        ai_engine: AIEngine
    ):
        self.query = query_api
        self.ai = ai_engine

        # Initialize analyzers
        self.requirement_analyzer = RequirementDivergenceAnalyzer(ai_engine)
        self.decision_tracer = DecisionImpactTracer(ai_engine)
        self.instruction_analyzer = InstructionQualityAnalyzer(ai_engine)
        self.failure_diagnoser = FailureDiagnosisGenerator(ai_engine)

    async def analyze_project(
        self, project_id: str
    ) -> ProjectAnalysis:
        """
        Run complete analysis on a project.

        Returns all 4 analysis types for entire project.
        """

    async def answer_fundamental_questions(
        self, project_id: str
    ) -> FundamentalQuestions:
        """
        Answer the three fundamental questions:

        1. Did we build what we said we would?
        2. Does it align with what the user wanted?
        3. Does it actually work?

        Returns structured answers with evidence.
        """
```

---

### 3.2: `src/marcus_mcp/tools/analysis.py`

```python
"""
MCP tools for Phase 2 analysis.

Exposes analysis functions to agents via MCP protocol.
"""

async def analyze_project_requirements(
    project_id: str,
    state: MarcusState
) -> dict[str, Any]:
    """
    Analyze requirement fidelity for all tasks in a project.

    Returns requirement divergence analysis with fidelity scores.
    """

async def trace_decision_impact(
    project_id: str,
    decision_id: str,
    state: MarcusState
) -> dict[str, Any]:
    """
    Trace impact of a specific decision.

    Returns decision impact analysis showing downstream effects.
    """

async def diagnose_failure(
    project_id: str,
    feature_name: str,
    state: MarcusState
) -> dict[str, Any]:
    """
    Diagnose why a feature failed.

    Returns natural language diagnosis with failure chain.
    """

async def answer_fundamental_questions(
    project_id: str,
    state: MarcusState
) -> dict[str, Any]:
    """
    Answer the three fundamental questions for a project.

    Returns structured responses to:
    1. Did we build what we said we would?
    2. Does it align with what the user wanted?
    3. Does it actually work?
    """
```

---

## Testing Strategy

### Unit Tests (80%+ coverage target)

**Schema Validation:**
- Every analysis output must match defined dataclass
- JSON responses must parse correctly
- All fields must be present

**Citation Validation:**
- Every divergence/claim must have citation
- Citations must include task/decision IDs
- Citations must include timestamps

**Consistency:**
- Same input → similar output (within 10% variance)
- Multiple runs should identify same issues

**Golden Examples:**
- 4 regression tests (one per analysis type)
- Known inputs with expected outputs
- Verify analysis detects known issues

### Integration Tests

**End-to-End Pipeline:**
- Load Phase 1 data → Run all 4 analyzers → Verify results
- Test with real project data
- Ensure all modules work together

**MCP Tool Integration:**
- Call MCP tools from agent context
- Verify responses match schema
- Test error handling

---

## Implementation Order

### Day 1: Helper Functions
1. ✅ Create file structure
2. ✅ Implement `helpers.py` (async generators)
3. ✅ Write tests for helpers
4. ✅ Implement `progress.py`
5. ✅ Write tests for progress

### Day 2: Storage & Indexing
1. ✅ Implement `analysis_store.py`
2. ✅ Write tests for storage
3. ✅ Implement `indexer.py` (optional optimization)
4. ✅ Write tests for indexer

### Day 3: Requirement Analyzer
1. ✅ Implement `base.py`
2. ✅ Implement `requirement.py`
3. ✅ Write LLM prompts
4. ✅ Create golden example
5. ✅ Write all tests
6. ✅ Run tests, iterate

### Day 4: Decision & Instruction Analyzers
1. ✅ Implement `decision.py`
2. ✅ Write tests
3. ✅ Implement `instruction.py`
4. ✅ Write tests

### Day 5: Failure Diagnoser
1. ✅ Implement `failure.py`
2. ✅ Write tests
3. ✅ Test with real project

### Day 6: Coordinator & Integration
1. ✅ Implement `coordinator.py`
2. ✅ Implement MCP tools
3. ✅ Integration tests
4. ✅ Example script

### Day 7: Polish & Documentation
1. ✅ Run mypy strict mode
2. ✅ Verify 80%+ coverage
3. ✅ Write documentation
4. ✅ Create PR

---

## Success Criteria

Phase 2 is complete when:

✅ Four analysis modules implemented and tested
✅ All LLM outputs include proper citations
✅ All analysis results pair raw data with interpretation
✅ Schema validation tests passing
✅ Regression tests with golden examples passing
✅ Human validation on 5+ real projects shows analysis is helpful
✅ 80%+ test coverage for analysis pipeline
✅ Mypy strict mode compliance
✅ Documentation with example analyses

---

## Risk Mitigation

**Risk:** LLM outputs are non-deterministic
**Mitigation:** Test pipeline structure, not content; use golden examples

**Risk:** Analysis is slow (LLM calls)
**Mitigation:** Progress reporting; async/concurrent analysis; caching

**Risk:** Large projects exceed context window
**Mitigation:** Selective context (only relevant tasks/decisions)

**Risk:** Phase 1 data quality issues
**Mitigation:** Validation layer; graceful degradation; report data gaps

---

## Next Steps After Phase 2

- Phase 3: Cato UI integration
- Historical mode vs Live monitoring
- Interactive visualization
- User feedback collection
