# Marcus Systems Architecture

Marcus is a comprehensive AI agent coordination platform with enterprise-grade reliability, real-time visibility, and intelligent automation capabilities. This document provides a complete overview of all systems and components.

## Core Architectural Systems

### 1. Multi-Tier Memory System (`src/core/`)
A cognitive-inspired memory management system with four tiers:
- **Memory System** (`memory.py`) - Base memory implementation
- **Advanced Memory** (`memory_advanced.py`) - Extended memory capabilities
- **Working Memory** - Current task contexts and immediate data
- **Episodic Memory** - Historical events and experiences
- **Semantic Memory** - Facts, patterns, and learned knowledge
- **Procedural Memory** - Skills and process knowledge
- Unified interface for cognitive-inspired memory management

### 2. Conversation Logger & Logging Systems (`src/logging/`)
Structured logging system for all agent-tool interactions:
- **Conversation Logger** (`conversation_logger.py`) - JSON-based conversation storage
- **Agent Events** (`agent_events.py`) - Agent-specific event logging
- Historical replay capabilities
- Integration with visualization systems
- Audit trail for all operations
- Structured event tracking

### 3. Context & Dependency System
Comprehensive dependency and context management:
- **Context Management** (`src/core/context.py`) - Rich context for task assignments
- **Dependency Inference** (`src/intelligence/dependency_inferer.py`) - Pattern-based detection
- **Adaptive Dependencies** (`src/core/adaptive_dependencies.py`) - Learning-based inference
- **Context Detector** (`src/detection/context_detector.py`) - Automatic context extraction

### 4. Kanban Board Integration (`src/integrations/`)
Abstract interface supporting multiple kanban providers:
- **Kanban Interface** (`kanban_interface.py`) - Abstract interface for multiple providers
- **Kanban Factory** (`kanban_factory.py`) - Provider instantiation
- **Kanban Client** (`kanban_client.py`, `kanban_client_with_create.py`) - Board operations
- **Providers** (`providers/`):
  - **Planka** - Open-source kanban board
  - **Linear** - Modern issue tracking system
  - **GitHub Projects** - Native GitHub integration
- **AI Analysis Engine** (`ai_analysis_engine.py`) - AI-powered board analysis
- **NLP Tools** (`nlp_base.py`, `nlp_tools.py`, `nlp_task_utils.py`) - Natural language processing
- **Pipeline Tracked NLP** (`pipeline_tracked_nlp.py`) - NLP with pipeline tracking

### 5. Visualization & UI Systems (`src/visualization/`)
Real-time project visualization and monitoring:
- **Event-Integrated Visualizer** (`event_integrated_visualizer.py`) - Real-time project visualization
- **Pipeline Flow Management** (`pipeline_flow.py`, `pipeline_manager.py`) - Stage-based workflow visualization
- **Pipeline Replay** (`pipeline_replay.py`) - Historical execution replay
- **Conversation Adapter** (`conversation_adapter.py`) - Conversation visualization
- **Pipeline Conversation Bridge** (`pipeline_conversation_bridge.py`) - Links conversations to pipeline stages
- **Shared Pipeline Events** (`shared_pipeline_events.py`) - WebSocket event distribution
- **WebSocket Event Distribution** - Live updates to UI

### 6. MCP (Model Context Protocol) Server (`src/marcus_mcp/`)
Full MCP implementation for AI agent integration:
- **Server Implementation** (`server.py`) - Main MCP server
- **Client** (`client.py`) - MCP client implementation
- **Handlers** (`handlers.py`, `handlers_fixed.py`) - Request handlers
- **Tools** (`tools/`) - Organized by domain:
  - Agent management tools
  - Context tools
  - NLP (Natural Language Processing) tools
  - Pipeline tools
  - Project management tools
  - System tools
  - Task management tools
- Tool registration and routing
- Agent-specific server capabilities

### 7. AI Intelligence Engine (`src/ai/`)
Hybrid intelligence system combining rules and AI:
- **AI Engine** (`core/ai_engine.py`) - Hybrid rule-based and AI intelligence coordination
- **Providers** (`providers/`) - Multi-provider support (Anthropic Claude, OpenAI)
- **Learning Systems** (`learning/`) - Contextual learner for pattern recognition
- **Advanced Features** (`advanced/`):
  - Multi-project support
  - PRD (Product Requirements Document) parsing
  - Prediction capabilities
  - Adaptation systems
- **Enrichment** (`enrichment/`) - Intelligent task enrichment
- **Decision Framework** (`decisions/`) - Hybrid decision-making framework
- **Task Enrichment** - AI-powered task enhancement

### 8. Error Framework (`src/core/error_framework.py`)
Comprehensive error handling and resilience:
- **Error Framework** (`error_framework.py`) - Base error classes and context
- **Error Strategies** (`error_strategies.py`) - Retry, circuit breaker patterns
- **Error Monitoring** (`error_monitoring.py`) - Pattern detection and tracking
- **Error Responses** (`error_responses.py`) - Standardized response formats
- Rich error taxonomy with context
- Resilience patterns (retry, circuit breaker, fallback)
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

### 22. Operational Modes (`src/modes/`)
Flexible operational configurations:
- **Creator Mode** (`creator/`) - Empty board project creation
- **Enricher Mode** (`enricher/`) - Enhance existing boards
- **Adaptive Mode** (`adaptive/`) - Add features to existing projects
- **Mode Registry** (`src/orchestration/mode_registry.py`) - Mode management
- **Hybrid Tools** (`src/orchestration/hybrid_tools.py`) - Tool orchestration

### 23. Task Management & Intelligence (`src/intelligence/`)
AI-powered task creation and management:
- **Intelligent Task Generator** (`intelligent_task_generator.py`) - AI-powered task creation
- **PRD Parser** (`prd_parser.py`) - Requirements document analysis
- **Dependency Inference** (`dependency_inferer.py`, `dependency_inferer_hybrid.py`) - Smart dependency detection

### 24. Analysis Tools (`src/analysis/`)
Advanced analysis and reporting:
- **Pipeline Comparison** (`pipeline_comparison.py`) - Compare multiple pipeline runs
- **What-If Engine** (`what_if_engine.py`) - Scenario analysis

### 25. Report Generation (`src/reports/`)
Comprehensive reporting system:
- **Pipeline Report Generator** (`pipeline_report_generator.py`) - Generate detailed reports
- **Templates** (`templates/`) - Report templates (HTML, Markdown)

### 26. Worker Support (`src/worker/`)
Client libraries for worker agents:
- **Worker Client** (`client.py`) - Client library for worker agents

### 27. Recommendation Engine (`src/recommendations/`)
AI-powered optimization:
- **Recommendation Engine** (`recommendation_engine.py`) - AI-powered optimization suggestions

### 28. Configuration Management (`src/config/`)
Application configuration:
- **Config Loader** (`config_loader.py`) - Configuration management
- **Settings** (`settings.py`) - Application settings
- **Hybrid Inference Config** (`hybrid_inference_config.py`) - AI configuration

### 29. Detection Systems (`src/detection/`)
State and context detection:
- **Board Analyzer** (`board_analyzer.py`) - Board state analysis
- **Context Detector** (`context_detector.py`) - Context detection

### 30. Testing Framework (`tests/`)
Comprehensive testing infrastructure:
- **Unit Tests** (`unit/`) - Isolated component testing
- **Integration Tests** (`integration/`) - End-to-end testing
- **Performance Tests** (`performance/`) - Load and benchmark testing
- **Future Features** (`future_features/`) - TDD for upcoming features

### 31. Resilience (`src/core/resilience.py`)
Fault-tolerant patterns:
- Fault-tolerant decorators and patterns
- Recovery strategies
- System resilience

### 32. Models (`src/core/models.py`)
Fundamental data structures:
- Task, TaskStatus, Priority, RiskLevel
- WorkerStatus, TaskAssignment, ProjectState
- Core domain models


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
