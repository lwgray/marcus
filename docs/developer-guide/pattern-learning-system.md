# Pattern Learning System

## Overview

The Pattern Learning System is Marcus's intelligent learning mechanism that automatically extracts patterns from completed projects to improve future project recommendations and risk assessment. It analyzes project outcomes, team performance, quality metrics, and implementation patterns to identify what makes projects successful or leads to failure.

## Architecture

The Pattern Learning System consists of three main components:

### 1. ProjectPatternLearner
The core engine that extracts comprehensive patterns from completed projects.

```python
from src.learning.project_pattern_learner import ProjectPatternLearner
from src.recommendations.recommendation_engine import ProjectOutcome

# Initialize the learner
learner = ProjectPatternLearner(
    pattern_db=pattern_database,
    ai_engine=ai_engine,
    code_analyzer=code_analyzer
)

# Learn from a completed project
pattern = await learner.learn_from_project(
    project_state=project_state,
    tasks=tasks,
    team_members=team_members,
    outcome=outcome,
    github_owner="org",
    github_repo="repo"
)
```

### 2. ProjectQualityAssessor
Comprehensive quality assessment system that evaluates projects across multiple dimensions.

```python
from src.quality.project_quality_assessor import ProjectQualityAssessor

# Initialize the assessor
assessor = ProjectQualityAssessor(
    ai_engine=ai_engine,
    github_mcp=github_interface,
    board_validator=validator
)

# Assess project quality
assessment = await assessor.assess_project_quality(
    project_state=project_state,
    tasks=tasks,
    team_members=team_members,
    github_config=github_config
)
```

### 3. Integration with ProjectMonitor
Automatic detection of project completion and pattern learning.

```python
# ProjectMonitor automatically triggers pattern learning
if project_completion_detected:
    await self._handle_project_completion(
        project_state, tasks, team_members
    )
```

## Key Features

### Automatic Pattern Extraction

The system extracts patterns across multiple dimensions:

1. **Quality Metrics**
   - Board quality score
   - Task description quality
   - Estimate accuracy
   - Completion rate
   - On-time delivery rate
   - Rework rate
   - Blocker rate

2. **Team Performance**
   - Average velocity
   - Task completion rate
   - Blocker resolution time
   - Collaboration score
   - Skill utilization
   - Per-agent performance

3. **Task Patterns**
   - Task size distribution
   - Dependency depth
   - Parallel work ratio
   - Task type distribution
   - Priority distribution
   - Phase structure

4. **Velocity Patterns**
   - Start phase velocity
   - Early phase velocity
   - Middle phase velocity
   - End phase velocity

5. **Implementation Patterns** (with GitHub integration)
   - Endpoints created
   - Models created
   - Test coverage
   - Code review metrics
   - Refactoring rate

### Multi-Source Quality Assessment

The quality assessment integrates data from multiple sources:

1. **Task Data**
   - Task completion metrics
   - Quality validation scores
   - Time estimates vs actuals

2. **GitHub Data** (optional)
   - Commit frequency
   - Pull request metrics
   - Code review coverage
   - Issue resolution time

3. **Team Data**
   - Workload distribution
   - Skill diversity
   - Performance scores

4. **AI Analysis**
   - Qualitative insights
   - Success/risk factors
   - Improvement recommendations

### Pattern-Based Recommendations

The system provides intelligent recommendations based on learned patterns:

```python
# Get recommendations for current project
recommendations = pattern_learner.get_recommendations_from_patterns(
    current_project={
        "total_tasks": 30,
        "team_size": 2,
        "velocity": 5.0
    }
)
```

## Data Models

### ProjectPattern

```python
@dataclass
class ProjectPattern:
    project_id: str
    project_name: str
    outcome: ProjectOutcome
    quality_metrics: Dict[str, float]
    team_composition: Dict[str, Any]
    velocity_pattern: Dict[str, float]
    task_patterns: Dict[str, Any]
    blocker_patterns: Dict[str, Any]
    technology_stack: List[str]
    implementation_patterns: Dict[str, Any]
    success_factors: List[str]
    risk_factors: List[str]
    extracted_at: datetime
    confidence_score: float
```

### ProjectQualityAssessment

```python
@dataclass
class ProjectQualityAssessment:
    project_id: str
    project_name: str
    assessment_date: datetime
    overall_score: float
    code_quality_score: float
    process_quality_score: float
    delivery_quality_score: float
    team_quality_score: float
    code_metrics: Optional[CodeQualityMetrics]
    process_metrics: Optional[ProcessQualityMetrics]
    quality_insights: List[str]
    improvement_areas: List[str]
    success_prediction: Dict[str, Any]
    ai_insights: Optional[Dict[str, Any]]
```

## Configuration

### Environment Variables

```bash
# Enable pattern learning
MARCUS_PATTERN_LEARNING_ENABLED=true

# Set completion threshold (default: 95%)
MARCUS_PROJECT_COMPLETION_THRESHOLD=95

# GitHub integration (optional)
GITHUB_OWNER=your-org
GITHUB_REPO=your-repo
```

### ProjectMonitor Configuration

```python
# In your Marcus configuration
PROJECT_MONITOR_CONFIG = {
    "check_interval": 300,  # 5 minutes
    "completion_threshold": 0.95,  # 95%
    "enable_pattern_learning": True,
    "enable_github_integration": True
}
```

## API Access

The pattern learning system is accessed through REST API endpoints, NOT through MCP tools. This ensures that agents cannot access or manipulate pattern data.

### Security Architecture
- Pattern learning tools are **NOT available through MCP**
- Agents and Claude Desktop cannot directly access patterns
- All access must go through the visualization UI via API endpoints

### API Endpoints

Access pattern learning features through these endpoints:

#### POST `/api/patterns/similar-projects`
Find projects similar to current context.

```bash
curl -X POST http://localhost:5000/api/patterns/similar-projects \
  -H "Content-Type: application/json" \
  -d '{
    "project_context": {
      "total_tasks": 50,
      "team_size": 3,
      "technology_stack": ["python", "react"]
    },
    "min_similarity": 0.7
  }'
```

#### GET `/api/patterns/assess-quality/{board_id}`
Get quality assessment for a project.

```bash
curl http://localhost:5000/api/patterns/assess-quality/project-123
```

#### POST `/api/patterns/recommendations`
Get recommendations based on learned patterns.

```bash
curl -X POST http://localhost:5000/api/patterns/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "project_context": {
      "total_tasks": 30,
      "team_size": 2,
      "velocity": 5.0
    }
  }'
```

#### GET `/api/patterns/quality-trends`
Analyze quality trends across projects.

```bash
curl "http://localhost:5000/api/patterns/quality-trends?days=30"
```

For detailed API documentation, see [Pattern Learning Architecture](./pattern-learning-architecture.md).

## Usage Examples

### Example 1: Manual Pattern Learning

```python
# After project completion
outcome = ProjectOutcome(
    successful=True,
    completion_time_days=45,
    quality_score=0.85,
    cost=50000.0,
    failure_reasons=[]
)

# Extract patterns
pattern = await pattern_learner.learn_from_project(
    project_state=final_state,
    tasks=all_tasks,
    team_members=team,
    outcome=outcome
)

print(f"Extracted pattern with confidence: {pattern.confidence_score}")
print(f"Success factors: {pattern.success_factors}")
print(f"Risk factors: {pattern.risk_factors}")
```

### Example 2: Finding Similar Projects

```python
# Find similar successful projects
similar_projects = pattern_learner.find_similar_projects(
    target_pattern=current_pattern,
    min_similarity=0.7
)

for project, similarity in similar_projects[:3]:
    print(f"{project.project_name}: {similarity:.0%} similar")
    print(f"  - Team size: {project.team_composition['team_size']}")
    print(f"  - Success: {project.outcome.successful}")
```

### Example 3: Quality Assessment with GitHub

```python
# Configure GitHub integration
github_config = {
    "github_owner": "acme-corp",
    "github_repo": "main-product",
    "project_start_date": "2024-01-01"
}

# Assess quality
assessment = await quality_assessor.assess_project_quality(
    project_state=state,
    tasks=tasks,
    team_members=team,
    github_config=github_config
)

print(f"Overall Quality Score: {assessment.overall_score:.0%}")
print(f"Code Quality: {assessment.code_quality_score:.0%}")
print(f"Process Quality: {assessment.process_quality_score:.0%}")
print("\nKey Insights:")
for insight in assessment.quality_insights:
    print(f"  - {insight}")
```

## Best Practices

### 1. Data Quality
- Ensure tasks have accurate estimates and due dates
- Maintain consistent labeling conventions
- Track actual hours for better accuracy

### 2. Team Information
- Keep team member skills up to date
- Track performance scores accurately
- Record task assignments properly

### 3. GitHub Integration
- Use meaningful commit messages
- Follow PR best practices
- Ensure code reviews are tracked

### 4. Pattern Confidence
- Patterns with confidence > 0.8 are highly reliable
- Consider project size when evaluating patterns
- More data points increase pattern accuracy

## Troubleshooting

### Common Issues

1. **Pattern Learning Not Triggering**
   - Check if project completion threshold is met (default 95%)
   - Verify MARCUS_PATTERN_LEARNING_ENABLED is true
   - Check ProjectMonitor logs for errors

2. **Low Pattern Confidence**
   - Ensure board quality score is high
   - Verify sufficient task count (>10 recommended)
   - Check team size (>2 recommended)

3. **GitHub Integration Issues**
   - Verify GitHub MCP server is running
   - Check authentication credentials
   - Ensure repository access permissions

### Debug Mode

Enable debug logging for pattern learning:

```python
import logging
logging.getLogger("src.learning").setLevel(logging.DEBUG)
logging.getLogger("src.quality").setLevel(logging.DEBUG)
```

## Performance Considerations

- Pattern extraction is CPU-intensive but runs asynchronously
- GitHub API calls are rate-limited; use caching when possible
- Pattern database grows over time; implement cleanup strategy
- AI analysis calls may incur costs; monitor usage

## Future Enhancements

1. **Machine Learning Integration**
   - Train predictive models on extracted patterns
   - Automated risk scoring
   - Success probability prediction

2. **Advanced Analytics**
   - Cross-project pattern analysis
   - Industry benchmark comparisons
   - Trend detection and alerts

3. **Enhanced Integrations**
   - Jira integration for additional metrics
   - CI/CD pipeline data integration
   - Time tracking system integration

## API Reference

For detailed API documentation, see:
- [ProjectPatternLearner API](./api/pattern_learner.md)
- [ProjectQualityAssessor API](./api/quality_assessor.md)
- [Pattern Learning MCP Tools](./api/pattern_mcp_tools.md)
