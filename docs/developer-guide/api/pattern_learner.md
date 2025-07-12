# ProjectPatternLearner API Reference

## Class: ProjectPatternLearner

Extracts and learns patterns from completed projects to improve future project recommendations.

### Constructor

```python
ProjectPatternLearner(
    pattern_db: Optional[PatternDatabase] = None,
    ai_engine: Optional[AIAnalysisEngine] = None,
    code_analyzer: Optional[CodeAnalyzer] = None
) -> None
```

**Parameters:**
- `pattern_db`: Database for storing patterns. Creates new if not provided.
- `ai_engine`: AI engine for analysis. Creates new if not provided.
- `code_analyzer`: Code analyzer for GitHub integration.

### Methods

#### learn_from_project

Extract patterns from a completed project.

```python
async def learn_from_project(
    self,
    project_state: ProjectState,
    tasks: List[Task],
    team_members: List[WorkerStatus],
    outcome: ProjectOutcome,
    github_owner: Optional[str] = None,
    github_repo: Optional[str] = None,
) -> ProjectPattern
```

**Parameters:**
- `project_state`: Final state of the completed project
- `tasks`: All tasks from the project
- `team_members`: Team members who worked on the project
- `outcome`: Actual project outcome metrics
- `github_owner`: GitHub repository owner for code analysis
- `github_repo`: GitHub repository name for code analysis

**Returns:**
- `ProjectPattern`: Extracted pattern from the project

**Example:**
```python
pattern = await learner.learn_from_project(
    project_state=final_state,
    tasks=all_tasks,
    team_members=team,
    outcome=ProjectOutcome(
        successful=True,
        completion_time_days=30,
        quality_score=0.85,
        cost=25000
    )
)
```

#### find_similar_projects

Find projects similar to a given pattern.

```python
def find_similar_projects(
    self,
    target_pattern: ProjectPattern,
    min_similarity: float = 0.7
) -> List[Tuple[ProjectPattern, float]]
```

**Parameters:**
- `target_pattern`: Pattern to match against
- `min_similarity`: Minimum similarity score (0-1)

**Returns:**
- List of (pattern, similarity_score) tuples sorted by similarity

**Example:**
```python
similar = learner.find_similar_projects(
    target_pattern=current_pattern,
    min_similarity=0.8
)
for pattern, score in similar[:5]:
    print(f"{pattern.project_name}: {score:.0%} similar")
```

#### get_recommendations_from_patterns

Get recommendations based on learned patterns.

```python
def get_recommendations_from_patterns(
    self,
    current_project: Dict[str, Any],
    max_recommendations: int = 5
) -> List[Dict[str, Any]]
```

**Parameters:**
- `current_project`: Current project information
- `max_recommendations`: Maximum number of recommendations to return

**Returns:**
- List of recommendations with confidence scores

**Example:**
```python
recommendations = learner.get_recommendations_from_patterns(
    current_project={
        "total_tasks": 40,
        "team_size": 3,
        "velocity": 8.0
    }
)
```

### Private Methods

#### _extract_quality_metrics

Extract detailed quality metrics from the project.

```python
def _extract_quality_metrics(
    self,
    quality_report: QualityReport,
    tasks: List[Task]
) -> Dict[str, float]
```

**Returns dictionary with:**
- `board_quality_score`: Overall board quality (0-1)
- `description_quality`: Task description coverage
- `label_quality`: Label coverage
- `estimate_accuracy`: How accurate time estimates were
- `completion_rate`: Percentage of tasks completed
- `on_time_delivery`: Percentage delivered on time
- `rework_rate`: Rate of tasks needing rework
- `blocker_rate`: Percentage of blocked tasks

#### _analyze_team_performance

Analyze team performance metrics.

```python
def _analyze_team_performance(
    self,
    tasks: List[Task],
    team_members: List[WorkerStatus]
) -> TeamPerformanceMetrics
```

**Returns TeamPerformanceMetrics with:**
- `average_velocity`: Tasks completed per week
- `task_completion_rate`: Overall completion percentage
- `blocker_resolution_time`: Average time to resolve blockers
- `collaboration_score`: Team collaboration effectiveness
- `skill_utilization`: How well skills were utilized
- `agent_performance`: Per-agent performance metrics

#### _analyze_velocity_pattern

Analyze velocity patterns throughout the project.

```python
def _analyze_velocity_pattern(
    self,
    tasks: List[Task]
) -> Dict[str, float]
```

**Returns velocity by phase:**
- `start`: Initial phase velocity
- `early`: Early phase velocity
- `middle`: Mid-project velocity
- `end`: Final phase velocity

#### _calculate_pattern_similarity

Calculate similarity between two project patterns.

```python
def _calculate_pattern_similarity(
    self,
    pattern1: ProjectPattern,
    pattern2: ProjectPattern
) -> float
```

**Returns:**
- Similarity score between 0 and 1

**Similarity factors:**
- Team composition (20% weight)
- Task patterns (30% weight)
- Technology stack (20% weight)
- Quality metrics (30% weight)

## Data Classes

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

### TeamPerformanceMetrics

```python
@dataclass
class TeamPerformanceMetrics:
    average_velocity: float
    task_completion_rate: float
    blocker_resolution_time: float
    collaboration_score: float
    skill_utilization: Dict[str, float]
    agent_performance: Dict[str, float]
```

## Error Handling

The ProjectPatternLearner handles various error conditions:

```python
try:
    pattern = await learner.learn_from_project(...)
except ValueError as e:
    # Invalid input data
    logger.error(f"Invalid data: {e}")
except ConnectionError as e:
    # GitHub API connection issues
    logger.error(f"GitHub connection failed: {e}")
except Exception as e:
    # Unexpected errors
    logger.error(f"Pattern learning failed: {e}")
```

## Performance Characteristics

- **Memory Usage**: O(n) where n is number of tasks
- **Time Complexity**: O(n log n) for pattern extraction
- **Storage**: ~5KB per pattern in JSON format
- **API Calls**: Up to 10 GitHub API calls if integration enabled

## Best Practices

1. **Sufficient Data**: Projects should have at least 10 tasks for meaningful patterns
2. **Complete Information**: Ensure all task fields are populated
3. **Accurate Outcomes**: Provide accurate project outcome metrics
4. **Regular Learning**: Run pattern learning for all completed projects
5. **Pattern Pruning**: Remove old patterns periodically (>1 year)

## Thread Safety

The ProjectPatternLearner is thread-safe for read operations but not for writes. Use appropriate locking when calling `learn_from_project` from multiple threads.

## Version Compatibility

- Introduced in: Marcus v2.5.0
- Requires: Python 3.8+
- Dependencies: AIAnalysisEngine v1.0+, CodeAnalyzer v1.0+
