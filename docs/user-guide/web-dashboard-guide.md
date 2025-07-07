# Marcus Web Dashboard User Guide

## Overview

The Marcus Web Dashboard provides a comprehensive interface for managing AI-driven software development projects. It combines project management, pipeline visualization, agent orchestration, and workflow analytics into a unified platform.

## Dashboard Tabs

### 1. Project Management Tab

**Purpose**: Create and manage software projects from inception to completion.

#### Key Features:

- **Create New Project**
  - Define project name, description, and type (Web App, API, CLI Tool, etc.)
  - Projects serve as containers for features and requirements

- **Add Features/Requirements**
  - Break down your project into specific features
  - Set priorities (High, Medium, Low)
  - Define acceptance criteria for each feature
  - Features are automatically converted into actionable tasks for agents

- **Workflow Controls**
  - **Auto-assign tasks**: Automatically distribute tasks to available agents
  - **Parallel execution**: Allow multiple agents to work simultaneously
  - **Continuous monitoring**: Track progress in real-time
  - **Max agents**: Control resource allocation (1-10 agents)

#### What to Look For:
- **Project Status Indicators**:
  - `Planning`: Initial setup phase
  - `Running`: Workflow is active
  - `Paused`: Temporarily halted
  - `Completed`: All tasks finished
  - `Stopped`: Manually terminated

#### Mitigation Strategies:
- Start with a small, well-defined project to test the system
- Add clear, specific acceptance criteria to avoid ambiguity
- Limit initial projects to 3-5 features
- Use high priority for critical path features

### 2. Live Monitor Tab

**Purpose**: Real-time visibility into active pipeline flows.

#### Key Metrics:
- **Active Flows**: Number of concurrent workflows
- **Flows/Hour**: Throughput rate
- **Success Rate**: Percentage of successful completions
- **Average Completion Time**: Typical duration for workflows

#### Flow Health Status:
- **Healthy** (Green): Normal operation
- **Warning** (Yellow): Potential issues detected
- **Critical** (Red): Immediate attention needed

#### What to Look For:
- Sudden drops in success rate
- Increasing completion times
- Flows stuck at specific stages
- Health status changes

#### Mitigation Strategies:
- **For Low Success Rate**: 
  - Check agent logs for errors
  - Verify external service availability
  - Review task complexity
  
- **For Slow Completion**:
  - Check for blocked tasks
  - Increase agent count
  - Enable parallel execution

### 3. Agent Management Tab

**Purpose**: Control and monitor AI agents working on your projects.

#### Agent States:
- **Idle**: Available for work
- **Working**: Currently processing a task
- **Blocked**: Waiting for resolution

#### Key Actions:
- **Register New Agent**: Add agents with specific roles
- **Request Task**: Manually assign work to idle agents
- **Task Progress Simulation**: Test agent responses

#### What to Look For:
- Agents frequently becoming blocked
- Uneven task distribution
- Low agent utilization
- Error patterns in agent logs

#### Mitigation Strategies:
- **For Blocked Agents**:
  - Check blocker reasons in logs
  - Provide missing dependencies
  - Clarify ambiguous requirements
  
- **For Low Utilization**:
  - Enable auto-assignment
  - Add more granular tasks
  - Balance agent skill sets

### 4. Pipeline Replay Tab

**Purpose**: Review and analyze completed workflow executions.

#### Features:
- Step through pipeline events chronologically
- View state at each point in time
- Identify bottlenecks and failures
- Export timeline data

#### What to Look For:
- Long gaps between events
- Repeated error patterns
- Task reassignments
- Resource constraints

#### Mitigation Strategies:
- Use replay to identify systematic issues
- Document failure patterns
- Adjust workflow parameters based on findings

### 5. What-If Analysis Tab

**Purpose**: Simulate changes to understand their impact before implementation.

#### Modification Types:
- **Requirements**: Change project scope
- **Constraints**: Adjust resource limits
- **Parameters**: Modify execution settings

#### Key Metrics to Monitor:
- Task count changes
- Complexity variations
- Cost implications
- Quality score impacts

#### Mitigation Strategies:
- Test removing low-priority features
- Simulate different agent configurations
- Evaluate trade-offs between speed and quality

### 6. Compare Flows Tab

**Purpose**: Analyze multiple pipeline executions to identify patterns.

#### Comparison Insights:
- Duration differences
- Cost variations
- Task count disparities
- Quality metrics
- Complexity ratings

#### What to Look For:
- Consistent performance degradation
- Cost outliers
- Quality variations between similar projects

#### Mitigation Strategies:
- Standardize successful patterns
- Avoid configurations that led to poor outcomes
- Document best practices from high-performing flows

### 7. Recommendations Tab

**Purpose**: AI-powered suggestions for optimization.

#### Recommendation Types:
- Performance improvements
- Cost optimizations
- Quality enhancements
- Risk mitigations

#### Confidence Levels:
- **90-100%**: Highly reliable, based on strong patterns
- **70-89%**: Good confidence, worth considering
- **Below 70%**: Experimental, test carefully

#### Mitigation Strategies:
- Implement high-confidence recommendations first
- Test recommendations in isolated projects
- Track recommendation outcomes

## Common Issues and Solutions

### Issue: Workflow Starts but No Progress

**Indicators**:
- Flow stays at 0% progress
- No agents pick up tasks
- No events in pipeline

**Solutions**:
1. Verify agents are registered and running
2. Check if PM Agent service is accessible
3. Review project requirements for clarity
4. Enable auto-assignment in workflow options

### Issue: High Failure Rate

**Indicators**:
- Success rate below 70%
- Multiple blocked agents
- Error events in pipeline

**Solutions**:
1. Review error messages in agent logs
2. Simplify complex requirements
3. Add more specific acceptance criteria
4. Check external dependencies

### Issue: Slow Performance

**Indicators**:
- Completion times increasing
- Low flows/hour metric
- Agents idle despite available work

**Solutions**:
1. Increase max agents setting
2. Enable parallel execution
3. Break down large features
4. Optimize task dependencies

## Best Practices

### Project Setup
1. Start with clear, concise project descriptions
2. Define 3-5 well-scoped features initially
3. Provide explicit acceptance criteria
4. Use appropriate project types

### Workflow Configuration
1. Begin with 2-3 agents maximum
2. Enable monitoring for visibility
3. Use auto-assignment for efficiency
4. Set realistic agent limits

### Monitoring
1. Check dashboard every 15-30 minutes
2. Address blocked agents promptly
3. Review completed flows for patterns
4. Export metrics for long-term analysis

### Optimization
1. Use What-If analysis before major changes
2. Compare similar projects for insights
3. Implement recommendations gradually
4. Document successful configurations

## Quick Start Checklist

1. ✅ Create a simple test project first
2. ✅ Add 2-3 clear features with acceptance criteria
3. ✅ Register at least 2 agents
4. ✅ Start workflow with default settings
5. ✅ Monitor Live Dashboard for 10 minutes
6. ✅ Use Pipeline Replay to review execution
7. ✅ Check Recommendations for improvements
8. ✅ Iterate based on insights

## Troubleshooting Commands

```bash
# Test the system
python test_project_workflow.py

# Check API health
curl http://localhost:5000/api/health

# View server logs
tail -f logs/marcus_api.log

# Reset project state
python scripts/reset_project_state.py
```

## Getting Help

- **Error Messages**: Check agent logs in the Agent Management tab
- **Performance Issues**: Use Compare Flows to identify patterns
- **Configuration**: Start with defaults, adjust based on Recommendations
- **Support**: Export flow data and logs when reporting issues