# MCP Tools Analysis - What's Needed from Phases 1-4

## Current State Analysis

### What Marcus Currently Has (Agent-focused)
- register_agent
- request_next_task  
- report_task_progress
- report_blocker
- get_project_status

### What Phases 1-4 Built (Not Exposed)
- **Phase 1**: Context detection, mode selection, safety checks
- **Phase 2**: Dependency inference, task enrichment, pattern learning  
- **Phase 3**: AI integration, semantic understanding, contextual learning
- **Phase 4**: PRD parsing, predictive analytics, multi-project intelligence

## Key Question: What Do Users Actually Need?

### User Scenarios We Must Support:

1. **"I want to build X"** → Create project from description
2. **"Add feature Y"** → Add feature with dependencies
3. **"Can we deploy?"** → Safety check with reasons
4. **"What should I work on?"** → Intelligent suggestions
5. **"Fix these messy tasks"** → Task enrichment
6. **"Here's my PRD"** → Parse requirements
7. **"How's the project?"** → Status and predictions

## Proposed MCP Tools

### Essential Tools (Must Have)

1. **process_natural_language**
   - Universal entry point for any request
   - Routes to appropriate internal handler
   - Leverages all Phase 1-4 capabilities

2. **create_project_from_description**
   - Uses Phase 4 PRD parser
   - Uses Phase 1 mode detection
   - Uses Phase 2 dependency inference

3. **analyze_and_suggest**
   - Uses Phase 3 AI analysis
   - Uses Phase 2 pattern learning
   - Provides next steps

4. **check_safety**
   - Uses Phase 1 safety checks
   - Uses Phase 3 hybrid decision framework
   - Deployment readiness

### Nice to Have (If Time Permits)

5. **enrich_board**
   - Uses Phase 2 enrichment
   - Batch processing

6. **get_insights**
   - Uses Phase 4 predictive analytics
   - Project health metrics

## Minimum Viable Plan

Instead of 20+ tools, we need just 3-4 core tools that expose the key capabilities:

```python
# 1. Main entry point
process_natural_language(request: str, context: dict)
→ Handles: create project, add feature, any question

# 2. Direct project creation  
create_project(description: str, constraints: dict)
→ Returns: tasks, dependencies, timeline

# 3. Intelligence layer
get_ai_analysis(query_type: str, context: dict)
→ Returns: suggestions, predictions, insights

# 4. Safety checks
check_action_safety(action: str, context: dict)
→ Returns: allowed, reasons, alternatives
```

## Integration Architecture

```
User speaks naturally
    ↓
Claude interprets
    ↓
MCP Tool (one of 4)
    ↓
Marcus routes internally:
├─ Context Detection (Phase 1)
├─ Mode Selection (Phase 1)
├─ AI Analysis (Phase 3)
├─ PRD Parser (Phase 4)
├─ Dependency Inferer (Phase 2)
├─ Safety Checker (Phase 1+3)
└─ Task Enricher (Phase 2)
    ↓
Updates Planka board
    ↓
Returns natural language response
```

## Decision: Start with MVP

Let's build these 4 core tools first:
1. `process_natural_language` - Catch-all natural language processor
2. `create_project` - Direct project creation
3. `get_ai_analysis` - Access to AI insights
4. `check_action_safety` - Safety validation

This covers 90% of use cases with 20% of the complexity.