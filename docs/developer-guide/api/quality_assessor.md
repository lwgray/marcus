# ProjectQualityAssessor API Reference

## Class: ProjectQualityAssessor

Comprehensive quality assessment system that evaluates projects across multiple dimensions including code quality, process quality, delivery metrics, and team performance.

### Constructor

```python
ProjectQualityAssessor(
    ai_engine: Optional[AIAnalysisEngine] = None,
    github_mcp: Optional[GitHubMCPInterface] = None,
    board_validator: Optional[BoardQualityValidator] = None
) -> None
```

**Parameters:**
- `ai_engine`: AI engine for qualitative analysis
- `github_mcp`: GitHub MCP interface for code metrics
- `board_validator`: Board quality validation tool

### Methods

#### assess_project_quality

Perform comprehensive quality assessment of a project.

```python
async def assess_project_quality(
    self,
    project_state: ProjectState,
    tasks: List[Task],
    team_members: List[WorkerStatus],
    github_config: Optional[Dict[str, str]] = None,
) -> ProjectQualityAssessment
```

**Parameters:**
- `project_state`: Current state of the project
- `tasks`: All project tasks
- `team_members`: Team members working on the project
- `github_config`: GitHub configuration for code analysis
  - `github_owner`: Repository owner
  - `github_repo`: Repository name
  - `project_start_date`: Project start date (ISO format)

**Returns:**
- `ProjectQualityAssessment`: Comprehensive quality assessment

**Example:**
```python
assessment = await assessor.assess_project_quality(
    project_state=state,
    tasks=tasks,
    team_members=team,
    github_config={
        "github_owner": "acme-corp",
        "github_repo": "main-app",
        "project_start_date": "2024-01-01"
    }
)
```

### Private Methods

#### _analyze_task_quality

Analyze quality metrics from tasks.

```python
def _analyze_task_quality(
    self,
    tasks: List[Task]
) -> Dict[str, Any]
```

**Returns dictionary with:**
- `total_tasks`: Total number of tasks
- `completed_tasks`: Number of completed tasks
- `completion_rate`: Percentage completed
- `board_quality_score`: Board validation score
- `blocked_task_rate`: Percentage of blocked tasks
- `task_description_quality`: Average description quality

#### _analyze_team_quality

Analyze team performance and dynamics.

```python
def _analyze_team_quality(
    self,
    tasks: List[Task],
    team_members: List[WorkerStatus]
) -> Dict[str, Any]
```

**Returns dictionary with:**
- `team_size`: Number of team members
- `avg_tasks_per_member`: Average task load
- `skill_diversity`: Number of unique skills
- `workload_balance`: Distribution evenness (0-1)
- `member_performance`: Individual performance metrics

#### _analyze_delivery_quality

Analyze project delivery metrics.

```python
def _analyze_delivery_quality(
    self,
    project_state: ProjectState,
    tasks: List[Task]
) -> Dict[str, Any]
```

**Returns dictionary with:**
- `progress_percent`: Overall completion percentage
- `velocity_trend`: Velocity direction (increasing/stable/decreasing)
- `on_time_delivery_rate`: Tasks delivered on schedule
- `late_task_rate`: Tasks delivered late
- `risk_score`: Overall project risk (0-1)
- `projected_completion_days`: Days to completion

#### _analyze_code_quality

Analyze code quality from GitHub data.

```python
async def _analyze_code_quality(
    self,
    github_data: Dict[str, Any]
) -> CodeQualityMetrics
```

**Returns CodeQualityMetrics with:**
- `commit_frequency`: Commits per day
- `test_coverage`: Test coverage percentage
- `code_review_coverage`: PRs with reviews
- `documentation_coverage`: Code with docs
- `technical_debt_score`: Technical debt level
- `maintainability_index`: Code maintainability

#### _analyze_process_quality

Analyze development process quality.

```python
async def _analyze_process_quality(
    self,
    github_data: Dict[str, Any]
) -> ProcessQualityMetrics
```

**Returns ProcessQualityMetrics with:**
- `pr_approval_rate`: Approved PR percentage
- `avg_review_time_hours`: Hours to review
- `issue_resolution_time`: Days to close issues
- `deployment_frequency`: Deploys per week
- `rollback_rate`: Failed deployment rate

#### _determine_project_success

Determine project success likelihood.

```python
def _determine_project_success(
    self,
    overall_score: float,
    delivery_metrics: Dict[str, Any],
    ai_assessment: Dict[str, Any]
) -> Dict[str, Any]
```

**Returns dictionary with:**
- `is_successful`: Boolean success prediction
- `confidence`: Confidence level (0-1)
- `factors`: Contributing factors
- `reasoning`: Explanation of determination

## Data Classes

### ProjectQualityAssessment

```python
@dataclass
class ProjectQualityAssessment:
    project_id: str
    project_name: str
    assessment_date: datetime
    overall_score: float  # 0-1
    code_quality_score: float  # 0-1
    process_quality_score: float  # 0-1
    delivery_quality_score: float  # 0-1
    team_quality_score: float  # 0-1
    code_metrics: Optional[CodeQualityMetrics]
    process_metrics: Optional[ProcessQualityMetrics]
    quality_insights: List[str]
    improvement_areas: List[str]
    success_prediction: Dict[str, Any]
    ai_insights: Optional[Dict[str, Any]]
```

### CodeQualityMetrics

```python
@dataclass
class CodeQualityMetrics:
    commit_frequency: float = 0.0
    test_coverage: float = 0.0
    code_review_coverage: float = 0.0
    documentation_coverage: float = 0.0
    technical_debt_score: float = 0.0
    maintainability_index: float = 0.0
```

### ProcessQualityMetrics

```python
@dataclass
class ProcessQualityMetrics:
    pr_approval_rate: float = 0.0
    avg_review_time_hours: float = 0.0
    issue_resolution_time: float = 0.0
    deployment_frequency: float = 0.0
    rollback_rate: float = 0.0
```

## Quality Score Calculation

The overall quality score is a weighted average of four dimensions:

```python
overall_score = (
    code_quality_score * 0.25 +
    process_quality_score * 0.25 +
    delivery_quality_score * 0.30 +
    team_quality_score * 0.20
)
```

### Score Interpretation

- **0.9-1.0**: Excellent - Project exemplifies best practices
- **0.8-0.9**: Good - High quality with minor improvements needed
- **0.7-0.8**: Satisfactory - Acceptable quality, some areas need attention
- **0.6-0.7**: Fair - Multiple quality issues requiring attention
- **< 0.6**: Poor - Significant quality problems

## GitHub Integration

When GitHub configuration is provided, additional metrics are collected:

```python
github_data = await assessor._collect_github_data({
    "github_owner": "org",
    "github_repo": "repo",
    "project_start_date": "2024-01-01"
})
```

### API Calls Made

1. `list_commits` - Get commit history
2. `search_issues` - Find pull requests
3. `search_issues` - Find issues
4. `list_pr_reviews` - Get review data

### Rate Limiting

GitHub API calls are subject to rate limits. The assessor implements:
- Automatic retry with exponential backoff
- Caching of results for 15 minutes
- Graceful degradation if API unavailable

## AI Analysis Integration

When AI engine is available, additional insights are generated:

```python
ai_insights = await assessor._get_ai_insights(
    project_summary=summary,
    metrics=all_metrics,
    github_data=github_data
)
```

### AI-Generated Insights Include

- Success factors identification
- Risk factor analysis
- Improvement recommendations
- Overall qualitative assessment
- Team dynamics observations

## Error Handling

```python
try:
    assessment = await assessor.assess_project_quality(...)
except GitHubConnectionError as e:
    # GitHub API issues - assessment continues without code metrics
    logger.warning(f"GitHub unavailable: {e}")
except AIAnalysisError as e:
    # AI engine issues - assessment continues without AI insights
    logger.warning(f"AI analysis failed: {e}")
except ValueError as e:
    # Invalid input data
    logger.error(f"Invalid input: {e}")
```

## Performance Characteristics

- **Time Complexity**: O(n) where n is number of tasks
- **API Latency**: ~2-5 seconds with GitHub integration
- **Memory Usage**: ~1MB per 1000 tasks
- **Caching**: 15-minute cache for GitHub data

## Best Practices

1. **Complete Data**: Ensure all task fields are populated
2. **GitHub Integration**: Configure for comprehensive code metrics
3. **Regular Assessment**: Run assessments at project milestones
4. **Track Trends**: Monitor quality scores over time
5. **Act on Insights**: Address identified improvement areas

## Configuration Options

```python
# Customize assessment thresholds
assessor.config = {
    "min_test_coverage": 0.8,
    "max_review_time_hours": 24,
    "min_documentation_coverage": 0.6,
    "completion_threshold": 0.95
}
```

## Thread Safety

The ProjectQualityAssessor is thread-safe and can handle concurrent assessments.

## Version Compatibility

- Introduced in: Marcus v2.5.0
- Requires: Python 3.8+, AIAnalysisEngine v1.0+
- Optional: GitHub MCP Server v1.0+
