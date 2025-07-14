# Marcus Systems Architecture

Marcus is a comprehensive AI agent coordination platform with enterprise-grade reliability, real-time visibility, and intelligent automation capabilities. This document provides a complete overview of all systems and components.

## Core Architectural Systems

### 1. Multi-Tier Memory System (`src/core/memory.py`)
A cognitive-inspired memory management system with four tiers:
- **Working Memory** - Current task contexts and immediate data
- **Episodic Memory** - Historical events and experiences
- **Semantic Memory** - Facts, patterns, and learned knowledge
- **Procedural Memory** - Skills and process knowledge
- Unified interface for cognitive-inspired memory management

### 2. Conversation Logger (`src/logging/conversation_logger.py`)
Structured logging system for all agent-tool interactions:
- JSON-based conversation storage
- Historical replay capabilities
- Integration with visualization systems
- Audit trail for all operations

### 3. Context & Dependency System
Comprehensive dependency and context management:
- **Context Management** (`src/core/context.py`) - Rich context for task assignments
- **Dependency Inference** (`src/intelligence/dependency_inferer.py`) - Pattern-based detection
- **Adaptive Dependencies** (`src/core/adaptive_dependencies.py`) - Learning-based inference
- **Context Detector** (`src/detection/context_detector.py`) - Automatic context extraction

### 4. Kanban Board Integration (`src/integrations/`)
Abstract interface supporting multiple kanban providers:
- **Planka** - Open-source kanban board
- **Linear** - Modern issue tracking system
- **GitHub Projects** - Native GitHub integration
- Dynamic provider factory pattern
- AI-powered board analysis

### 5. Visualization & UI Systems (`src/visualization/`)
Real-time project visualization and monitoring:
- **Event-Integrated Visualizer** - Real-time project visualization
- **Pipeline Flow Manager** - Stage-based workflow visualization
- **Pipeline Replay** - Historical analysis tools
- **WebSocket Event Distribution** - Live updates to UI
- **Conversation Bridge** - Links conversations to pipeline stages

### 6. MCP (Model Context Protocol) Server (`src/marcus_mcp/`)
Full MCP implementation for AI agent integration:
- Modular tool system (agent, task, project, system tools)
- Agent-specific server capabilities
- Natural language processing tools
- Tool registration and routing

### 7. AI Intelligence Engine (`src/ai/`)
Hybrid intelligence system combining rules and AI:
- **Hybrid Decision Framework** - Rules + AI intelligence
- **Provider Abstraction** - Support for Claude, OpenAI, etc.
- **Contextual Learning** - Pattern recognition
- **Task Enrichment** - AI-powered task enhancement
- **Advanced PRD Parsing** - Intelligent requirement analysis

### 8. Error Framework (`src/core/error_framework.py`)
Comprehensive error handling and resilience:
- Rich error taxonomy with context
- Resilience patterns (retry, circuit breaker, fallback)
- Error monitoring and pattern detection
- Standardized error responses
- Integration with monitoring systems

### 9. Event-Driven Architecture (`src/core/events.py`)
Central publish/subscribe system:
- Loose coupling between components
- Real-time updates across systems
- Event replay capabilities
- Multi-channel event distribution

### 10. Persistence Layer (`src/core/persistence.py`)
Unified storage with multiple backends:
- File and SQLite backends
- Assignment state management
- Project state persistence
- Transaction support

## Specialized Systems

### 11. Monitoring Systems (`src/monitoring/`)
Comprehensive monitoring and alerting:
- **Project Monitor** - Continuous health tracking
- **Assignment Monitor** - Task distribution analysis
- **Pipeline Monitor** - Real-time workflow tracking
- **Error Predictor** - Proactive issue detection

### 12. Communication Hub (`src/communication/communication_hub.py`)
Multi-channel notification system:
- Slack integration
- Email notifications
- Kanban updates
- Event-based messaging
- Configurable notification rules

### 13. Cost Tracking (`src/cost_tracking/`)
AI usage monitoring and optimization:
- Real-time token usage tracking
- Per-provider cost calculation
- Usage analytics and reporting
- Budget alerts

### 14. Workspace Isolation (`src/core/workspace.py`)
Security and resource management:
- Security boundaries for agents
- Resource isolation
- Safe execution environments
- Workspace lifecycle management

### 15. Service Registry (`src/core/service_registry.py`)
Dynamic service management:
- Service discovery
- Health checking
- Service lifecycle management
- Load balancing

### 16. Project Management
Comprehensive project coordination:
- **Project Registry** (`src/core/project_registry.py`) - Project configuration
- **Project Context Manager** (`src/core/project_context_manager.py`) - Context isolation
- **Project Workflow** (`src/workflow/project_workflow.py`) - Workflow orchestration
- Multi-project support with isolated contexts

### 17. Learning Systems (`src/learning/`)
Continuous improvement through pattern recognition:
- Pattern recognition across projects
- Adaptive behavior based on history
- Project-specific pattern learning
- Performance optimization

### 18. Quality Assurance (`src/quality/`)
Automated quality validation:
- Board quality validation
- Project quality assessment
- Automated quality checks
- Compliance verification

### 19. Natural Language Processing
Advanced NLP capabilities:
- PRD parsing and understanding
- Task description analysis
- Intelligent task generation from requirements
- Context extraction from natural language

### 20. Pipeline Systems
Sophisticated workflow management:
- Stage-based workflow tracking
- Pipeline tracking and replay
- What-if scenario analysis
- Pipeline comparison tools
- Performance metrics

### 21. Agent Coordination
Intelligent agent management:
- AI-powered task assignment
- Worker capability tracking
- Load balancing and optimization
- Agent event tracking
- Performance monitoring

### 22. Operational Modes
Flexible operational configurations:
- **Creator Mode** - Task generation from requirements
- **Enricher Mode** - Task enhancement and organization
- **Adaptive Mode** - Learning and optimization

## System Integration Points

### Data Flow
1. **Input Sources** → MCP Tools → Event System → Core Processing
2. **Core Processing** → AI Engine → Decision Making → Task Assignment
3. **Task Assignment** → Kanban Integration → Agent Execution
4. **Agent Execution** → Monitoring → Visualization → Feedback Loop

### Key Integration Patterns
- **Event-Driven** - All systems communicate via events
- **Context-Aware** - Rich context flows through all decisions
- **AI-Enhanced** - AI augments but doesn't replace human judgment
- **Resilient** - Failures are isolated and recovered gracefully
- **Observable** - All operations are tracked and visible

## Architecture Principles

1. **Event-Driven Architecture** - Central Events system for loose coupling
2. **Multi-Tier Memory Model** - Cognitive-inspired memory management
3. **Hybrid Intelligence** - Rule-based safety with AI enhancement
4. **Provider Abstraction** - Swappable integrations (Kanban, AI)
5. **Resilience First** - Comprehensive error handling and recovery
6. **Context-Aware** - Rich context for all decisions
7. **Real-Time Visibility** - Event-based updates throughout
8. **Modular Tool System** - MCP tools organized by domain
9. **Learning & Adaptation** - Continuous improvement through patterns
10. **Security by Design** - Workspace isolation and validation

## System Categories

### Core Infrastructure
- Events, Memory, Persistence, Error Framework
- Service Registry, Workspace Isolation

### Intelligence Layer
- AI Engine, Learning Systems, NLP
- Dependency Inference, Pattern Recognition

### Integration Layer
- MCP Server, Kanban Providers
- Communication Hub, GitHub Integration

### Operational Layer
- Monitoring, Cost Tracking, Quality Assurance
- Pipeline Management, Agent Coordination

### User Interface Layer
- Visualization Systems, WebSocket Events
- Pipeline UI, Real-time Updates

## Future Architecture Directions

1. **Distributed Agent Execution** - Scale across multiple machines
2. **Advanced Learning** - Deep learning for pattern recognition
3. **Multi-Cloud Support** - Deploy across cloud providers
4. **Enhanced Security** - Zero-trust architecture
5. **GraphQL API** - Modern API for external integrations
