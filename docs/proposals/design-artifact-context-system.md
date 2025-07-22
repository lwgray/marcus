# Design Artifact Context System Proposal

## Overview

Enhance Marcus's context system to automatically capture and propagate artifacts from design phase tasks to their dependent implementation tasks, creating a rich knowledge transfer pipeline.

## Problem Statement

Currently, when agents complete design tasks, their outputs (API specs, wireframes, architecture decisions, data models) are lost in task comments or completion messages. Implementation agents must piece together context from minimal task descriptions.

## Proposed Solution

### 1. Artifact Capture During Design Phase

```python
@dataclass
class TaskArtifact:
    artifact_id: str
    task_id: str
    artifact_type: str  # 'api_spec', 'wireframe', 'data_model', 'architecture_decision'
    content: str
    format: str  # 'markdown', 'json', 'yaml', 'image_url'
    created_by: str  # agent_id
    created_at: datetime
    embeddings: Optional[List[float]]  # For vector search

class DesignArtifactExtractor:
    """Extract structured artifacts from design task completions"""

    async def extract_artifacts(self, task: Task, completion_message: str) -> List[TaskArtifact]:
        # Use AI to identify and extract structured artifacts
        artifacts = []

        # Extract API specifications
        api_specs = self._extract_api_specs(completion_message)
        for spec in api_specs:
            artifacts.append(TaskArtifact(
                artifact_type='api_spec',
                content=spec,
                format='yaml',
                embeddings=await self._generate_embeddings(spec)
            ))

        # Extract data models
        data_models = self._extract_data_models(completion_message)
        # ... similar processing

        return artifacts
```

### 2. Context Propagation to Dependent Tasks

```python
class EnhancedTaskContext:
    """Enhanced context with design artifacts"""

    task_id: str
    previous_implementations: Dict[str, Any]
    dependent_tasks: List[Dict[str, Any]]
    related_patterns: List[Dict[str, Any]]
    architectural_decisions: List[Dict[str, Any]]

    # NEW: Design phase artifacts
    design_artifacts: List[TaskArtifact]
    related_artifacts: List[TaskArtifact]  # From vector similarity

    def to_agent_prompt(self) -> str:
        """Generate rich context prompt for agent"""
        prompt = f"""
## Task Context

### Design Specifications
{self._format_design_artifacts()}

### API Contracts
{self._format_api_specs()}

### Data Models
{self._format_data_models()}

### Architecture Decisions
{self._format_architecture_decisions()}

### Similar Past Implementations
{self._format_previous_implementations()}
"""
        return prompt
```

### 3. Implementation in Task Assignment Flow

```python
async def get_task_context(task_id: str, state: Any) -> TaskContext:
    task = state.get_task(task_id)

    # Get direct dependency artifacts
    design_artifacts = []
    for dep_id in task.dependencies:
        dep_task = state.get_task(dep_id)
        if is_design_task(dep_task):
            artifacts = await state.artifact_store.get_artifacts(dep_id)
            design_artifacts.extend(artifacts)

    # Get related artifacts via vector search
    task_embedding = await generate_embedding(task.name + task.description)
    related_artifacts = await state.vector_db.search_similar_artifacts(
        embedding=task_embedding,
        limit=5,
        artifact_types=['api_spec', 'data_model']
    )

    return TaskContext(
        task_id=task_id,
        design_artifacts=design_artifacts,
        related_artifacts=related_artifacts,
        # ... other context
    )
```

## Benefits

1. **Reduced Context Loss**: Design decisions and specifications flow naturally to implementation
2. **Faster Implementation**: Agents don't need to reverse-engineer requirements
3. **Better Consistency**: Implementation follows design specifications exactly
4. **Learning System**: Vector DB accumulates organizational knowledge over time

## Example Workflow

1. **Design Task Completion**:
   ```
   Agent completes "Design User Authentication API"
   Output includes:
   - OpenAPI spec for /auth endpoints
   - JWT token structure
   - User data model
   - Security considerations
   ```

2. **Artifact Extraction**:
   ```
   System extracts:
   - api_spec: auth_endpoints.yaml
   - data_model: user_schema.json
   - decisions: jwt_strategy.md
   ```

3. **Implementation Task Assignment**:
   ```
   Agent receives "Implement User Authentication API"
   Context includes:
   - Full OpenAPI spec from design
   - User model schema
   - JWT implementation decisions
   - Similar auth implementations from other projects
   ```

## Technical Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                Design Artifact Pipeline                      │
├─────────────────┬───────────────────┬───────────────────────┤
│ Artifact        │ Vector           │ Context              │
│ Extraction      │ Embedding        │ Integration          │
│                 │                  │                      │
│ • AI Parsing    │ • Semantic Index │ • Task Assignment    │
│ • Type Detection│ • Similarity     │ • Prompt Generation  │
│ • Validation    │ • Clustering     │ • Agent Delivery     │
└─────────────────┴───────────────────┴───────────────────────┘
```

## Implementation Phases

### Phase 1: Basic Artifact Capture (1-2 weeks)
- Modify task completion to extract markdown artifacts
- Store artifacts linked to tasks
- Basic context propagation to dependent tasks

### Phase 2: Vector Search Integration (2-3 weeks)
- Implement embedding generation for artifacts
- Set up vector database (Pinecone/Weaviate/Qdrant)
- Add similarity search to context generation

### Phase 3: Intelligent Extraction (3-4 weeks)
- AI-powered artifact identification
- Structured data extraction (JSON, YAML, etc.)
- Artifact validation and quality scoring

### Phase 4: Advanced Features (4-6 weeks)
- Cross-project artifact learning
- Artifact versioning and evolution tracking
- Team-specific artifact preferences
