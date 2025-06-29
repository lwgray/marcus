# Marcus MCP Tools Implementation Plan

## Overview
We'll add 4 core MCP tools that expose the Phase 1-4 capabilities to Claude. These tools will be the bridge between natural language and Marcus's AI intelligence.

## Tools to Implement

### 1. process_natural_language
**Purpose**: Universal handler for any natural language request
```typescript
{
  name: "process_natural_language",
  description: "Process any natural language project management request using Marcus AI",
  inputSchema: {
    type: "object",
    properties: {
      request: {
        type: "string",
        description: "Natural language request (create project, add feature, ask question)"
      },
      context: {
        type: "object",
        description: "Optional context about current project state",
        properties: {
          current_task_count: { type: "integer" },
          project_phase: { type: "string" },
          team_size: { type: "integer" }
        }
      }
    },
    required: ["request"]
  }
}
```

**Examples**:
- "I want to build a blog with comments" → Creates full project
- "Add user authentication" → Adds auth tasks with dependencies
- "Can we deploy?" → Checks safety and returns blockers
- "What should I work on?" → Analyzes and suggests tasks

### 2. create_project
**Purpose**: Create a complete project from description
```typescript
{
  name: "create_project",
  description: "Create a new project with tasks, dependencies, and timeline from a description",
  inputSchema: {
    type: "object",
    properties: {
      description: {
        type: "string", 
        description: "Natural language project description or PRD"
      },
      constraints: {
        type: "object",
        properties: {
          team_size: { type: "integer", default: 3 },
          deadline_days: { type: "integer" },
          tech_stack: { 
            type: "array",
            items: { type: "string" }
          },
          budget: { type: "number" }
        }
      }
    },
    required: ["description"]
  }
}
```

**Returns**:
```json
{
  "success": true,
  "project": {
    "task_count": 35,
    "phases": ["Foundation", "Backend", "Frontend", "Testing", "Deployment"],
    "estimated_days": 45,
    "dependencies_mapped": 23,
    "critical_path": ["Setup", "Auth", "Core Features", "Testing", "Deploy"],
    "risks": ["Payment integration complexity", "Real-time features"]
  },
  "tasks": [...],
  "board_url": "http://localhost:3000/boards/..."
}
```

### 3. get_ai_analysis
**Purpose**: Get AI-powered insights and recommendations
```typescript
{
  name: "get_ai_analysis",
  description: "Get AI-powered analysis, suggestions, and predictions for your project",
  inputSchema: {
    type: "object",
    properties: {
      analysis_type: {
        type: "string",
        enum: ["next_tasks", "blockers", "risks", "timeline", "health", "all"],
        description: "Type of analysis needed"
      },
      options: {
        type: "object",
        properties: {
          include_predictions: { type: "boolean", default: true },
          include_recommendations: { type: "boolean", default: true },
          max_suggestions: { type: "integer", default: 5 }
        }
      }
    },
    required: ["analysis_type"]
  }
}
```

**Returns**:
```json
{
  "analysis_type": "next_tasks",
  "recommendations": [
    {
      "task": "Implement user authentication",
      "reason": "Blocks 8 other tasks",
      "estimated_impact": "Unblocks 40% of project",
      "effort": "8 hours",
      "dependencies": []
    }
  ],
  "insights": {
    "bottlenecks": ["Single backend developer"],
    "velocity": "2.5 tasks/day",
    "predicted_completion": "2024-03-15",
    "confidence": 0.85
  }
}
```

### 4. check_action_safety
**Purpose**: Validate if an action is safe to perform
```typescript
{
  name: "check_action_safety",
  description: "Check if an action (like deployment) is safe to perform",
  inputSchema: {
    type: "object",
    properties: {
      action: {
        type: "string",
        description: "Action to check (deploy, release, migrate, etc)"
      },
      target: {
        type: "string", 
        description: "Target environment or scope",
        enum: ["development", "staging", "production"],
        default: "production"
      },
      force_check: {
        type: "boolean",
        description: "Force complete safety analysis",
        default: false
      }
    },
    required: ["action"]
  }
}
```

**Returns**:
```json
{
  "action": "deploy",
  "target": "production",
  "safe": false,
  "confidence": 0.98,
  "reasons": [
    "Implementation tasks incomplete (5 tasks)",
    "No tests written for payment module",
    "Security review not performed"
  ],
  "requirements": [
    "Complete: Implement payment processing",
    "Complete: Write integration tests", 
    "Complete: Security audit"
  ],
  "estimated_ready_date": "2024-02-20"
}
```

## Backend Integration Points

### 1. Natural Language Router
```python
class NaturalLanguageRouter:
    async def route_request(self, request: str, context: dict):
        # Detect intent
        intent = await self.detect_intent(request)
        
        # Route to appropriate handler
        if intent == "create_project":
            return await self.handle_create_project(request)
        elif intent == "add_feature":
            return await self.handle_add_feature(request)
        elif intent == "check_deployment":
            return await self.handle_safety_check(request)
        elif intent == "get_suggestion":
            return await self.handle_get_suggestions(request)
```

### 2. Project Creator Integration
```python
class ProjectCreator:
    async def create_from_description(self, description: str, constraints: dict):
        # Phase 1: Detect context
        context = self.context_detector.detect_context(board_state)
        
        # Phase 4: Parse PRD
        prd_analysis = await self.prd_parser.parse(description, constraints)
        
        # Phase 2: Infer dependencies
        dependencies = await self.dependency_inferer.infer(prd_analysis.tasks)
        
        # Phase 3: Enhance with AI
        enhanced_tasks = await self.ai_enricher.enrich_batch(tasks)
        
        # Create on board
        await self.create_tasks_on_board(enhanced_tasks)
```

### 3. AI Analysis Integration
```python
class AIAnalysisEngine:
    async def analyze(self, analysis_type: str, options: dict):
        # Get current board state
        board_state = await self.get_board_state()
        
        # Phase 3: Use hybrid intelligence
        analysis = await self.hybrid_ai.analyze(board_state, analysis_type)
        
        # Phase 2: Apply learned patterns
        patterns = await self.pattern_learner.get_relevant_patterns()
        
        # Phase 4: Add predictions
        predictions = await self.predictive_engine.predict(board_state)
        
        return self.format_analysis(analysis, patterns, predictions)
```

### 4. Safety Checker Integration
```python
class SafetyChecker:
    async def check_action(self, action: str, target: str):
        # Phase 1: Rule-based safety
        rule_check = self.safety_rules.check(action, target)
        
        # Phase 3: AI enhancement
        ai_check = await self.ai_engine.analyze_safety(action, target)
        
        # Hybrid decision
        final_decision = self.hybrid_framework.decide(rule_check, ai_check)
        
        return final_decision
```

## Test Scenarios

### Scenario 1: End-to-End Project Creation
```python
async def test_create_blog_project():
    """Test creating a blog project from natural language"""
    
    # Call MCP tool
    result = await mcp_call("process_natural_language", {
        "request": "I want to build a blog platform with user accounts, comments, and markdown support"
    })
    
    # Verify project created
    assert result["action_taken"] == "created_project"
    assert result["tasks_created"] >= 20
    assert "user authentication" in str(result["tasks"]).lower()
    assert "markdown" in str(result["tasks"]).lower()
    
    # Verify logical ordering
    deploy_task = find_task("Deploy to production", result["tasks"])
    impl_tasks = find_tasks_with_label("implementation", result["tasks"])
    assert all(task["id"] in deploy_task["dependencies"] for task in impl_tasks)
```

### Scenario 2: Feature Addition with Dependencies
```python
async def test_add_feature_with_dependencies():
    """Test adding a feature that depends on existing work"""
    
    # Create base project first
    await create_test_project()
    
    # Add feature
    result = await mcp_call("process_natural_language", {
        "request": "Add email notifications when users comment on posts"
    })
    
    # Verify feature tasks created
    assert result["action_taken"] == "added_feature"
    assert result["tasks_created"] >= 3
    
    # Verify dependencies
    notification_tasks = result["new_tasks"]
    auth_task = await get_task_by_name("User authentication")
    comment_task = await get_task_by_name("Comment system")
    
    for task in notification_tasks:
        if "email" in task["name"].lower():
            assert auth_task["id"] in task["dependencies"]
            assert comment_task["id"] in task["dependencies"]
```

### Scenario 3: Deployment Safety Check
```python
async def test_deployment_safety():
    """Test that deployment is blocked when unsafe"""
    
    # Create project with incomplete tasks
    await create_project_with_incomplete_implementation()
    
    # Try to deploy
    result = await mcp_call("check_action_safety", {
        "action": "deploy",
        "target": "production"
    })
    
    # Verify blocked
    assert result["safe"] == False
    assert len(result["reasons"]) > 0
    assert "implementation" in str(result["reasons"]).lower()
    assert result["confidence"] > 0.9
```

### Scenario 4: AI Recommendations
```python
async def test_ai_recommendations():
    """Test getting intelligent task suggestions"""
    
    # Create project with some progress
    await create_project_with_mixed_progress()
    
    # Get recommendations
    result = await mcp_call("get_ai_analysis", {
        "analysis_type": "next_tasks"
    })
    
    # Verify intelligent suggestions
    assert len(result["recommendations"]) > 0
    
    top_recommendation = result["recommendations"][0]
    assert "reason" in top_recommendation
    assert "blocks" in top_recommendation["reason"].lower()
    assert top_recommendation["estimated_impact"] is not None
```

## Implementation Steps

1. **Week 1**: 
   - Implement `process_natural_language` tool
   - Create natural language router
   - Write comprehensive tests

2. **Week 2**:
   - Implement `create_project` tool
   - Integrate with PRD parser and dependency inferer
   - Add `get_ai_analysis` tool

3. **Week 3**:
   - Implement `check_action_safety` tool
   - Polish and optimize
   - End-to-end testing

## Success Metrics

1. **Natural Language Understanding**: 90%+ intent detection accuracy
2. **Project Creation**: Creates logical task structure 100% of time
3. **Safety**: Never allows unsafe deployments
4. **Performance**: All operations < 3 seconds
5. **User Satisfaction**: Natural conversation flow