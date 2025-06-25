# Marcus System Architecture

## Complete System Overview

```{mermaid}
graph TB
    subgraph "Worker Agents Layer"
        WA1[Worker Agent 1<br/>Skills: Python, API]
        WA2[Worker Agent 2<br/>Skills: React, UI]
        WA3[Worker Agent N<br/>Skills: Various]
    end

    subgraph "Marcus Core"
        MCP[Marcus MCP Server<br/>Central Coordinator]
        AI[AI Analysis Engine<br/>Claude-powered Intelligence]
        
        subgraph "Core Services"
            TM[Task Manager]
            AM[Agent Manager]
            CM[Communication Manager]
        end
    end

    subgraph "Data Layer"
        subgraph "Kanban Providers"
            PL[Planka<br/>Self-hosted]
            GH[GitHub Projects]
            LN[Linear]
        end
        
        KF[Kanban Factory<br/>Provider Abstraction]
    end

    subgraph "Intelligence Components"
        TA[Task Assignment<br/>Intelligence]
        IG[Instruction<br/>Generator]
        BA[Blocker<br/>Analyzer]
        RA[Risk<br/>Assessor]
    end

    subgraph "Monitoring & Visualization"
        PM[Project Monitor<br/>Health Tracking]
        VD[Visualization Dashboard<br/>Real-time UI]
        CL[Conversation Logger<br/>Decision Tracking]
    end

    subgraph "Communication Channels"
        SL[Slack Integration]
        EM[Email Service]
        KC[Kanban Comments]
    end

    %% Worker Agent Connections
    WA1 -->|MCP Protocol| MCP
    WA2 -->|MCP Protocol| MCP
    WA3 -->|MCP Protocol| MCP

    %% Core Connections
    MCP --> TM
    MCP --> AM
    MCP --> CM
    MCP --> AI

    %% AI Engine Connections
    AI --> TA
    AI --> IG
    AI --> BA
    AI --> RA

    %% Data Layer Connections
    TM --> KF
    KF --> PL
    KF --> GH
    KF --> LN

    %% Monitoring Connections
    MCP --> PM
    MCP --> CL
    PM --> VD
    CL --> VD

    %% Communication Connections
    CM --> SL
    CM --> EM
    CM --> KC

    classDef worker fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef core fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef ai fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef data fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    classDef monitor fill:#fce4ec,stroke:#880e4f,stroke-width:2px

    class WA1,WA2,WA3 worker
    class MCP,TM,AM,CM core
    class AI,TA,IG,BA,RA ai
    class PL,GH,LN,KF data
    class PM,VD,CL,SL,EM,KC monitor
```

## Detailed Component Interactions

### 1. Task Lifecycle Flow

```{mermaid}
sequenceDiagram
    participant W as Worker Agent
    participant P as Marcus
    participant AI as AI Engine
    participant K as Kanban Board
    participant M as Monitor

    Note over W,M: Task Assignment Flow
    W->>P: register_agent(skills, capacity)
    P->>P: Store agent profile
    
    W->>P: request_next_task()
    P->>K: Get available tasks
    K-->>P: Task list
    P->>AI: match_task_to_agent(tasks, agent)
    AI-->>P: Optimal task + confidence
    P->>AI: generate_instructions(task, agent)
    AI-->>P: Detailed instructions
    P->>K: Move task to IN_PROGRESS
    P->>M: Log assignment decision
    P-->>W: Task + Instructions

    Note over W,M: Progress Tracking
    W->>P: report_task_progress(25%)
    P->>K: Update task status
    P->>M: Track progress metric
    
    Note over W,M: Blocker Handling
    W->>P: report_blocker(description)
    P->>AI: analyze_blocker(task, description)
    AI-->>P: Resolution steps
    P->>K: Add blocker comment
    P->>M: Log blocker event
    P-->>W: Suggested resolutions

    Note over W,M: Task Completion
    W->>P: report_task_progress(100%)
    P->>K: Move task to DONE
    P->>M: Update metrics
    P->>P: Update agent stats
```

### 2. AI Engine Decision Flow

```{mermaid}
graph LR
    subgraph "Input Data"
        TD[Task Data<br/>- Name<br/>- Description<br/>- Priority<br/>- Labels]
        AD[Agent Data<br/>- Skills<br/>- Capacity<br/>- History]
        PD[Project Data<br/>- State<br/>- Timeline<br/>- Risks]
    end

    subgraph "AI Processing"
        CP[Claude Prompt<br/>Generation]
        CA[Claude API<br/>Call]
        JP[JSON Response<br/>Parsing]
        FB[Fallback<br/>Logic]
    end

    subgraph "Output"
        DEC[Decision<br/>+ Confidence]
        INS[Instructions<br/>+ Context]
        RES[Resolution<br/>Steps]
    end

    TD --> CP
    AD --> CP
    PD --> CP
    CP --> CA
    CA -->|Success| JP
    CA -->|Failure| FB
    JP --> DEC
    JP --> INS
    JP --> RES
    FB --> DEC
```

### 3. Multi-Provider Kanban Integration

```{mermaid}
graph TD
    subgraph "Marcus"
        KC[Kanban Client<br/>Interface]
    end

    subgraph "Factory Pattern"
        KF[KanbanFactory]
        PC[Provider Config]
    end

    subgraph "Providers"
        subgraph "Planka"
            PM[Planka MCP<br/>Client]
            PA[Planka API]
        end
        
        subgraph "GitHub"
            GC[GitHub<br/>Client]
            GA[GitHub API]
        end
        
        subgraph "Linear"
            LC[Linear<br/>Client]
            LA[Linear API]
        end
    end

    KC --> KF
    PC --> KF
    KF -->|provider=planka| PM
    KF -->|provider=github| GC
    KF -->|provider=linear| LC
    
    PM --> PA
    GC --> GA
    LC --> LA

    style KF fill:#ffeb3b,stroke:#f57f17
```

### 4. Real-time Monitoring System

```{mermaid}
graph TB
    subgraph "Event Sources"
        PE[Marcus<br/>Events]
        KE[Kanban<br/>Changes]
        AE[Agent<br/>Activities]
    end

    subgraph "Event Processing"
        CL[Conversation<br/>Logger]
        EH[Event<br/>Handler]
        MA[Metric<br/>Aggregator]
    end

    subgraph "Storage"
        JL[JSONL<br/>Log Files]
        MS[Memory<br/>Store]
    end

    subgraph "Visualization"
        WS[WebSocket<br/>Server]
        WD[Web<br/>Dashboard]
        subgraph "Views"
            CV[Conversation<br/>View]
            DV[Decision<br/>View]
            KG[Knowledge<br/>Graph]
            MV[Metrics<br/>View]
        end
    end

    PE --> EH
    KE --> EH
    AE --> EH
    
    EH --> CL
    EH --> MA
    
    CL --> JL
    MA --> MS
    
    CL --> WS
    MA --> WS
    
    WS --> WD
    WD --> CV
    WD --> DV
    WD --> KG
    WD --> MV
```

## Key System Characteristics

### 1. **Stateless Architecture**
- No persistent database
- Kanban board is source of truth
- State rebuilt from kanban on restart
- In-memory caching for performance

### 2. **Event-Driven Design**
- All actions trigger events
- Events logged for analysis
- Real-time visualization
- Enables replay and debugging

### 3. **Provider Agnostic**
- Common interface for all kanban providers
- Easy to add new providers
- Configuration-driven selection
- No vendor lock-in

### 4. **AI-Enhanced Decision Making**
- Every decision can be AI-powered
- Graceful fallbacks ensure reliability
- Structured prompts for consistency
- Learning potential from outcomes

### 5. **Security & Isolation**
- Worker agents isolated from Marcus code
- Configurable forbidden paths
- Audit logging of violations
- Workspace sandboxing

### 6. **Observable by Design**
- Every decision logged with rationale
- Real-time metrics and monitoring
- Visual dashboard for insights
- Comprehensive error tracking

## Communication Flow Patterns

### 1. **Synchronous Operations** (Request/Response)
```
Worker Agent <--> Marcus MCP Server <--> Kanban Provider
```

### 2. **Asynchronous Notifications**
```
Marcus --> Communication Hub --> [Slack, Email, Kanban Comments]
```

### 3. **Real-time Monitoring**
```
Marcus --> Event Stream --> WebSocket --> Dashboard
```

### 4. **AI Analysis Pipeline**
```
Marcus --> AI Engine --> Claude API --> Structured Response
```

## Deployment Architecture

### Local Development
```yaml
services:
  planka:       # Kanban board
    ports: 3000
  planka-db:    # PostgreSQL for Planka
    ports: 5432
  pm-agent:     # Marcus Server
    ports: 3100
  viz-server:   # Visualization
    ports: 8080
```

### Production Deployment
```yaml
services:
  pm-agent:
    environment:
      - KANBAN_PROVIDER=github
      - ANTHROPIC_API_KEY=xxx
    deploy:
      replicas: 1
      resources:
        limits:
          memory: 2G
```

## Scalability Considerations

### Current Limitations
1. Single Marcus instance (no clustering)
2. In-memory state (lost on restart)
3. Sequential task processing
4. Limited to one kanban board

### Future Scaling Options
1. **Horizontal Scaling**: Multiple Marcus instances with distributed state
2. **Persistent State**: Add Redis/database for state persistence
3. **Queue-based Processing**: Use message queue for async operations
4. **Multi-board Support**: Manage multiple projects simultaneously

## Integration Points

### 1. **MCP Protocol** (Worker Agents)
- Tools: register_agent, request_next_task, report_progress, report_blocker
- JSON-RPC based communication
- Stateless interactions

### 2. **Kanban APIs**
- RESTful interfaces
- Webhook support (future)
- Real-time updates via polling

### 3. **AI Service**
- Anthropic Claude API
- Structured prompt templates
- JSON response format

### 4. **Monitoring/Observability**
- Prometheus metrics (future)
- OpenTelemetry traces (future)
- Custom event logging

## Security Model

### 1. **Authentication**
- API keys for external services
- No built-in auth (relies on deployment security)

### 2. **Authorization**
- All agents have equal access
- No role-based permissions yet

### 3. **Isolation**
- Workspace isolation for agents
- Forbidden path enforcement
- Audit logging

### 4. **Data Protection**
- No sensitive data in logs
- API keys in environment variables
- TLS for external communications

This architecture enables Marcus to effectively coordinate multiple AI agents on complex software projects while maintaining flexibility, observability, and reliability.