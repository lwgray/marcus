# Marcus Analytics Tools Reference

This document provides a comprehensive reference for all 51 analytics tools available in the Marcus MCP system, organized by category with detailed descriptions of their purpose, analytics output, and usage.

## Tool Categories Overview

| Category | Tool Count | Purpose |
|----------|------------|---------|
| **Core Agent Management** | 6 | Agent lifecycle, registration, and monitoring |
| **Task Management & Analysis** | 8 | Task routing, progress tracking, and analysis |
| **Project Management & Monitoring** | 8 | Project lifecycle and health monitoring |
| **AI-Powered Predictions** | 5 | Predictive analytics and forecasting |
| **System Health & Diagnostics** | 4 | System monitoring and diagnostics |
| **Code Production Metrics** | 4 | Developer productivity and code quality |
| **Natural Language Processing** | 2 | AI-powered project and feature creation |
| **Pipeline Enhancement & Analysis** | 14 | Pipeline optimization and analysis |

---

## Core Agent Management (6 tools)

### 1. register_agent
**Purpose**: Register a new agent with the Marcus system
**Analytics Output**:
- Agent metadata (ID, name, role, skills)
- Registration timestamps
- Skill distribution across agents
- Role assignment patterns

**Input Parameters**:
- `agent_id` (string): Unique identifier for the agent
- `name` (string): Display name of the agent
- `role` (string): Agent role (developer, tester, analyst, etc.)
- `skills` (array): List of agent capabilities

### 2. get_agent_status
**Purpose**: Get real-time status and current assignment for an agent
**Analytics Output**:
- Agent availability status
- Current task assignment
- Activity timeline
- Utilization metrics

**Input Parameters**:
- `agent_id` (string): Agent to query

### 3. list_registered_agents
**Purpose**: List all registered agents in the system
**Analytics Output**:
- Complete agent roster
- Skill distribution analysis
- Role assignment overview
- Agent capacity planning data

**Input Parameters**: None

### 4. get_agent_metrics
**Purpose**: Get comprehensive performance metrics for a specific agent
**Analytics Output**:
- Utilization percentage
- Tasks completed vs assigned
- Success rate and failure analysis
- Skill distribution and effectiveness
- Average task completion time
- Performance trends over time

**Input Parameters**:
- `agent_id` (string): Agent to analyze
- `time_window` (string): Analysis period (1h/24h/7d/30d)

### 5. authenticate
**Purpose**: Authenticate client with role-based access control
**Analytics Output**:
- Authentication event logging
- Role assignment tracking
- Access pattern analysis
- Security metrics

**Input Parameters**:
- `client_id` (string): Client identifier
- `client_type` (string): Type of client (human/agent/system)
- `role` (string): Requested access role
- `metadata` (object): Additional client information

### 6. check_assignment_health
**Purpose**: Check health of the agent assignment tracking system
**Analytics Output**:
- Assignment system health score
- Lease statistics and distribution
- Assignment bottlenecks
- System capacity metrics

**Input Parameters**: None

---

## Task Management & Analysis (8 tools)

### 7. request_next_task
**Purpose**: Request optimal task assignment for an agent using AI-powered matching
**Analytics Output**:
- Task assignment optimization data
- Agent-task matching scores
- Assignment algorithm performance
- Queue depth and distribution

**Input Parameters**:
- `agent_id` (string): Agent requesting work

### 8. report_task_progress
**Purpose**: Report progress updates on assigned tasks
**Analytics Output**:
- Progress tracking metrics
- Velocity calculations
- Completion rate analysis
- Status transition patterns

**Input Parameters**:
- `agent_id` (string): Reporting agent
- `task_id` (string): Task being updated
- `status` (string): Current task status
- `progress` (number): Completion percentage
- `message` (string): Progress description

### 9. report_blocker
**Purpose**: Report blockers and impediments on tasks
**Analytics Output**:
- Blocker frequency analysis
- Root cause categorization
- Resolution time tracking
- Blocker impact assessment

**Input Parameters**:
- `agent_id` (string): Reporting agent
- `task_id` (string): Blocked task
- `blocker_description` (string): Description of the blocker
- `severity` (string): Blocker severity level

### 10. get_task_context
**Purpose**: Get comprehensive context for a specific task
**Analytics Output**:
- Task relationship mapping
- Decision history analysis
- Artifact dependency tracking
- Context switching patterns

**Input Parameters**:
- `task_id` (string): Task to analyze

### 11. get_task_metrics
**Purpose**: Get aggregated task metrics across all projects
**Analytics Output**:
- Task distribution by status/priority/assignee/label
- Completion rates and velocity
- Backlog analysis
- Resource allocation patterns

**Input Parameters**:
- `time_window` (string): Analysis period
- `group_by` (string): Grouping dimension (status/priority/assignee/label)

### 12. check_task_dependencies
**Purpose**: Analyze task dependencies and critical paths
**Analytics Output**:
- Upstream/downstream dependency mapping
- Circular dependency detection
- Critical path analysis
- Dependency bottleneck identification

**Input Parameters**:
- `task_id` (string): Task to analyze

### 13. log_decision
**Purpose**: Log architectural and technical decisions
**Analytics Output**:
- Decision impact analysis
- Architectural choice tracking
- Decision reversal patterns
- Knowledge base metrics

**Input Parameters**:
- `agent_id` (string): Decision maker
- `task_id` (string): Related task
- `decision` (object): Decision details

### 14. log_artifact
**Purpose**: Store and track work artifacts with smart organization
**Analytics Output**:
- Artifact creation patterns
- Knowledge base growth metrics
- Artifact reuse analysis
- Content categorization

**Input Parameters**:
- `task_id` (string): Associated task
- `filename` (string): Artifact name
- `content` (string): Artifact content
- `artifact_type` (string): Type classification
- `description` (string): Artifact description
- `location` (string): Storage location

---

## Project Management & Monitoring (8 tools)

### 15. get_project_status
**Purpose**: Get comprehensive current project status and health metrics
**Analytics Output**:
- Project velocity trends
- Completion percentage
- Resource utilization
- Health score calculation

**Input Parameters**: None (uses current project)

### 16. list_projects
**Purpose**: List and filter all available projects
**Analytics Output**:
- Project portfolio overview
- Tag-based categorization
- Provider distribution
- Project lifecycle analysis

**Input Parameters**:
- `filter_tags` (array): Optional tag filters
- `provider` (string): Optional provider filter

### 17. switch_project
**Purpose**: Switch active project context
**Analytics Output**:
- Project usage patterns
- Context switch frequency
- Project popularity metrics
- Workflow analysis

**Input Parameters**:
- `project_id` (string): Target project ID
- `project_name` (string): Alternative: project name

### 18. get_current_project
**Purpose**: Get information about the currently active project
**Analytics Output**:
- Active project metadata
- Usage tracking
- Session analytics
- Context utilization

**Input Parameters**: None

### 19. add_project
**Purpose**: Add new project to the system
**Analytics Output**:
- Project creation patterns
- Configuration analysis
- Setup complexity metrics
- Adoption tracking

**Input Parameters**:
- `name` (string): Project name
- `provider` (string): Provider type (planka, github, etc.)
- `config` (object): Provider-specific configuration
- `tags` (array): Project tags
- `make_active` (boolean): Set as active project

### 20. remove_project
**Purpose**: Remove project from the registry
**Analytics Output**:
- Project deletion tracking
- Cleanup metrics
- Project lifecycle analysis
- Data retention patterns

**Input Parameters**:
- `project_id` (string): Project to remove
- `confirm` (boolean): Confirmation flag

### 21. update_project
**Purpose**: Update existing project configuration
**Analytics Output**:
- Configuration change patterns
- Update frequency analysis
- Maintenance metrics
- Evolution tracking

**Input Parameters**:
- `project_id` (string): Project to update
- `name` (string): Optional new name
- `tags` (array): Optional new tags
- `config` (object): Optional configuration updates

### 22. get_project_metrics
**Purpose**: Get detailed performance metrics for a specific project
**Analytics Output**:
- Project velocity and trends
- Progress percentage
- Blocked task ratio
- Health score calculation
- Burndown chart data
- Resource allocation efficiency

**Input Parameters**:
- `project_id` (string): Project to analyze
- `time_window` (string): Analysis period

---

## AI-Powered Predictions (5 tools)

### 23. predict_completion_time
**Purpose**: Predict project completion with statistical confidence intervals
**Analytics Output**:
- Predicted completion dates
- Confidence intervals (50%, 80%, 95%)
- Velocity analysis and trends
- Risk factor identification
- Monte Carlo simulation results

**Input Parameters**:
- `project_id` (string): Project to analyze
- `include_confidence` (boolean): Include confidence intervals

### 24. predict_task_outcome
**Purpose**: Predict success probability for specific task assignments
**Analytics Output**:
- Success probability percentage
- Estimated completion duration
- Blockage risk assessment
- Confidence score
- Recommendation rationale

**Input Parameters**:
- `task_id` (string): Task to analyze
- `agent_id` (string): Proposed assignee

### 25. predict_blockage_probability
**Purpose**: Predict probability of tasks becoming blocked
**Analytics Output**:
- Blockage probability percentage
- Likely blocker categories
- Mitigation strategy recommendations
- At-risk dependencies
- Historical pattern analysis

**Input Parameters**:
- `task_id` (string): Task to analyze
- `include_mitigation` (boolean): Include mitigation suggestions

### 26. predict_cascade_effects
**Purpose**: Predict ripple effects of task delays across project
**Analytics Output**:
- Affected task identification
- Total project delay impact
- Critical path changes
- Completion date adjustments
- Resource reallocation suggestions

**Input Parameters**:
- `task_id` (string): Task with potential delay
- `delay_days` (number): Assumed delay duration

### 27. get_task_assignment_score
**Purpose**: Calculate fitness score for agent-task pairings
**Analytics Output**:
- Overall fitness score (0-100)
- Skill match percentage
- Agent availability score
- Historical performance factor
- Assignment recommendation strength

**Input Parameters**:
- `task_id` (string): Task to assign
- `agent_id` (string): Candidate agent

---

## System Health & Diagnostics (4 tools)

### 28. ping
**Purpose**: System connectivity check with advanced diagnostic capabilities
**Analytics Output**:
- System health indicators
- Lease statistics
- Assignment system state
- Performance metrics
- Diagnostic command results

**Input Parameters**:
- `echo` (string): Optional diagnostic command ('health', 'cleanup', 'reset')

### 29. get_system_metrics
**Purpose**: Get comprehensive system-wide performance metrics
**Analytics Output**:
- Active agent count
- System throughput metrics
- Average task duration
- System health score
- Resource utilization
- Performance trends

**Input Parameters**:
- `time_window` (string): Analysis period

### 30. check_board_health
**Purpose**: Analyze overall board health and detect systemic issues
**Analytics Output**:
- Overall health score
- Skill mismatch detection
- Circular dependency identification
- Bottleneck analysis
- Workload distribution assessment
- System recommendations

**Input Parameters**: None

### 31. get_usage_report
**Purpose**: Generate comprehensive usage statistics from audit logs
**Analytics Output**:
- Event count analysis
- Client activity patterns
- Error rate tracking
- Tool usage statistics
- Behavioral insights
- Performance patterns

**Input Parameters**:
- `days` (number): Analysis period in days

---

## Code Production Metrics (4 tools)

### 32. get_code_metrics
**Purpose**: Calculate comprehensive code production metrics for individual agents
**Analytics Output**:
- Commit frequency and patterns
- Lines of code added/deleted
- Files changed statistics
- Programming language distribution
- Code review activity
- Productivity trends

**Input Parameters**:
- `agent_id` (string): Agent to analyze
- `start_date` (string): Analysis start date
- `end_date` (string): Analysis end date

### 33. get_repository_metrics
**Purpose**: Get code metrics for entire repository
**Analytics Output**:
- Total commit count
- Pull request statistics
- Contributor activity
- Merge rate analysis
- Language breakdown
- Review turnaround times

**Input Parameters**:
- `repository` (string): Repository to analyze
- `time_window` (string): Analysis period

### 34. get_code_review_metrics
**Purpose**: Analyze code review activity and participation
**Analytics Output**:
- Reviews given vs received
- Review turnaround times
- Participation rate analysis
- Bottleneck identification
- Quality metrics
- Collaboration patterns

**Input Parameters**:
- `agent_id` (string): Agent to analyze
- `time_window` (string): Analysis period

### 35. get_code_quality_metrics
**Purpose**: Get code quality metrics from static analysis tools
**Analytics Output**:
- Test coverage percentage
- Code complexity metrics
- Technical debt analysis
- Code smell detection
- Security vulnerability count
- Quality trend analysis

**Input Parameters**:
- `repository` (string): Repository to analyze
- `branch` (string): Branch to analyze

---

## Natural Language Processing (2 tools)

### 36. create_project
**Purpose**: Create complete project structure from natural language description
**Analytics Output**:
- Project complexity analysis
- Task generation patterns
- Technology stack recommendations
- Effort estimation
- Success probability
- Template usage patterns

**Input Parameters**:
- `description` (string): Natural language project description
- `project_name` (string): Optional project name
- `options` (object): Configuration options
  - `complexity` (string): Project complexity level
  - `deployment` (string): Deployment preferences
  - `team_size` (number): Expected team size
  - `tech_stack` (array): Preferred technologies
  - `deadline` (string): Target completion date

### 37. add_feature
**Purpose**: Add feature to existing project using natural language
**Analytics Output**:
- Feature complexity analysis
- Integration point selection
- Task breakdown patterns
- Impact assessment
- Effort estimation
- Implementation recommendations

**Input Parameters**:
- `feature_description` (string): Natural language feature description
- `integration_point` (string): Where to integrate the feature

---

## Pipeline Enhancement & Analysis (14 tools)

### 38. pipeline_replay_start
**Purpose**: Start replay session for pipeline flow analysis
**Analytics Output**:
- Flow execution timeline
- Step-by-step analysis
- Performance bottlenecks
- Resource utilization patterns

**Input Parameters**:
- `flow_id` (string): Pipeline flow to replay

### 39. pipeline_replay_forward
**Purpose**: Step forward in pipeline replay session
**Analytics Output**:
- Forward execution patterns
- Step progression metrics
- Performance deltas
- State transitions

**Input Parameters**: None (uses active replay session)

### 40. pipeline_replay_backward
**Purpose**: Step backward in pipeline replay session
**Analytics Output**:
- Backward navigation patterns
- Regression analysis
- State rollback metrics
- Historical comparisons

**Input Parameters**: None (uses active replay session)

### 41. pipeline_replay_jump
**Purpose**: Jump to specific position in replay session
**Analytics Output**:
- Jump navigation patterns
- Position-specific analysis
- State comparison metrics
- Navigation efficiency

**Input Parameters**:
- `position` (number): Target position in replay

### 42. what_if_start
**Purpose**: Start what-if analysis session for scenario planning
**Analytics Output**:
- Baseline scenario establishment
- Parameter sensitivity analysis
- Optimization opportunity identification
- Risk assessment

**Input Parameters**:
- `flow_id` (string): Pipeline flow for analysis

### 43. what_if_simulate
**Purpose**: Simulate pipeline with specific modifications
**Analytics Output**:
- Modification impact assessment
- Performance delta analysis
- Resource requirement changes
- Risk factor updates

**Input Parameters**:
- `modifications` (array): List of modifications to apply

### 44. what_if_compare
**Purpose**: Compare all what-if scenarios for optimization
**Analytics Output**:
- Comparative performance analysis
- Optimization recommendations
- Trade-off analysis
- Best scenario identification

**Input Parameters**: None (compares all scenarios in session)

### 45. pipeline_compare
**Purpose**: Compare multiple pipeline flows for optimization
**Analytics Output**:
- Performance comparisons
- Efficiency metrics
- Pattern differences
- Optimization opportunities

**Input Parameters**:
- `flow_ids` (array): List of flows to compare

### 46. pipeline_report
**Purpose**: Generate comprehensive pipeline analysis report
**Analytics Output**:
- Complete flow analysis
- Performance metrics summary
- Optimization recommendations
- Executive summary
- Detailed technical analysis

**Input Parameters**:
- `flow_id` (string): Pipeline flow to report on
- `format` (string): Output format (HTML/Markdown/JSON)

### 47. pipeline_monitor_dashboard
**Purpose**: Get real-time monitoring dashboard data
**Analytics Output**:
- Live performance metrics
- Active flow status
- System resource utilization
- Alert notifications
- Trend indicators

**Input Parameters**: None

### 48. pipeline_monitor_flow
**Purpose**: Track specific flow progress and performance
**Analytics Output**:
- Flow-specific metrics
- Progress tracking
- Performance indicators
- Bottleneck identification
- Resource consumption

**Input Parameters**:
- `flow_id` (string): Flow to monitor

### 49. pipeline_predict_risk
**Purpose**: Predict failure risk and performance issues
**Analytics Output**:
- Failure probability assessment
- Risk factor identification
- Mitigation strategy recommendations
- Performance degradation predictions

**Input Parameters**:
- `flow_id` (string): Flow to analyze

### 50. pipeline_recommendations
**Purpose**: Get AI-powered optimization recommendations
**Analytics Output**:
- Performance improvement suggestions
- Efficiency optimization recommendations
- Resource allocation advice
- Best practice recommendations

**Input Parameters**:
- `flow_id` (string): Flow to optimize

### 51. pipeline_find_similar
**Purpose**: Find similar pipeline flows for pattern analysis
**Analytics Output**:
- Similar flow identification
- Pattern matching scores
- Reusability analysis
- Template suggestions
- Optimization transfer opportunities

**Input Parameters**:
- `flow_id` (string): Reference flow
- `limit` (number): Maximum similar flows to return

---

## Access Control Summary

**Human Endpoint** (23 tools): Essential tools for human developers using Claude Code
**Agent Endpoint** (16 tools): Core workflow tools for autonomous agents
**Analytics Endpoint** (51 tools): Complete tool suite for comprehensive analytics and monitoring

## Integration with Seneca Dashboard

These analytics tools provide the data foundation for Seneca's comprehensive dashboard capabilities:

1. **Real-time Monitoring**: Live system, project, and agent performance
2. **Predictive Analytics**: AI-powered forecasting and risk assessment
3. **Code Intelligence**: Developer productivity and quality metrics
4. **Pipeline Optimization**: Flow analysis and performance tuning
5. **Health Diagnostics**: System and project health monitoring
6. **Usage Analytics**: System utilization and behavioral insights

The combination of these 51 tools makes Marcus a comprehensive project management and analytics platform capable of providing deep insights into development team performance, project health, and optimization opportunities.
