# Fairer Reliability Decay Experiment Design

## Problem with Original Design

The article discusses **direct LLM output → LLM input chains** where unvalidated outputs compound errors.

Our original experiment has agents writing **code files**, which get validated by:
- Python interpreter (syntax checking)
- Git (version control)
- Tests (if written)
- Board state (task completion)

This isn't quite the same as the article's concern about **unstructured LLM outputs** propagating errors.

## Redesigned Experiment: LLM Output Chains

### Project: API Specification Pipeline

**Goal:** Create a complete API specification through sequential LLM generation steps.

#### Sequential Stages (Direct Output Passing)

1. **Schema Generation** (Agent/Stage 1)
   - Input: Business requirements
   - Output: JSON schema defining data models
   - Failure mode: Missing fields, wrong types, inconsistent naming

2. **API Endpoint Specification** (Agent/Stage 2)
   - Input: JSON schema from Stage 1
   - Output: OpenAPI/Swagger spec
   - Failure mode: References non-existent schema fields, wrong HTTP methods

3. **Request/Response Examples** (Agent/Stage 3)
   - Input: OpenAPI spec from Stage 2
   - Output: JSON examples for each endpoint
   - Failure mode: Examples don't match schema, invalid JSON

4. **Test Case Specification** (Agent/Stage 4)
   - Input: Endpoint spec + examples from Stages 2-3
   - Output: Test case descriptions
   - Failure mode: Tests validate wrong behavior

5. **Documentation Generation** (Agent/Stage 5)
   - Input: All previous outputs
   - Output: Markdown documentation
   - Failure mode: Documents incorrect API, propagates all prior errors

#### Why This is Fairer

**Matches the article's model:**
- ✅ Unstructured LLM outputs (JSON, YAML, Markdown)
- ✅ Each stage reads previous stage's raw output
- ✅ No external validation (no compiler, no tests)
- ✅ Errors can propagate silently through the chain

**Failure propagation example:**
```
Stage 1: Schema has typo "user_nane" instead of "user_name"
         ↓
Stage 2: API spec references "user_nane" (propagates error)
         ↓
Stage 3: Examples use "user_nane" (compounds error)
         ↓
Stage 4: Tests validate "user_nane" exists (error now validated!)
         ↓
Stage 5: Docs describe "user_nane" field (error is now documented!)
```

### Comparison: Pipeline vs Marcus

**Pipeline Mode (Article's Model):**
```python
# Pseudo-code
schema = agent_1.generate("Create user schema")
api_spec = agent_2.generate(f"Create API spec for: {schema}")
examples = agent_3.generate(f"Create examples for: {api_spec}")
tests = agent_4.generate(f"Create tests for: {api_spec} and {examples}")
docs = agent_5.generate(f"Document: {api_spec}")

# No validation between stages
# If schema is wrong, everything downstream is wrong
```

**Marcus Mode:**
```python
# Each stage is a task on the Kanban board
# Task 1: Generate schema
#   - Agent A completes
#   - Output saved to board/file
#   - Task marked "Done"

# Task 2: Generate API spec
#   - Agent B waits for Task 1 "Done"
#   - Reads schema from validated source
#   - Board could enforce schema validation before marking Task 1 done
#   - If Agent B finds errors, can report blocker
#   - Task can be reassigned or retried

# Key differences:
# - Explicit task boundaries
# - Validation checkpoints possible
# - Failures are observable (task stays "In Progress" or "Blocked")
# - Can retry without starting from scratch
```

### Metrics to Track

1. **Schema Correctness** (Ground Truth)
   - Compare final schema to reference schema
   - Count: missing fields, type errors, naming inconsistencies

2. **Error Propagation**
   - Track: If Stage 1 has error, does Stage 2 catch it or propagate it?
   - Count: errors introduced per stage

3. **Validation Success Rate**
   - Can final outputs pass validation against reference?
   - Pipeline: Expect exponential decay (0.98^n)
   - Marcus: Expect stable (validation boundaries)

4. **Recovery Capability**
   - Pipeline: Must restart entire chain if any stage fails
   - Marcus: Can retry individual failed tasks

### Injecting Failures (Controlled Experiment)

To make this scientifically rigorous, **inject known errors**:

1. **Control Run**: All agents work normally
   - Measure baseline success rate

2. **Injected Error Run**: Stage 1 produces intentionally flawed schema
   - Measure: Does Stage 2 catch it?
   - Measure: How many stages propagate the error?
   - Measure: Does final output validation fail?

3. **Compare**: Pipeline vs Marcus
   - Pipeline: Expect error to propagate through all stages
   - Marcus: Expect validation boundaries to catch error

### Implementation Changes Needed

**Project Description:**
```markdown
# API Specification Pipeline

Create a complete REST API specification for a task management system.

## Stage 1: Data Schema
Generate JSON schema for:
- User model (id, email, name, created_at)
- Task model (id, title, description, status, assigned_to, due_date)
- Project model (id, name, description, owner)

Output: `schema.json`

## Stage 2: API Endpoints
Generate OpenAPI 3.0 specification with endpoints:
- POST /users (create)
- GET /users/{id}
- GET /tasks (list with filters)
- POST /tasks (create)
- PATCH /tasks/{id} (update)
- GET /projects
- POST /projects

Input: Read `schema.json`
Output: `openapi.yaml`

## Stage 3: Request/Response Examples
Generate realistic JSON examples for each endpoint.

Input: Read `openapi.yaml`
Output: `examples.json`

## Stage 4: Test Scenarios
Generate test case descriptions (not code, just specifications).

Input: Read `openapi.yaml` and `examples.json`
Output: `test_scenarios.md`

## Stage 5: Documentation
Generate user-facing API documentation.

Input: Read all previous outputs
Output: `API_DOCS.md`

## Validation (Post-Experiment)
Compare outputs against reference implementations to measure:
- Schema completeness (all required fields present?)
- API spec correctness (endpoints match schema?)
- Example validity (examples match schema?)
- Test coverage (test scenarios cover all endpoints?)
- Documentation accuracy (docs match actual spec?)
```

### Expected Results

**Article's Model (Pipeline):**
```
Success rate = 0.98^5 = 90.4%
Error propagation: Silent, compounds at each stage
```

**Marcus (Board-Mediated):**
```
Success rate = 96-98% (validation boundaries prevent decay)
Error propagation: Explicit, caught at task boundaries
```

## Conclusion

This redesigned experiment:
1. **Matches the article's threat model** (LLM output chains)
2. **Tests Marcus's actual value proposition** (board-mediated coordination)
3. **Provides fair comparison** (same tasks, different coordination)
4. **Measures the right metrics** (error propagation, not just completion rate)

The original code-writing experiment is still valuable (tests Marcus in real-world scenarios), but this LLM-output-chain experiment directly addresses the article's specific claims.
