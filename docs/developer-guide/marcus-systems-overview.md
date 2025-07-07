# Marcus Systems Overview

## Table of Contents
1. [Core Systems](#core-systems)
2. [Visibility & Visualization Systems](#visibility--visualization-systems)
3. [Context Management Systems](#context-management-systems)
4. [Dependency Tracking Systems](#dependency-tracking-systems)
5. [Communication Systems](#communication-systems)
6. [Logging & Monitoring Systems](#logging--monitoring-systems)
7. [Error Handling Systems](#error-handling-systems)
8. [Memory & State Management](#memory--state-management)
9. [Agent Coordination Systems](#agent-coordination-systems)
10. [Task Management Systems](#task-management-systems)
11. [Event Systems](#event-systems)
12. [API Systems](#api-systems)
13. [MCP Integration](#mcp-integration)
14. [AI & Intelligence Systems](#ai--intelligence-systems)
15. [Cost Tracking Systems](#cost-tracking-systems)
16. [Integration Systems](#integration-systems)
17. [Security & Workspace Management](#security--workspace-management)
18. [Persistence Systems](#persistence-systems)

---

## Core Systems

### Models (`src/core/models.py`)
**Purpose**: Defines fundamental data structures used throughout Marcus
- **Key Classes**:
  - `Task`: Work item representation with status, priority, dependencies
  - `TaskStatus`: Enum for task states (TODO, IN_PROGRESS, DONE, BLOCKED)
  - `Priority`: Task urgency levels (LOW, MEDIUM, HIGH, URGENT)
  - `RiskLevel`: Risk severity classification
  - `WorkerStatus`: Agent state tracking
  - `TaskAssignment`: Task-to-agent mapping
  - `ProjectState`: Overall project health metrics

### Resilience (`src/core/resilience.py`)
**Purpose**: Provides fault-tolerant decorators and error handling patterns
- **Features**:
  - `@with_fallback`: Graceful degradation decorator
  - `@resilient_persistence`: Robust storage operations
  - Automatic retry mechanisms
  - Circuit breaker patterns

---

## Visibility & Visualization Systems

### Event-Integrated Visualizer (`src/visualization/event_integrated_visualizer.py`)
**Purpose**: Real-time visualization updates without polling
- **Features**:
  - Subscribes to Events system for instant updates
  - Maps events to pipeline stages
  - Maintains active flow tracking
  - Bridges Events system with visualization pipeline

### Pipeline Flow (`src/visualization/pipeline_flow.py`)
**Purpose**: Visual pipeline stage management
- **Key Components**:
  - `PipelineStage`: Enum for pipeline phases
  - Flow state tracking
  - Stage transition management

### Shared Pipeline Events (`src/visualization/shared_pipeline_events.py`)
**Purpose**: Event distribution for visualization components
- **Features**:
  - WebSocket integration
  - Real-time update broadcasting
  - Client synchronization

### UI Server (`src/visualization/ui_server.py`)
**Purpose**: Frontend server for visualization interfaces
- **Components**:
  - Web dashboard serving
  - Real-time data streaming
  - Interactive visualizations

---

## Context Management Systems

### Context System (`src/core/context.py`)
**Purpose**: Rich context for task assignments including dependencies and patterns
- **Key Classes**:
  - `TaskContext`: Complete context for assignments
  - `DependentTask`: Dependency relationship tracking
  - `Decision`: Architectural decision logging
  - `Context`: Main context manager
- **Features**:
  - Previous implementation tracking
  - Dependency inference (explicit & implicit)
  - Architectural decision storage
  - Pattern recognition
  - Circular dependency detection
  - Task ordering suggestions

---

## Dependency Tracking Systems

### Dependency Inferer (`src/intelligence/dependency_inferer.py`)
**Purpose**: Intelligent dependency detection and management
- **Features**:
  - Pattern-based dependency rules
  - Action-based inference
  - Entity-based inference
  - Technical stack dependencies

### Context Dependency Analysis (`src/core/context.py`)
**Purpose**: Built into Context system
- **Methods**:
  - `analyze_dependencies()`: Comprehensive dependency analysis
  - `_infer_dependency()`: Rule-based dependency inference
  - `_detect_circular_dependencies()`: Cycle detection
  - `suggest_task_order()`: Topological sorting with priorities

---

## Communication Systems

### Communication Hub (`src/communication/communication_hub.py`)
**Purpose**: Multi-channel notification system
- **Channels**:
  - Slack integration
  - Email notifications
  - Kanban board comments
- **Features**:
  - Async message delivery
  - Agent preference management
  - Formatted message generation
  - Error isolation per channel

---

## Logging & Monitoring Systems

### Conversation Logger (`src/logging/conversation_logger.py`)
**Purpose**: Structured conversation and event logging
- **Classes**:
  - `ConversationType`: Interaction type enumeration
  - `ConversationLogger`: Main logging interface
- **Features**:
  - JSON-formatted logs
  - Automatic file rotation
  - Real-time visualization support
  - Decision replay capability

### Project Monitor (`src/monitoring/project_monitor.py`)
**Purpose**: Continuous project health tracking
- **Features**:
  - Real-time metrics collection
  - AI-powered health analysis
  - Risk assessment
  - Blocker tracking
  - Historical trend analysis
  - Automated alerting

### Assignment Monitor (`src/monitoring/assignment_monitor.py`)
**Purpose**: Task assignment tracking and analysis
- **Features**:
  - Assignment pattern detection
  - Performance metrics
  - Bottleneck identification

---

## Error Handling Systems

### Error Framework (`src/core/error_framework.py`)
**Purpose**: Comprehensive error handling for autonomous agents
- **Key Classes**:
  - `MarcusBaseError`: Base exception with rich context
  - `ErrorContext`: Detailed error information
  - `RemediationSuggestion`: Actionable recovery steps
  - `ErrorSeverity`: Priority levels
  - `ErrorCategory`: Classification system
- **Features**:
  - Structured error types
  - Rich context capture
  - Remediation suggestions
  - Correlation tracking

### Error Strategies (`src/core/error_strategies.py`)
**Purpose**: Resilience patterns and recovery strategies
- **Decorators**:
  - `@with_retry`: Configurable retry logic
  - `@with_circuit_breaker`: Service protection
  - `@with_fallback`: Graceful degradation

### Error Monitoring (`src/core/error_monitoring.py`)
**Purpose**: Error pattern detection and analysis
- **Features**:
  - Error frequency tracking
  - Pattern recognition
  - Automatic alerting

---

## Memory & State Management

### Memory System (`src/core/memory.py`)
**Purpose**: Multi-tier cognitive memory model
- **Classes**:
  - `TaskOutcome`: Execution result tracking
  - `AgentProfile`: Learned capabilities
  - `TaskPattern`: Task type patterns
  - `Memory`: Main memory manager
- **Memory Tiers**:
  - Working memory: Active task state
  - Episodic memory: Event sequences
  - Semantic memory: Learned patterns
  - Procedural memory: Best practices

### Enhanced Memory (`src/core/memory_enhanced.py`)
**Purpose**: Advanced memory features and analytics
- **Features**:
  - Predictive capabilities
  - Pattern learning
  - Performance optimization

---

## Agent Coordination Systems

### AI-Powered Task Assignment (`src/core/ai_powered_task_assignment.py`)
**Purpose**: Intelligent task-to-agent matching
- **Features**:
  - Skill-based matching
  - Load balancing
  - Performance prediction
  - Context-aware assignment

### Assignment Persistence (`src/core/assignment_persistence.py`)
**Purpose**: Durable assignment state management
- **Features**:
  - Assignment history
  - State recovery
  - Audit trail

### Assignment Reconciliation (`src/core/assignment_reconciliation.py`)
**Purpose**: Consistency management across systems
- **Features**:
  - State synchronization
  - Conflict resolution
  - Orphaned task detection

---

## Task Management Systems

### Intelligent Task Generator (`src/intelligence/intelligent_task_generator.py`)
**Purpose**: AI-powered task creation and decomposition
- **Features**:
  - Natural language parsing
  - Task breakdown
  - Dependency generation

### PRD Parser (`src/intelligence/prd_parser.py`)
**Purpose**: Product requirement document analysis
- **Features**:
  - Requirement extraction
  - Task generation
  - Priority inference

---

## Event Systems

### Events (`src/core/events.py`)
**Purpose**: Loose coupling through publish/subscribe pattern
- **Classes**:
  - `Event`: Base event structure
  - `Events`: Event distribution system
  - `EventTypes`: Standard event type enumeration
- **Features**:
  - Async event handling
  - Event history storage
  - Error isolation
  - Wildcard subscriptions

---

## API Systems

### Main API Server (`src/api/app.py`)
**Purpose**: REST API and WebSocket server
- **Endpoints**:
  - Pipeline enhancement API
  - Agent management API
  - Project management API
  - Cost tracking API
  - Context visualization API
  - Memory insights API

### Context Visualization API (`src/api/context_visualization_api.py`)
**Purpose**: Context system data access
- **Features**:
  - Dependency graph endpoints
  - Decision history access
  - Real-time context updates

### Memory Insights API (`src/api/memory_insights_api.py`)
**Purpose**: Memory system analytics
- **Features**:
  - Performance metrics
  - Pattern analysis
  - Prediction endpoints

---

## MCP Integration

### MCP Server (`src/marcus_mcp/server.py`)
**Purpose**: Model Context Protocol server implementation
- **Components**:
  - Tool registration
  - Request handling
  - State management
  - Pipeline integration

### MCP Tools (`src/marcus_mcp/tools/`)
**Purpose**: Modular tool implementations
- **Tool Categories**:
  - `agent_tools.py`: Agent management
  - `context_tools.py`: Context operations
  - `nlp_tools.py`: Natural language processing
  - `pipeline_tools.py`: Pipeline operations
  - `project_tools.py`: Project management
  - `system_tools.py`: System operations
  - `task_tools.py`: Task management

---

## AI & Intelligence Systems

### AI Engine (`src/ai/core/ai_engine.py`)
**Purpose**: Hybrid intelligence coordination
- **Components**:
  - `RuleBasedEngine`: Safety-first logic
  - `AIEngine`: Enhancement layer
- **Features**:
  - Rule/AI hybrid approach
  - Safety guarantees
  - Intelligence amplification

### LLM Abstraction (`src/ai/providers/llm_abstraction.py`)
**Purpose**: Provider-agnostic AI interface
- **Supported Providers**:
  - Anthropic (Claude)
  - OpenAI
  - Extensible to others

### Learning Systems (`src/ai/learning/`)
**Purpose**: Continuous improvement
- **Components**:
  - `ContextualLearner`: Pattern recognition
  - `PatternLearner`: Task pattern analysis

---

## Cost Tracking Systems

### Token Tracker (`src/cost_tracking/token_tracker.py`)
**Purpose**: Real-time AI usage cost monitoring
- **Features**:
  - Per-project token tracking
  - Spend rate calculation
  - Cost projections
  - Historical analytics
  - Sliding window analysis

### AI Usage Middleware (`src/cost_tracking/ai_usage_middleware.py`)
**Purpose**: Automatic usage capture
- **Features**:
  - Request/response tracking
  - Model detection
  - Cost attribution

---

## Integration Systems

### Kanban Interface (`src/integrations/kanban_interface.py`)
**Purpose**: Abstract interface for kanban providers
- **Implementations**:
  - Planka
  - Linear
  - GitHub Projects
- **Common Operations**:
  - Task CRUD
  - Board management
  - Assignment tracking

### Kanban Factory (`src/integrations/kanban_factory.py`)
**Purpose**: Provider instantiation
- **Features**:
  - Dynamic provider loading
  - Configuration management
  - Connection pooling

---

## Security & Workspace Management

### Workspace Manager (`src/core/workspace_manager.py`)
**Purpose**: Agent isolation and security
- **Classes**:
  - `WorkspaceConfig`: Workspace configuration
  - `ProjectWorkspaces`: Multi-workspace management
  - `WorkspaceSecurityError`: Security violations
- **Features**:
  - Path validation
  - Access control
  - Audit logging
  - Marcus installation protection

---

## Persistence Systems

### Persistence (`src/core/persistence.py`)
**Purpose**: Unified storage interface
- **Backends**:
  - `FilePersistence`: JSON file storage
  - `SQLitePersistence`: Database storage
- **Features**:
  - Collection-based storage
  - Atomic operations
  - Query capabilities
  - Old data cleanup
  - Lock management

---

## System Integration Flow

1. **Task Creation**: PRD Parser → Task Generator → Kanban Integration
2. **Assignment**: Context System → AI Engine → Assignment System → Agent
3. **Execution**: Agent → Events → Monitoring → Visualization
4. **Learning**: Memory System → Pattern Recognition → Context Enhancement
5. **Communication**: Events → Communication Hub → Multi-channel delivery

## Key Design Principles

1. **Event-Driven Architecture**: Loose coupling through Events system
2. **Resilience First**: Error handling, fallbacks, and graceful degradation
3. **Context-Aware**: Rich context for every decision
4. **Learning System**: Continuous improvement through Memory
5. **Multi-Provider**: Abstract interfaces for integrations
6. **Real-Time Visibility**: Event-based updates, no polling
7. **Security by Design**: Workspace isolation and validation

## Extension Points

1. **New Kanban Providers**: Implement `KanbanInterface`
2. **AI Providers**: Extend `BaseProvider`
3. **Communication Channels**: Add to `CommunicationHub`
4. **Event Types**: Register in `EventTypes`
5. **Memory Tiers**: Extend `Memory` class
6. **Error Types**: Inherit from `MarcusBaseError`
7. **API Endpoints**: Add blueprints to `app.py`