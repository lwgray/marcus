# Phase 2: LLM-Powered Analysis Engine

## Overview

Phase 2 builds intelligent analysis on top of Phase 1's data foundation by:
1. Using LLMs to understand **why** things went wrong (not just **what** happened)
2. Always presenting **raw data + LLM interpretation** for transparency
3. Generating actionable insights with specific citations
4. Creating modular analyzers for different failure modes

**Duration:** 5-7 days
**Dependencies:** Phase 1 complete
**Deliverable:** Analysis API that answers "why?" questions with citations

## Core Principle: Raw Data + Interpretation

**CRITICAL:** Never show LLM interpretation alone. Always pair with raw data.

### Anti-Pattern (Bad)
```
Analysis: "The login feature failed because the agent used the wrong API version."
```

**Users can't verify this claim!**

### Correct Pattern (Good)
```
RAW DATA:
  Task: task_login_implement
  Status: Completed
  Instructions Received:
    - Context from task_auth_design: {api_version: "v1"}
  Implementation:
    - Used endpoint: /api/v1/auth/login
  Test Result: FAILED - 401 Unauthorized

  Dependency: task_auth_design
  Status: Completed (with blocker)
  Blocker: "Missing v2 API docs" (2025-11-03 14:23)
  Decision: "Proceeding with v1 API from cached docs"
    Logged by: agent_designer_1
    Timestamp: 2025-11-03 14:25

LLM INTERPRETATION:
  The login implementation failed because:

  1. The design task (task_auth_design) was blocked waiting for v2 API docs
  2. Agent_designer_1 made a fallback decision to use v1 API instead
  3. This decision was logged at 2025-11-03 14:25 in the design task
  4. The implementation task received {api_version: "v1"} in its context
  5. However, the production API had already migrated to v2
  6. Result: 401 Unauthorized due to API version mismatch

  ROOT CAUSE: Blocked design task led to stale context being provided to
  implementation. The agent correctly followed instructions but was given
  outdated information.

  RECOMMENDATION: When design tasks are blocked, do not proceed with
  dependent implementation tasks. Either wait for blocker resolution or
  explicitly mark implementation as "provisional/may need rework."
```

**Users can now:**
- Verify the LLM's reasoning against raw data
- Spot errors in interpretation
- Understand the full context
- Trust the analysis

## Analysis Modules

### Module 1: Requirement Divergence Analyzer

**Purpose:** Determine if implementation matches original requirements semantically

**Input:**
- Original task description (from Kanban)
- Implementation artifacts (code, designs, specs)
- Task outcome (success/failure, blockers)

**Output:**
```python
@dataclass
class RequirementDivergenceAnalysis:
    """Analysis of how implementation diverged from requirements."""

    task_id: str
    fidelity_score: float  # 0.0-1.0
    divergences: list[Divergence]
    raw_data: Dict[str, Any]
    llm_interpretation: str
    recommendations: list[str]


@dataclass
class Divergence:
    """A specific divergence from requirements."""

    requirement: str  # What was required
    implementation: str  # What was actually implemented
    severity: str  # "critical", "major", "minor"
    citation: str  # Line/section reference
    impact: str  # How this affects functionality
```

**Example Output:**
```
RAW DATA:
  Task Description:
    "Implement user login with OAuth2 authentication using GitHub provider.
     Users should be redirected to GitHub, authorize the app, and return
     with an access token."

  Implementation Artifact: src/auth/login.py
    Lines 45-67:
    ```python
    @app.post("/login")
    async def login(username: str, password: str):
        user = await db.get_user(username)
        if user and verify_password(password, user.hashed_password):
            return {"token": create_jwt(user.id)}
        raise HTTPException(401, "Invalid credentials")
    ```

  Decision: "Use JWT auth instead of OAuth2"
    Rationale: "Simpler to implement, fewer external dependencies"
    Logged by: agent_worker_1
    Timestamp: 2025-11-04 10:15

LLM INTERPRETATION:
  CRITICAL DIVERGENCE DETECTED (Fidelity Score: 0.2/1.0)

  Requirement: OAuth2 authentication via GitHub provider
  Implementation: Username/password authentication with JWT

  This is a fundamental divergence from requirements. The specification
  explicitly requested OAuth2 (third-party auth) but the implementation
  used traditional credentials (username/password).

  ROOT CAUSE:
  Agent_worker_1 made an architectural decision (cited above) to use JWT
  instead of OAuth2, citing "simpler to implement." However, this decision
  fundamentally changes the authentication model from third-party to
  first-party, which may not align with product requirements.

  IMPACT:
  - Users cannot log in with GitHub accounts
  - Application now requires user registration and password management
  - Security implications: password storage, reset flows, etc.
  - Integration with GitHub API may not work (if it relied on OAuth tokens)

  RECOMMENDATIONS:
  1. Clarify with stakeholders if OAuth2 is required or negotiable
  2. If OAuth2 is required, reimplement using OAuth2 flow
  3. If JWT is acceptable, update original requirements to reflect this
  4. Add validation: agent decisions that change authentication strategy
     should require explicit approval before implementation proceeds
```

**LLM Prompt Structure:**
```python
async def analyze_requirement_divergence(
    task: TaskHistory,
    artifacts: list[Artifact]
) -> RequirementDivergenceAnalysis:
    """Use LLM to analyze requirement-implementation divergence."""

    prompt = f"""
    You are analyzing whether a software implementation matches its original requirements.

    ORIGINAL REQUIREMENT:
    {task.description}

    IMPLEMENTATION:
    {artifacts[0].content if artifacts else "No artifacts found"}

    ARCHITECTURAL DECISIONS MADE:
    {json.dumps([d.to_dict() for d in task.decisions_made], indent=2)}

    TASK OUTCOME:
    Status: {task.outcome.success}
    Blockers: {task.outcome.blockers}
    Actual vs Estimated: {task.actual_hours}h vs {task.estimated_hours}h

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
      "recommendations": ["action 1", "action 2"]
    }}

    Be thorough and cite specific evidence. If implementation matches
    requirements, state this clearly and give high fidelity score.
    """

    response = await ai_engine.analyze(prompt)
    analysis_result = json.loads(response.content)

    return RequirementDivergenceAnalysis(
        task_id=task.task_id,
        fidelity_score=analysis_result["fidelity_score"],
        divergences=[Divergence(**d) for d in analysis_result["divergences"]],
        raw_data={
            "task_description": task.description,
            "artifacts": [a.to_dict() for a in artifacts],
            "decisions": [d.to_dict() for d in task.decisions_made],
            "outcome": task.outcome.to_dict()
        },
        llm_interpretation=response.reasoning,
        recommendations=analysis_result["recommendations"]
    )
```

### Module 2: Decision Impact Tracer

**Purpose:** Determine if architectural decisions caused downstream failures

**Input:**
- Decision with rationale
- Tasks affected by decision (from dependency graph)
- Outcomes of affected tasks

**Output:**
```python
@dataclass
class DecisionImpactAnalysis:
    """Analysis of decision's downstream impact."""

    decision_id: str
    decision_was_sound: bool
    affected_tasks_count: int
    success_rate: float
    blockers_caused: list[str]
    unexpected_consequences: list[str]
    raw_data: Dict[str, Any]
    llm_interpretation: str
```

**Example Output:**
```
RAW DATA:
  Decision: dec_uuid_012
    What: "Use Redis for session storage instead of PostgreSQL"
    Why: "Redis is faster for read-heavy workloads, reduces DB load"
    Logged by: agent_architect_1
    Timestamp: 2025-11-02 11:00
    Confidence: 0.85

  Affected Tasks:
    1. task_session_implement
       Status: Completed
       Outcome: Success
       Duration: 2.5h (estimated 3h)

    2. task_logout_implement
       Status: Completed with blocker
       Outcome: Success (after blocker resolved)
       Blocker: "Redis connection timeout in test environment"
       Resolution: "Added Redis instance to test docker-compose"
       Duration: 4h (estimated 2h)

    3. task_load-test_implement
       Status: Failed
       Outcome: Failure
       Blocker: "Sessions not persisting across app restarts"
       Reason: "Redis configured in-memory only, no persistence"

  Overall Impact:
    - 3 tasks affected
    - 2 succeeded, 1 failed
    - Success rate: 66.7%
    - Total extra hours: 3.5h (blocker + debugging)

LLM INTERPRETATION:
  DECISION ASSESSMENT: Partially sound, but incomplete

  The decision to use Redis was technically reasonable:
  ✅ Redis is indeed faster for session reads (good rationale)
  ✅ Reduces PostgreSQL load (benefit achieved)
  ✅ Implementation task succeeded efficiently

  However, the decision lacked important considerations:
  ❌ Test environment Redis setup not addressed (caused blocker)
  ❌ Redis persistence not configured (caused test failure)
  ❌ Session data durability requirements not analyzed

  UNEXPECTED CONSEQUENCES:
  1. Test infrastructure complexity: Required Redis in test docker-compose,
     adding 2h of unplanned work (task_logout_implement blocker)

  2. Data persistence issue: Sessions lost on app restart because Redis
     was configured in-memory only. This violates implied requirement that
     "users stay logged in across server restarts"

  ROOT CAUSE OF FAILURE:
  The decision was made at 0.85 confidence but didn't consider operational
  concerns (test setup, persistence). The architect focused on performance
  but not durability.

  RECOMMENDATIONS:
  1. When making infrastructure decisions, explicitly address:
     - Development/test environment setup
     - Data persistence requirements
     - Operational concerns (backups, failover, etc.)

  2. For decisions with confidence < 0.9, require explicit checklist:
     [ ] Test environment impact analyzed
     [ ] Data durability requirements confirmed
     [ ] Operational runbook updated

  3. For this specific issue:
     - Configure Redis with AOF persistence
     - Document session expiration policy
     - Add monitoring for session store health
```

### Module 3: Instruction Quality Analyzer

**Purpose:** Assess if task instructions were clear and complete

**Input:**
- Instructions provided to agent (from `get_task_context`)
- Task outcome (success/failure, duration, blockers)
- Agent feedback (if any)

**Output:**
```python
@dataclass
class InstructionQualityAnalysis:
    """Analysis of instruction clarity and completeness."""

    task_id: str
    clarity_score: float  # 0.0-1.0
    completeness_score: float  # 0.0-1.0
    missing_information: list[str]
    ambiguities: list[str]
    raw_data: Dict[str, Any]
    llm_interpretation: str
    improvement_suggestions: list[str]
```

**Example Output:**
```
RAW DATA:
  Instructions Received (from get_task_context):
    Task: task_payment_implement
    Description: "Implement payment processing"

    Context from Dependencies:
      - task_payment_design artifact: payment_design.md
        Summary: "Use Stripe API, support credit cards"

      - Decision from task_api_design:
        "All API endpoints must validate JWT tokens"

    No other context provided.

  Task Outcome:
    Status: Completed with blocker
    Blocker 1: "Which Stripe API version?" (2h lost)
    Blocker 2: "Test credit card numbers unclear" (1h lost)
    Blocker 3: "Unclear if webhooks needed for async confirmation" (3h lost)
    Duration: 12h (estimated 6h)
    Success: Eventually yes, but with significant delays

LLM INTERPRETATION:
  INSTRUCTION QUALITY: Poor (Clarity: 0.4, Completeness: 0.3)

  MISSING CRITICAL INFORMATION:
  1. Stripe API Version
     - Design said "Use Stripe API" but didn't specify v1 or v2
     - Agent blocked for 2h researching which to use
     - Eventually chose v2, but decision should have been made in design

  2. Test Environment Setup
     - No test API keys provided
     - No documentation of test card numbers
     - Agent blocked 1h finding Stripe test docs

  3. Webhook Requirements
     - Design didn't specify if async payment confirmation needed
     - Agent unsure if webhooks should be implemented
     - Blocked 3h waiting for clarification
     - Eventually implemented webhooks "just in case"

  4. Error Handling Strategy
     - No guidance on retry logic for failed payments
     - No specification of error messages to return
     - Agent made assumptions, may not align with product needs

  AMBIGUITIES:
  1. "Support credit cards" - Amex? Discover? All major brands?
  2. "Payment processing" - One-time only or recurring subscriptions?
  3. "Validate JWT tokens" - How does this interact with Stripe webhooks
     (which don't have JWT)?

  IMPACT ON EXECUTION:
  - 6h of blockers (100% time overrun) due to unclear instructions
  - Agent made assumptions that may not match requirements
  - Uncertainty led to over-implementation (webhooks might not be needed)

  ROOT CAUSE:
  The design task (task_payment_design) provided high-level guidance but
  lacked implementation-ready details. The instruction was sufficient for
  understanding WHAT to build but not HOW to build it.

  IMPROVEMENT SUGGESTIONS:
  1. Design artifacts should include:
     [ ] Specific library/API versions
     [ ] Test environment setup instructions
     [ ] Error handling strategy
     [ ] Edge case handling
     [ ] Acceptance criteria (when is it "done"?)

  2. Before marking design as complete, validate it answers:
     "Could an implementer start coding immediately without asking questions?"

  3. For this specific task, the design should have specified:
     - Stripe API v2 (payment_intents)
     - Test mode API keys: sk_test_xxx, pk_test_xxx
     - Test cards: 4242 4242 4242 4242 (success), 4000 0000 0000 0002 (decline)
     - Webhooks required: payment_intent.succeeded, payment_intent.failed
     - Retry strategy: 3 attempts with exponential backoff
```

### Module 4: Failure Diagnosis Generator

**Purpose:** Generate natural language explanation of why a feature failed

**Input:**
- User query: "Why doesn't feature X work?"
- Project history with all tasks, decisions, artifacts

**Output:**
```python
@dataclass
class FailureDiagnosis:
    """Natural language diagnosis of failure."""

    feature_name: str
    diagnosis: str  # Natural language explanation
    task_chain: list[str]  # Sequence of tasks leading to failure
    root_causes: list[str]  # Specific root causes identified
    raw_evidence: Dict[str, Any]  # All supporting data
    recommendations: list[str]
```

**Example Output:**
```
USER QUERY: "Why doesn't the login feature work?"

RAW EVIDENCE:
  Related Tasks:
    1. task_auth_design (completed, no blockers)
    2. task_login_ui_implement (completed, no blockers)
    3. task_login_api_implement (completed with blocker)
    4. task_session_implement (failed)

  Task: task_login_api_implement
    Blocker: "CORS errors in browser" (2025-11-04 15:00)
    Resolution: "Added CORS middleware"
    Artifact: src/api/auth.py

  Task: task_session_implement
    Status: Failed
    Error: "Sessions not persisting across requests"
    Root Cause: "Redis not configured with persistence"
    Logged by: agent_worker_3
    Timestamp: 2025-11-05 09:30

  Decision: dec_uuid_025 (from task_session_implement)
    What: "Skip Redis persistence for now, use in-memory only"
    Why: "Faster to test, can add persistence later"
    Confidence: 0.6
    Impact: Sessions lost when Redis restarts

DIAGNOSIS:
  The login feature doesn't work because user sessions are not persisting
  between browser requests. Here's the failure chain:

  1. USER ACTION: User enters credentials and clicks "Login"

  2. BACKEND (task_login_api_implement): API validates credentials ✅
     - Credentials checked correctly
     - JWT token generated ✅
     - Token returned to browser ✅

  3. SESSION STORAGE (task_session_implement): Session created but not persisted ❌
     - Redis configured in-memory only (decision dec_uuid_025)
     - Session stored successfully initially
     - BUT: Redis container restarted (common in dev environment)
     - Session data lost

  4. SUBSEQUENT REQUEST: Browser sends JWT token
     - API validates token structure ✅
     - API looks up session in Redis ❌
     - Session not found (was lost on Redis restart)
     - API returns 401 Unauthorized
     - User appears "logged out" even though they just logged in

  ROOT CAUSES:
  1. ARCHITECTURAL DECISION: Agent_worker_3 decided to skip Redis
     persistence "to test faster" (decision dec_uuid_025 at 2025-11-05 09:30)

  2. LOW CONFIDENCE: Decision made with only 0.6 confidence, indicating
     uncertainty

  3. ENVIRONMENT INSTABILITY: Development Redis container restarts frequently
     (detected in logs), but this wasn't considered in decision

  4. REQUIREMENT GAP: Original requirements didn't explicitly specify
     "sessions must survive server restart," so agent assumed it was optional

  WHY TESTS DIDN'T CATCH THIS:
  - Tests run in single process, no Redis restarts
  - Integration tests passed because they don't simulate container restarts
  - No explicit acceptance criteria for "session durability"

RECOMMENDATIONS:
  IMMEDIATE FIX:
  1. Configure Redis with AOF persistence:
     ```yaml
     # docker-compose.yml
     redis:
       command: redis-server --appendonly yes
       volumes:
         - redis-data:/data
     ```

  2. Add integration test for session persistence:
     ```python
     async def test_session_survives_redis_restart():
         # Login
         token = await client.post("/login", ...)
         # Restart Redis
         await restart_redis()
         # Verify session still valid
         response = await client.get("/protected", headers={"Authorization": token})
         assert response.status_code == 200
     ```

  PROCESS IMPROVEMENTS:
  1. Require explicit acceptance criteria for "session durability"
  2. Flag low-confidence decisions (< 0.7) for review before proceeding
  3. Add "operational requirements" checklist to design tasks:
     [ ] Data persistence requirements defined
     [ ] Container restart behavior specified
     [ ] Test environment matches production architecture
```

## LLM Prompt Engineering Principles

### 1. Structured Output

Always request JSON output for programmatic processing:

```python
prompt = f"""
... analysis instructions ...

OUTPUT FORMAT: JSON
{{
  "field1": "value",
  "field2": 0.0-1.0,
  "citations": ["source1", "source2"]
}}

Do not include any text before or after the JSON.
"""
```

### 2. Citation Requirements

Require specific citations in every analysis:

```python
prompt = f"""
For every claim you make:
1. Cite the specific data source (task_id, decision_id, timestamp)
2. Quote exact text from source
3. Provide line numbers for code references

Example:
  CLAIM: "Agent used wrong API version"
  CITATION: Decision dec_uuid_123 (2025-11-03 14:25) by agent_worker_1:
            "Proceeding with v1 API" (line 45 of task_auth_design decision log)
  EVIDENCE: Implementation in src/auth.py:67 uses "/api/v1/login" endpoint
"""
```

### 3. Chain-of-Thought Reasoning

Ask LLM to show its reasoning:

```python
prompt = f"""
Analyze the following failure.

STEP 1: Identify all tasks involved
STEP 2: For each task, extract key facts (outcome, blockers, decisions)
STEP 3: Build causal chain (what led to what)
STEP 4: Identify root cause (earliest decision/action that led to failure)
STEP 5: Provide recommendations

Show your work for each step before providing final answer.
"""
```

### 4. Confidence Scores

Ask LLM to indicate confidence:

```python
{
  "analysis": "...",
  "confidence": 0.85,
  "confidence_rationale": "High confidence because we have complete task history with all decisions logged. Would be 1.0 if we had actual code implementation to review."
}
```

## Testing Strategy

### Challenge: How do you test LLM output?

**Approach:** Test the analysis pipeline, not the LLM content

#### 1. Schema Validation Tests

```python
def test_requirement_divergence_output_schema():
    """Verify analysis output matches expected schema."""
    analysis = await analyze_requirement_divergence(task, artifacts)

    assert 0.0 <= analysis.fidelity_score <= 1.0
    assert isinstance(analysis.divergences, list)
    for div in analysis.divergences:
        assert div.severity in ["critical", "major", "minor"]
        assert div.citation  # Must have citation
        assert div.requirement and div.implementation  # Must quote both
```

#### 2. Citation Validation Tests

```python
def test_analysis_includes_citations():
    """Verify LLM output includes proper citations."""
    analysis = await analyze_requirement_divergence(task, artifacts)

    # Every divergence must cite a source
    for div in analysis.divergences:
        # Citation must include task/decision ID
        assert re.search(r'task_[a-z0-9_-]+', div.citation) or \
               re.search(r'dec_uuid_[a-z0-9]+', div.citation)
        # Citation must include timestamp
        assert re.search(r'\d{4}-\d{2}-\d{2}', div.citation)
```

#### 3. Consistency Tests

```python
def test_analysis_consistency():
    """Verify same input produces similar output."""
    # Run analysis twice
    analysis1 = await analyze_requirement_divergence(task, artifacts)
    analysis2 = await analyze_requirement_divergence(task, artifacts)

    # Fidelity scores should be within 10%
    assert abs(analysis1.fidelity_score - analysis2.fidelity_score) < 0.1

    # Should identify same divergences (may differ in wording)
    assert len(analysis1.divergences) == len(analysis2.divergences)
```

#### 4. Regression Tests with Golden Examples

```python
# tests/fixtures/golden_examples/auth_mismatch_analysis.json
{
  "task_description": "Implement OAuth2 login",
  "implementation": "def login(username, password): ...",
  "expected_divergences": [
    {
      "requirement_contains": "OAuth2",
      "implementation_contains": "username.*password",
      "expected_severity": "critical"
    }
  ],
  "expected_fidelity_range": [0.0, 0.3]
}

def test_auth_mismatch_golden_example():
    """Test against known good example."""
    golden = load_golden_example("auth_mismatch_analysis.json")
    analysis = await analyze_requirement_divergence(
        task=golden["task"],
        artifacts=golden["artifacts"]
    )

    # Should detect the critical divergence
    assert any(
        d.severity == "critical" and
        "OAuth2" in d.requirement and
        "password" in d.implementation
        for d in analysis.divergences
    )

    # Fidelity score should be low
    assert golden["expected_fidelity_range"][0] <= \
           analysis.fidelity_score <= \
           golden["expected_fidelity_range"][1]
```

#### 5. Human Validation Tests

For initial development, include human-in-the-loop validation:

```python
@pytest.mark.manual  # Requires human review
def test_failure_diagnosis_makes_sense(real_project_id):
    """
    Generate diagnosis for real failed project and review manually.

    HUMAN REVIEWER:
    1. Read the diagnosis
    2. Check if raw evidence supports LLM claims
    3. Verify citations are accurate
    4. Confirm recommendations are actionable
    5. Mark test as PASS/FAIL based on analysis quality
    """
    diagnosis = await diagnose_failure(
        project_id=real_project_id,
        feature_name="login"
    )

    print("=== RAW EVIDENCE ===")
    print(json.dumps(diagnosis.raw_evidence, indent=2))

    print("\\n=== LLM DIAGNOSIS ===")
    print(diagnosis.diagnosis)

    print("\\n=== RECOMMENDATIONS ===")
    for rec in diagnosis.recommendations:
        print(f"- {rec}")

    # Human marks test result
    human_approved = input("Does this analysis make sense? (y/n): ")
    assert human_approved.lower() == "y"
```

## Integration with Phase 1

Phase 2 builds on Phase 1's query API:

```python
# Analysis coordinator
class PostProjectAnalyzer:
    """Orchestrates all analysis modules."""

    def __init__(
        self,
        query_api: ProjectHistoryQuery,  # From Phase 1
        ai_engine: AIEngine
    ):
        self.query = query_api
        self.ai = ai_engine

        # Analysis modules
        self.requirement_analyzer = RequirementDivergenceAnalyzer(ai_engine)
        self.decision_tracer = DecisionImpactTracer(ai_engine)
        self.instruction_analyzer = InstructionQualityAnalyzer(ai_engine)
        self.failure_diagnoser = FailureDiagnosisGenerator(ai_engine)

    async def analyze_project(self, project_id: str) -> ProjectAnalysis:
        """Run complete analysis on a project."""

        # Load project history (Phase 1)
        history = await self.query.get_project_history(project_id)

        # Run analyses
        task_analyses = []
        for task in history.tasks:
            task_analysis = TaskAnalysis(
                task_id=task.task_id,
                requirement_fidelity=await self.requirement_analyzer.analyze(task),
                instruction_quality=await self.instruction_analyzer.analyze(task),
                decisions_impact=[
                    await self.decision_tracer.analyze(d)
                    for d in task.decisions_made
                ]
            )
            task_analyses.append(task_analysis)

        # Overall project assessment
        overall_assessment = await self._generate_overall_assessment(
            history,
            task_analyses
        )

        return ProjectAnalysis(
            project_id=project_id,
            snapshot=history.snapshot,
            task_analyses=task_analyses,
            overall_assessment=overall_assessment
        )
```

## Success Criteria

Phase 2 is complete when:

✅ Four analysis modules implemented and tested (requirement, decision, instruction, failure)
✅ All LLM outputs include proper citations with timestamps
✅ All analysis results pair raw data with interpretation
✅ Schema validation tests passing for all output formats
✅ Regression tests with golden examples passing
✅ Human validation on 5+ real failed projects shows analysis is helpful
✅ 80%+ test coverage for analysis pipeline (excluding LLM calls)
✅ Mypy strict mode compliance
✅ Documentation with example analyses

## Next Steps

After Phase 2 completion:
1. Generate analysis for several real failed projects
2. Collect user feedback on analysis quality
3. Refine prompts based on failure modes
4. Proceed to Phase 3: Build Cato UI for interactive exploration
