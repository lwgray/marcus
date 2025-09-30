# Agent Support Tools: Context, Logging & System Intelligence
## Internal Systems Architecture Deep Dive

Marcus provides agents with **sophisticated support tools** beyond the core workflow (register, request task, report progress, report blockers). These support tools include system connectivity verification (`ping`), contextual intelligence (`get_task_context`), decision audit trail (`log_decision`), artifact tracking (`log_artifact`), and dependency validation (`check_task_dependencies`). This document explains the internal complexity behind these agent support capabilities.

---

## 🎯 **System Overview**

```
Agent Support Tools Architecture
        ↓
Multi-Function Agent Intelligence Support
        ↓
┌─────────────────┬─────────────────┬─────────────────┐
│ System Health   │ Context &       │ Audit & Logging │
│ & Connectivity  │ Dependencies    │ Intelligence    │
└─────────────────┴─────────────────┴─────────────────┘
        ↓                ↓                ↓
┌─────────────────┬─────────────────┬─────────────────┐
│ Ping System     │ Task Context    │ Decision &      │
│ Health Check    │ & Dependency    │ Artifact        │
│                 │ Analysis        │ Tracking        │
└─────────────────┴─────────────────┴─────────────────┘
```

**Core Purpose**: Provide agents with comprehensive support intelligence for connectivity verification, contextual decision-making, and audit compliance.

---

## 🏗️ **Core Agent Support Tools**

### **Tool 1: System Health Verification (`ping`)**
**File**: `src/marcus_mcp/tools/system.py` - `ping` function
**Purpose**: Verify Marcus connectivity and system status for agents

When an agent calls `ping("checking connectivity")`, Marcus performs **intelligent system verification** tailored to the agent's needs:

```python
async def ping(echo: str, state: Any) -> Dict[str, Any]:
    """
    Check Marcus status and connectivity with agent-specific diagnostics.

    For agents, this provides:
    - System connectivity verification
    - Current project status
    - Agent registry confirmation
    - Service availability status
    """
```

#### **Agent-Focused Health Check Process:**

**Stage 1: Agent Context Recognition**
```python
# Determine if this is an agent ping
if echo and ("agent" in echo.lower() or "checking" in echo.lower()):
    client_type = "agent_client"

    # Agent-specific health information
    agent_health_info = {
        "marcus_status": "operational",
        "agent_services_available": True,
        "task_assignment_system": "ready",
        "progress_reporting_system": "ready",
        "blocker_resolution_system": "ready"
    }
```

**Stage 2: Project Context Validation**
```python
# Verify agent can access project context
project_context = {}
if hasattr(state, 'project_registry') and state.project_registry:
    active_project = await state.project_registry.get_active_project()
    if active_project:
        project_context = {
            "active_project": active_project.name,
            "project_id": active_project.id,
            "kanban_provider": active_project.kanban_provider,
            "agent_access": "confirmed"
        }
    else:
        project_context = {
            "active_project": None,
            "agent_access": "no_active_project",
            "required_action": "project_selection_needed"
        }
```

**Stage 3: Service Readiness Confirmation**
```python
# Verify core services are ready for agent operations
service_status = {
    "task_scheduling": await _check_task_scheduling_availability(state),
    "progress_tracking": await _check_progress_tracking_availability(state),
    "blocker_analysis": await _check_blocker_analysis_availability(state),
    "context_services": await _check_context_services_availability(state)
}

return {
    "status": "ok",
    "echo": echo,
    "agent_services": agent_health_info,
    "project_context": project_context,
    "service_readiness": service_status,
    "timestamp": datetime.now().isoformat()
}
```

### **Tool 2: Task Context Intelligence (`get_task_context`)**
**File**: `src/marcus_mcp/tools/context.py` - `get_task_context` function
**Purpose**: Provide agents with comprehensive contextual intelligence about tasks

When an agent calls `get_task_context("task_015")`, Marcus provides **deep contextual intelligence**:

```python
async def get_task_context(task_id: str, state: Any) -> Dict[str, Any]:
    """
    Get comprehensive contextual information about a task.

    Provides agents with:
    - Task details and requirements
    - Dependency relationships and status
    - Historical context and patterns
    - Implementation guidance and examples
    - Risk factors and considerations
    """
```

#### **Context Intelligence Generation Process:**

**Stage 1: Task Information Aggregation**
```python
# Get comprehensive task information
task = await _get_task_by_id(task_id, state)
if not task:
    return {
        "success": False,
        "error": f"Task {task_id} not found",
        "suggestion": "Verify task ID or refresh project state"
    }

# Base task information
task_info = {
    "id": task.id,
    "name": task.name,
    "description": task.description,
    "status": task.status,
    "priority": task.priority,
    "labels": task.labels,
    "estimated_effort": task.estimated_effort,
    "assigned_to": task.assigned_to,
    "created_at": task.created_at,
    "updated_at": task.updated_at
}
```

**Stage 2: Dependency Analysis & Relationship Mapping**
```python
# Analyze task dependencies
dependency_context = await state.context.analyze_task_dependencies(task_id)

dependency_info = {
    "depends_on": [],
    "blocks": [],
    "related_tasks": [],
    "dependency_status": "ready"  # ready/waiting/blocked
}

# Map dependency relationships
for dep_id in task.dependencies:
    dep_task = await _get_task_by_id(dep_id, state)
    if dep_task:
        dependency_info["depends_on"].append({
            "task_id": dep_id,
            "name": dep_task.name,
            "status": dep_task.status,
            "completion_percentage": dep_task.progress_percentage,
            "blocking_reason": None if dep_task.status == "DONE" else "incomplete",
            "expected_completion": dep_task.estimated_completion
        })

# Find tasks that depend on this one
dependent_tasks = await state.context.find_dependent_tasks(task_id)
for dep_task in dependent_tasks:
    dependency_info["blocks"].append({
        "task_id": dep_task.id,
        "name": dep_task.name,
        "waiting_for": "task_completion",
        "impact_if_delayed": await _assess_delay_impact(dep_task, state)
    })
```

**Stage 3: Implementation Context & Patterns**
```python
# Get implementation context (for GitHub-integrated projects)
implementation_context = {}
if state.provider == "github" and state.code_analyzer:
    owner = os.getenv("GITHUB_OWNER")
    repo = os.getenv("GITHUB_REPO")

    # Find similar implementations
    similar_implementations = await state.code_analyzer.find_similar_implementations(
        task_description=task.description,
        task_labels=task.labels,
        owner=owner,
        repo=repo
    )

    if similar_implementations:
        implementation_context = {
            "similar_patterns_found": len(similar_implementations),
            "examples": similar_implementations[:3],  # Top 3 most relevant
            "recommended_approach": similar_implementations[0] if similar_implementations else None,
            "code_patterns": await state.code_analyzer.extract_patterns(similar_implementations)
        }

# Add architectural decisions and context
if hasattr(state.context, 'get_architectural_decisions'):
    arch_decisions = await state.context.get_architectural_decisions(task_id)
    implementation_context["architectural_decisions"] = arch_decisions
```

**Stage 4: Risk Assessment & Guidance**
```python
# Analyze potential risks and provide guidance
risk_analysis = await state.memory.predict_task_risks(task_id, task)

context_guidance = {
    "complexity_assessment": await _assess_task_complexity(task, state),
    "skill_requirements": await _analyze_skill_requirements(task, state),
    "estimated_duration": await _predict_task_duration(task, state),
    "success_factors": await _identify_success_factors(task, state),
    "common_pitfalls": await _identify_common_pitfalls(task.type, state),
    "quality_criteria": await _define_quality_criteria(task, state)
}

return {
    "success": True,
    "task_info": task_info,
    "dependencies": dependency_info,
    "implementation_context": implementation_context,
    "guidance": context_guidance,
    "risk_analysis": risk_analysis,
    "generated_at": datetime.now().isoformat()
}
```

### **Tool 3: Decision Audit Trail (`log_decision`)**
**File**: `src/marcus_mcp/tools/attachment.py` - `log_decision` function
**Purpose**: Enable agents to log important decisions for audit trail and learning

When an agent calls `log_decision("Use PostgreSQL for user data storage", "Better ACID compliance than NoSQL for user transactions")`, Marcus creates **comprehensive decision documentation**:

```python
async def log_decision(
    decision: str,
    rationale: str,
    task_id: str = None,
    state: Any = None
) -> Dict[str, Any]:
    """
    Log an important decision made by an agent during task execution.

    Creates audit trail for:
    - Technical architecture decisions
    - Implementation approach choices
    - Risk mitigation strategies
    - Design trade-off evaluations
    """
```

#### **Decision Logging Process:**

**Stage 1: Decision Context Enrichment**
```python
# Enrich decision with context
decision_context = {
    "timestamp": datetime.now().isoformat(),
    "decision_type": await _classify_decision_type(decision),
    "task_context": None,
    "project_context": await _get_current_project_context(state),
    "agent_context": await _get_current_agent_context(state)
}

# Add task context if provided
if task_id:
    task_context = await _get_task_context_for_decision(task_id, state)
    decision_context["task_context"] = {
        "task_id": task_id,
        "task_name": task_context.name,
        "task_phase": task_context.current_phase,
        "dependencies_affected": await _analyze_decision_impact_on_dependencies(
            decision, task_id, state
        )
    }
```

**Stage 2: Decision Impact Analysis**
```python
# Analyze decision impact
impact_analysis = await state.ai_engine.analyze_decision_impact(
    decision=decision,
    rationale=rationale,
    context=decision_context
)

decision_record = {
    "decision": decision,
    "rationale": rationale,
    "context": decision_context,
    "impact_analysis": {
        "affected_components": impact_analysis.affected_components,
        "risk_level": impact_analysis.risk_assessment,
        "reversibility": impact_analysis.reversibility_score,
        "future_implications": impact_analysis.future_implications
    },
    "decision_id": f"decision_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{task_id or 'general'}"
}
```

**Stage 3: Knowledge Base Integration**
```python
# Add to project knowledge base
await state.knowledge_base.add_decision_record(decision_record)

# Update patterns in memory system
await state.memory.record_decision_pattern({
    "decision_type": decision_context["decision_type"],
    "context_pattern": decision_context,
    "outcome_tracking": "pending",  # Will be updated based on results
    "learning_value": "high" if impact_analysis.risk_level == "high" else "medium"
})

return {
    "success": True,
    "decision_id": decision_record["decision_id"],
    "decision_logged": True,
    "impact_assessment": decision_record["impact_analysis"],
    "tracking_enabled": True,
    "knowledge_base_updated": True
}
```

### **Tool 4: Artifact Tracking (`log_artifact`)**
**File**: `src/marcus_mcp/tools/attachment.py` - `log_artifact` function
**Purpose**: Track important artifacts created during task execution

When an agent calls `log_artifact("database_schema.sql", "user_authentication", "Database schema for user auth system")`, Marcus creates **comprehensive artifact tracking**:

```python
async def log_artifact(
    file_path: str,
    category: str,
    description: str,
    task_id: str = None,
    state: Any = None
) -> Dict[str, Any]:
    """
    Log an important artifact created during task execution.

    Tracks artifacts like:
    - Code files and modules
    - Configuration files
    - Documentation
    - Test files
    - Database schemas
    """
```

#### **Artifact Tracking Process:**

**Stage 1: Artifact Analysis & Classification**
```python
# Analyze the artifact
artifact_analysis = {
    "file_path": file_path,
    "file_type": await _classify_file_type(file_path),
    "category": category,
    "description": description,
    "file_exists": os.path.exists(file_path),
    "file_size": os.path.getsize(file_path) if os.path.exists(file_path) else None,
    "created_at": datetime.now().isoformat()
}

# Enhanced analysis if file exists
if artifact_analysis["file_exists"]:
    artifact_analysis.update({
        "file_hash": await _calculate_file_hash(file_path),
        "line_count": await _count_lines(file_path),
        "complexity_metrics": await _analyze_file_complexity(file_path),
        "dependencies": await _analyze_file_dependencies(file_path)
    })
```

**Stage 2: Task Integration & Context**
```python
# Link to task context
task_context = None
if task_id:
    task_context = {
        "task_id": task_id,
        "task_name": await _get_task_name(task_id, state),
        "artifact_relevance": await _assess_artifact_relevance(file_path, task_id, state),
        "completion_evidence": await _assess_completion_evidence(file_path, task_id, state)
    }

# Create artifact record
artifact_record = {
    "artifact_id": f"artifact_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{category}",
    "file_info": artifact_analysis,
    "task_context": task_context,
    "tracking_metadata": {
        "logged_by": "agent",
        "tracking_reason": "task_deliverable",
        "importance": await _assess_artifact_importance(category, description),
        "reusability": await _assess_artifact_reusability(file_path, category)
    }
}
```

**Stage 3: Knowledge Base & Learning Integration**
```python
# Add to artifact tracking system
await state.artifact_tracker.add_artifact(artifact_record)

# Update project knowledge patterns
await state.memory.record_artifact_pattern({
    "artifact_type": artifact_analysis["file_type"],
    "category": category,
    "task_phase": task_context.get("task_phase") if task_context else "unknown",
    "quality_indicators": artifact_analysis.get("complexity_metrics"),
    "reuse_potential": artifact_record["tracking_metadata"]["reusability"]
})

return {
    "success": True,
    "artifact_id": artifact_record["artifact_id"],
    "artifact_tracked": True,
    "file_analysis": artifact_analysis,
    "task_integration": task_context is not None,
    "knowledge_updated": True
}
```

### **Tool 5: Dependency Validation (`check_task_dependencies`)**
**File**: `src/marcus_mcp/tools/context.py` - `check_task_dependencies` function
**Purpose**: Validate task dependencies and readiness status

When an agent calls `check_task_dependencies("task_020")`, Marcus performs **comprehensive dependency validation**:

```python
async def check_task_dependencies(task_id: str, state: Any) -> Dict[str, Any]:
    """
    Check if task dependencies are satisfied and ready for execution.

    Validates:
    - All dependency tasks completion status
    - Dependency output availability
    - Integration readiness
    - Blocking factors analysis
    """
```

#### **Dependency Validation Process:**

**Stage 1: Dependency Discovery & Status Check**
```python
# Get task and its dependencies
task = await _get_task_by_id(task_id, state)
if not task:
    return {"success": False, "error": f"Task {task_id} not found"}

dependency_status = {
    "task_id": task_id,
    "task_name": task.name,
    "total_dependencies": len(task.dependencies),
    "satisfied_dependencies": 0,
    "unsatisfied_dependencies": [],
    "ready_for_execution": False
}

# Check each dependency
for dep_id in task.dependencies:
    dep_task = await _get_task_by_id(dep_id, state)

    if not dep_task:
        dependency_status["unsatisfied_dependencies"].append({
            "dependency_id": dep_id,
            "status": "task_not_found",
            "blocking_reason": "Dependency task does not exist",
            "resolution": "Verify dependency ID or update task dependencies"
        })
        continue

    # Check completion status
    if dep_task.status == "DONE":
        dependency_status["satisfied_dependencies"] += 1
    else:
        dependency_status["unsatisfied_dependencies"].append({
            "dependency_id": dep_id,
            "dependency_name": dep_task.name,
            "current_status": dep_task.status,
            "progress_percentage": dep_task.progress_percentage,
            "estimated_completion": dep_task.estimated_completion,
            "blocking_reason": f"Dependency not complete (status: {dep_task.status})",
            "assigned_to": dep_task.assigned_to
        })
```

**Stage 2: Integration Readiness Assessment**
```python
# Check if completed dependencies provide required outputs
integration_readiness = {
    "outputs_available": True,
    "integration_blockers": [],
    "missing_artifacts": []
}

for dep_id in [d["dependency_id"] for d in dependency_status["unsatisfied_dependencies"] if d.get("current_status") == "DONE"]:
    # Check if dependency outputs are available
    required_outputs = await _get_required_outputs_from_dependency(task_id, dep_id, state)

    for output in required_outputs:
        if not await _verify_output_availability(output, state):
            integration_readiness["missing_artifacts"].append({
                "dependency": dep_id,
                "missing_output": output.name,
                "output_type": output.type,
                "required_for": output.usage_context
            })
            integration_readiness["outputs_available"] = False

# Overall readiness assessment
dependency_status["ready_for_execution"] = (
    len(dependency_status["unsatisfied_dependencies"]) == 0 and
    integration_readiness["outputs_available"]
)
```

**Stage 3: Predictive Analysis & Recommendations**
```python
# Provide predictive analysis for incomplete dependencies
if dependency_status["unsatisfied_dependencies"]:
    predictions = []

    for unsatisfied_dep in dependency_status["unsatisfied_dependencies"]:
        if unsatisfied_dep.get("estimated_completion"):
            predictions.append({
                "dependency": unsatisfied_dep["dependency_id"],
                "predicted_ready_at": unsatisfied_dep["estimated_completion"],
                "confidence": await _assess_completion_prediction_confidence(
                    unsatisfied_dep["dependency_id"], state
                ),
                "recommendation": await _generate_dependency_recommendation(
                    unsatisfied_dep, task_id, state
                )
            })

    dependency_status["predictions"] = predictions

return {
    "success": True,
    "dependency_status": dependency_status,
    "integration_readiness": integration_readiness,
    "overall_assessment": {
        "ready": dependency_status["ready_for_execution"],
        "blocking_factors": len(dependency_status["unsatisfied_dependencies"]),
        "estimated_ready_time": await _predict_dependency_ready_time(task_id, state) if not dependency_status["ready_for_execution"] else "now"
    },
    "generated_at": datetime.now().isoformat()
}
```


---

## 🔍 **Integration Points**

### **With Core Marcus Systems**
All agent support tools integrate deeply with Marcus's core intelligence:

```python
# Context tools integrate with memory system
context_insights = await state.memory.enhance_context_with_patterns(context_data)

# Decision logging feeds into learning system
await state.memory.record_decision_pattern(decision_data)

# Artifact tracking updates knowledge base
await state.knowledge_base.index_artifact(artifact_data)

# Dependency validation uses predictive intelligence
dependency_predictions = await state.ai_engine.predict_dependency_completion(dep_data)
```

---

## 🎯 **Key Capabilities**

### **1. Intelligent System Support**
Agent support tools provide sophisticated intelligence beyond basic functionality:

- **Health Verification**: Comprehensive system status tailored to agent needs
- **Contextual Intelligence**: Deep task context with implementation guidance
- **Audit Compliance**: Complete decision and artifact tracking for governance
- **Dependency Intelligence**: Comprehensive dependency validation and prediction

### **2. AI-Enhanced Decision Support**
Advanced AI integration provides intelligent assistance:

- **Context Analysis**: AI-powered task context and risk assessment
- **Decision Impact**: Intelligent analysis of decision consequences
- **Artifact Intelligence**: Smart artifact classification and reusability assessment

### **3. Learning Integration**
All support tools contribute to Marcus's continuous learning:

- **Pattern Recognition**: Decision and artifact patterns improve future guidance
- **Context Enhancement**: Context intelligence improves with each interaction
- **Dependency Learning**: Dependency patterns enhance prediction accuracy

---

## 🎯 **System Impact**

### **Without Agent Support Tools**
- Agents work in isolation without system context
- No audit trail of important decisions and artifacts
- Manual dependency checking and validation
- Limited learning from agent activities

### **With Agent Support Tools**
- **Comprehensive Context**: Agents have full situational awareness and implementation guidance
- **Audit Compliance**: Complete tracking of decisions and artifacts for governance and learning
- **Intelligent Validation**: Automated dependency checking with predictive insights
- **Continuous Learning**: Every agent interaction improves system intelligence

---

## 🎯 **Key Takeaway**

The Agent Support Tools transform Marcus from a basic task assignment system into a **comprehensive agent intelligence platform** that provides sophisticated context, audit compliance, validation intelligence, and AI-powered project creation capabilities.

These tools ensure that agents are not just assigned work, but are provided with the contextual intelligence, decision support, and creation capabilities needed to work effectively as part of an intelligent coordination system.
