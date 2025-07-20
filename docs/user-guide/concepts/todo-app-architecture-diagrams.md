# Todo Management Application - Architecture Diagrams

## System Architecture Overview

### High-Level System Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        WEB[Web Browser]
        MOBILE[Mobile App]
        CLI[CLI Tool]
    end

    subgraph "API Gateway"
        GATEWAY[API Gateway<br/>Authentication/Rate Limiting]
    end

    subgraph "Application Layer"
        API[Todo API Service<br/>FastAPI]
        WS[WebSocket Service<br/>Real-time Updates]
        WORKER[Background Workers<br/>Celery]
    end

    subgraph "Integration Layer"
        MARCUS[Marcus Integration<br/>MCP Client]
        NOTIF[Notification Service]
    end

    subgraph "Data Layer"
        DB[(PostgreSQL<br/>Primary Database)]
        REDIS[(Redis<br/>Cache & Queue)]
        S3[S3/MinIO<br/>File Storage]
    end

    WEB --> GATEWAY
    MOBILE --> GATEWAY
    CLI --> GATEWAY

    GATEWAY --> API
    GATEWAY --> WS

    API --> DB
    API --> REDIS
    API --> S3
    API --> MARCUS
    API --> WORKER

    WS --> REDIS
    WORKER --> DB
    WORKER --> NOTIF
    WORKER --> MARCUS

    MARCUS --> |MCP Protocol| MARCUSCORE[Marcus Core]
```

### Component Architecture

```mermaid
graph LR
    subgraph "Frontend Components"
        UI[UI Layer]
        STATE[State Management]
        API_CLIENT[API Client]
        WS_CLIENT[WebSocket Client]
    end

    subgraph "Backend Services"
        ROUTES[API Routes]
        BIZ[Business Logic]
        DAL[Data Access Layer]
        EVENTS[Event System]
    end

    subgraph "Shared"
        MODELS[Data Models]
        VALIDATORS[Validators]
        UTILS[Utilities]
    end

    UI --> STATE
    STATE --> API_CLIENT
    STATE --> WS_CLIENT

    API_CLIENT --> ROUTES
    WS_CLIENT --> EVENTS

    ROUTES --> BIZ
    BIZ --> DAL
    BIZ --> EVENTS

    DAL --> MODELS
    ROUTES --> VALIDATORS
    BIZ --> UTILS
```

## Data Flow Diagrams

### Todo Creation Flow

```mermaid
sequenceDiagram
    participant User
    participant UI
    participant API
    participant DB
    participant Cache
    participant WS
    participant Marcus

    User->>UI: Enter todo details
    UI->>UI: Validate input
    UI->>API: POST /todos
    API->>API: Validate request
    API->>DB: Insert todo
    DB-->>API: Todo created
    API->>Cache: Invalidate cache
    API->>WS: Publish todo.created
    API-->>UI: Return todo
    UI->>UI: Update state

    opt Marcus Integration Enabled
        API->>Marcus: Create task
        Marcus-->>API: Task ID
        API->>DB: Update sync info
    end

    WS-->>UI: Real-time update
    UI->>User: Show success
```

### Todo Update Flow

```mermaid
sequenceDiagram
    participant User
    participant UI
    participant API
    participant DB
    participant Cache
    participant Events
    participant Marcus

    User->>UI: Update todo
    UI->>API: PATCH /todos/{id}
    API->>Cache: Check cache

    alt Cache Hit
        Cache-->>API: Todo data
    else Cache Miss
        API->>DB: Get todo
        DB-->>API: Todo data
        API->>Cache: Store in cache
    end

    API->>API: Validate ownership
    API->>API: Apply updates
    API->>DB: Update todo
    DB-->>API: Updated
    API->>Cache: Update cache
    API->>Events: Emit todo.updated

    opt Status Changed to Completed
        API->>API: Set completed_at
        API->>Events: Emit todo.completed
        opt Marcus Sync Enabled
            API->>Marcus: Update task status
        end
    end

    API-->>UI: Updated todo
    Events-->>UI: Real-time update
```

### Bulk Operations Flow

```mermaid
flowchart TB
    START[Bulk Request] --> VALIDATE{Validate<br/>Request}
    VALIDATE -->|Invalid| ERROR[Return Error]
    VALIDATE -->|Valid| BATCH[Create Batches]

    BATCH --> PROCESS[Process Batch]
    PROCESS --> CHECK{More<br/>Batches?}
    CHECK -->|Yes| PROCESS
    CHECK -->|No| AGGREGATE[Aggregate Results]

    subgraph "Process Batch"
        TRANS[Start Transaction]
        TRANS --> LOOP[For Each Todo]
        LOOP --> UPDATE[Update Todo]
        UPDATE --> LOG[Log Result]
        LOG --> NEXT{Next Todo?}
        NEXT -->|Yes| UPDATE
        NEXT -->|No| COMMIT[Commit]
    end

    AGGREGATE --> RESPONSE[Return Summary]
```

## Database Schema Diagram

```mermaid
erDiagram
    USERS ||--o{ TODOS : creates
    USERS ||--o{ CATEGORIES : owns
    USERS ||--o{ COMMENTS : writes
    USERS ||--o{ ATTACHMENTS : uploads

    TODOS ||--o{ TODO_CATEGORIES : has
    CATEGORIES ||--o{ TODO_CATEGORIES : contains

    TODOS ||--o{ TODO_TAGS : has
    TAGS ||--o{ TODO_TAGS : labels

    TODOS ||--o{ COMMENTS : has
    TODOS ||--o{ ATTACHMENTS : has
    TODOS ||--o| MARCUS_TODO_SYNC : syncs

    USERS {
        uuid id PK
        string email UK
        string name
        string password_hash
        boolean is_active
        boolean is_verified
        timestamp created_at
        timestamp updated_at
        timestamp last_login
    }

    TODOS {
        uuid id PK
        uuid user_id FK
        string title
        text description
        string status
        string priority
        timestamp due_date
        timestamp completed_at
        boolean is_deleted
        timestamp created_at
        timestamp updated_at
    }

    CATEGORIES {
        uuid id PK
        uuid user_id FK
        string name
        string color
        string description
        timestamp created_at
        timestamp updated_at
    }

    TODO_CATEGORIES {
        uuid todo_id FK
        uuid category_id FK
    }

    TAGS {
        uuid id PK
        string name UK
        timestamp created_at
    }

    TODO_TAGS {
        uuid todo_id FK
        uuid tag_id FK
    }

    COMMENTS {
        uuid id PK
        uuid todo_id FK
        uuid user_id FK
        text content
        boolean edited
        timestamp created_at
        timestamp updated_at
    }

    ATTACHMENTS {
        uuid id PK
        uuid todo_id FK
        uuid user_id FK
        string filename
        integer file_size
        string mime_type
        string storage_path
        timestamp created_at
    }

    MARCUS_TODO_SYNC {
        uuid todo_id PK
        string marcus_task_id
        uuid marcus_project_id
        boolean sync_enabled
        timestamp last_synced
        timestamp created_at
        timestamp updated_at
    }
```

## State Management Diagram

```mermaid
stateDiagram-v2
    [*] --> Pending: Create Todo

    Pending --> InProgress: Start Work
    Pending --> Cancelled: Cancel

    InProgress --> Completed: Complete
    InProgress --> Blocked: Block
    InProgress --> Cancelled: Cancel

    Blocked --> InProgress: Unblock
    Blocked --> Cancelled: Cancel

    Completed --> [*]
    Cancelled --> [*]

    note right of Completed
        Terminal state
        Sets completed_at
    end note

    note right of Blocked
        Can add blocker reason
        Notifies assignee
    end note
```

## Authentication Flow

```mermaid
sequenceDiagram
    participant User
    participant Client
    participant API
    participant Auth
    participant DB
    participant Redis

    User->>Client: Login credentials
    Client->>API: POST /auth/login
    API->>Auth: Validate credentials
    Auth->>DB: Check user
    DB-->>Auth: User data
    Auth->>Auth: Verify password

    alt Valid Credentials
        Auth->>Auth: Generate JWT
        Auth->>Redis: Store refresh token
        Auth-->>API: Tokens
        API-->>Client: Access & Refresh tokens
        Client->>Client: Store tokens
        Client->>User: Login success
    else Invalid Credentials
        Auth-->>API: Unauthorized
        API-->>Client: 401 Error
        Client->>User: Login failed
    end

    note over Client: Subsequent requests

    Client->>API: Request + Bearer token
    API->>Auth: Validate JWT

    alt Valid Token
        Auth-->>API: User context
        API->>API: Process request
        API-->>Client: Response
    else Expired Token
        API-->>Client: 401 Token expired
        Client->>API: POST /auth/refresh
        API->>Redis: Validate refresh token
        Redis-->>API: Valid
        API->>Auth: Generate new JWT
        Auth-->>API: New access token
        API-->>Client: New token
        Client->>API: Retry request
    end
```

## Marcus Integration Architecture

```mermaid
graph TB
    subgraph "Todo Application"
        TODO_API[Todo API]
        SYNC[Sync Service]
        QUEUE[Task Queue]
    end

    subgraph "Marcus MCP Server"
        MCP[MCP Endpoint]
        PM[Project Manager]
        KB[Kanban Interface]
    end

    subgraph "Kanban Providers"
        PLANKA[Planka]
        LINEAR[Linear]
        GITHUB[GitHub Projects]
    end

    TODO_API -->|Create Task| QUEUE
    QUEUE -->|Process| SYNC
    SYNC -->|MCP Protocol| MCP

    MCP --> PM
    PM --> KB

    KB --> PLANKA
    KB --> LINEAR
    KB --> GITHUB

    SYNC -->|Status Updates| TODO_API
    MCP -->|Task Updates| SYNC
```

## Deployment Architecture

### Development Environment

```mermaid
graph TB
    subgraph "Developer Machine"
        subgraph "Docker Compose"
            FRONTEND[Frontend<br/>React Dev Server<br/>:3000]
            BACKEND[Backend<br/>FastAPI<br/>:8000]
            DB[PostgreSQL<br/>:5432]
            REDIS[Redis<br/>:6379]
            MINIO[MinIO<br/>:9000]
        end

        subgraph "Marcus"
            MARCUS_LOCAL[Marcus MCP<br/>Local Server]
        end
    end

    FRONTEND --> BACKEND
    BACKEND --> DB
    BACKEND --> REDIS
    BACKEND --> MINIO
    BACKEND --> MARCUS_LOCAL
```

### Production Architecture

```mermaid
graph TB
    subgraph "Internet"
        USERS[Users]
        CF[CloudFlare CDN]
    end

    subgraph "AWS VPC"
        subgraph "Public Subnet"
            ALB[Application<br/>Load Balancer]
            NAT[NAT Gateway]
        end

        subgraph "Private Subnet 1"
            subgraph "ECS Cluster"
                FRONT1[Frontend Task]
                FRONT2[Frontend Task]
                API1[API Task]
                API2[API Task]
                WORKER1[Worker Task]
            end
        end

        subgraph "Private Subnet 2"
            subgraph "Data Tier"
                RDS[(RDS PostgreSQL<br/>Multi-AZ)]
                ELASTICACHE[(ElastiCache<br/>Redis Cluster)]
            end
        end

        S3[S3 Bucket<br/>Static Assets]
    end

    subgraph "External"
        MARCUS_PROD[Marcus Production<br/>MCP Server]
    end

    USERS --> CF
    CF --> ALB
    ALB --> FRONT1
    ALB --> FRONT2

    FRONT1 --> API1
    FRONT2 --> API2

    API1 --> RDS
    API2 --> RDS
    API1 --> ELASTICACHE
    API2 --> ELASTICACHE
    API1 --> S3

    WORKER1 --> RDS
    WORKER1 --> ELASTICACHE

    API1 --> NAT
    NAT --> MARCUS_PROD
```

## Performance Optimization Strategy

```mermaid
flowchart LR
    subgraph "Client Optimizations"
        LAZY[Lazy Loading]
        VIRTUAL[Virtual Scrolling]
        CACHE_C[Client Cache]
        OPTIMISTIC[Optimistic Updates]
    end

    subgraph "API Optimizations"
        BATCH[Request Batching]
        COMPRESS[Compression]
        CACHE_S[Server Cache]
        POOL[Connection Pooling]
    end

    subgraph "Database Optimizations"
        INDEX[Indexes]
        PARTITION[Partitioning]
        REPLICAS[Read Replicas]
        PREPARED[Prepared Statements]
    end

    LAZY --> BATCH
    VIRTUAL --> COMPRESS
    CACHE_C --> CACHE_S
    OPTIMISTIC --> POOL

    BATCH --> INDEX
    COMPRESS --> PARTITION
    CACHE_S --> REPLICAS
    POOL --> PREPARED
```

## Monitoring and Observability

```mermaid
graph TB
    subgraph "Application"
        APP[Todo App]
        METRICS[Metrics Collector]
        LOGS[Log Aggregator]
        TRACES[Trace Collector]
    end

    subgraph "Monitoring Stack"
        PROM[Prometheus]
        LOKI[Loki]
        TEMPO[Tempo]
        GRAFANA[Grafana]
    end

    subgraph "Alerting"
        ALERT[Alert Manager]
        PAGER[PagerDuty]
        SLACK[Slack]
    end

    APP --> METRICS
    APP --> LOGS
    APP --> TRACES

    METRICS --> PROM
    LOGS --> LOKI
    TRACES --> TEMPO

    PROM --> GRAFANA
    LOKI --> GRAFANA
    TEMPO --> GRAFANA

    PROM --> ALERT
    ALERT --> PAGER
    ALERT --> SLACK
```

## Security Architecture

```mermaid
graph TB
    subgraph "Security Layers"
        WAF[Web Application Firewall]
        DDOS[DDoS Protection]
        SSL[SSL/TLS Termination]

        subgraph "Application Security"
            AUTH[Authentication]
            AUTHZ[Authorization]
            VALIDATE[Input Validation]
            SANITIZE[Output Sanitization]
        end

        subgraph "Data Security"
            ENCRYPT[Encryption at Rest]
            TRANSIT[Encryption in Transit]
            BACKUP[Secure Backups]
        end
    end

    subgraph "Security Monitoring"
        IDS[Intrusion Detection]
        AUDIT[Audit Logging]
        VULN[Vulnerability Scanning]
    end

    WAF --> SSL
    SSL --> AUTH
    AUTH --> AUTHZ
    AUTHZ --> VALIDATE
    VALIDATE --> SANITIZE

    SANITIZE --> ENCRYPT
    ENCRYPT --> TRANSIT

    IDS --> AUDIT
    AUDIT --> VULN
```

These architectural diagrams provide a comprehensive visual representation of the Todo Management application's design, showing data flows, component interactions, deployment topology, and integration points with the Marcus ecosystem.
