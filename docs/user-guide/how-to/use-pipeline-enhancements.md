# How to Use Pipeline Enhancement Features

This guide walks you through using Marcus's advanced pipeline enhancement features to analyze, optimize, and improve your project creation workflows.

## Overview

The Pipeline Enhancement features transform Marcus from a passive task generator into an active decision-support system with:

- **Pipeline Replay** - Step through past project creations
- **What-If Analysis** - Simulate changes before implementation
- **Flow Comparison** - Compare multiple projects
- **Live Monitoring** - Track active pipelines in real-time
- **Risk Prediction** - Identify potential failures early
- **Smart Recommendations** - Get AI-powered suggestions

## Accessing the Features

### Via MCP Tools

If you're using Marcus through an MCP client (like Claude Desktop), you can access these features directly:

```bash
# Start a replay session
pipeline_replay_start flow_id: "your-flow-id"

# Get recommendations
pipeline_recommendations flow_id: "your-flow-id"

# Compare multiple flows
pipeline_compare flow_ids: ["flow1", "flow2", "flow3"]
```

### Via Web Dashboard

1. Start the web server:
   ```bash
   python -m src.api.app
   ```

2. Open your browser to `http://localhost:5000`

3. Navigate through the tabs to access different features

### Via API

All features are available through REST API endpoints:

```bash
# Get live dashboard
curl http://localhost:5000/api/pipeline/monitor/dashboard

# Generate report
curl http://localhost:5000/api/pipeline/report/your-flow-id?format=html
```

## Feature Guide

### 1. Pipeline Replay

Replay allows you to step through a past project creation to understand decisions and identify improvements.

#### Starting a Replay

**MCP Tool:**
```bash
pipeline_replay_start flow_id: "project-123"
```

**Web Dashboard:**
1. Go to the "Pipeline Replay" tab
2. Enter the flow ID
3. Click "Start Replay"

#### Replay Controls

- **Step Forward/Backward** - Move through events one at a time
- **Jump to Position** - Skip to specific points
- **Play/Pause** - Auto-advance through events
- **Timeline Slider** - Visualize progress

#### What to Look For

- Decision points with low confidence
- Stages that took longer than expected
- Points where errors or retries occurred
- Requirements that led to many tasks

### 2. What-If Analysis

Test how changes would affect your project before implementing them.

#### Starting Analysis

**MCP Tool:**
```bash
what_if_start flow_id: "project-123"
```

**Web Dashboard:**
1. Go to "What-If Analysis" tab
2. Enter flow ID
3. View original metrics

#### Creating Modifications

You can modify:
- **Requirements** - Add/remove/change project requirements
- **Constraints** - Adjust deadlines, budget, team size
- **Parameters** - Change technology choices, complexity settings

Example modifications:
```json
{
  "modifications": [
    {
      "parameter_type": "requirement",
      "parameter_name": "authentication",
      "old_value": "Basic auth",
      "new_value": "OAuth2 + MFA"
    },
    {
      "parameter_type": "parameter",
      "parameter_name": "team_size",
      "old_value": 3,
      "new_value": 5
    }
  ]
}
```

#### Running Simulations

After adding modifications:
1. Click "Run Simulation"
2. Review predicted changes in:
   - Task count
   - Complexity
   - Cost
   - Timeline
   - Quality score

#### Interpreting Results

The radar chart shows:
- **Blue line** - Original metrics
- **Red line** - Predicted metrics with changes

Look for:
- Unexpected cost increases
- Complexity spikes
- Quality degradation
- Timeline extensions

### 3. Pipeline Comparison

Compare multiple project flows to identify patterns and best practices.

#### Selecting Flows to Compare

**MCP Tool:**
```bash
pipeline_compare flow_ids: ["api-project", "web-app", "mobile-app"]
```

**Web Dashboard:**
1. Go to "Compare Flows" tab
2. Add flow IDs (minimum 2)
3. Click "Compare Flows"

#### Understanding the Comparison

The comparison report includes:

**Flow Summaries Table:**
- Duration, cost, task count for each flow
- Quality and complexity scores
- Quick performance overview

**Common Patterns:**
- Decisions made across multiple flows
- Shared requirement types
- Common task categories

**Performance Analysis:**
- Best/worst performers by metric
- Cost and time efficiency
- Token usage optimization

**Recommendations:**
- Insights based on comparison
- Optimization opportunities
- Best practices to adopt

### 4. Live Monitoring Dashboard

Monitor active pipeline executions in real-time.

#### Accessing the Dashboard

**MCP Tool:**
```bash
pipeline_monitor_dashboard
```

**Web Dashboard:**
- Default tab when opening the interface
- Auto-updates every second

#### Dashboard Metrics

**System Overview:**
- Active flows count
- Flows per hour throughput
- Average completion time
- Overall success rate

**Flow Cards:**
Each active flow shows:
- Current progress percentage
- Health status (healthy/warning/critical)
- Current stage
- Estimated completion time
- Issues or blockers

#### Health Status Indicators

- **Green (Healthy)** - Normal operation
- **Yellow (Warning)** - Slow stages or minor issues
- **Red (Critical)** - Errors or stalled execution

### 5. Risk Prediction

Identify potential failures before they occur.

#### Getting Risk Assessment

**MCP Tool:**
```bash
pipeline_predict_risk flow_id: "active-flow-123"
```

**API:**
```bash
curl http://localhost:5000/api/pipeline/monitor/risk/active-flow-123
```

#### Risk Factors

The system analyzes:
- **High task count** - Projects with >50 tasks
- **Low AI confidence** - Average confidence <60%
- **High complexity** - Complexity score >0.8
- **Many ambiguities** - Unclear requirements
- **Missing considerations** - No testing/documentation

#### Risk Categories

- **Low (0-40%)** - Normal project, proceed
- **Medium (40-60%)** - Monitor closely
- **High (60-80%)** - Consider interventions
- **Critical (80-100%)** - Immediate action needed

#### Mitigation Strategies

Each risk factor includes specific mitigation:
- "Break project into phases"
- "Clarify requirements"
- "Add testing tasks"
- "Simplify dependencies"

### 6. Smart Recommendations

Get AI-powered suggestions based on historical data.

#### Getting Recommendations

**MCP Tool:**
```bash
pipeline_recommendations flow_id: "project-123"
```

**Web Dashboard:**
1. Go to "Recommendations" tab
2. Enter flow ID
3. View prioritized suggestions

#### Types of Recommendations

**Template Usage:**
- When similar projects exist
- Saves 30-40% of time
- Reuses proven patterns

**Project Phasing:**
- For high-complexity projects
- Reduces risk by 40%
- Improves manageability

**Testing Coverage:**
- When testing <15% of tasks
- Improves quality by 30-50%
- Reduces post-launch bugs

**Cost Optimization:**
- When costs exceed thresholds
- Suggests cheaper alternatives
- Identifies inefficiencies

#### Similar Flows

The system also shows:
- Projects similar to yours
- Similarity percentage
- Quick access to compare

## Best Practices

### 1. Regular Monitoring

- Check dashboard during active projects
- Set up alerts for critical flows
- Review health status frequently

### 2. Post-Project Analysis

After each project:
1. Run pipeline replay
2. Generate comprehensive report
3. Compare with similar projects
4. Document lessons learned

### 3. Continuous Improvement

- Use recommendations to refine processes
- Test changes with what-if analysis
- Apply successful patterns to new projects
- Build template library from best flows

### 4. Risk Management

- Check risk predictions early
- Apply mitigations proactively
- Monitor high-risk flows closely
- Document risk patterns

## Troubleshooting

### Common Issues

**No replay data available**
- Ensure pipeline visualization was enabled
- Check if flow completed successfully
- Verify flow ID is correct

**What-if simulation fails**
- Validate modification format
- Ensure parameters exist in original flow
- Check for conflicting modifications

**Recommendations not appearing**
- Verify historical data exists
- Check pattern database initialization
- Ensure flow has completed

**Dashboard not updating**
- Check WebSocket connection
- Verify monitoring service is running
- Check browser console for errors

### Getting Help

For issues or questions:
1. Check the [troubleshooting guide](/docs/troubleshooting)
2. Review API documentation
3. Submit issue on GitHub
4. Contact support team

## Advanced Usage

### Custom Integrations

You can integrate pipeline enhancements into your workflow:

```python
from src.mcp.tools.pipeline_enhancement_tools import pipeline_tools

# Get recommendations programmatically
recommendations = await pipeline_tools.get_recommendations("flow-123")

# Run what-if analysis in scripts
result = await pipeline_tools.simulate_modification([
    {"parameter_type": "requirement", "parameter_name": "scale", 
     "new_value": "1000 users/second"}
])
```

### Batch Analysis

For multiple projects:

```python
# Compare all API projects
api_flows = get_flows_by_type("api")
comparison = await pipeline_tools.compare_pipelines(api_flows)

# Generate reports for all completed flows
for flow_id in completed_flows:
    report = await pipeline_tools.generate_report(flow_id, "html")
    save_report(report)
```

### Automation

Set up automated monitoring:

```python
# Alert on high-risk flows
async def monitor_risks():
    dashboard = await pipeline_tools.get_live_dashboard()
    for flow in dashboard['active_flows']:
        risk = await pipeline_tools.predict_failure_risk(flow['flow_id'])
        if risk['risk_category'] in ['high', 'critical']:
            send_alert(flow, risk)
```

## Next Steps

1. Start with replay on your last project
2. Try what-if analysis for upcoming changes
3. Compare your best and worst projects
4. Set up monitoring for active flows
5. Apply recommendations to new projects

The pipeline enhancement features help you continuously improve your project creation process, reduce risks, and deliver better results faster.