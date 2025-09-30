# Recommendation Engine System

## System Overview

The Recommendation Engine is Marcus's intelligent advisory system that learns from historical project executions to provide actionable recommendations for future projects. This system analyzes patterns from completed projects, identifies success factors, and suggests optimizations to improve project outcomes.

**Primary Location**: `src/recommendations/recommendation_engine.py`

## Architecture

### Core Components

#### 1. PipelineRecommendationEngine
The main orchestrator that coordinates recommendation generation:
- **Purpose**: Central hub for all recommendation activities
- **Dependencies**: PatternDatabase, SuccessAnalyzer, PipelineComparator, SharedPipelineEvents
- **Key Methods**: `get_recommendations()`, `learn_from_outcome()`, `get_pattern_based_recommendations()`

#### 2. PatternDatabase
Persistent storage and management of success/failure patterns:
- **Storage Location**: `data/pattern_db.json`
- **Data Types**: Success patterns, failure patterns, templates, optimization rules
- **Key Features**: Pattern extraction, project type inference, task categorization

#### 3. SuccessAnalyzer
Analyzes what makes projects successful:
- **Metrics Tracked**: Task count, complexity scores, confidence levels, task distribution
- **Output**: Optimal ranges, proven decisions, success factors

#### 4. Data Models
```python
@dataclass
class Recommendation:
    type: str              # Category of recommendation
    confidence: float      # Confidence score (0-1)
    message: str          # Human-readable message
    impact: str           # Expected impact description
    action: Optional[Callable]  # Executable action
    supporting_data: Optional[Dict]  # Evidence/context

@dataclass
class ProjectOutcome:
    successful: bool
    completion_time_days: float
    quality_score: float
    cost: float
    failure_reasons: List[str]
```

## Integration with Marcus Ecosystem

### Data Sources
1. **SharedPipelineEvents**: Provides historical flow data and metrics
2. **PipelineComparator**: Supplies similarity analysis and flow comparisons
3. **ProjectPatternLearner**: Advanced pattern learning from completed projects (when available)

### Data Flow
```
Historical Projects → Pattern Extraction → Pattern Database
                                        ↓
Current Project → Similarity Analysis → Recommendation Generation
                                        ↓
                    Actionable Recommendations → User/Agent
```

### Storage Architecture
- **Pattern Database**: `data/pattern_db.json` (persistent)
- **Learned Patterns**: `data/learned_patterns.json` (from ProjectPatternLearner)
- **In-Memory Cache**: Active flow data and computed similarities

## Workflow Integration

### Position in Marcus Workflow
```
create_project → register_agent → [RECOMMENDATION ENGINE] → request_next_task
                                          ↓
                              Template/Phase Suggestions
                                          ↓
report_progress → [CONTINUOUS ANALYSIS] → report_blocker → finish_task
                                          ↓
                              Optimization Recommendations
```

### Invocation Points

#### 1. Project Creation Phase
- **Trigger**: New project flow begins
- **Analysis**: Similar project detection, template suggestions
- **Recommendations**: Use existing templates, phase project for complexity

#### 2. Task Generation Phase
- **Trigger**: Task list created
- **Analysis**: Task distribution, testing coverage, documentation gaps
- **Recommendations**: Add missing task categories, optimize distribution

#### 3. Decision Making Phase
- **Trigger**: Critical decisions made
- **Analysis**: Decision confidence, proven approaches
- **Recommendations**: Review low-confidence decisions, apply proven patterns

#### 4. Progress Monitoring Phase
- **Trigger**: Milestone reports
- **Analysis**: Performance vs. historical patterns
- **Recommendations**: Speed/cost optimizations, risk mitigation

#### 5. Project Completion Phase
- **Trigger**: Project outcome recorded
- **Analysis**: Success/failure pattern learning
- **Action**: Update pattern database, adjust recommendation weights

## System Capabilities

### 1. Template Detection and Application
```python
def should_use_template(current_flow, similar_flows) -> bool:
    # Analyzes similarity scores (>85% threshold)
    # Considers project name, task count, requirements
    # Returns template recommendation with confidence
```

**Criteria**:
- 3+ similar projects with >85% similarity
- Proven success patterns
- Compatible project scope

### 2. Complexity Analysis and Phasing
```python
def detect_high_complexity(current_flow) -> bool:
    return (
        complexity_score > 0.8 or
        task_count > 40 or
        (task_count > 25 and complexity_score > 0.6)
    )
```

**Phase Suggestions**:
- **High Complexity (>30 tasks)**: 3-phase approach (Foundation → Implementation → Polish)
- **Medium Complexity (15-30 tasks)**: 2-phase approach (Core → Enhancement)

### 3. Task Distribution Analysis
**Optimal Ratios**:
- Testing: ≥15% of total tasks
- Documentation: ≥5% of total tasks
- Implementation: 40-60% of total tasks

**Missing Category Detection**:
- Automated suggestions for under-represented task types
- Priority-based task generation recommendations

### 4. Performance Optimization
**Cost Optimization**:
- Triggers when total_cost > $0.50
- Suggests model downgrading, batching, caching
- Estimates potential savings (up to 30%)

**Speed Optimization**:
- Triggers when execution > 30 seconds
- Suggests parallelization, caching, prompt optimization
- Targets 30-40% time reduction

### 5. Decision Quality Analysis
**Low Confidence Detection**:
- Identifies decisions with confidence < 0.7
- Cross-references with proven successful decisions
- Suggests review and reconsideration

## Technical Implementation Details

### Pattern Extraction Algorithm
```python
def _extract_pattern(self, flow_data):
    return {
        "project_type": self._infer_project_type(flow_data),
        "task_count": flow_data["metrics"]["task_count"],
        "complexity": flow_data["metrics"]["complexity_score"],
        "task_categories": self._categorize_tasks(flow_data["tasks"]),
        "decisions": extracted_decisions,
        "requirements_summary": summarized_requirements
    }
```

### Similarity Calculation
Uses multiple metrics weighted equally:
1. **Project Name Similarity**: String matching using `difflib.SequenceMatcher`
2. **Task Count Similarity**: Normalized difference calculation
3. **Requirements Similarity**: Text-based content matching

**Threshold**: 70% similarity for recommendation consideration

### Project Type Inference
Keyword-based classification system:
- **API Projects**: "api", "rest", "endpoint", "crud"
- **Web Applications**: "web", "frontend", "ui", "dashboard"
- **Mobile Apps**: "mobile", "ios", "android", "app"
- **Data Projects**: "data", "etl", "pipeline", "analytics"
- **ML Projects**: "ml", "machine", "learning", "model", "ai"
- **Infrastructure**: "infrastructure", "devops", "deployment", "ci/cd"

## Handling Simple vs Complex Tasks

### Simple Projects (≤15 tasks, complexity ≤0.4)
- **Recommendations**: Minimal, focused on quick wins
- **Template Usage**: High threshold for application
- **Monitoring**: Basic progress tracking
- **Optimizations**: Cost-focused suggestions

### Complex Projects (>30 tasks, complexity >0.6)
- **Recommendations**: Comprehensive, multi-dimensional
- **Phasing**: Mandatory phase suggestions
- **Template Usage**: More aggressive matching
- **Monitoring**: Intensive risk analysis
- **Optimizations**: Full performance analysis

### Decision Matrix
```python
if task_count <= 15 and complexity <= 0.4:
    return simple_recommendations(flow)
elif task_count > 30 or complexity > 0.6:
    return complex_recommendations(flow)
else:
    return standard_recommendations(flow)
```

## Board-Specific Considerations

### Kanban Integration
- **Data Source**: Task states, progress metrics from board
- **Feedback Loop**: Updates pattern database with actual outcomes
- **Board Metrics**: Task completion rates, blocker frequency, cycle times

### Board Quality Impact
```python
# Board quality affects recommendation confidence
if board_quality_score > 0.8:
    recommendation.confidence *= 1.2  # Boost confidence
elif board_quality_score < 0.5:
    recommendation.confidence *= 0.8  # Reduce confidence
```

### Board-Specific Patterns
- **Different board providers** may have varying optimal patterns
- **Team size correlation** with board complexity preferences
- **Board structure impact** on task distribution recommendations

## Seneca Integration

### Visualization Handoff
- **Marcus Role**: Pattern analysis and recommendation generation
- **Seneca Role**: Visualization, user interaction, recommendation presentation
- **Data Exchange**: JSON-formatted recommendation reports

### API Integration Points
```python
# Marcus provides recommendations via MCP tools
def get_recommendations_for_seneca(flow_id: str) -> Dict[str, Any]:
    recommendations = engine.get_recommendations(flow_id)
    return {
        "recommendations": [asdict(r) for r in recommendations],
        "metadata": {"generated_at": datetime.now(), "flow_id": flow_id}
    }
```

### Shared Data Models
- Recommendation format standardized for Seneca consumption
- Supporting data includes visualization hints
- Action callbacks translated to API endpoints

## Pros and Cons of Current Implementation

### Strengths
1. **Comprehensive Analysis**: Multiple recommendation dimensions
2. **Learning Capability**: Improves with more project data
3. **Actionable Output**: Specific, implementable suggestions
4. **Pattern Recognition**: Effective similarity detection
5. **Performance Awareness**: Cost and speed optimization focus
6. **Modular Design**: Easy to extend with new recommendation types

### Limitations
1. **Cold Start Problem**: Limited effectiveness with few historical projects
2. **Simple Similarity Metrics**: Could benefit from advanced ML techniques
3. **Static Thresholds**: Hard-coded values may not suit all contexts
4. **Limited Context**: Doesn't consider team expertise or external factors
5. **No Temporal Patterns**: Doesn't account for seasonal or trending patterns
6. **Binary Success Model**: Oversimplifies complex project outcomes

### Technical Debt
1. **Mock Data Dependencies**: Some components use placeholder patterns
2. **File-Based Storage**: Could benefit from proper database
3. **Synchronous Processing**: Could be optimized with async operations
4. **Limited Error Handling**: Needs more robust exception management

## Design Rationale

### Why This Approach Was Chosen

#### 1. Pattern-Based Learning
- **Decision**: Use historical pattern matching vs. pure ML
- **Rationale**: Provides explainable recommendations with immediate value
- **Trade-off**: Simplicity and interpretability over sophisticated prediction

#### 2. Multi-Dimensional Analysis
- **Decision**: Analyze multiple aspects (complexity, distribution, performance)
- **Rationale**: Holistic view prevents tunnel vision on single metrics
- **Trade-off**: Complexity in implementation for comprehensive coverage

#### 3. Confidence-Based Ranking
- **Decision**: Use confidence scores for recommendation prioritization
- **Rationale**: Allows users to focus on high-impact, reliable suggestions
- **Trade-off**: Requires careful calibration of confidence calculations

#### 4. Actionable Recommendations
- **Decision**: Include executable actions with recommendations
- **Rationale**: Enables automated application of suggestions
- **Trade-off**: Implementation complexity for user experience

## Future Evolution

### Phase 1: Enhanced Pattern Recognition
- **ML Integration**: Replace similarity algorithms with trained models
- **Temporal Analysis**: Incorporate time-based patterns and trends
- **Context Awareness**: Consider team skills, project constraints, deadlines
- **Advanced Clustering**: Use sophisticated clustering for project categorization

### Phase 2: Real-Time Adaptation
- **Dynamic Thresholds**: Adjust recommendation criteria based on success rates
- **A/B Testing**: Experiment with different recommendation strategies
- **Feedback Loop**: Learn from recommendation acceptance/rejection
- **Personalization**: Tailor recommendations to specific teams or users

### Phase 3: Predictive Capabilities
- **Risk Prediction**: Forecast potential project failures and blockers
- **Resource Planning**: Predict optimal team composition and timeline
- **Quality Forecasting**: Estimate final project quality based on early patterns
- **Success Probability**: Provide statistical likelihood of project success

### Phase 4: Advanced Intelligence
- **Natural Language Understanding**: Parse free-text requirements for patterns
- **Cross-Project Learning**: Learn from patterns across different organizations
- **Market Intelligence**: Incorporate industry trends and best practices
- **Automated Optimization**: Self-tuning recommendation algorithms

## Performance Characteristics

### Computational Complexity
- **Pattern Extraction**: O(n) where n = number of tasks
- **Similarity Calculation**: O(m) where m = number of historical projects
- **Recommendation Generation**: O(p) where p = number of pattern types
- **Overall**: Linear scaling with historical data size

### Memory Usage
- **Pattern Database**: ~1MB per 1000 projects
- **In-Memory Cache**: ~10KB per active flow
- **Recommendation Objects**: ~1KB per recommendation

### Response Times
- **Small Projects (≤20 tasks)**: <100ms for recommendations
- **Large Projects (>50 tasks)**: <500ms for recommendations
- **Historical Analysis**: <2s for similarity detection across 1000+ projects

## Error Handling and Resilience

### Graceful Degradation
```python
def get_recommendations(self, flow_id: str) -> List[Recommendation]:
    try:
        # Full analysis with all components
        return self._complete_analysis(flow_id)
    except PatternDatabaseError:
        # Fallback to basic recommendations
        return self._basic_recommendations(flow_id)
    except Exception:
        # Return empty list rather than crash
        return []
```

### Data Validation
- **Flow Data Integrity**: Validates required fields before analysis
- **Pattern Consistency**: Ensures stored patterns match expected schema
- **Recommendation Validity**: Verifies recommendation objects before return

### Recovery Mechanisms
- **Pattern Database Corruption**: Rebuild from backup or start fresh
- **Missing Components**: Provide degraded functionality
- **Network Issues**: Cache recommendations for offline operation

---

*This documentation provides a comprehensive technical overview of the Recommendation Engine system. For implementation details, see the source code at `src/recommendations/recommendation_engine.py` and related test files.*
