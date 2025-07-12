# How to Use Pattern Learning

## Overview

Marcus's Pattern Learning System automatically learns from your completed projects to provide better recommendations, identify risks early, and improve project success rates. This guide shows you how to leverage pattern learning in your workflow.

## Prerequisites

- Marcus v2.5.0 or later
- Pattern learning enabled in configuration
- At least one completed project for initial patterns

## Enabling Pattern Learning

### 1. Environment Configuration

Set the following environment variables:

```bash
# Enable pattern learning
export MARCUS_PATTERN_LEARNING_ENABLED=true

# Set project completion threshold (optional, default: 95%)
export MARCUS_PROJECT_COMPLETION_THRESHOLD=95

# Enable GitHub integration (optional but recommended)
export GITHUB_OWNER=your-organization
export GITHUB_REPO=your-repository
```

### 2. Marcus Configuration

In your Marcus settings:

```json
{
  "project_monitor": {
    "enable_pattern_learning": true,
    "completion_threshold": 0.95,
    "check_interval": 300
  }
}
```

## Automatic Pattern Learning

### How It Works

1. **Project Monitoring**: Marcus continuously monitors project progress
2. **Completion Detection**: When a project reaches 95% completion, pattern extraction begins
3. **Pattern Extraction**: System analyzes project data across multiple dimensions
4. **Learning Storage**: Patterns are stored for future recommendations
5. **Continuous Improvement**: Each completed project improves recommendations

### What Marcus Learns

- **Team Patterns**
  - Optimal team size and composition
  - Skill utilization effectiveness
  - Collaboration patterns

- **Velocity Patterns**
  - Task completion rates by project phase
  - Factors affecting velocity
  - Bottlenecks and accelerators

- **Quality Patterns**
  - Code quality indicators
  - Process effectiveness
  - Delivery reliability

- **Risk Patterns**
  - Common failure points
  - Early warning signs
  - Mitigation strategies

## Using Pattern-Based Recommendations

### 1. During Project Planning

When creating a new project, Marcus automatically:
- Finds similar past projects
- Suggests optimal team composition
- Recommends task structure
- Identifies potential risks

Example interaction:
```
You: Create a new e-commerce platform project

Marcus: Based on 5 similar successful projects, I recommend:
- Team size: 4 developers (2 backend, 1 frontend, 1 full-stack)
- Estimated duration: 45-50 days
- Key success factors:
  • Implement comprehensive testing (80%+ coverage)
  • Daily code reviews
  • Weekly stakeholder demos
- Risk factors to watch:
  • Payment integration complexity
  • Third-party API dependencies
```

### 2. During Project Execution

Marcus provides real-time recommendations:

```
You: Show current project recommendations

Marcus: Based on learned patterns:

📊 Velocity Improvement:
- Current: 5.2 tasks/week
- Target: 8.0 tasks/week (based on similar projects)
- Suggestions:
  • Reduce task dependencies
  • Implement pair programming for complex tasks
  • Consider adding a backend developer

⚠️ Risk Mitigation:
- Detected pattern: Projects with 3+ blocked tasks often delay
- Current blocked tasks: 2
- Action: Prioritize unblocking before taking new tasks

✅ Quality Assurance:
- Similar successful projects had 85%+ test coverage
- Current coverage: 72%
- Recommendation: Increase test coverage before proceeding
```

### 3. Quality Assessment

Get comprehensive quality analysis:

```
You: Assess project quality

Marcus: Quality Assessment for "E-Commerce Platform":

Overall Score: 82% (Good)

📊 Breakdown:
- Code Quality: 85% ✅
  • High test coverage (81%)
  • Consistent code reviews
  • Good documentation

- Process Quality: 78% ⚠️
  • PR review time above average (28h vs 24h target)
  • Consider streamlining review process

- Delivery Quality: 80% ✅
  • On track for deadline
  • 90% on-time task delivery

- Team Quality: 84% ✅
  • Well-balanced workload
  • High collaboration score

💡 Insights from Similar Projects:
- Projects with your current metrics have 87% success rate
- Key success predictor: Maintaining velocity through final phase
- Recommendation: Plan for 20% velocity drop in last week
```

## Viewing Pattern Insights

### 1. Similar Projects

Find projects similar to yours:

```
You: Show similar projects to current

Marcus: Found 3 similar projects:

1. "Online Marketplace" (89% similar)
   - Team size: 4 → Success ✅
   - Duration: 48 days
   - Quality score: 0.87
   - Key success: Strong testing culture

2. "B2B Platform" (82% similar)
   - Team size: 3 → Success ✅
   - Duration: 52 days
   - Quality score: 0.84
   - Key success: Incremental delivery

3. "SaaS Dashboard" (78% similar)
   - Team size: 5 → Challenged ⚠️
   - Duration: 65 days
   - Quality score: 0.72
   - Key issue: Scope creep
```

### 2. Quality Trends

Monitor quality trends across projects:

```
You: Show quality trends for last 3 months

Marcus: Quality Trends Analysis:

📈 Overall Trend: Improving (+8%)

Monthly Averages:
- Month 1: 75%
- Month 2: 78%
- Month 3: 82%

✅ Improvements:
- Test coverage: 68% → 81%
- Code review coverage: 85% → 95%
- On-time delivery: 72% → 88%

⚠️ Areas Needing Attention:
- Documentation coverage declining (65% → 58%)
- Average PR review time increasing (24h → 28h)

💡 Recommendation:
Focus on documentation and review efficiency in next sprint
```

## Best Practices

### 1. Provide Complete Information

For better pattern learning:
- Set accurate task estimates
- Track actual time spent
- Maintain task dependencies
- Use consistent labeling

### 2. Regular Quality Assessments

Run quality assessments at milestones:
- Sprint boundaries
- Major feature completions
- Before releases

### 3. Act on Recommendations

Pattern-based recommendations improve outcomes:
- Team composition suggestions: +15% velocity
- Risk mitigation alerts: -30% delays
- Quality recommendations: +20% success rate

### 4. Continuous Improvement

Each project improves patterns:
- More data = better recommendations
- Patterns adapt to your team
- Success factors become clearer

## Troubleshooting

### Pattern Learning Not Activating

Check:
1. Is `MARCUS_PATTERN_LEARNING_ENABLED=true`?
2. Has project reached 95% completion?
3. Are there at least 10 tasks in the project?
4. Check logs: `marcus logs --filter=pattern_learning`

### No Similar Projects Found

Possible causes:
- First project of its type
- Unique technology stack
- Unusual team composition

Solution: Complete more projects to build pattern database

### Low-Confidence Recommendations

Causes:
- Insufficient historical data
- Unique project characteristics
- Inconsistent past outcomes

Solution: Focus on general best practices until more patterns emerge

## Advanced Usage

### Custom Pattern Queries

For advanced users with API access:

```python
# Find all successful Python/React projects
patterns = marcus.find_patterns(
    technology_stack=["python", "react"],
    min_success_rate=0.8,
    min_projects=3
)

# Get team composition recommendations
team_rec = marcus.get_team_recommendations(
    project_size=50,  # tasks
    technologies=["python", "react", "postgresql"],
    deadline_days=45
)
```

### Export Pattern Data

Export learned patterns for analysis:

```bash
marcus patterns export --format=json > patterns.json
marcus patterns report --days=90 > pattern_report.md
```

## Security and Privacy

- Patterns are stored locally
- No code content is analyzed (only metadata)
- GitHub integration is optional
- Patterns can be cleared: `marcus patterns clear`

## Next Steps

1. Enable pattern learning in your Marcus instance
2. Complete your first project to establish baseline patterns
3. Review recommendations on your next project
4. Monitor quality trends over time
5. Share success stories with the Marcus community

For more details, see the [Pattern Learning System Documentation](../../developer-guide/pattern-learning-system.md).
