# Marcus MCP Tools Enhancement Plan

## Overview

Currently, Marcus MCP only exposes agent-based task execution tools. We need to add project management tools that let Claude access Marcus's AI capabilities for natural language project creation and management.

## New MCP Tools to Build

### 1. **create_project**
```typescript
{
  name: "create_project",
  description: "Create a new project from natural language description using AI",
  inputSchema: {
    type: "object",
    properties: {
      description: {
        type: "string",
        description: "Natural language project description or PRD"
      },
      team_size: {
        type: "integer",
        description: "Number of developers",
        default: 3
      },
      tech_stack: {
        type: "array",
        items: { type: "string" },
        description: "Technologies to use",
        default: []
      },
      deadline_days: {
        type: "integer",
        description: "Days until deadline",
        default: null
      }
    },
    required: ["description"]
  }
}
```

**How users use it:**
- User: "I need an e-commerce site for selling handmade crafts"
- Claude calls: `create_project({ description: "..." })`
- Marcus: Creates 35+ tasks with dependencies, phases, and estimates

### 2. **add_feature**
```typescript
{
  name: "add_feature",
  description: "Add a new feature to existing project using natural language",
  inputSchema: {
    type: "object",
    properties: {
      feature_description: {
        type: "string",
        description: "Natural language description of the feature"
      },
      target_phase: {
        type: "string",
        description: "Which phase to add to",
        enum: ["current", "next", "backlog"],
        default: "current"
      }
    },
    required: ["feature_description"]
  }
}
```

**How users use it:**
- User: "Add a wishlist feature where users can save products"
- Claude calls: `add_feature({ feature_description: "..." })`
- Marcus: Creates wishlist tasks with proper dependencies

### 3. **analyze_project**
```typescript
{
  name: "analyze_project",
  description: "Get AI-powered analysis of current project state",
  inputSchema: {
    type: "object",
    properties: {
      analysis_type: {
        type: "string",
        enum: ["health", "risks", "dependencies", "recommendations", "all"],
        description: "Type of analysis to perform",
        default: "all"
      },
      include_ai_insights: {
        type: "boolean",
        description: "Include AI-powered insights",
        default: true
      }
    }
  }
}
```

**How users use it:**
- User: "How's the project looking?"
- Claude calls: `analyze_project({ analysis_type: "all" })`
- Marcus: Returns health metrics, risks, bottlenecks, and AI recommendations

### 4. **suggest_next_tasks**
```typescript
{
  name: "suggest_next_tasks",
  description: "Get AI-powered suggestions for what to work on next",
  inputSchema: {
    type: "object",
    properties: {
      num_suggestions: {
        type: "integer",
        description: "Number of task suggestions",
        default: 3
      },
      for_agent: {
        type: "string",
        description: "Specific agent to suggest for",
        default: null
      },
      optimization_goal: {
        type: "string",
        enum: ["unblock_most", "quick_wins", "critical_path", "balanced"],
        default: "unblock_most"
      }
    }
  }
}
```

**How users use it:**
- User: "What should I work on next?"
- Claude calls: `suggest_next_tasks({ optimization_goal: "unblock_most" })`
- Marcus: "Work on user auth - it's blocking 8 other tasks"

### 5. **check_deployment_readiness**
```typescript
{
  name: "check_deployment_readiness",
  description: "Check if project is ready for deployment with AI safety checks",
  inputSchema: {
    type: "object",
    properties: {
      environment: {
        type: "string",
        enum: ["development", "staging", "production"],
        default: "production"
      },
      include_checklist: {
        type: "boolean",
        description: "Include detailed deployment checklist",
        default: true
      }
    }
  }
}
```

**How users use it:**
- User: "Can we deploy to production?"
- Claude calls: `check_deployment_readiness({ environment: "production" })`
- Marcus: "❌ Cannot deploy - 5 critical tasks incomplete"

### 6. **enrich_existing_tasks**
```typescript
{
  name: "enrich_existing_tasks",
  description: "Use AI to enhance vague or poorly defined tasks",
  inputSchema: {
    type: "object",
    properties: {
      task_filter: {
        type: "string",
        enum: ["all", "vague", "no_description", "no_estimate"],
        default: "vague"
      },
      enrich_with: {
        type: "array",
        items: {
          type: "string",
          enum: ["description", "acceptance_criteria", "estimates", "labels", "dependencies"]
        },
        default: ["description", "estimates", "labels"]
      }
    }
  }
}
```

**How users use it:**
- User: "These tasks are a mess, can you clean them up?"
- Claude calls: `enrich_existing_tasks({ task_filter: "vague" })`
- Marcus: Enriches tasks with descriptions, estimates, and labels

### 7. **parse_requirements**
```typescript
{
  name: "parse_requirements",
  description: "Parse a requirements document or user story into tasks",
  inputSchema: {
    type: "object",
    properties: {
      requirements_text: {
        type: "string",
        description: "Requirements document or user stories"
      },
      format: {
        type: "string",
        enum: ["prd", "user_stories", "technical_spec", "auto_detect"],
        default: "auto_detect"
      },
      add_to_board: {
        type: "boolean",
        description: "Automatically add to board",
        default: false
      }
    },
    required: ["requirements_text"]
  }
}
```

**How users use it:**
- User: *pastes PRD* "Can you break this down into tasks?"
- Claude calls: `parse_requirements({ requirements_text: "...", add_to_board: true })`
- Marcus: Parses PRD, creates task hierarchy with dependencies

## Backend Integration Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Claude User   │────▶│  Claude Desktop  │────▶│  Marcus MCP     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                 │                         │
                                 │ MCP Protocol           │
                                 ▼                         ▼
                        ┌──────────────────┐     ┌─────────────────┐
                        │  New MCP Tools   │     │  Marcus Core    │
                        └──────────────────┘     └─────────────────┘
                                                          │
                                ┌─────────────────────────┴─────────────────┐
                                │                                           │
                        ┌───────▼────────┐                       ┌─────────▼────────┐
                        │ Context Detector│                       │   AI Engine      │
                        │ (Phase 1)      │                       │  (Phase 3-4)     │
                        └────────────────┘                       └──────────────────┘
                                │                                          │
                        ┌───────▼────────┐     ┌──────────────┐  ┌───────▼────────┐
                        │ Creator Mode   │     │ Adaptive Mode│  │ PRD Parser     │
                        │ Enricher Mode  │     │              │  │ Task Enricher  │
                        └────────────────┘     └──────────────┘  └────────────────┘
                                │                      │                   │
                                └──────────────────────┴───────────────────┘
                                                      │
                                              ┌───────▼────────┐
                                              │  Planka MCP    │
                                              │  (Task Board)  │
                                              └────────────────┘
```

### Integration Points:

1. **MCP Tool Handler** → **Marcus Core**
   - Tools call into existing Marcus services
   - Maintains backward compatibility

2. **Marcus Core** → **AI Services**
   - Context detection for mode selection
   - AI engine for analysis and generation
   - PRD parser for requirements processing

3. **AI Services** → **Planka MCP**
   - Generated tasks sent to board
   - Dependencies mapped
   - Progress tracked

## Test Scenarios

### Scenario 1: Create New Project
```python
# Test: Natural language project creation
async def test_create_project_from_description():
    # Given: Natural language description
    description = """
    I need a task management app where teams can:
    - Create and assign tasks
    - Set deadlines and priorities  
    - Track progress with burndown charts
    - Get email notifications
    
    Tech: React frontend, Node.js API, PostgreSQL
    """
    
    # When: Create project
    result = await mcp_call("create_project", {
        "description": description,
        "team_size": 3,
        "tech_stack": ["React", "Node.js", "PostgreSQL"]
    })
    
    # Then: Should create structured project
    assert result["success"] == True
    assert result["tasks_created"] >= 20
    assert result["phases"] == ["Foundation", "Backend", "Frontend", "Integration", "Testing", "Deployment"]
    assert result["estimated_days"] > 0
    assert result["dependencies_mapped"] > 0
    
    # And: Should enforce logical ordering
    tasks = result["tasks"]
    deploy_task = find_task_by_name(tasks, "Deploy to production")
    impl_tasks = find_tasks_by_label(tasks, "implementation")
    
    assert all(impl_task in deploy_task["dependencies"] for impl_task in impl_tasks)
```

### Scenario 2: Add Feature to Existing Project
```python
# Test: Add feature with dependency detection
async def test_add_feature_with_dependencies():
    # Given: Existing project with user auth
    await create_test_project_with_auth()
    
    # When: Add social login feature
    result = await mcp_call("add_feature", {
        "feature_description": "Add social login with Google and Facebook"
    })
    
    # Then: Should create related tasks
    assert result["tasks_created"] >= 4
    task_names = [t["name"] for t in result["tasks"]]
    assert any("OAuth" in name for name in task_names)
    assert any("Google" in name for name in task_names)
    assert any("Facebook" in name for name in task_names)
    
    # And: Should depend on existing auth
    auth_task = find_task_by_name(existing_tasks, "User authentication")
    for new_task in result["tasks"]:
        if "OAuth" in new_task["name"]:
            assert auth_task["id"] in new_task["dependencies"]
```

### Scenario 3: Deployment Safety Check
```python
# Test: Prevent premature deployment
async def test_deployment_safety_check():
    # Given: Project with incomplete implementation
    await create_project_with_incomplete_tasks()
    
    # When: Check deployment readiness
    result = await mcp_call("check_deployment_readiness", {
        "environment": "production",
        "include_checklist": True
    })
    
    # Then: Should block deployment
    assert result["can_deploy"] == False
    assert len(result["blockers"]) > 0
    assert "implementation" in str(result["blockers"]).lower()
    
    # And: Should provide specific blockers
    assert result["incomplete_critical_tasks"] > 0
    assert result["missing_tests"] == True
    assert len(result["checklist"]["failed"]) > 0
```

### Scenario 4: AI-Powered Analysis
```python
# Test: Get intelligent project insights
async def test_ai_project_analysis():
    # Given: Project in progress
    await create_project_with_mixed_progress()
    
    # When: Analyze project
    result = await mcp_call("analyze_project", {
        "analysis_type": "all",
        "include_ai_insights": True
    })
    
    # Then: Should provide comprehensive analysis
    assert result["health_score"] >= 0 and result["health_score"] <= 100
    assert len(result["risks"]) > 0
    assert len(result["bottlenecks"]) >= 0
    assert result["critical_path"] is not None
    
    # And: Should include AI recommendations
    assert len(result["ai_insights"]["recommendations"]) > 0
    assert result["ai_insights"]["predicted_completion_date"] is not None
    assert result["ai_insights"]["confidence_level"] > 0
```

### Scenario 5: Task Enrichment
```python
# Test: Enhance vague tasks
async def test_enrich_vague_tasks():
    # Given: Board with poor task definitions
    await create_tasks([
        {"name": "fix bug"},
        {"name": "add feature"},
        {"name": "update stuff"}
    ])
    
    # When: Enrich tasks
    result = await mcp_call("enrich_existing_tasks", {
        "task_filter": "vague",
        "enrich_with": ["description", "estimates", "labels"]
    })
    
    # Then: Should enhance all vague tasks
    assert result["tasks_enriched"] == 3
    
    # And: Each task should be improved
    for enriched in result["enriched_tasks"]:
        assert len(enriched["description"]) > 20
        assert enriched["estimated_hours"] > 0
        assert len(enriched["labels"]) > 0
        assert enriched["original_name"] != enriched["enhanced_name"]
```

### Scenario 6: Natural Language Parsing
```python
# Test: Parse complex requirements
async def test_parse_complex_requirements():
    # Given: Detailed PRD
    prd = """
    Product: Social Learning Platform
    
    Users can create study groups, share notes, and have video study sessions.
    Must support real-time collaboration and work on mobile devices.
    
    Requirements:
    - User profiles with academic interests
    - Study group creation and management
    - Real-time collaborative note-taking
    - Video chat for study sessions
    - Calendar integration for scheduling
    - Mobile apps (iOS and Android)
    
    Non-functional:
    - Support 50 users per study session
    - Real-time sync latency < 100ms
    - 99.9% uptime
    """
    
    # When: Parse requirements
    result = await mcp_call("parse_requirements", {
        "requirements_text": prd,
        "format": "prd",
        "add_to_board": True
    })
    
    # Then: Should extract all features
    assert result["features_identified"] >= 6
    assert result["tasks_created"] >= 25
    assert result["non_functional_requirements"] >= 3
    
    # And: Should create proper structure
    assert "User Management" in result["phases"]
    assert "Real-time Features" in result["phases"]
    assert "Mobile Development" in result["phases"]
    
    # And: Should identify technical requirements
    assert "WebRTC" in result["identified_technologies"]
    assert "real-time" in result["technical_challenges"]
```

## Implementation Plan

1. **Phase 1: Core Tools** (Week 1)
   - create_project
   - add_feature
   - check_deployment_readiness

2. **Phase 2: Analysis Tools** (Week 2)
   - analyze_project
   - suggest_next_tasks
   - enrich_existing_tasks

3. **Phase 3: Advanced Tools** (Week 3)
   - parse_requirements
   - Additional analysis capabilities

## Success Criteria

1. **Natural Language**: Users can describe projects naturally
2. **Safety**: Deployment checks prevent dangerous operations
3. **Intelligence**: AI provides valuable insights and suggestions
4. **Integration**: Seamless with existing agent-based tools
5. **Performance**: All operations complete in < 5 seconds