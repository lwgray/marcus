# Vector Relationship Database for Intelligent Blocker Resolution

## Overview

Build a vector database of task relationships, blockers, and resolutions that Marcus can query to provide intelligent suggestions when agents encounter obstacles.

## Problem Statement

When agents hit blockers, Marcus currently has limited ability to suggest solutions based on:
- Generic AI analysis
- Simple pattern matching
- No organizational memory of past resolutions

This misses the rich learning opportunity from previously resolved blockers and successful task relationships.

## Proposed Solution

### 1. Relationship Vector Database Schema

```python
@dataclass
class TaskRelationship:
    relationship_id: str
    relationship_type: str  # 'blocker', 'dependency', 'integration', 'conflict'
    source_task: TaskSnapshot
    target_task: TaskSnapshot
    context: Dict[str, Any]
    resolution: Optional[Resolution]
    embeddings: RelationshipEmbeddings
    metadata: Dict[str, Any]

@dataclass
class TaskSnapshot:
    task_id: str
    name: str
    description: str
    type: str
    phase: str
    tech_stack: List[str]
    labels: List[str]

@dataclass
class Resolution:
    resolution_id: str
    blocker_type: str  # 'technical', 'dependency', 'resource', 'knowledge'
    solution: str
    solution_steps: List[str]
    success: bool
    time_to_resolve: int  # hours
    agent_feedback: str

@dataclass
class RelationshipEmbeddings:
    # Multiple embeddings for different aspects
    problem_embedding: List[float]      # The blocker/issue
    context_embedding: List[float]      # Surrounding context
    solution_embedding: List[float]     # The resolution
    combined_embedding: List[float]     # Overall relationship
```

### 2. Blocker Analysis & Resolution Engine

```python
class BlockerResolutionEngine:
    def __init__(self, vector_db: VectorDatabase):
        self.vector_db = vector_db
        self.ai_engine = MarcusAIEngine()

    async def analyze_blocker(self, blocker_report: BlockerReport) -> BlockerAnalysis:
        """Analyze a blocker using vector search and AI"""

        # Generate embeddings for the current blocker
        blocker_embedding = await self._generate_blocker_embedding(blocker_report)

        # Search for similar past blockers
        similar_blockers = await self.vector_db.search(
            embedding=blocker_embedding,
            filter={
                'relationship_type': 'blocker',
                'resolution.success': True,
                'tech_stack': {'$overlap': blocker_report.tech_stack}
            },
            limit=10
        )

        # Analyze patterns in successful resolutions
        resolution_patterns = self._analyze_resolution_patterns(similar_blockers)

        # Generate contextual suggestions
        suggestions = await self._generate_suggestions(
            blocker_report,
            similar_blockers,
            resolution_patterns
        )

        return BlockerAnalysis(
            blocker_type=self._classify_blocker(blocker_report),
            similar_cases=similar_blockers,
            suggested_solutions=suggestions,
            confidence_scores=self._calculate_confidence(similar_blockers),
            estimated_resolution_time=self._estimate_resolution_time(similar_blockers)
        )

    async def _generate_suggestions(self, blocker, similar_cases, patterns):
        """Generate intelligent suggestions based on past resolutions"""

        # Build context from successful resolutions
        context = {
            'current_blocker': blocker.description,
            'similar_resolutions': [
                {
                    'problem': case.context['blocker_description'],
                    'solution': case.resolution.solution,
                    'steps': case.resolution.solution_steps
                }
                for case in similar_cases[:5]
            ],
            'common_patterns': patterns
        }

        # Use AI to synthesize suggestions
        prompt = f"""
        Based on similar blockers that were successfully resolved, suggest solutions:

        Current Blocker: {blocker.description}
        Task Context: {blocker.task_context}

        Similar Successful Resolutions:
        {json.dumps(context['similar_resolutions'], indent=2)}

        Generate 3-5 specific, actionable suggestions based on what worked before.
        """

        suggestions = await self.ai_engine.generate_suggestions(prompt)
        return suggestions
```

### 3. Continuous Learning System

```python
class RelationshipLearningSystem:
    """Continuously learn from task relationships and resolutions"""

    async def record_blocker_resolution(self, blocker_id: str, resolution: Resolution):
        """Record how a blocker was resolved"""

        blocker = await self.get_blocker(blocker_id)

        # Create relationship record
        relationship = TaskRelationship(
            relationship_type='blocker',
            source_task=blocker.task_snapshot,
            target_task=blocker.blocking_task_snapshot,
            context={
                'blocker_description': blocker.description,
                'agent_analysis': blocker.agent_analysis,
                'environment': blocker.environment_context
            },
            resolution=resolution,
            embeddings=await self._generate_embeddings(blocker, resolution)
        )

        # Store in vector database
        await self.vector_db.upsert(relationship)

        # Update pattern recognition
        await self._update_resolution_patterns(relationship)

    async def analyze_task_relationships(self, project_id: str):
        """Analyze all relationships in a project for patterns"""

        tasks = await self.get_project_tasks(project_id)

        # Extract different types of relationships
        relationships = []

        # Dependency relationships
        for task in tasks:
            for dep_id in task.dependencies:
                dep_task = self.get_task(dep_id)
                relationship = await self._analyze_dependency_relationship(task, dep_task)
                relationships.append(relationship)

        # Integration relationships
        integration_pairs = self._find_integration_points(tasks)
        for task_a, task_b in integration_pairs:
            relationship = await self._analyze_integration_relationship(task_a, task_b)
            relationships.append(relationship)

        # Store all relationships
        await self.vector_db.bulk_upsert(relationships)
```

### 4. Integration with Marcus Workflow

```python
# In report_blocker flow
async def report_task_blocker(agent_id: str, task_id: str, blocker_info: Dict) -> Dict:
    # Current blocker reporting...

    # NEW: Intelligent blocker analysis
    blocker_analysis = await blocker_resolution_engine.analyze_blocker(
        BlockerReport(
            task_id=task_id,
            agent_id=agent_id,
            description=blocker_info['description'],
            tech_stack=current_task.tech_stack,
            task_context=await get_task_context(task_id)
        )
    )

    # Provide intelligent suggestions
    response = {
        'blocker_recorded': True,
        'similar_blockers_found': len(blocker_analysis.similar_cases),
        'suggested_solutions': blocker_analysis.suggested_solutions,
        'estimated_resolution_time': blocker_analysis.estimated_resolution_time,
        'confidence': blocker_analysis.confidence_scores
    }

    # Learn from the resolution later
    asyncio.create_task(
        monitor_blocker_resolution(blocker_id, relationship_learning_system)
    )

    return response
```

## Benefits

### 1. Intelligent Blocker Resolution
- **Pattern Recognition**: Identifies common blocker patterns and proven solutions
- **Contextual Suggestions**: Provides specific solutions based on similar past cases
- **Time Estimation**: Predicts resolution time based on historical data
- **Confidence Scoring**: Indicates reliability of suggestions

### 2. Organizational Learning
- **Knowledge Accumulation**: Every resolved blocker adds to organizational knowledge
- **Cross-Project Learning**: Solutions from one project help others
- **Team Expertise Capture**: Preserves problem-solving knowledge as agents work

### 3. Relationship Intelligence
- **Hidden Dependencies**: Discovers non-obvious task relationships through analysis
- **Integration Patterns**: Learns common integration points between components
- **Conflict Prediction**: Anticipates potential conflicts based on past patterns

## Example Use Cases

### Use Case 1: API Integration Blocker
```
Agent reports: "Cannot connect frontend to auth API - CORS errors"

Vector search finds:
- 5 similar CORS blockers in React/Node projects
- 3 were resolved by proxy configuration
- 2 were resolved by backend CORS middleware

Marcus suggests:
1. Add proxy configuration to package.json (worked in 60% of cases)
2. Configure CORS middleware with specific origins (worked in 40%)
3. Provides exact code snippets from successful resolutions
```

### Use Case 2: Database Migration Dependency
```
Agent reports: "Cannot run migrations - missing database schema"

Vector search finds:
- Pattern: Migration tasks often blocked when DB setup incomplete
- Common resolution: Run seed data task first
- Alternative: Use migration rollback and re-run

Marcus suggests:
1. Check if "Setup Database" task is complete
2. Run pending seed data scripts
3. Provides migration troubleshooting checklist
```

### Use Case 3: Cross-Feature Integration
```
Agent reports: "Payment service cannot access user session data"

Vector search finds:
- Integration pattern between auth and payment services
- Similar issues resolved by shared session store
- Redis commonly used for session sharing

Marcus suggests:
1. Implement Redis session store (example provided)
2. Update both services to use shared store
3. Add integration tests for session sharing
```

## Technical Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                 Vector Relationship Database                     │
├─────────────────┬────────────────┬──────────────────────────────┤
│ Ingestion       │ Vector Store   │ Query & Analysis             │
│ Pipeline        │                │                              │
│                 │                │                              │
│ • Relationship  │ • Embeddings   │ • Similarity Search          │
│   Extraction    │ • Indexing     │ • Pattern Analysis           │
│ • Resolution    │ • Clustering   │ • AI Synthesis               │
│   Tracking      │ • Updates      │ • Suggestion Generation      │
└─────────────────┴────────────────┴──────────────────────────────┘
                           │
                           ├── Pinecone/Weaviate/Qdrant
                           ├── Multiple embedding models
                           └── Hybrid search (vector + metadata)
```

## Implementation Roadmap

### Phase 1: Foundation (2-3 weeks)
- Set up vector database infrastructure
- Implement basic relationship extraction
- Create embedding generation pipeline

### Phase 2: Blocker Resolution (3-4 weeks)
- Build blocker analysis engine
- Implement similarity search
- Create suggestion generation system

### Phase 3: Learning System (4-5 weeks)
- Implement resolution tracking
- Build pattern recognition
- Create feedback loops

### Phase 4: Advanced Intelligence (5-6 weeks)
- Cross-project learning
- Predictive blocker detection
- Team-specific pattern adaptation

## Configuration Options

```python
@dataclass
class VectorDBConfig:
    # Vector search parameters
    similarity_threshold: float = 0.75
    max_results: int = 10
    embedding_model: str = "text-embedding-ada-002"

    # Learning parameters
    min_success_rate: float = 0.7  # Minimum success rate for pattern
    pattern_confidence_threshold: float = 0.8

    # Filtering options
    consider_tech_stack: bool = True
    consider_team_size: bool = True
    time_decay_factor: float = 0.95  # Newer resolutions weighted higher
```

## Privacy & Security Considerations

1. **Data Sanitization**: Remove sensitive data before embedding
2. **Access Control**: Limit vector search to authorized projects
3. **Embedding Security**: Use local models for sensitive domains
4. **Audit Trail**: Track all relationship queries and suggestions
