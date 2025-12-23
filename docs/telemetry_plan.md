# Marcus Telemetry System - Implementation Plan

## Executive Summary

Marcus will implement a **phone-home telemetry system** to collect anonymized usage data from distributed, self-hosted Marcus instances. This centralized collection is critical for understanding:

- **Success rates**: Are Marcus projects completing successfully?
- **Failure patterns**: Why are projects failing?
- **Application types**: What kinds of applications are users building?
- **AI usage patterns**: Which models are being used and how much do they cost?
- **Feature usage**: Which MCP tools and capabilities are being used?
- **Performance**: How well is the agent coordination performing?

**Key Philosophy**: Be permissive in what we collect. We get one shot at this - updating libraries post-release will be difficult, so the initial schema must capture sufficient data for future analysis while respecting user privacy.

**Critical Addition - AI Usage Telemetry**: Following the Anthropic model, we collect:
1. **Basic AI metrics** (default opt-in): Model usage, token counts, costs, response times - NO prompt content
2. **Full prompt logging** (separate opt-in): Complete prompts/responses for training and improvement - requires explicit user consent

**Infrastructure**: Three services on `marcus-ai.dev`:
- `telemetry.marcus-ai.dev` - Data collection API
- `stats.marcus-ai.dev` - Public statistics dashboard
- `privacy.marcus-ai.dev` - Privacy policy and transparency documentation

## Goals and Requirements

### Primary Goals

1. **Success Monitoring**: Track project completion rates and identify failure patterns
2. **Application Intelligence**: Understand what types of applications users build
3. **Performance Analytics**: Measure agent coordination efficiency and system performance
4. **Feature Adoption**: Identify which MCP tools and features are valuable
5. **Error Detection**: Catch and categorize errors for improvement prioritization
6. **Research Data**: Support MAS (Multi-Agent System) research initiatives

### Requirements

- **Privacy-First**: Anonymize all PII, no code/file paths/stack traces
- **Opt-In Consent**: First-run prompt with clear transparency
- **Permissive Collection**: Capture broad data - we can always filter, but can't retroactively add fields
- **Batched Transmission**: Efficient bandwidth usage with background sending
- **Offline-Capable**: Queue events when telemetry service unavailable
- **Versioned Schema**: Support schema evolution for future improvements

## Industry Research

### What Others Collect

**Anthropic Claude API**:
- Token usage (input/output counts)
- Model selection and API version
- Response times and error rates
- Opt-in: Full prompt/response logging for training

**VS Code**:
- Extension activation events
- Command usage frequency
- Performance metrics (startup time, responsiveness)
- Crash reports with stack traces (anonymized)
- Hashed user IDs for session tracking

**Homebrew**:
- Install/upgrade/uninstall events
- Build failures with formula names
- Command usage (install, search, etc.)
- OS version and architecture
- **Opt-out by default** (user can disable)

**npm packages**:
- Import patterns (which modules/functions)
- Runtime environment (Node version, OS)
- **Only in CI environments** (respects user privacy)

### Lessons Learned

1. **Versioning is critical** - All systems version their telemetry schemas
2. **Aggregate > Individual** - Focus on trends, not tracking individual users
3. **Error context matters** - Knowing *why* something failed is more valuable than knowing *that* it failed
4. **Performance data is actionable** - Timing/resource metrics drive optimization priorities
5. **Transparency builds trust** - Public dashboards and clear opt-in/out mechanisms

## Telemetry Event Schema

### Overview

Nine event types balance permissive collection with privacy protection:

1. **project_lifecycle** - Project success/failure tracking
2. **project_classification** - AI-extracted application types
3. **agent_registration** - Track which AI models agents are using (BYOA - Bring Your Own Agent)
4. **agent_session** - Agent coordination and performance
5. **ai_usage** - Model usage and token consumption
6. **coordination_quality** - Task dependencies, scheduling efficiency, and quality metrics
7. **feature_usage** - MCP tool and capability usage
8. **performance_metrics** - System performance and resource usage
9. **error_report** - Error patterns and failure analysis

All events include:
- `event_id`: UUID for deduplication
- `event_type`: One of the eight types above
- `event_version`: Schema version (e.g., "1.0.0")
- `timestamp`: ISO 8601 UTC timestamp
- `instance_id`: Anonymized instance identifier (hashed MAC address)
- `marcus_version`: Marcus library version (e.g., "0.1.0")
- `system_info`: OS, Python version, architecture

### Event Type 1: project_lifecycle

**Purpose**: Track whether projects complete successfully and why they fail.

**When Sent**:
- Project creation (start)
- Project completion (success)
- Project failure (abandon/error)
- Milestone completion (optional)

**Schema**:
```json
{
  "event_type": "project_lifecycle",
  "instance_id": "anon-abc123def456",
  "project_id_hash": "sha256-hash-of-project-name",
  "lifecycle_event": "created|completed|failed|abandoned",
  "project_summary": {
    "description_length": 250,
    "description_keywords": ["api", "authentication", "rest", "oauth"],
    "category": "backend-api",
    "complexity_score": 7.5,
    "estimated_task_count": 15,
    "estimated_duration_hours": 8.0
  },
  "outcome": {
    "status": "completed|failed|abandoned",
    "completion_percentage": 0.85,
    "actual_task_count": 18,
    "actual_duration_hours": 8.5,
    "agent_count": 3,
    "total_subtasks": 45
  },
  "failure_context": {
    "failure_type": "error|user_abandoned|dependency_issue|timeout",
    "error_category": "authentication|database|network|configuration",
    "failed_at_stage": "planning|execution|verification",
    "retry_count": 2
  }
}
```

**Anonymization**:
- **Project name**: Hashed with instance salt
- **Description**: AI-extracted keywords only (no raw text)
- **Category**: Classification, not verbatim description
- **No file paths, code, or specific error messages**

**Example AI Keyword Extraction**:
```
Raw: "Build a REST API for user authentication with OAuth2 and JWT tokens"
→ Keywords: ["api", "authentication", "rest", "oauth", "jwt", "security"]
→ Category: "backend-api"
→ Complexity: 7.5 (0-10 scale)
```

### Event Type 2: project_classification

**Purpose**: Understand what types of applications users build.

**When Sent**: After project planning completes (enough context for classification).

**Schema**:
```json
{
  "event_type": "project_classification",
  "instance_id": "anon-abc123def456",
  "project_id_hash": "sha256-hash-of-project-name",
  "classification": {
    "primary_category": "web-app|cli-tool|data-pipeline|ml-model|mobile-app|api|library|automation",
    "secondary_categories": ["authentication", "database", "rest-api"],
    "tech_stack_inferred": {
      "languages": ["python"],
      "frameworks": ["fastapi", "sqlalchemy"],
      "platforms": ["docker"]
    },
    "domain_area": "fintech|healthcare|e-commerce|education|productivity|entertainment|dev-tools",
    "scale": "personal-project|startup|enterprise",
    "complexity_indicators": {
      "has_database": true,
      "has_authentication": true,
      "has_third_party_apis": true,
      "has_background_jobs": false,
      "has_real_time_features": false
    }
  }
}
```

**Anonymization**:
- **Classification only** - No specific implementation details
- **Tech stack**: Inferred from generic patterns, not file paths
- **Domain area**: Broad category, not specific company/product

**AI Classification Approach**:
Use LLM to analyze project description and task structure, returning only structured categories (no raw text).

### Event Type 3: agent_registration

**Purpose**: Track which AI models external agents are using in Marcus's BYOA (Bring Your Own Agent) system.

**When Sent**: When an agent registers with Marcus via the `register_agent` MCP tool.

**Critical Requirement**: All agents MUST specify their model when registering. This is mandatory for telemetry.

**Schema**:
```json
{
  "event_type": "agent_registration",
  "instance_id": "anon-abc123def456",
  "project_id_hash": "sha256-hash-of-project-name",
  "agent_info": {
    "agent_id_hash": "hash-of-agent-id",
    "role": "Backend Developer",
    "skills_count": 5,
    "skill_categories": ["python", "api", "database", "testing", "devops"],
    "model_info": {
      "provider": "anthropic",
      "model_name": "claude-3-5-sonnet-20241022",
      "model_version": "20241022",
      "api_type": "anthropic_api"
    },
    "agent_type": "external_byoa",
    "registration_source": "mcp_client"
  },
  "timestamp": "2025-12-22T15:30:00Z"
}
```

**Key Insights**:
- **Model diversity**: What AI models are users bringing to Marcus?
- **Provider distribution**: Anthropic vs. OpenAI vs. custom models
- **Role patterns**: Which roles use which models?
- **Skill coverage**: What skills are agents bringing?
- **BYOA adoption**: How many users are using external agents vs. Marcus-managed agents?

**Agent Model Field Requirements**:

The `register_agent` MCP tool MUST be updated to require `model_info`:

```python
# REQUIRED fields for agent registration:
{
  "agent_id": "unique-agent-id",
  "name": "Agent Display Name",
  "role": "Backend Developer",
  "skills": ["python", "fastapi", "postgresql"],
  "model_info": {  # NEW - REQUIRED
    "provider": "anthropic|openai|custom",
    "model_name": "claude-3-5-sonnet-20241022",
    "model_version": "20241022",  # Optional but recommended
    "api_type": "anthropic_api|openai_api|custom"  # Optional
  }
}
```

**Why This Matters**:
1. **Model tracking**: Currently we don't know what models BYOA agents are using
2. **Cost analysis**: Different models have different costs - this helps users understand total project costs
3. **Performance correlation**: Correlate model choice with task success rates
4. **Recommendation engine**: Suggest optimal models for specific roles/tasks
5. **Support**: Help debug issues specific to certain models

**Privacy Notes**:
- `agent_id_hash`: Hashed with instance salt (same agent on different instances = different hash)
- `skills`: Categorized, not verbatim (e.g., "python" not "Python 3.11 with asyncio expertise")
- No agent names or personal identifiers

### Event Type 4: agent_session

**Purpose**: Measure agent coordination efficiency and MAS performance.

**When Sent**: After each agent session completes (task assignment → execution → result).

**Schema**:
```json
{
  "event_type": "agent_session",
  "instance_id": "anon-abc123def456",
  "project_id_hash": "sha256-hash-of-project-name",
  "agent_metrics": {
    "agent_count": 3,
    "agent_models": [
      {
        "provider": "anthropic",
        "model_name": "claude-3-5-sonnet-20241022",
        "role": "Backend Developer"
      },
      {
        "provider": "anthropic",
        "model_name": "claude-3-5-sonnet-20241022",
        "role": "Frontend Developer"
      },
      {
        "provider": "openai",
        "model_name": "gpt-4-turbo-2024-04-09",
        "role": "QA Engineer"
      }
    ],
    "session_duration_seconds": 450,
    "coordination_events": 5,
    "task_handoffs": 2,
    "parallel_tasks": 2,
    "sequential_tasks": 3
  },
  "agent_activity": {
    "total_idle_time_seconds": 120,
    "avg_idle_time_per_agent_seconds": 40,
    "max_idle_time_seconds": 85,
    "idle_time_percentage": 0.27,
    "total_active_time_seconds": 330,
    "active_time_percentage": 0.73,
    "agents_waiting_for_work": {
      "count": 2,
      "avg_wait_duration_seconds": 45,
      "max_wait_duration_seconds": 85
    },
    "work_distribution": {
      "tasks_per_agent": [3, 2, 1],
      "avg_tasks_per_agent": 2.0,
      "work_balance_coefficient": 0.65
    }
  },
  "performance": {
    "avg_task_completion_seconds": 90,
    "max_task_completion_seconds": 180,
    "tasks_completed": 5,
    "tasks_failed": 0,
    "retry_count": 1
  },
  "coordination_quality": {
    "conflict_count": 0,
    "duplicate_work_detected": false,
    "communication_overhead_percentage": 0.15
  },
  "bottlenecks": {
    "task_queue_depth_max": 5,
    "task_queue_depth_avg": 2.3,
    "blocked_by_dependencies_count": 1,
    "resource_contention_events": 0
  },
  "parallelization_analysis": {
    "total_tasks": 6,
    "sequential_required": 3,
    "parallelizable_tasks": 3,
    "parallelization_potential": 0.50,
    "dependency_depth": 3,
    "dependency_chains": 2,
    "parallel_opportunities_missed": 1,
    "agent_underutilization_events": 2
  }
}
```

**Key Insights**:
- **Agent utilization**: How much time are agents spending idle vs. actively working?
- **Work distribution**: Are tasks balanced across agents or concentrated on one?
- **Waiting patterns**: How long do agents wait for new work assignments?
- **Bottleneck detection**: Are task queues backing up? Are dependencies blocking progress?
- **Resource efficiency**: Are we over-provisioning agents (high idle time) or under-provisioning (high queue depth)?

**Agent Activity Metrics Explained**:
- `idle_time_percentage`: Percentage of session where agents had no work (target: <30%)
- `agents_waiting_for_work`: How many agents are blocked waiting for task assignment
- `work_balance_coefficient`: 0-1 scale, higher = more balanced distribution (1.0 = perfectly balanced)
- `task_queue_depth`: Number of tasks waiting to be picked up by agents
- `blocked_by_dependencies`: Tasks that can't start because they're waiting on other tasks

**Parallelization Analysis Explained**:
- `parallelization_potential`: Ratio of parallelizable tasks to total tasks (0.5 = 50% could run in parallel)
- `dependency_depth`: Longest chain of dependent tasks (higher = more sequential work required)
- `dependency_chains`: Number of separate dependency chains (more chains = more parallel opportunities)
- `parallel_opportunities_missed`: Times when agents were idle while parallelizable tasks were available
- `agent_underutilization_events`: Times when agents could have been working in parallel but weren't

**Critical Insight - Context Matters**:
Load balancing depends heavily on the task structure:
- **High sequential projects** (e.g., database migrations): One agent doing all work is EXPECTED, not a problem
- **High parallel projects** (e.g., feature development): Multiple idle agents with parallelizable tasks = inefficiency

This metric helps distinguish between:
1. **Natural sequentiality**: Project has high dependency depth (e.g., 80% sequential tasks) → one agent working is optimal
2. **Missed parallelization**: Project has low dependency depth (e.g., 80% parallelizable) but agents are idle → opportunity to optimize

**Research Value**: MAS coordination patterns, agent efficiency, scaling characteristics, optimal agent count determination, dependency graph complexity patterns.

### Event Type 5: ai_usage

**Purpose**: Track AI model usage and token consumption for cost analysis and model selection insights.

**When Sent**: Aggregated hourly (batch of AI API calls).

**Schema**:
```json
{
  "event_type": "ai_usage",
  "instance_id": "anon-abc123def456",
  "project_id_hash": "sha256-hash-of-project-name",
  "reporting_period": {
    "start_time": "2025-12-22T00:00:00Z",
    "end_time": "2025-12-22T01:00:00Z"
  },
  "model_usage": {
    "claude-3-5-sonnet-20241022": {
      "call_count": 45,
      "total_input_tokens": 125000,
      "total_output_tokens": 35000,
      "avg_input_tokens": 2777,
      "avg_output_tokens": 777,
      "total_cost_usd": 0.525,
      "successful_calls": 44,
      "failed_calls": 1,
      "avg_response_time_ms": 1250
    },
    "claude-3-haiku-20240307": {
      "call_count": 12,
      "total_input_tokens": 18000,
      "total_output_tokens": 3000,
      "avg_input_tokens": 1500,
      "avg_output_tokens": 250,
      "total_cost_usd": 0.008,
      "successful_calls": 12,
      "failed_calls": 0,
      "avg_response_time_ms": 450
    }
  },
  "usage_by_operation": {
    "task_decomposition": {
      "call_count": 8,
      "total_tokens": 45000,
      "primary_model": "claude-3-5-sonnet-20241022"
    },
    "code_generation": {
      "call_count": 25,
      "total_tokens": 85000,
      "primary_model": "claude-3-5-sonnet-20241022"
    },
    "keyword_extraction": {
      "call_count": 12,
      "total_tokens": 15000,
      "primary_model": "claude-3-haiku-20240307"
    },
    "error_analysis": {
      "call_count": 12,
      "total_tokens": 18000,
      "primary_model": "claude-3-haiku-20240307"
    }
  },
  "provider_distribution": {
    "anthropic": 57,
    "openai": 0,
    "custom": 0
  },
  "cost_summary": {
    "total_cost_usd": 0.533,
    "cost_per_project": 0.533,
    "estimated_monthly_cost_usd": 16.0
  }
}
```

**Key Insights**:
- **Model selection patterns**: Which models are preferred for which tasks?
- **Token consumption trends**: Are users hitting expensive operations?
- **Cost analysis**: What's the typical cost per project?
- **Performance comparison**: Response times across models
- **Provider diversity**: Are users using multiple AI providers?

**Privacy Notes**:
- **No prompt content** - Only token counts and metadata
- **Aggregated hourly** - Individual API calls not tracked
- **Operation categories** - Generic types (task_decomposition, code_generation), not specific prompts

**Opt-In Prompt Logging** (separate consent):

Users can opt-in to full prompt/response logging for training:

```json
{
  "event_type": "ai_usage_detailed",
  "instance_id": "anon-abc123def456",
  "project_id_hash": "sha256-hash-of-project-name",
  "prompt_logging_consent": true,
  "call_details": [
    {
      "call_id": "uuid-v4",
      "timestamp": "2025-12-22T15:30:00Z",
      "model": "claude-3-5-sonnet-20241022",
      "operation": "task_decomposition",
      "prompt": "Full prompt text here...",
      "response": "Full response text here...",
      "input_tokens": 2500,
      "output_tokens": 800,
      "response_time_ms": 1200,
      "success": true
    }
  ]
}
```

**Opt-In Configuration**:
```json
{
  "telemetry": {
    "phone_home": {
      "send_ai_usage_basic": true,
      "send_ai_usage_prompts": false  // Requires explicit opt-in
    }
  }
}
```

**Opt-In Prompt** (shown separately from basic telemetry):
```
┌─────────────────────────────────────────────────────────────────┐
│              Advanced Telemetry: Prompt Logging                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│ Help improve Marcus by sharing your AI prompts and responses.    │
│                                                                   │
│ This is OPTIONAL and separate from basic telemetry.              │
│                                                                   │
│ What we'll collect:                                              │
│   ✓ Full prompt text sent to AI models                          │
│   ✓ Full response text from AI models                           │
│   ✓ Associated project context (anonymized)                     │
│                                                                   │
│ Why this helps:                                                  │
│   • Improve AI task decomposition accuracy                       │
│   • Train better Marcus-specific models                          │
│   • Identify common prompt patterns                              │
│   • Reduce hallucinations and errors                             │
│                                                                   │
│ Privacy:                                                         │
│   • Project names/descriptions still anonymized                  │
│   • No file paths or code from your project                      │
│   • Used only for Marcus improvement, never sold                 │
│   • Can be disabled anytime                                      │
│                                                                   │
│ Enable prompt logging? [y/N]:                                    │
│                                                                   │
│ Change later:                                                    │
│   marcus config set telemetry.phone_home.send_ai_usage_prompts true │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

**Research Value**:
- **Training data**: Improve Marcus-specific AI models
- **Prompt engineering**: Identify effective prompt patterns
- **Error analysis**: Understand why certain prompts fail
- **Model comparison**: Compare responses across models for same prompts

### Event Type 6: coordination_quality

**Purpose**: Track task dependency management, scheduling efficiency, and system quality metrics to understand coordination effectiveness.

**When Sent**: On project completion or at major project milestones (25%, 50%, 75% completion).

**Schema**:
```json
{
  "event_type": "coordination_quality",
  "instance_id": "anon-abc123def456",
  "project_id_hash": "sha256-hash-of-project-name",
  "timestamp": "2025-12-22T16:00:00Z",
  "dependency_metrics": {
    "total_dependencies": 28,
    "dependency_depth": 5,
    "dependency_width": 8,
    "circular_dependency_detections": 0,
    "inference_methods_used": {
      "pattern_based": 12,
      "ai_powered": 16,
      "hybrid": 0
    },
    "average_confidence_score": 0.85,
    "cross_parent_dependencies": 6
  },
  "scheduling_efficiency": {
    "optimal_agent_count_calculated": 4,
    "actual_agent_count_used": 3,
    "parallelization_potential": 0.65,
    "parallelization_achieved": 0.48,
    "efficiency_gain_predicted": 0.62,
    "efficiency_gain_actual": 0.51,
    "critical_path_hours_predicted": 28.5,
    "critical_path_hours_actual": 32.0,
    "scaling_decisions": {
      "scale_up_triggered": 1,
      "scale_down_triggered": 0,
      "agent_resource_blockers": 2
    }
  },
  "task_coordination": {
    "total_assignments": 45,
    "assignment_conflicts": 2,
    "average_assignment_latency_ms": 320,
    "ai_powered_assignments": 28,
    "simple_assignments": 17,
    "orphan_recovery_events": 1,
    "task_reversion_count": 3,
    "assignment_monitor_uptime_percent": 99.8
  },
  "quality_metrics": {
    "overall_quality_score": 0.78,
    "quality_level": "GOOD",
    "code_quality_score": 0.82,
    "process_quality_score": 0.75,
    "delivery_quality_score": 0.80,
    "team_quality_score": 0.74,
    "task_validation_pass_rate": 0.91,
    "test_coverage_percent": 87.5,
    "code_review_coverage_percent": 95.0,
    "technical_debt_indicators": 3
  },
  "retry_strategy_effectiveness": {
    "average_idle_time_seconds": 180,
    "missed_work_opportunities": 2,
    "early_completion_detections": 7,
    "parallel_utilization_percent": 68.5,
    "smart_retry_invocations": 12
  },
  "monitoring_health": {
    "risk_assessments": {
      "LOW": 15,
      "MEDIUM": 8,
      "HIGH": 3,
      "CRITICAL": 0
    },
    "prediction_accuracy_percent": 82.0,
    "bottleneck_detections": 4,
    "health_check_failures": 1
  },
  "project_complexity": {
    "total_tasks": 32,
    "complexity_score": 0.68,
    "technology_diversity_score": 0.45,
    "requirement_ambiguity_count": 2,
    "sequential_task_percent": 35.0,
    "parallel_task_percent": 65.0
  }
}
```

**What We Learn**:
- **Dependency Management**: How complex are project dependencies and which inference methods work best?
- **Scheduling Optimization**: How well does CPM predict resource needs vs actual usage?
- **Coordination Efficiency**: Are agents being assigned tasks efficiently without conflicts?
- **Quality Trends**: What quality patterns emerge across projects?
- **Retry Strategy**: Is the smart retry system reducing idle time effectively?
- **Monitoring Accuracy**: How accurate are our risk predictions and bottleneck detections?
- **Complexity Patterns**: What complexity characteristics lead to successful vs failed projects?

**Privacy**:
- All project identifiers hashed
- No task names, descriptions, or code
- Only aggregate metrics and distributions
- No personally identifiable information

**Anonymization**:
```python
# Example anonymization
coordination_event = {
    "dependency_metrics": {
        "total_dependencies": len(dependencies),
        "inference_methods_used": count_by_method(dependencies),
        # No dependency content or task names
    },
    "quality_metrics": {
        "overall_quality_score": calculate_score(metrics),
        # No code snippets or file paths
    }
}
```

**Benefits for Marcus Development**:
- Identify which dependency inference methods are most accurate
- Understand when CPM predictions diverge from reality
- Detect coordination bottlenecks in the assignment system
- Learn quality patterns that predict project success
- Optimize retry strategies based on real-world agent behavior
- Improve risk prediction models with actual outcome data

### Event Type 7: feature_usage

**Purpose**: Identify which MCP tools and Marcus features are valuable.

**When Sent**: Aggregated hourly (batch of tool usage).

**Schema**:
```json
{
  "event_type": "feature_usage",
  "instance_id": "anon-abc123def456",
  "reporting_period": {
    "start_time": "2025-12-22T00:00:00Z",
    "end_time": "2025-12-22T01:00:00Z"
  },
  "mcp_tools": {
    "request_next_task": 15,
    "report_task_progress": 12,
    "create_project": 1,
    "get_task_context": 8,
    "log_decision": 3,
    "log_artifact": 5
  },
  "features": {
    "kanban_integration_enabled": true,
    "ai_task_decomposition": true,
    "cato_dashboard": false,
    "custom_agent_types": 0,
    "hooks_configured": 2
  },
  "integrations": {
    "kanban_board_connected": true,
    "external_apis_count": 0,
    "custom_mcp_servers": 1
  }
}
```

**Aggregation**: Hourly batches reduce transmission overhead and anonymize individual actions.

### Event Type 8: performance_metrics

**Purpose**: Measure system performance for optimization priorities.

**When Sent**: Every 6 hours (batched performance snapshots).

**Schema**:
```json
{
  "event_type": "performance_metrics",
  "instance_id": "anon-abc123def456",
  "system_performance": {
    "avg_api_response_ms": 450,
    "p95_api_response_ms": 1200,
    "p99_api_response_ms": 2500,
    "max_api_response_ms": 5000
  },
  "resource_usage": {
    "peak_memory_mb": 512,
    "avg_cpu_percentage": 25,
    "disk_io_operations": 1500
  },
  "system_info": {
    "os": "Darwin",
    "os_version": "24.6.0",
    "python_version": "3.11.5",
    "architecture": "arm64",
    "cpu_cores": 8,
    "total_memory_gb": 16
  },
  "database_performance": {
    "avg_query_ms": 15,
    "slow_queries_count": 2,
    "connection_pool_size": 10
  }
}
```

**Privacy**: Aggregated metrics only, no query content or user data.

### Event Type 9: error_report

**Purpose**: Identify error patterns for prioritizing fixes and understanding recovery effectiveness.

**When Sent**: Immediately after errors occur (with rate limiting).

**Schema**:
```json
{
  "event_type": "error_report",
  "instance_id": "anon-abc123def456",
  "project_id_hash": "sha256-hash-of-project-name",
  "timestamp": "2025-12-22T16:30:00Z",
  "error_info": {
    "error_category": "transient|configuration|business_logic|integration|security|system",
    "error_class": "NetworkTimeoutError|KanbanIntegrationError|AIProviderError|ConfigurationError|etc",
    "error_type": "timeout|authentication|validation|rate_limit|dependency_missing|resource_exhaustion",
    "severity": "low|medium|high|critical",
    "error_code": "KANBAN_TIMEOUT_001",
    "is_retryable": true,
    "retryable_suggested": true,
    "recovery_action_taken": "retry|fallback|skip|abort|escalate"
  },
  "context": {
    "operation": "create_task|register_agent|sync_board|generate_description|assign_task",
    "operation_id": "uuid-v4",
    "correlation_id": "uuid-v4",
    "agent_id_hash": "hash-of-agent-id",
    "task_id_hash": "hash-of-task-id",
    "retry_attempt": 2,
    "max_retries_configured": 3,
    "time_since_operation_start_ms": 120000,
    "previous_errors_in_session": 1,
    "integration_name": "planka|linear|github|anthropic|openai"
  },
  "recovery": {
    "recovery_attempted": true,
    "recovery_successful": false,
    "recovery_strategy_used": "exponential_backoff|circuit_breaker|fallback_cache|degraded_mode",
    "fallback_triggered": true,
    "circuit_breaker_state": "closed|open|half_open",
    "remediation_suggestion_followed": true
  },
  "system_state": {
    "active_agents": 3,
    "pending_tasks": 5,
    "completed_tasks": 12,
    "kanban_connected": false,
    "kanban_last_success_minutes_ago": 5,
    "ai_provider_status": "available",
    "memory_usage_percent": 65,
    "error_rate_last_hour": 0.02
  },
  "pattern_indicators": {
    "cascading_failure": false,
    "repeated_same_error": true,
    "repeat_count_last_hour": 3,
    "affects_multiple_agents": false,
    "critical_path_blocked": true
  }
}
```

**What We Learn**:
- **Error Patterns**: Which error types occur most frequently across Marcus instances
- **Recovery Effectiveness**: Success rates of different recovery strategies (retry, circuit breaker, fallback)
- **Integration Reliability**: Which external services (Planka, Anthropic, etc.) have highest error rates
- **Cascading Failures**: Detection of cascading failure patterns that indicate systemic issues
- **Critical Path Impact**: How often errors block critical path tasks vs non-critical work
- **Agent Impact**: Whether errors affect single agents or spread across the team
- **Recovery Strategy Optimization**: Which recovery strategies work best for different error types
- **Circuit Breaker Effectiveness**: How often circuit breakers prevent cascading failures

**Anonymization**:
- **No stack traces** (sensitive file paths)
- **No error messages** (may contain PII)
- **Categories and types only** - Broad error classification
- **Context only** - What operation failed, not specific data
- **Hashed IDs** - Agent and task IDs are hashed for privacy
- **Correlation IDs** - Anonymous UUIDs for tracking error chains

**Rate Limiting**: Max 10 error reports per hour per instance (avoid spam).

**Integration with Marcus Error Framework**:
This telemetry integrates with Marcus's comprehensive error framework (`src/core/error_framework.py`):
- Maps all 6 error categories (Transient, Configuration, Business Logic, Integration, Security, System)
- Captures all 4 severity levels (Low, Medium, High, Critical)
- Tracks recovery strategies from `src/core/error_strategies.py` (retry, circuit breaker, fallback)
- Uses ErrorContext for operation tracking and correlation IDs
- Captures remediation suggestion effectiveness

## Anonymization Strategy

### Instance Identification

**Goal**: Track individual Marcus instances without identifying users.

**Approach**: Hash-based instance ID from MAC address:

```python
import hashlib
import getmac

def generate_instance_id() -> str:
    """Generate stable anonymous instance ID."""
    mac = getmac.get_mac_address()
    if mac:
        # Salt with "marcus-" prefix for namespace separation
        return hashlib.sha256(f"marcus-{mac}".encode()).hexdigest()[:16]
    else:
        # Fallback to random UUID if MAC unavailable
        return str(uuid.uuid4())[:16]
```

**Properties**:
- **Stable**: Same ID across restarts on same machine
- **Anonymous**: Cannot reverse to identify user
- **Collision-resistant**: 16-hex-char hash (64 bits entropy)
- **Machine-bound**: Different ID if user reinstalls on new hardware

### Project Identification

**Goal**: Track project lifecycle without exposing project names.

**Approach**: Hash project name with instance-specific salt:

```python
def hash_project_id(project_name: str, instance_salt: str) -> str:
    """Hash project ID with instance-specific salt."""
    combined = f"{instance_salt}:{project_name}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]
```

**Properties**:
- **Per-instance isolation**: Same project name on different instances = different hashes
- **Lifecycle tracking**: Can track start → complete for same project
- **Cannot correlate across instances**: Different users building "todo-app" have different hashes

### AI Keyword Extraction

**Goal**: Extract semantic meaning from descriptions without transmitting raw text.

**Approach**: Use LLM to extract structured keywords:

```python
async def extract_keywords(description: str) -> dict:
    """Extract anonymized keywords from project description."""
    prompt = f"""
    Extract structured metadata from this project description.

    Description: {description}

    Return JSON with:
    - keywords: List of 3-10 technical keywords
    - category: One of [web-app, cli-tool, data-pipeline, ml-model, api, library, automation]
    - complexity: Float 0-10 (0=trivial, 10=extremely complex)
    - tech_stack: Inferred technologies (languages, frameworks)

    Do NOT include any raw text from the description.
    """

    response = await ai_provider.generate(prompt)
    return json.loads(response)
```

**Example**:
```
Input: "Build a REST API for managing user authentication with OAuth2, JWT tokens, and PostgreSQL database"

Output:
{
  "keywords": ["api", "authentication", "oauth", "jwt", "database", "rest"],
  "category": "backend-api",
  "complexity": 7.5,
  "tech_stack": {
    "languages": ["python"],
    "frameworks": ["fastapi", "sqlalchemy"],
    "databases": ["postgresql"]
  }
}
```

### What We Don't Collect

**Explicitly Excluded**:
- ❌ User names, emails, or any PII
- ❌ File paths or directory structures
- ❌ Source code or code snippets
- ❌ Raw error messages or stack traces
- ❌ Raw project descriptions (only AI-extracted keywords)
- ❌ Task descriptions (only counts and classifications)
- ❌ Kanban board names or card content
- ❌ API keys, credentials, or configuration values
- ❌ IP addresses (not logged by telemetry service)
- ❌ Session tokens or authentication data
- ❌ Individual agent actions or decisions (only aggregated session metrics)

**Privacy Principles**:
1. **Aggregate over individual** - Track patterns, not people
2. **Classify, don't copy** - Categories instead of content
3. **Count, don't capture** - Metrics instead of data
4. **Hash, don't store** - Anonymize identifiers

## Infrastructure Architecture

### Services Overview

| Service | Domain | Purpose | Technology |
|---------|--------|---------|------------|
| Telemetry API | `telemetry.marcus-ai.dev` | Event collection endpoint | FastAPI + PostgreSQL |
| Stats Dashboard | `stats.marcus-ai.dev` | Public analytics dashboard | React + TypeScript |
| Privacy Docs | `privacy.marcus-ai.dev` | Privacy policy and transparency | MkDocs / Docusaurus |

### Telemetry Collection API

**Endpoint**: `https://telemetry.marcus-ai.dev/api/v1/events`

**Technology Stack**:
- **Framework**: FastAPI (async Python web framework)
- **Database**: PostgreSQL 15 with JSONB support
- **Cache**: Redis (rate limiting, deduplication)
- **Deployment**: Docker + Kubernetes (DigitalOcean/AWS)

**API Endpoints**:

```
POST /api/v1/events
- Accept batch of telemetry events
- Validate schema and version
- Deduplicate by event_id
- Rate limit by instance_id
- Return 202 Accepted (async processing)

GET /api/v1/health
- Health check endpoint
- Database connectivity status
- Queue depth metrics

GET /api/v1/stats
- Public aggregated statistics
- Powers stats.marcus-ai.dev dashboard
- Cached heavily (Redis)
```

**Request Schema**:
```json
{
  "events": [
    {
      "event_id": "uuid-v4",
      "event_type": "project_lifecycle",
      "event_version": "1.0.0",
      "timestamp": "2025-12-22T15:30:00Z",
      "instance_id": "anon-abc123def456",
      "marcus_version": "0.1.0",
      "system_info": {
        "os": "Darwin",
        "python_version": "3.11.5",
        "architecture": "arm64"
      },
      "data": {
        // Event-specific payload
      }
    }
  ]
}
```

**Rate Limiting**:
- **Per instance**: 1000 events/hour
- **Global**: 100k events/hour (burst protection)
- **Error reports**: 10/hour per instance (prevent spam)

**Database Schema**:

```sql
CREATE TABLE telemetry_events (
    id BIGSERIAL PRIMARY KEY,
    event_id UUID UNIQUE NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    event_version VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    instance_id VARCHAR(32) NOT NULL,
    marcus_version VARCHAR(20) NOT NULL,
    system_info JSONB,
    data JSONB,
    received_at TIMESTAMPTZ DEFAULT NOW(),
    processed BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_event_type ON telemetry_events(event_type);
CREATE INDEX idx_instance_id ON telemetry_events(instance_id);
CREATE INDEX idx_timestamp ON telemetry_events(timestamp);
CREATE INDEX idx_received_at ON telemetry_events(received_at);
CREATE INDEX idx_processed ON telemetry_events(processed);

-- JSONB indexes for common queries
CREATE INDEX idx_data_category ON telemetry_events
    USING gin ((data->'classification'->'primary_category'));
CREATE INDEX idx_data_outcome ON telemetry_events
    USING gin ((data->'outcome'->'status'));
```

**Data Retention**:
- **Raw events**: 90 days (then archived to S3/cold storage)
- **Aggregated stats**: Indefinite
- **Error reports**: 30 days

### Stats Dashboard

**Domain**: `https://stats.marcus-ai.dev`

**Purpose**: Public transparency dashboard showing aggregated telemetry data.

**Technology Stack**:
- **Frontend**: React + TypeScript + Recharts
- **Deployment**: Static hosting (Vercel/Netlify) or S3 + CloudFront
- **API**: Consumes `/api/v1/stats` from telemetry service

**Dashboard Sections**:

1. **Usage Overview**:
   - Total Marcus instances (unique instance_ids in last 30 days)
   - Active projects (last 7 days)
   - Total projects created (all-time)

2. **Success Metrics**:
   - Project completion rate (completed / total)
   - Average completion time
   - Common failure categories

3. **Application Types**:
   - Pie chart: Primary categories (web-app, cli-tool, api, etc.)
   - Bar chart: Top secondary categories
   - Trend: Category popularity over time

4. **Agent Model Distribution** (BYOA Tracking):
   - Most popular agent models (Claude 3.5 Sonnet, GPT-4, etc.)
   - Provider distribution (Anthropic, OpenAI, Custom)
   - Model selection by role (which models for Backend vs Frontend vs QA)
   - Agent registration trends over time

5. **AI Usage Metrics**:
   - Most popular models (Claude 3.5 Sonnet, GPT-4, etc.)
   - Average tokens per project
   - Average cost per project
   - Token consumption trends over time
   - Model selection by operation type

6. **Agent Activity & Efficiency**:
   - Average agent idle time percentage
   - Work distribution balance (coefficient)
   - Agents waiting for work (count and duration)
   - Task queue depth trends
   - Bottleneck frequency (dependency blocks, resource contention)
   - Parallelization potential vs actual utilization
   - Missed parallel opportunities trend
   - Assignment conflict rates
   - Smart retry effectiveness

7. **Coordination & Scheduling Metrics**:
   - Average dependency graph complexity (depth/width)
   - Dependency inference method effectiveness
   - CPM prediction accuracy (predicted vs actual critical path)
   - Optimal vs actual agent count distribution
   - Scheduling efficiency gain achieved
   - Task reversion and orphan recovery rates
   - Assignment monitor uptime

8. **Quality Metrics**:
   - Quality score distribution (Excellent/Good/Basic/Poor)
   - Code quality trends (test coverage, review coverage)
   - Process quality patterns
   - Delivery quality metrics
   - Quality prediction accuracy
   - Technical debt indicators

9. **Performance**:
   - Average API response times (p50, p95, p99)
   - Average agent session duration
   - Average tasks per project

10. **Feature Adoption**:
   - MCP tool usage frequency
   - Integration enablement rates (Kanban, Cato)
   - Marcus version distribution

11. **System Health**:
   - Error rate trend
   - Top error categories
   - Recovery success rate

**Example Chart**:
```typescript
// Project completion rate over time
interface CompletionData {
  date: string;
  completed: number;
  failed: number;
  abandoned: number;
  completion_rate: number;
}

const CompletionRateChart: React.FC = () => {
  const { data } = useTelemetryStats('/api/v1/stats/completion-rate');

  return (
    <LineChart data={data}>
      <XAxis dataKey="date" />
      <YAxis />
      <Tooltip />
      <Line type="monotone" dataKey="completion_rate" stroke="#8884d8" />
    </LineChart>
  );
};
```

**Data Refresh**: Every 15 minutes (cached at API level).

### Privacy Documentation Site

**Domain**: `https://privacy.marcus-ai.dev`

**Purpose**: Transparent documentation of telemetry practices.

**Technology Stack**:
- **Framework**: MkDocs or Docusaurus (static site generator)
- **Deployment**: GitHub Pages or Netlify

**Content Structure**:

```
/
├── index.md                  # Privacy overview
├── what-we-collect.md        # Event types and schemas
├── anonymization.md          # How we protect privacy
├── opt-out.md                # How to disable telemetry
├── data-retention.md         # Storage and deletion policies
├── third-parties.md          # Where data is sent (none)
├── transparency-report.md    # Quarterly usage reports
└── contact.md                # Privacy questions contact
```

**Key Pages**:

**`what-we-collect.md`**:
- Complete list of 6 event types
- Full JSON schemas with examples
- Explanation of each field
- What we DON'T collect (exclusion list)

**`anonymization.md`**:
- Instance ID generation explained
- Project hashing approach
- AI keyword extraction process
- No PII guarantee

**`opt-out.md`**:
```bash
# Disable telemetry entirely
marcus config set telemetry.phone_home.enabled false

# Disable specific event types
marcus config set telemetry.phone_home.send_project_lifecycle false
marcus config set telemetry.phone_home.send_error_reports false

# Check current telemetry settings
marcus config get telemetry
```

**`transparency-report.md`**:
- Quarterly report: Total events received, unique instances, top categories
- Example: "Q1 2026: 50,000 events from 1,200 instances, top category: backend-api (35%)"

## Client Implementation

### Phone-Home Client

**File**: `src/telemetry/phone_home.py`

```python
"""Phone-home telemetry client for Marcus."""

import asyncio
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiofiles
import getmac
import httpx

from src.config.marcus_config import get_config


class PhoneHomeClient:
    """Handles phone-home telemetry transmission."""

    def __init__(
        self,
        endpoint: str | None = None,
        batch_size: int = 100,
        batch_interval_seconds: int = 600,
        enabled: bool = True,
    ):
        """
        Initialize phone-home client.

        Parameters
        ----------
        endpoint : str | None
            Telemetry API endpoint (default from config)
        batch_size : int
            Events to batch before sending (default 100)
        batch_interval_seconds : int
            Max time between sends (default 600 = 10 min)
        enabled : bool
            Whether telemetry is enabled
        """
        config = get_config()
        self.endpoint = endpoint or config.telemetry.phone_home.endpoint
        self.batch_size = batch_size
        self.batch_interval_seconds = batch_interval_seconds
        self.enabled = enabled and config.telemetry.phone_home.enabled

        self._batch: list[dict[str, Any]] = []
        self._queue_file = Path("data/telemetry/phone_home_queue.jsonl")
        self._queue_file.parent.mkdir(parents=True, exist_ok=True)

        self._instance_id = self._generate_instance_id()
        self._background_task: asyncio.Task | None = None

    def _generate_instance_id(self) -> str:
        """Generate stable anonymous instance ID from MAC address."""
        mac = getmac.get_mac_address()
        if mac:
            return hashlib.sha256(f"marcus-{mac}".encode()).hexdigest()[:16]
        else:
            # Fallback to random UUID
            return str(uuid.uuid4())[:16]

    async def log_event(
        self, event_type: str, event_data: dict[str, Any]
    ) -> None:
        """
        Log telemetry event for phone-home transmission.

        Parameters
        ----------
        event_type : str
            Event type (project_lifecycle, agent_session, etc.)
        event_data : dict[str, Any]
            Event-specific payload
        """
        if not self.enabled:
            return

        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "event_version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "instance_id": self._instance_id,
            "marcus_version": "0.1.0",  # TODO: Get from package metadata
            "system_info": self._get_system_info(),
            "data": event_data,
        }

        self._batch.append(event)

        # Send if batch full
        if len(self._batch) >= self.batch_size:
            await self._send_batch()

    def _get_system_info(self) -> dict[str, str]:
        """Get system information for telemetry context."""
        import platform
        import sys

        return {
            "os": platform.system(),
            "os_version": platform.release(),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "architecture": platform.machine(),
        }

    async def _send_batch(self) -> None:
        """Send batched events to telemetry service."""
        if not self._batch:
            return

        payload = {"events": self._batch}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.endpoint,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()

            # Clear batch on success
            self._batch.clear()

        except (httpx.HTTPError, httpx.TimeoutException) as e:
            # Queue for retry on failure
            await self._queue_for_retry(payload)
            # Don't raise - telemetry failures shouldn't break Marcus

    async def _queue_for_retry(self, payload: dict[str, Any]) -> None:
        """Queue failed batch for retry."""
        async with aiofiles.open(self._queue_file, mode="a") as f:
            await f.write(json.dumps(payload) + "\n")

    async def start_background_sender(self) -> None:
        """Start background task for periodic batch sending."""
        if self._background_task is not None:
            return

        async def sender_loop() -> None:
            while True:
                await asyncio.sleep(self.batch_interval_seconds)
                await self._send_batch()

        self._background_task = asyncio.create_task(sender_loop())

    async def stop_background_sender(self) -> None:
        """Stop background sender and flush remaining events."""
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
            self._background_task = None

        # Final flush
        await self._send_batch()

    async def flush(self) -> None:
        """Immediately send all batched events."""
        await self._send_batch()


# Global instance
_phone_home_client: PhoneHomeClient | None = None


def get_phone_home_client() -> PhoneHomeClient:
    """Get global phone-home client instance."""
    global _phone_home_client
    if _phone_home_client is None:
        _phone_home_client = PhoneHomeClient()
    return _phone_home_client
```

### Anonymizer

**File**: `src/telemetry/anonymizer.py`

```python
"""Anonymization utilities for telemetry data."""

import hashlib
import json
from typing import Any

from src.ai.base_ai_provider import BaseAIProvider


class TelemetryAnonymizer:
    """Handles anonymization of telemetry data."""

    def __init__(self, instance_id: str, ai_provider: BaseAIProvider):
        """
        Initialize anonymizer.

        Parameters
        ----------
        instance_id : str
            Anonymous instance identifier
        ai_provider : BaseAIProvider
            AI provider for keyword extraction
        """
        self.instance_id = instance_id
        self.ai_provider = ai_provider

    def hash_project_id(self, project_name: str) -> str:
        """
        Hash project name with instance-specific salt.

        Parameters
        ----------
        project_name : str
            Original project name

        Returns
        -------
        str
            Anonymized project ID hash
        """
        combined = f"{self.instance_id}:{project_name}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    async def extract_project_keywords(
        self, description: str
    ) -> dict[str, Any]:
        """
        Extract anonymized keywords from project description.

        Parameters
        ----------
        description : str
            Raw project description

        Returns
        -------
        dict[str, Any]
            Extracted metadata (keywords, category, complexity, tech_stack)
        """
        prompt = f"""
Extract structured metadata from this project description.

Description: {description}

Return ONLY valid JSON with this exact structure:
{{
  "keywords": ["keyword1", "keyword2", ...],  // 3-10 technical keywords
  "category": "web-app|cli-tool|data-pipeline|ml-model|mobile-app|api|library|automation",
  "complexity": 0.0,  // Float 0-10 (0=trivial, 10=extremely complex)
  "tech_stack": {{
    "languages": ["python", ...],
    "frameworks": ["fastapi", ...],
    "databases": ["postgresql", ...]
  }}
}}

Rules:
- Do NOT include any raw text from the description
- Only extract technical keywords
- Infer tech stack from generic patterns
- Classify into broad categories only
"""

        try:
            response = await self.ai_provider.generate(
                prompt=prompt,
                temperature=0.3,  # Low temperature for consistent extraction
            )

            # Parse JSON response
            metadata = json.loads(response.strip())

            # Validate structure
            assert "keywords" in metadata
            assert "category" in metadata
            assert "complexity" in metadata
            assert "tech_stack" in metadata

            return metadata

        except (json.JSONDecodeError, AssertionError, KeyError):
            # Fallback to minimal metadata on failure
            return {
                "keywords": [],
                "category": "unknown",
                "complexity": 0.0,
                "tech_stack": {
                    "languages": [],
                    "frameworks": [],
                    "databases": [],
                },
            }

    def anonymize_error_context(
        self, error_message: str, stack_trace: str
    ) -> dict[str, str]:
        """
        Anonymize error information (category only, no details).

        Parameters
        ----------
        error_message : str
            Raw error message
        stack_trace : str
            Raw stack trace

        Returns
        -------
        dict[str, str]
            Anonymized error context (category, type, severity)
        """
        # Simple keyword-based categorization
        # In production, use LLM for more accurate classification

        error_lower = error_message.lower()

        # Determine category
        if "kanban" in error_lower or "board" in error_lower:
            category = "kanban_integration"
        elif "anthropic" in error_lower or "openai" in error_lower:
            category = "ai_provider"
        elif "database" in error_lower or "sql" in error_lower:
            category = "database"
        elif "config" in error_lower or "credential" in error_lower:
            category = "configuration"
        elif "timeout" in error_lower or "network" in error_lower:
            category = "network"
        else:
            category = "unknown"

        # Determine type
        if "timeout" in error_lower:
            error_type = "timeout"
        elif "auth" in error_lower or "permission" in error_lower:
            error_type = "authentication"
        elif "validation" in error_lower or "invalid" in error_lower:
            error_type = "validation"
        elif "rate" in error_lower and "limit" in error_lower:
            error_type = "rate_limit"
        elif "not found" in error_lower or "missing" in error_lower:
            error_type = "dependency_missing"
        else:
            error_type = "unknown"

        return {
            "error_category": category,
            "error_type": error_type,
            "severity": "error",  # TODO: Infer from exception type
        }
```

### Integration with Existing Audit Logger

**File**: `src/marcus_mcp/audit.py` (modifications)

```python
# Add to existing AuditLogger class

async def log_for_phone_home(
    self,
    event_type: str,
    event_data: dict[str, Any],
) -> None:
    """
    Log event for phone-home telemetry in addition to local audit.

    Parameters
    ----------
    event_type : str
        Telemetry event type
    event_data : dict[str, Any]
        Event-specific payload (already anonymized)
    """
    from src.telemetry.phone_home import get_phone_home_client

    client = get_phone_home_client()
    await client.log_event(event_type, event_data)
```

### Configuration

**File**: `config_marcus.json` (add telemetry section)

```json
{
  "telemetry": {
    "phone_home": {
      "enabled": true,
      "endpoint": "https://telemetry.marcus-ai.dev/api/v1/events",
      "batch_size": 100,
      "batch_interval_seconds": 600,
      "send_project_lifecycle": true,
      "send_project_classification": true,
      "send_agent_performance": true,
      "send_ai_usage_basic": true,
      "send_ai_usage_prompts": false,
      "send_coordination_quality": true,
      "send_feature_usage": true,
      "send_performance_metrics": true,
      "send_error_reports": true
    },
    "local_audit": {
      "enabled": true,
      "retention_days": 30
    }
  }
}
```

**File**: `src/config/schemas.py` (add schema)

```python
class PhoneHomeTelemetryConfig(BaseModel):
    """Phone-home telemetry configuration."""

    enabled: bool = True
    endpoint: str = "https://telemetry.marcus-ai.dev/api/v1/events"
    batch_size: int = 100
    batch_interval_seconds: int = 600
    send_project_lifecycle: bool = True
    send_project_classification: bool = True
    send_agent_performance: bool = True
    send_ai_usage_basic: bool = True
    send_ai_usage_prompts: bool = False
    send_coordination_quality: bool = True
    send_feature_usage: bool = True
    send_performance_metrics: bool = True
    send_error_reports: bool = True


class LocalAuditConfig(BaseModel):
    """Local audit logging configuration."""

    enabled: bool = True
    retention_days: int = 30


class TelemetryConfig(BaseModel):
    """Telemetry configuration."""

    phone_home: PhoneHomeTelemetryConfig = Field(
        default_factory=PhoneHomeTelemetryConfig
    )
    local_audit: LocalAuditConfig = Field(default_factory=LocalAuditConfig)
```

## First-Run Consent Flow

### User Experience

On first Marcus run, display privacy prompt:

```
┌─────────────────────────────────────────────────────────────────┐
│                  Marcus Telemetry & Privacy                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│ Marcus collects anonymous telemetry to improve the system.       │
│                                                                   │
│ What we collect:                                                  │
│   ✓ Project success/failure rates (anonymized)                   │
│   ✓ Application types (AI-extracted keywords only)               │
│   ✓ Agent performance metrics                                    │
│   ✓ AI model usage and token consumption (no prompts)            │
│   ✓ Feature usage (which MCP tools you use)                      │
│   ✓ System performance (response times, resource usage)          │
│   ✓ Error patterns (categories only, no details)                 │
│                                                                   │
│ What we DON'T collect:                                           │
│   ✗ Your name, email, or any personal information                │
│   ✗ Source code or file paths                                    │
│   ✗ Project names or descriptions (only AI keywords)             │
│   ✗ AI prompts or responses (unless you opt-in separately)       │
│   ✗ Error messages or stack traces                               │
│                                                                   │
│ Your instance ID: anon-abc123def456 (cannot identify you)        │
│                                                                   │
│ Learn more: https://privacy.marcus-ai.dev                        │
│ See collected data: https://stats.marcus-ai.dev                  │
│                                                                   │
│ Enable telemetry? [Y/n]:                                         │
│                                                                   │
│ You can change this later:                                       │
│   marcus config set telemetry.phone_home.enabled false           │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

**Default**: Opt-in (requires explicit 'Y' or Enter)

**Implementation**:

```python
async def show_telemetry_consent() -> bool:
    """
    Show first-run telemetry consent prompt.

    Returns
    -------
    bool
        True if user consented, False otherwise
    """
    print("┌" + "─" * 65 + "┐")
    print("│" + " " * 20 + "Marcus Telemetry & Privacy" + " " * 19 + "│")
    print("├" + "─" * 65 + "┤")
    # ... (print full prompt)

    response = input("Enable telemetry? [Y/n]: ").strip().lower()

    if response in ("y", "yes", ""):
        # Save consent
        config = get_config()
        config.telemetry.phone_home.enabled = True
        save_config(config)
        print("\n✓ Telemetry enabled. Thank you for helping improve Marcus!")
        return True
    else:
        config = get_config()
        config.telemetry.phone_home.enabled = False
        save_config(config)
        print("\n✓ Telemetry disabled. You can enable it later with:")
        print("  marcus config set telemetry.phone_home.enabled true")
        return False
```

### Privacy Policy Summary

**Key Points**:

1. **What we collect**: 6 event types (lifecycle, classification, agent sessions, features, performance, errors)
2. **What we don't collect**: PII, code, file paths, raw descriptions, error messages, stack traces
3. **Anonymization**: Hash-based instance IDs, AI keyword extraction, categorization only
4. **Data retention**: 90 days raw, indefinite aggregated
5. **Third parties**: None (data not shared)
6. **Opt-out**: `marcus config set telemetry.phone_home.enabled false`
7. **Transparency**: Public stats at `stats.marcus-ai.dev`
8. **Contact**: `privacy@marcus-ai.dev`

## Week 2 Implementation Timeline

### Monday: User Journey Tracking + Agent Registration

**Goal**: Implement project lifecycle and agent registration telemetry.

**Tasks**:
1. Implement `PhoneHomeClient` in `src/telemetry/phone_home.py`
2. Implement `TelemetryAnonymizer` in `src/telemetry/anonymizer.py`
3. Add telemetry config schema to `src/config/schemas.py`
4. **Update `register_agent` MCP tool** in `src/marcus_mcp/tools/agent.py`:
   - Add REQUIRED `model_info` parameter
   - Log `agent_registration` telemetry event
   - Validate model_info structure
5. Integrate with project creation in `src/marcus_mcp/tools/project_management.py`:
   - Log `project_lifecycle` event on `create_project`
6. Integrate with project completion tracking
7. Add first-run consent prompt
8. Write unit tests for anonymization and agent registration

**Deliverables**:
- Phone-home client with batching and queueing
- `register_agent` tool updated with required `model_info`
- Agent registration events being sent
- Project lifecycle events being sent
- First-run consent flow
- 80%+ test coverage

### Tuesday: AI Usage Tracking

**Goal**: Implement AI model usage and token consumption telemetry.

**Tasks**:
1. Add token tracking to AI provider base class (`src/ai/base_ai_provider.py`)
2. Implement `ai_usage` event aggregation (hourly batches)
3. Track model selection, token counts, and costs per operation
4. Add operation categorization (task_decomposition, code_generation, etc.)
5. Implement opt-in prompt logging infrastructure (disabled by default)
6. Write unit tests for token tracking

**Deliverables**:
- AI usage telemetry (basic) working
- Token consumption being tracked
- Cost estimation per project
- Opt-in prompt logging ready (disabled)
- Tests passing

### Wednesday: Agent Sessions and Feature Usage

**Goal**: Implement agent session and feature usage telemetry with parallelization analysis.

**Tasks**:
1. Add `agent_session` event logging to agent coordination code
2. Implement parallelization analysis:
   - Track dependency graphs
   - Calculate parallelization potential
   - Detect missed parallel opportunities
   - Identify agent underutilization events
3. Implement `feature_usage` aggregation (hourly batches)
4. Track MCP tool calls in `src/marcus_mcp/handlers.py`
5. Add performance metrics collection
6. Implement background sender task
7. Write integration tests

**Deliverables**:
- Agent session telemetry with parallelization analysis
- Feature usage tracking
- Background batch sender running
- Integration tests passing

### Thursday: Coordination Quality, Project Classification, and Error Reporting

**Goal**: Implement coordination quality metrics, AI-based project classification, and error reporting telemetry.

**Tasks**:
1. **Implement coordination_quality event collection**:
   - Collect dependency metrics from `src/marcus_mcp/coordinator/dependency_wiring.py`
   - Track scheduling efficiency from `src/marcus_mcp/coordinator/scheduler.py`
   - Monitor task coordination from assignment system
   - Gather quality metrics from `src/monitoring/project_monitor.py`
   - Track retry strategy effectiveness from smart retry system
   - Collect monitoring health data
   - Calculate project complexity indicators
2. Implement AI keyword extraction in `TelemetryAnonymizer`
3. Add `project_classification` event after planning completes
4. Test classification accuracy with sample projects
5. Integrate with error framework (`src/core/error_framework.py`)
6. Add `error_report` event logging to error handlers
7. Implement error categorization
8. Add rate limiting for error reports (max 10/hour)
9. Write tests for coordination metrics, keyword extraction, and error anonymization

**Deliverables**:
- Coordination quality telemetry working (dependency, scheduling, quality metrics)
- AI keyword extraction working
- Project classification events being sent
- Error reports being sent
- Proper categorization and anonymization
- Rate limiting working

### Friday: Testing & Documentation

**Goal**: Complete testing and documentation.

**Tasks**:
1. End-to-end telemetry testing
2. Verify all 9 event types being sent correctly:
   - project_lifecycle
   - project_classification
   - agent_registration (with model_info)
   - agent_session (with parallelization analysis)
   - ai_usage (with token tracking)
   - coordination_quality (NEW)
   - feature_usage
   - performance_metrics
   - error_report
3. Test opt-out flow for basic telemetry
4. Test opt-in flow for prompt logging (separate consent)
5. Test agent registration with model_info requirement
6. Load testing (simulate 1000 events/hour)
7. Verify token counting accuracy across different models
8. Verify parallelization analysis accuracy
9. Verify coordination quality metrics collection:
   - Dependency metrics accuracy
   - Scheduling efficiency calculations
   - Quality score computations
   - Retry strategy measurements
10. Write telemetry documentation:
    - `docs/telemetry.md` - User-facing telemetry guide
    - `docs/telemetry_development.md` - Developer guide
    - Include AI usage, agent registration, coordination quality, and prompt logging sections
11. Update `README.md` with telemetry info
12. Code review and cleanup

**Deliverables**:
- All tests passing (unit + integration + e2e)
- 80%+ coverage
- All 9 event types verified and sending correctly
- `register_agent` MCP tool updated to require `model_info`
- Parallelization analysis working correctly
- Coordination quality metrics collecting accurately
- Opt-in/opt-out flows tested
- Documentation complete
- Ready for Week 3 (CATO API integration)

## Infrastructure Deployment

### DNS Configuration

**Domain**: `marcus-ai.dev`

**DNS Records** (in your DNS provider):

```
# Telemetry API
telemetry.marcus-ai.dev    A       <API_SERVER_IP>
telemetry.marcus-ai.dev    AAAA    <API_SERVER_IPv6>

# Stats Dashboard
stats.marcus-ai.dev        CNAME   stats-dashboard.vercel.app
# OR (if self-hosting)
stats.marcus-ai.dev        A       <STATS_SERVER_IP>

# Privacy Docs
privacy.marcus-ai.dev      CNAME   marcus-ai.github.io
# OR (if self-hosting)
privacy.marcus-ai.dev      A       <DOCS_SERVER_IP>
```

### Deployment Options

#### Option 1: Minimal (MVP)

**For**: Early testing, low traffic (<10k events/day)

**Stack**:
- **Telemetry API**: DigitalOcean App Platform ($12/month)
- **Database**: Managed PostgreSQL Basic ($15/month)
- **Cache**: Redis Basic ($10/month)
- **Stats Dashboard**: Vercel Free Tier ($0)
- **Privacy Docs**: GitHub Pages ($0)

**Total**: ~$37/month

**Deployment**:
```bash
# Deploy API to DigitalOcean App Platform
doctl apps create --spec .do/app.yaml

# Deploy dashboard to Vercel
cd stats-dashboard
vercel deploy --prod

# Deploy docs to GitHub Pages
cd privacy-docs
mkdocs gh-deploy
```

#### Option 2: Production (Scalable)

**For**: Production use, high traffic (>100k events/day)

**Stack**:
- **Telemetry API**: AWS ECS Fargate (2 tasks, $50/month)
- **Database**: AWS RDS PostgreSQL (db.t3.medium, $75/month)
- **Cache**: AWS ElastiCache Redis (cache.t3.micro, $15/month)
- **CDN**: CloudFront ($5-20/month)
- **Stats Dashboard**: S3 + CloudFront ($5/month)
- **Privacy Docs**: S3 + CloudFront ($5/month)

**Total**: ~$155/month

**Deployment**:
```bash
# Infrastructure as Code (Terraform)
cd infrastructure/terraform
terraform init
terraform plan
terraform apply

# Deploy API to ECS
aws ecr get-login-password | docker login --username AWS --password-stdin <ECR_URI>
docker build -t marcus-telemetry-api .
docker tag marcus-telemetry-api:latest <ECR_URI>/marcus-telemetry-api:latest
docker push <ECR_URI>/marcus-telemetry-api:latest
aws ecs update-service --cluster marcus --service telemetry-api --force-new-deployment

# Deploy dashboard to S3
cd stats-dashboard
npm run build
aws s3 sync dist/ s3://stats.marcus-ai.dev/ --delete
aws cloudfront create-invalidation --distribution-id <DIST_ID> --paths "/*"
```

### Monitoring and Alerting

**Metrics to Monitor**:
- Event ingestion rate (events/second)
- API response time (p50, p95, p99)
- Database connection pool usage
- Redis cache hit rate
- Error rate (5xx responses)
- Queue depth (unprocessed events)

**Alerts**:
- API down (health check failing)
- High error rate (>1% of requests)
- Database connection errors
- High queue depth (>1000 unprocessed events)
- Disk space low (<20% remaining)

**Tools**:
- **Monitoring**: Prometheus + Grafana
- **Logging**: AWS CloudWatch or Datadog
- **Uptime**: UptimeRobot (free tier)
- **Alerting**: PagerDuty or email

## Cost Estimates

### Infrastructure Costs

| Service | Minimal (MVP) | Production |
|---------|--------------|------------|
| **API Server** | DigitalOcean App Platform ($12) | AWS ECS Fargate 2 tasks ($50) |
| **Database** | Managed PostgreSQL Basic ($15) | AWS RDS db.t3.medium ($75) |
| **Cache** | Redis Basic ($10) | AWS ElastiCache ($15) |
| **CDN** | None ($0) | CloudFront ($5-20) |
| **Dashboard** | Vercel Free ($0) | S3 + CloudFront ($5) |
| **Docs** | GitHub Pages ($0) | S3 + CloudFront ($5) |
| **Monitoring** | None ($0) | Grafana Cloud Free ($0) |
| **Domain** | marcus-ai.dev ($12/year = $1/month) | Same ($1) |
| **Total/month** | **$38** | **$156** |

### Traffic Estimates

**Assumptions**:
- 1,000 active Marcus instances
- Each instance sends ~100 events/day (averaged)
- Total: 100,000 events/day = 3M events/month

**Storage**:
- Average event size: 2 KB
- Monthly storage: 3M × 2 KB = 6 GB
- PostgreSQL storage (90-day retention): 18 GB
- Database cost: Covered by managed DB pricing

**Bandwidth**:
- Ingress: 6 GB/month (free on most clouds)
- Egress (stats API): ~1 GB/month (free tier)

### Scaling Considerations

**When to scale**:
- **10k events/day**: Minimal setup sufficient
- **100k events/day**: Consider production setup
- **1M events/day**: Add read replicas, separate analytics DB
- **10M events/day**: Partition tables, data warehousing (BigQuery/Redshift)

## Privacy and Compliance

### GDPR Compliance

**Right to Access**: Users can see aggregated stats at `stats.marcus-ai.dev`

**Right to Erasure**: Users can request deletion:
```bash
# Email privacy@marcus-ai.dev with instance_id
# We delete all events for that instance_id within 30 days
```

**Right to Opt-Out**: Built into config:
```bash
marcus config set telemetry.phone_home.enabled false
```

**Data Minimization**: Only collect what's necessary for improvement.

**Anonymization**: No PII collected, instance IDs are hashed.

### Legal Requirements

**Privacy Policy**: Required at `privacy.marcus-ai.dev`

**Terms of Service**: Optional (telemetry is opt-in)

**Cookie Policy**: Not applicable (no cookies, no browser tracking)

**Data Processing Agreement**: Not required (no personal data processed)

## Testing Strategy

### Unit Tests

**File**: `tests/unit/telemetry/test_phone_home.py`

```python
"""Unit tests for phone-home telemetry client."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from src.telemetry.phone_home import PhoneHomeClient


class TestPhoneHomeClient:
    """Test suite for PhoneHomeClient."""

    @pytest.fixture
    def mock_httpx_client(self):
        """Mock httpx.AsyncClient."""
        mock_client = Mock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.post = AsyncMock()
        return mock_client

    @pytest.mark.asyncio
    async def test_log_event_batches_events(self):
        """Test that events are batched before sending."""
        client = PhoneHomeClient(batch_size=3, enabled=True)

        await client.log_event("test_event", {"data": "1"})
        await client.log_event("test_event", {"data": "2"})

        # Batch not full yet, should not send
        assert len(client._batch) == 2

    @pytest.mark.asyncio
    async def test_send_batch_on_size_limit(self, mock_httpx_client):
        """Test that batch sends when size limit reached."""
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            client = PhoneHomeClient(batch_size=2, enabled=True)

            await client.log_event("test_event", {"data": "1"})
            await client.log_event("test_event", {"data": "2"})

            # Should have triggered send
            assert mock_httpx_client.post.called
            assert len(client._batch) == 0

    @pytest.mark.asyncio
    async def test_disabled_telemetry_does_not_send(self):
        """Test that disabled telemetry doesn't send events."""
        client = PhoneHomeClient(enabled=False)

        await client.log_event("test_event", {"data": "1"})

        assert len(client._batch) == 0
```

### Integration Tests

**File**: `tests/integration/telemetry/test_end_to_end.py`

```python
"""Integration tests for telemetry end-to-end flow."""

import pytest

from src.telemetry.phone_home import get_phone_home_client
from src.marcus_mcp.tools.project_management import create_project


class TestTelemetryEndToEnd:
    """Test end-to-end telemetry flow."""

    @pytest.mark.asyncio
    async def test_project_creation_logs_telemetry(self):
        """Test that creating a project logs telemetry event."""
        client = get_phone_home_client()
        initial_batch_size = len(client._batch)

        # Create project (should log telemetry)
        await create_project(
            project_name="test-project",
            project_description="A test project for telemetry",
        )

        # Verify event was logged
        assert len(client._batch) > initial_batch_size

        # Verify event structure
        event = client._batch[-1]
        assert event["event_type"] == "project_lifecycle"
        assert event["data"]["lifecycle_event"] == "created"
```

## Future Enhancements

### Phase 2: Advanced Analytics

- **Cohort analysis**: Track instance cohorts (install date groups)
- **Funnel analysis**: Project creation → completion funnel
- **Retention metrics**: How many instances stay active over time
- **A/B testing**: Compare feature variations

### Phase 3: Real-Time Streaming

- **WebSocket API**: Real-time event streaming for Cato dashboard
- **Event replay**: Debug agent sessions by replaying telemetry
- **Live monitoring**: Watch active projects in real-time

### Phase 4: ML-Powered Insights

- **Anomaly detection**: Identify unusual error patterns
- **Predictive models**: Predict project success likelihood
- **Recommendation engine**: Suggest best practices based on patterns

## Appendix: Example Events

### Example 1: Successful Project

```json
{
  "event_type": "project_lifecycle",
  "instance_id": "anon-abc123def456",
  "project_id_hash": "p-789xyz",
  "lifecycle_event": "completed",
  "project_summary": {
    "description_length": 180,
    "description_keywords": ["api", "rest", "authentication", "jwt", "fastapi"],
    "category": "backend-api",
    "complexity_score": 7.0,
    "estimated_task_count": 12,
    "estimated_duration_hours": 6.0
  },
  "outcome": {
    "status": "completed",
    "completion_percentage": 1.0,
    "actual_task_count": 14,
    "actual_duration_hours": 5.5,
    "agent_count": 2,
    "total_subtasks": 28
  }
}
```

### Example 2: Failed Project

```json
{
  "event_type": "project_lifecycle",
  "instance_id": "anon-abc123def456",
  "project_id_hash": "p-456abc",
  "lifecycle_event": "failed",
  "project_summary": {
    "description_length": 120,
    "description_keywords": ["cli", "automation", "scripts"],
    "category": "cli-tool",
    "complexity_score": 4.0,
    "estimated_task_count": 5,
    "estimated_duration_hours": 2.0
  },
  "outcome": {
    "status": "failed",
    "completion_percentage": 0.4,
    "actual_task_count": 2,
    "actual_duration_hours": 1.5,
    "agent_count": 1,
    "total_subtasks": 5
  },
  "failure_context": {
    "failure_type": "dependency_issue",
    "error_category": "configuration",
    "failed_at_stage": "execution",
    "retry_count": 3
  }
}
```

### Example 3: Agent Session

```json
{
  "event_type": "agent_session",
  "instance_id": "anon-abc123def456",
  "project_id_hash": "p-789xyz",
  "agent_metrics": {
    "agent_count": 3,
    "agent_models": [
      {
        "provider": "anthropic",
        "model_name": "claude-3-5-sonnet-20241022",
        "role": "Backend Developer"
      },
      {
        "provider": "anthropic",
        "model_name": "claude-3-5-sonnet-20241022",
        "role": "Frontend Developer"
      },
      {
        "provider": "openai",
        "model_name": "gpt-4-turbo-2024-04-09",
        "role": "QA Engineer"
      }
    ],
    "session_duration_seconds": 420,
    "coordination_events": 8,
    "task_handoffs": 3,
    "parallel_tasks": 2,
    "sequential_tasks": 4
  },
  "agent_activity": {
    "total_idle_time_seconds": 95,
    "avg_idle_time_per_agent_seconds": 32,
    "max_idle_time_seconds": 55,
    "idle_time_percentage": 0.23,
    "total_active_time_seconds": 325,
    "active_time_percentage": 0.77,
    "agents_waiting_for_work": {
      "count": 1,
      "avg_wait_duration_seconds": 32,
      "max_wait_duration_seconds": 55
    },
    "work_distribution": {
      "tasks_per_agent": [3, 2, 1],
      "avg_tasks_per_agent": 2.0,
      "work_balance_coefficient": 0.67
    }
  },
  "performance": {
    "avg_task_completion_seconds": 105,
    "max_task_completion_seconds": 180,
    "tasks_completed": 6,
    "tasks_failed": 0,
    "retry_count": 1
  },
  "coordination_quality": {
    "conflict_count": 0,
    "duplicate_work_detected": false,
    "communication_overhead_percentage": 0.18
  },
  "bottlenecks": {
    "task_queue_depth_max": 3,
    "task_queue_depth_avg": 1.5,
    "blocked_by_dependencies_count": 0,
    "resource_contention_events": 0
  }
}
```

### Example 4: Error Report

```json
{
  "event_type": "error_report",
  "instance_id": "anon-abc123def456",
  "project_id_hash": "p-456abc",
  "error_info": {
    "error_category": "kanban_integration",
    "error_type": "timeout",
    "severity": "error",
    "is_recoverable": true,
    "recovery_action_taken": "retry"
  },
  "context": {
    "operation": "create_task",
    "retry_count": 2,
    "time_since_start_seconds": 180,
    "previous_errors_in_session": 0
  },
  "system_state": {
    "active_agents": 2,
    "pending_tasks": 8,
    "kanban_connected": false,
    "ai_provider_status": "available"
  }
}
```

---

**Document Version**: 1.0.0
**Last Updated**: 2025-12-22
**Author**: Marcus Development Team
**Status**: Ready for Implementation (Week 2)
