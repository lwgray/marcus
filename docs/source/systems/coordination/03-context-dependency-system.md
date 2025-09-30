# Context & Dependency System

## Overview

The Context & Dependency System is one of Marcus's core intelligence subsystems, responsible for providing rich contextual information to agents and inferring dependencies between tasks to prevent illogical assignments. This system transforms Marcus from a simple task dispatcher into an intelligent project coordination platform that understands relationships, learns from patterns, and adapts to different project structures.

## What This System Does

The Context & Dependency System serves multiple critical functions:

1. **Task Context Generation**: Provides agents with rich context including previous implementations, dependent tasks, related patterns, and architectural decisions
2. **Dependency Inference**: Automatically identifies logical dependencies between tasks using multiple strategies (pattern-based, AI-enhanced, and adaptive learning)
3. **Architectural Decision Tracking**: Maintains a history of decisions made by agents to inform future work
4. **Task Ordering Optimization**: Suggests optimal task execution order based on dependencies and priorities
5. **Pattern Learning**: Learns from project completions and user feedback to improve future recommendations

## Architecture

The system consists of several interconnected components:

```
┌─────────────────────────────────────────────────────────────┐
│                Context & Dependency System                  │
├─────────────────┬──────────────────┬─────────────────────────┤
│   Core Context  │  Dependency      │  Detection &            │
│   Management    │  Inference       │  Analysis               │
│                 │                  │                         │
│ • Context       │ • DependencyIn-  │ • ContextDetector       │
│ • TaskContext   │   ferer (Base)   │ • BoardAnalyzer         │
│ • Decision      │ • HybridDepen-   │ • AdaptiveDependen-     │
│ • DependentTask │   dencyInferer   │   cyInferer             │
│                 │ • DependencyGraph│                         │
└─────────────────┴──────────────────┴─────────────────────────┘
```

### Component Breakdown

#### 1. Core Context Management (`src/core/context.py`)
- **Context**: Main orchestrator class that manages all context operations
- **TaskContext**: Complete context package for task assignments
- **Decision**: Architectural decision tracking
- **DependentTask**: Information about task dependencies

#### 2. Dependency Inference Engine (`src/intelligence/dependency_inferer.py`)
- **DependencyInferer**: Base pattern-based dependency inference
- **DependencyPattern**: Rule definitions for common dependency patterns
- **InferredDependency**: Dependency relationship with confidence scoring
- **DependencyGraph**: Graph representation with cycle detection

#### 3. Hybrid Inference Engine (`src/intelligence/dependency_inferer_hybrid.py`)
- **HybridDependencyInferer**: Combines patterns with AI analysis
- **HybridDependency**: Enhanced dependency with multiple inference methods
- Intelligent caching and batch processing for AI calls

#### 4. Adaptive Learning System (`src/core/adaptive_dependencies.py`)
- **AdaptiveDependencyInferer**: Learns from user feedback and board state
- **RelationshipPattern**: User-defined and learned patterns
- **DependencySignal**: Multiple weak signals combined for inference
- **WorkflowPattern**: Domain-specific workflow templates

#### 5. Context Detection (`src/detection/context_detector.py`)
- **ContextDetector**: Determines optimal Marcus mode based on board state
- **MarcusMode**: Creator, Enricher, or Adaptive modes
- **UserIntent**: Intent detection from user messages

## Integration with Marcus Ecosystem

### Event System Integration
The Context system publishes events for:
- `IMPLEMENTATION_FOUND`: When new implementation context is added
- `DECISION_LOGGED`: When architectural decisions are recorded
- `CONTEXT_UPDATED`: When task context is generated

### Persistence Integration
- Stores decisions and implementations for long-term learning
- Graceful degradation when persistence is unavailable
- Supports various persistence backends

### AI Engine Integration
- Uses Claude/AI engines for complex dependency inference
- Implements intelligent caching to minimize API calls
- Fallback to pattern-based inference when AI is unavailable

### MCP Tools Integration
- Exposes context functionality through MCP tools
- Provides `get_task_context` for detailed task information
- Supports dependency analysis through `analyze_dependencies`

## Workflow Integration

In the typical Marcus workflow, the Context & Dependency System is invoked at these points:

```
create_project → register_agent → [CONTEXT ANALYSIS] → request_next_task →
[DEPENDENCY CHECK] → report_progress → [DECISION TRACKING] → report_blocker →
[CONTEXT UPDATE] → finish_task → [PATTERN LEARNING]
```

### 1. Project Creation Phase
- Analyzes board state to determine optimal Marcus mode
- Provides recommendations for project structure

### 2. Agent Registration
- Establishes context tracking for the agent
- Initializes dependency inference capabilities

### 3. Task Request Phase
- **Primary Integration Point**: Generates rich context for task assignments
- Analyzes dependencies to ensure logical task ordering
- Provides implementation patterns from previous work

### 4. Progress Reporting
- Tracks implementation details for future context
- Records architectural decisions
- Updates dependency relationships

### 5. Blocker Resolution
- Uses context to suggest solutions based on previous implementations
- Analyzes dependency chains to identify root causes

### 6. Task Completion
- Extracts patterns for future use
- Updates confidence scores based on successful completions
- Feeds learning back into the system

## What Makes This System Special

### 1. Multi-Strategy Inference
Unlike simple rule-based systems, Marcus employs three complementary strategies:

- **Pattern-Based**: Fast, deterministic rules for common cases
- **AI-Enhanced**: Sophisticated analysis for complex scenarios
- **Adaptive Learning**: Learns from user feedback and project outcomes

### 2. Graceful Degradation
The system maintains functionality even when components are unavailable:
- Falls back to patterns when AI is unavailable
- Continues working without persistence
- Provides basic context even without previous implementations

### 3. Context-Aware Task Assignment
Each task assignment includes:
- **Previous Implementations**: What other agents have built
- **Dependent Tasks**: What depends on this work
- **Related Patterns**: Similar work done before
- **Architectural Decisions**: Relevant decisions that affect this task

### 4. Intelligent Caching
- Caches AI inference results to minimize costs
- Uses content-based cache keys for consistency
- Implements TTL for cache freshness

## Technical Implementation Details

### Dependency Inference Strategies

#### Pattern-Based Rules (Fast Path)
```python
# Example patterns from dependency_inferer.py
DependencyPattern(
    name="testing_before_deployment",
    description="Testing must complete before deployment",
    condition_pattern=r"(deploy|release|launch|production)",
    dependency_pattern=r"(test|qa|quality|verify)",
    confidence=0.95,
    mandatory=True
)
```

#### AI-Enhanced Analysis (Complex Cases)
```python
# Batch analysis for ambiguous cases
prompt = f"""Analyze these task pairs and determine dependencies.
A dependency exists if one task must be completed before another.

Task pairs to analyze: {json.dumps(pairs_to_analyze, indent=2)}

Return JSON with dependency direction and reasoning."""
```

#### Adaptive Learning (User Feedback)
```python
# Learning from user corrections
def record_feedback(self, task_a_id, task_b_id, is_dependency,
                   user_confirmed, reason=None):
    # Adjust feature weights based on feedback
    # Learn new patterns from confirmed dependencies
    # Update confidence thresholds
```

### Context Generation

#### Task Context Assembly
```python
@dataclass
class TaskContext:
    task_id: str
    previous_implementations: Dict[str, Any]  # From completed tasks
    dependent_tasks: List[Dict[str, Any]]     # Tasks depending on this
    related_patterns: List[Dict[str, Any]]    # Similar previous work
    architectural_decisions: List[Dict[str, Any]]  # Relevant decisions
```

#### Decision Tracking
```python
@dataclass
class Decision:
    decision_id: str
    task_id: str
    agent_id: str
    timestamp: datetime
    what: str      # What was decided
    why: str       # Why it was decided
    impact: str    # Impact on other components
```

### Performance Optimizations

#### Intelligent AI Usage
- Only uses AI for ambiguous cases identified by pattern analysis
- Batches multiple inferences into single API calls
- Implements exponential backoff for API failures

#### Memory Management
- Automatic cleanup of old context data
- Configurable retention periods
- Efficient graph algorithms for cycle detection

#### Caching Strategy
- Content-based cache keys for consistency
- TTL-based expiration for freshness
- Memory-efficient storage of inference results

## Simple vs Complex Task Handling

### Simple Tasks (Pattern-Based)
For straightforward dependencies like "test after implement":
- Fast pattern matching (< 1ms)
- High confidence scores (0.9+)
- Deterministic results
- No AI calls required

### Complex Tasks (Hybrid Approach)
For ambiguous relationships:
- Initial pattern screening
- AI analysis for unclear cases
- Confidence combination from multiple sources
- Learning from user feedback

### Adaptive Behavior
The system adapts its complexity based on:
- **Board maturity**: More sophisticated analysis for larger projects
- **User feedback**: Learns domain-specific patterns
- **Project type**: Different strategies for different domains

## Board-Specific Considerations

### Empty Boards
- Minimal context available
- Focus on high-level architectural patterns
- Recommend Creator mode for structure generation

### Chaotic Boards
- High dependency inference activity
- Pattern learning from existing relationships
- Recommend Enricher mode for organization

### Well-Structured Boards
- Leverage existing metadata and relationships
- Optimize for agent coordination
- Recommend Adaptive mode for efficiency

### Board Quality Integration
The system considers board quality metrics:
- **Structure Score**: Influences inference confidence
- **Metadata Completeness**: Affects context richness
- **Dependency Clarity**: Determines analysis depth

## Integration with Seneca (Kanban Provider)

### Bidirectional Synchronization
- Reads explicit dependencies from Seneca board
- Suggests new dependencies through Marcus interface
- Respects user-defined relationships as ground truth

### Metadata Enhancement
- Enriches Seneca tasks with inferred relationships
- Adds confidence scores for suggested dependencies
- Provides reasoning for all inferences

### User Preference Handling
- Respects user settings for inference aggressiveness
- Allows disabling of automatic inference
- Provides manual override capabilities

## Current Implementation Pros and Cons

### Pros

#### Sophisticated Multi-Strategy Approach
- Combines speed of patterns with intelligence of AI
- Graceful degradation ensures reliability
- Learns and adapts from user feedback

#### Rich Context Generation
- Provides agents with comprehensive background
- Reduces time spent understanding existing code
- Enables better integration between agent work

#### Intelligent Resource Management
- Minimizes AI API costs through caching
- Efficient pattern matching for common cases
- Scales gracefully with project size

#### User-Centric Design
- Respects user preferences and explicit relationships
- Provides clear reasoning for all inferences
- Allows easy override of system suggestions

### Cons

#### Complexity Overhead
- Multiple inference strategies increase maintenance burden
- Cache management adds complexity
- Error handling across multiple failure modes

#### AI Dependency
- Reduced functionality when AI services are unavailable
- Potential latency for complex inference operations
- Cost implications for large-scale usage

#### Learning Curve
- Multiple modes and settings may confuse new users
- Requires understanding of confidence thresholds
- Pattern configuration may be intimidating

#### Performance Scaling
- Graph algorithms may not scale to very large projects
- Memory usage grows with project history
- Cache invalidation complexity

## Why This Approach Was Chosen

### Problem Statement
Traditional task management systems lack understanding of task relationships, leading to:
- Illogical task assignments (testing before implementation)
- Agents working without context of previous decisions
- Repeated work due to lack of pattern recognition
- Poor coordination between distributed agents

### Design Principles

#### Pragmatic Intelligence
- Use simple patterns for obvious cases
- Apply AI only where needed
- Learn from real user behavior

#### Graceful Degradation
- System remains functional when components fail
- Multiple fallback strategies
- No single point of failure

#### User Agency
- Users remain in control of their project structure
- System provides suggestions, not mandates
- Easy override of system decisions

#### Performance Consciousness
- Minimize external API calls
- Cache aggressively
- Optimize for common cases

### Alternative Approaches Considered

#### Pure Rule-Based System
- **Rejected**: Too rigid for diverse project types
- **Problem**: Can't handle edge cases or domain-specific patterns

#### Pure AI-Based System
- **Rejected**: Too expensive and unreliable
- **Problem**: Latency and cost issues for all decisions

#### Manual-Only Dependencies
- **Rejected**: Places too much burden on users
- **Problem**: Most users don't specify comprehensive dependencies

#### Simple Heuristics
- **Rejected**: Too simplistic for complex projects
- **Problem**: High false positive/negative rates

## Future Evolution Possibilities

### Enhanced AI Integration
- **Multi-Model Ensemble**: Combine different AI models for robustness
- **Domain-Specific Models**: Fine-tuned models for different project types
- **Real-Time Learning**: Continuous learning from user interactions

### Advanced Pattern Recognition
- **Natural Language Processing**: Better extraction of semantics from task descriptions
- **Code Analysis Integration**: Analyze actual code to infer technical dependencies
- **Temporal Pattern Recognition**: Learn from timing patterns in project completion

### Improved User Experience
- **Visual Dependency Editor**: Graphical interface for dependency management
- **Confidence Explanations**: Detailed explanations of inference reasoning
- **Interactive Learning**: Real-time feedback incorporation

### Performance Optimizations
- **Distributed Processing**: Scale to very large projects
- **Incremental Updates**: Efficient updates for changing project state
- **Predictive Caching**: Anticipate needed context before requests

### Extended Context Types
- **Code Context**: Integration with version control systems
- **Communication Context**: Learn from team chat and comments
- **Performance Context**: Track task completion times and success rates

### Integration Expansions
- **Multiple Board Support**: Work across multiple Kanban boards
- **External Tool Integration**: Context from JIRA, GitHub, etc.
- **Team Collaboration**: Shared context across team members

## Conclusion

The Context & Dependency System represents a sophisticated approach to project intelligence that balances automation with user control, performance with accuracy, and simplicity with power. By providing rich context to agents and intelligently inferring relationships between tasks, it transforms Marcus from a simple coordinator into an intelligent project partner that learns and adapts to each team's unique workflow patterns.

The system's multi-strategy approach ensures reliable operation across diverse scenarios while its adaptive learning capabilities enable continuous improvement. As projects evolve and teams provide feedback, the system becomes increasingly valuable, making it a cornerstone of Marcus's intelligent project management capabilities.
