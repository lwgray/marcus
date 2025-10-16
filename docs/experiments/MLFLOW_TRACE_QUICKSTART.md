# MLflow Trace Quick Reference

## 🚀 Quick Start (3 Steps)

### 1. Import
```python
from mlflow_tracing import trace_agent_task, trace_llm_call, TracedExperiment
```

### 2. Add Decorators
```python
@trace_agent_task("task_name")
def my_task(input_data):
    result = do_work(input_data)
    return result

@trace_llm_call(model="claude-sonnet-4-5", operation="generate")
def call_llm(prompt):
    response = llm.generate(prompt)
    return response
```

### 3. Wrap Experiment
```python
with TracedExperiment("my_experiment", run_name="run_1") as exp:
    exp.log_param("agent_count", 3)
    result = my_task(data)
    exp.log_metric("accuracy", result.score)
```

---

## 📋 Common Patterns

### Pattern 1: Trace Agent Workflow
```python
@trace_agent_task("complete_task")
def complete_task(task):
    # Design
    design = create_design(task)

    # Implement
    code = implement(design)

    # Test
    results = test(code)

    return results
```

### Pattern 2: Trace LLM with Token Tracking
```python
@trace_llm_call(model="claude-sonnet-4-5", operation="code_gen")
def generate_code(prompt):
    response = anthropic.messages.create(
        model="claude-sonnet-4.5-20250929",
        messages=[{"role": "user", "content": prompt}]
    )

    return {
        "content": response.content[0].text,
        "usage": {
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens
        }
    }
```

### Pattern 3: Nested Spans
```python
import mlflow
from mlflow.entities import SpanType

def complex_workflow(task):
    with mlflow.start_span(name="phase_1", span_type=SpanType.CHAIN) as span:
        span.set_attribute("phase", "design")
        result1 = do_phase_1()

    with mlflow.start_span(name="phase_2", span_type=SpanType.CHAIN) as span:
        span.set_attribute("phase", "implement")
        result2 = do_phase_2(result1)

    return result2
```

### Pattern 4: Marcus MCP Integration
```python
from mlflow_tracing import TracedExperiment, trace_agent_task

with TracedExperiment("marcus_experiment") as exp:

    @trace_agent_task("register")
    def register():
        return marcus.register_agent(
            agent_id="agent-1",
            name="Agent 1",
            role="Developer",
            skills=["python", "api"]
        )

    @trace_agent_task("execute_task")
    def execute_task():
        task = marcus.request_next_task(agent_id="agent-1")
        result = implement(task)
        marcus.report_task_progress(
            agent_id="agent-1",
            task_id=task["id"],
            status="completed"
        )
        return result

    register()
    result = execute_task()
    exp.log_metric("tasks_completed", 1)
```

---

## 🎯 Span Types

- **`SpanType.AGENT`** - Agent task execution
- **`SpanType.LLM`** - LLM API calls
- **`SpanType.TOOL`** - Tool/function calls
- **`SpanType.CHAIN`** - Sequential workflow steps

---

## 📊 Logging Metrics

```python
with TracedExperiment("experiment") as exp:
    # Parameters (static config)
    exp.log_param("agent_count", 5)
    exp.log_param("model", "claude-sonnet-4-5")

    # Metrics (numerical values)
    exp.log_metric("accuracy", 0.95)
    exp.log_metric("tokens_used", 1000)
    exp.log_metric("latency_ms", 234.5)

    # Tags (metadata)
    exp.set_tag("environment", "production")
    exp.set_tag("version", "1.0.0")

    # Artifacts (files)
    exp.log_artifact("results.json")
```

---

## 🔍 Viewing Traces

### 1. Start MLflow UI
```bash
mlflow ui --port 5000
```

### 2. Open Browser
http://localhost:5000

### 3. Navigate
1. Click your experiment name
2. Select a run
3. Click "Traces" tab
4. Explore the trace tree

---

## 📝 Custom Attributes

```python
with mlflow.start_span(name="my_span") as span:
    # Add metadata
    span.set_attribute("user_id", "user123")
    span.set_attribute("priority", "high")
    span.set_attribute("retry_count", 3)

    # Add inputs
    span.set_inputs({"query": "search term"})

    # Do work
    result = do_work()

    # Add outputs
    span.set_outputs({"result_count": len(result)})
```

---

## ⚡ Examples

### Run Provided Examples
```bash
# Basic tracing example
python experiments/traced_agent_example.py

# View your existing experiment data
python view_experiment_data.py
```

### Files Created
- `mlflow_tracing.py` - Core tracing utilities
- `experiments/traced_agent_example.py` - Full examples
- `MLFLOW_TRACE_INTEGRATION_GUIDE.md` - Detailed guide
- `view_experiment_data.py` - Query experiment data

---

## 🐛 Troubleshooting

**Traces not appearing?**
- Ensure MLflow UI is running: `mlflow ui --port 5000`
- Check experiment name matches
- Verify `mlruns/` directory exists

**Performance issues?**
- Reduce span granularity
- Don't trace trivial operations
- Use sampling for high-frequency operations

**Missing token counts?**
- Ensure LLM response includes `usage` field
- Format: `{"usage": {"prompt_tokens": X, "completion_tokens": Y}}`

---

## 📚 Resources

- **Integration Guide**: `MLFLOW_TRACE_INTEGRATION_GUIDE.md`
- **MLflow UI**: http://localhost:5000
- **Example Code**: `experiments/traced_agent_example.py`
- **MLflow Docs**: https://mlflow.org/docs/latest/llms/tracing/

---

## ✅ Checklist

- [ ] Install MLflow: `pip install mlflow>=2.9.0`
- [ ] Import utilities: `from mlflow_tracing import ...`
- [ ] Add decorators to functions
- [ ] Wrap experiments with `TracedExperiment`
- [ ] Start MLflow UI: `mlflow ui --port 5000`
- [ ] Run your code
- [ ] View traces at http://localhost:5000
