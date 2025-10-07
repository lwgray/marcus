# Architecture Diagrams - Task Management System

## 1. System Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                         CLIENT APPLICATIONS                          │
│                                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │   Web App   │  │ Mobile App  │  │     CLI     │  │  Third-    │ │
│  │  (React)    │  │(iOS/Android)│  │   Client    │  │   Party    │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────┬──────┘ │
│         │                │                │               │        │
└─────────┼────────────────┼────────────────┼───────────────┼────────┘
          │                │                │               │
          │                └────────────────┼───────────────┘
          │                                 │
          └─────────────────────────────────┘
                          │
                          │ HTTPS/JSON
                          │
┌─────────────────────────▼─────────────────────────────────────────────┐
│                         API GATEWAY / LOAD BALANCER                   │
│                                                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │ Rate Limiter │  │ Auth Checker │  │ Request Log  │               │
│  └──────────────┘  └──────────────┘  └──────────────┘               │
└─────────────────────────┬──────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
┌─────────▼──────┐ ┌──────▼──────┐ ┌─────▼────────┐
│   API Server   │ │ API Server  │ │ API Server   │
│   Instance 1   │ │ Instance 2  │ │ Instance 3   │
└────────┬───────┘ └──────┬──────┘ └─────┬────────┘
         │                │              │
         └────────────────┼──────────────┘
                          │
    ┌─────────────────────┼─────────────────────┐
    │                     │                     │
┌───▼────────────┐  ┌─────▼──────────┐  ┌──────▼─────────┐
│   PostgreSQL   │  │     Redis      │  │  Background    │
│   (Primary)    │  │    (Cache)     │  │  Job Queue     │
│                │  │                │  │   (Celery)     │
└───┬────────────┘  └────────────────┘  └────────────────┘
    │
┌───▼────────────┐
│   PostgreSQL   │
│   (Replica)    │
│   (Read-Only)  │
└────────────────┘
```

## 2. Application Layer Architecture

```
┌────────────────────────────────────────────────────────────┐
│                   APPLICATION LAYERS                        │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              API LAYER (FastAPI/Express)              │  │
│  │                                                        │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌────────────────┐ │  │
│  │  │   Routes    │ │ Middleware  │ │   Error        │ │  │
│  │  │             │ │             │ │   Handlers     │ │  │
│  │  │ - /tasks    │ │ - Auth      │ │                │ │  │
│  │  │ - /projects │ │ - CORS      │ │ - Validation   │ │  │
│  │  │ - /users    │ │ - Logging   │ │ - Not Found    │ │  │
│  │  │ - /webhooks │ │ - Metrics   │ │ - Server Error │ │  │
│  │  └──────┬──────┘ └─────────────┘ └────────────────┘ │  │
│  └─────────┼──────────────────────────────────────────┘  │
│            │                                              │
│  ┌─────────▼──────────────────────────────────────────┐  │
│  │              BUSINESS LOGIC LAYER                   │  │
│  │                                                      │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌──────────────┐ │  │
│  │  │   Task      │ │   Project   │ │   User       │ │  │
│  │  │   Service   │ │   Service   │ │   Service    │ │  │
│  │  │             │ │             │ │              │ │  │
│  │  │ - create()  │ │ - create()  │ │ - register() │ │  │
│  │  │ - update()  │ │ - update()  │ │ - login()    │ │  │
│  │  │ - delete()  │ │ - delete()  │ │ - logout()   │ │  │
│  │  │ - list()    │ │ - list()    │ │ - profile()  │ │  │
│  │  └──────┬──────┘ └──────┬──────┘ └──────┬───────┘ │  │
│  └─────────┼────────────────┼────────────────┼────────┘  │
│            │                │                │           │
│  ┌─────────▼────────────────▼────────────────▼────────┐  │
│  │              DATA ACCESS LAYER                      │  │
│  │                                                      │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌──────────────┐ │  │
│  │  │   Task      │ │   Project   │ │   User       │ │  │
│  │  │  Repository │ │  Repository │ │  Repository  │ │  │
│  │  │             │ │             │ │              │ │  │
│  │  │ - findById()│ │ - findById()│ │ - findById() │ │  │
│  │  │ - findAll() │ │ - findAll() │ │ - findByEmail│ │  │
│  │  │ - save()    │ │ - save()    │ │ - save()     │ │  │
│  │  │ - delete()  │ │ - delete()  │ │ - delete()   │ │  │
│  │  └──────┬──────┘ └──────┬──────┘ └──────┬───────┘ │  │
│  └─────────┼────────────────┼────────────────┼────────┘  │
│            │                │                │           │
│  ┌─────────▼────────────────▼────────────────▼────────┐  │
│  │              DATABASE MODELS (ORM)                  │  │
│  │                                                      │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌──────────────┐ │  │
│  │  │    Task     │ │   Project   │ │    User      │ │  │
│  │  │    Model    │ │    Model    │ │    Model     │ │  │
│  │  └─────────────┘ └─────────────┘ └──────────────┘ │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

## 3. Request Flow Diagram

```
┌──────────┐
│  Client  │
└────┬─────┘
     │
     │ 1. POST /tasks
     │    Authorization: Bearer <token>
     │    { title, description, priority }
     │
┌────▼─────────────────┐
│   API Gateway        │
│                      │
│ 2. Check Rate Limit  │
│ 3. Validate Token    │
└────┬─────────────────┘
     │
     │ 4. Forward Request
     │
┌────▼─────────────────┐
│   API Server         │
│   (Task Route)       │
│                      │
│ 5. Parse Request     │
│ 6. Validate Schema   │
└────┬─────────────────┘
     │
     │ 7. Call Service
     │
┌────▼─────────────────┐
│   Task Service       │
│                      │
│ 8. Business Logic    │
│    - Validate data   │
│    - Check due date  │
│    - Set defaults    │
└────┬─────────────────┘
     │
     │ 9. Call Repository
     │
┌────▼─────────────────┐
│  Task Repository     │
│                      │
│ 10. Build SQL Query  │
│ 11. Execute Insert   │
└────┬─────────────────┘
     │
     │ 12. INSERT INTO tasks...
     │
┌────▼─────────────────┐
│   PostgreSQL         │
│                      │
│ 13. Store Record     │
│ 14. Return ID        │
└────┬─────────────────┘
     │
     │ 15. Return Task Object
     │
┌────▼─────────────────┐
│  Task Repository     │
└────┬─────────────────┘
     │
     │ 16. Return Task
     │
┌────▼─────────────────┐
│   Task Service       │
│                      │
│ 17. Schedule         │
│     Reminder (async) │
└────┬─────────────────┘
     │
     │ 18. Return Task
     │
┌────▼─────────────────┐
│   API Server         │
│                      │
│ 19. Format Response  │
└────┬─────────────────┘
     │
     │ 20. 201 Created
     │     { success: true, data: { id, title, ... }}
     │
┌────▼─────┐
│  Client  │
└──────────┘
```

## 4. Data Model Relationships

```
┌─────────────────────┐
│       User          │
│─────────────────────│
│ id (PK)             │
│ email (UNIQUE)      │
│ name                │
│ created_at          │
│ updated_at          │
└──────────┬──────────┘
           │
           │ 1
           │
           │ owns
           │
           │ N
     ┌─────▼──────┐
     │            │
┌────▼─────────┐  │  ┌─────────────────────┐
│   Project    │  │  │       Task          │
│──────────────│  │  │─────────────────────│
│ id (PK)      │  │  │ id (PK)             │
│ name         │  │  │ title               │
│ description  │  └──┤ description         │
│ user_id (FK) │  N  │ due_date            │
│ created_at   │─────┤ priority (ENUM)     │
│ updated_at   │     │ status (ENUM)       │
└──────────────┘     │ tags (ARRAY)        │
                     │ created_at          │
                     │ updated_at          │
                     │ completed_at        │
                     │ user_id (FK)        │
                     │ project_id (FK)     │
                     └─────────────────────┘

Relationships:
- User has many Projects (1:N)
- User has many Tasks (1:N)
- Project has many Tasks (1:N)
- Task belongs to one User (N:1)
- Task belongs to zero or one Project (N:0..1)
```

## 5. Authentication Flow

```
┌──────────┐
│  Client  │
└────┬─────┘
     │
     │ 1. POST /auth/login
     │    { email, password }
     │
┌────▼─────────────────┐
│   Auth Endpoint      │
│                      │
│ 2. Validate Schema   │
└────┬─────────────────┘
     │
     │ 3. Call Auth Service
     │
┌────▼─────────────────┐
│   Auth Service       │
│                      │
│ 4. Find User by      │
│    Email             │
└────┬─────────────────┘
     │
     │ 5. Query User
     │
┌────▼─────────────────┐
│   User Repository    │
│                      │
│ 6. SELECT * FROM     │
│    users WHERE       │
│    email = ?         │
└────┬─────────────────┘
     │
     │ 7. Return User
     │
┌────▼─────────────────┐
│   Auth Service       │
│                      │
│ 8. Verify Password   │
│    (bcrypt)          │
│                      │
│ 9. Generate JWT      │
│    Token             │
│    - user_id         │
│    - exp: 24h        │
└────┬─────────────────┘
     │
     │ 10. Return Token
     │
┌────▼─────────────────┐
│   Auth Endpoint      │
│                      │
│ 11. Format Response  │
└────┬─────────────────┘
     │
     │ 12. 200 OK
     │     { token, user }
     │
┌────▼─────┐
│  Client  │
│          │
│ 13. Store│
│    Token │
│    (localStorage)
│          │
│ 14. Include in
│     subsequent
│     requests:
│     Authorization:
│     Bearer <token>
└──────────┘
```

## 6. Caching Strategy

```
┌──────────────────────────────────────────────────────┐
│              CACHING ARCHITECTURE                     │
└──────────────────────────────────────────────────────┘

GET Request Flow:

┌──────────┐
│  Client  │
└────┬─────┘
     │
     │ GET /tasks/123
     │
┌────▼─────────────────┐
│   API Server         │
└────┬─────────────────┘
     │
     │ Check Cache
     │
┌────▼─────────────────┐      ┌─────────────────────┐
│   Cache Layer        │──────│   Redis Cache       │
│   (Service)          │ Hit  │                     │
│                      │◄─────│ Key: task:123:u456  │
│ 1. Check Redis       │      │ Value: {task JSON}  │
│    key: task:123:u456│      │ TTL: 300 seconds    │
└────┬─────────────────┘      └─────────────────────┘
     │
     │ Cache Miss
     │
┌────▼─────────────────┐
│   Database Query     │
│                      │
│ 2. SELECT * FROM     │
│    tasks WHERE       │
│    id = 123          │
└────┬─────────────────┘
     │
     │ 3. Task Data
     │
┌────▼─────────────────┐
│   Cache Layer        │      ┌─────────────────────┐
│                      │──────│   Redis Cache       │
│ 4. Store in Redis    │Store │                     │
│    TTL: 5 minutes    │─────►│ SET task:123:u456   │
└────┬─────────────────┘      │ EX 300              │
     │                        └─────────────────────┘
     │ 5. Return Data
     │
┌────▼─────────────────┐
│   API Server         │
└────┬─────────────────┘
     │
     │ 6. JSON Response
     │
┌────▼─────┐
│  Client  │
└──────────┘

Cache Invalidation:

PUT /tasks/123
     │
     ▼
┌─────────────┐
│ Update Task │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│ Delete Cache Entry  │──► Redis: DEL task:123:u456
└─────────────────────┘

Cache Keys Pattern:
- task:{task_id}:{user_id}
- user:{user_id}:tasks:page:{page}
- project:{project_id}:tasks
```

## 7. Background Job Processing

```
┌──────────────────────────────────────────────────────┐
│           BACKGROUND JOB ARCHITECTURE                 │
└──────────────────────────────────────────────────────┘

                    ┌──────────────┐
                    │  API Server  │
                    └──────┬───────┘
                           │
                           │ 1. Task Created
                           │    Schedule Reminder
                           │
                    ┌──────▼───────┐
                    │  Job Queue   │
                    │   (Celery)   │
                    │              │
                    │ ┌──────────┐ │
                    │ │ Task ID  │ │
                    │ │ Job Type │ │
                    │ │ Payload  │ │
                    │ └──────────┘ │
                    └──────┬───────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
  ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐
  │   Worker 1  │   │   Worker 2  │   │   Worker 3  │
  │             │   │             │   │             │
  │ 2. Pick Job │   │ 2. Pick Job │   │ 2. Pick Job │
  │             │   │             │   │             │
  │ 3. Process  │   │ 3. Process  │   │ 3. Process  │
  │    Job      │   │    Job      │   │    Job      │
  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘
         │                 │                 │
         └─────────────────┼─────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
  ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐
  │   Email     │   │  Webhook    │   │  Analytics  │
  │   Service   │   │  Service    │   │  Service    │
  └─────────────┘   └─────────────┘   └─────────────┘

Job Types:
1. send_reminder - Send task due date reminders
2. send_webhook - Trigger webhook notifications
3. cleanup_tasks - Archive old completed tasks
4. generate_report - Create productivity reports
5. sync_calendar - Sync with external calendars
```

## 8. Deployment Architecture

```
┌────────────────────────────────────────────────────────┐
│                    PRODUCTION DEPLOYMENT                │
└────────────────────────────────────────────────────────┘

                      ┌──────────────┐
                      │   Internet   │
                      └──────┬───────┘
                             │
                             │ HTTPS
                             │
                      ┌──────▼───────┐
                      │     CDN      │
                      │  (CloudFlare)│
                      └──────┬───────┘
                             │
                      ┌──────▼───────────────┐
                      │   Load Balancer      │
                      │   (AWS ALB/Nginx)    │
                      │                      │
                      │ - SSL Termination    │
                      │ - Health Checks      │
                      │ - Request Distribution
                      └──────┬───────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼────────┐  ┌────────▼────────┐  ┌───────▼────────┐
│   API Server   │  │   API Server    │  │   API Server   │
│   Container 1  │  │   Container 2   │  │   Container 3  │
│                │  │                 │  │                │
│   Docker       │  │   Docker        │  │   Docker       │
│   - FastAPI    │  │   - FastAPI     │  │   - FastAPI    │
│   - Python 3.11│  │   - Python 3.11 │  │   - Python 3.11│
└───────┬────────┘  └────────┬────────┘  └───────┬────────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼────────┐  ┌────────▼────────┐  ┌───────▼────────┐
│   PostgreSQL   │  │     Redis       │  │   Celery       │
│   Primary      │  │     Cache       │  │   Workers      │
│                │  │                 │  │                │
│   RDS/Managed  │  │   ElastiCache   │  │   ECS Tasks    │
└───────┬────────┘  └─────────────────┘  └────────────────┘
        │
┌───────▼────────┐
│   PostgreSQL   │
│   Replica      │
│   (Read-Only)  │
│                │
│   RDS/Managed  │
└────────────────┘

Monitoring & Logging:
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   Prometheus    │  │   Grafana       │  │   ELK Stack     │
│   (Metrics)     │  │   (Dashboards)  │  │   (Logs)        │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

## 9. Security Architecture

```
┌──────────────────────────────────────────────────────┐
│              SECURITY LAYERS                          │
└──────────────────────────────────────────────────────┘

Layer 1: Network Security
┌────────────────────────────────────────┐
│ - HTTPS Only (TLS 1.3)                 │
│ - WAF (Web Application Firewall)       │
│ - DDoS Protection                      │
│ - IP Whitelisting (Admin)              │
└────────────────────────────────────────┘
                  ▼
Layer 2: API Gateway Security
┌────────────────────────────────────────┐
│ - Rate Limiting (100 req/min)          │
│ - Request Size Limits                  │
│ - API Key Validation                   │
│ - CORS Configuration                   │
└────────────────────────────────────────┘
                  ▼
Layer 3: Authentication & Authorization
┌────────────────────────────────────────┐
│ - JWT Token Validation                 │
│ - Token Expiration Check               │
│ - User Identity Verification           │
│ - Role-Based Access Control            │
└────────────────────────────────────────┘
                  ▼
Layer 4: Input Validation
┌────────────────────────────────────────┐
│ - Schema Validation (Pydantic)         │
│ - SQL Injection Prevention             │
│ - XSS Protection                       │
│ - Input Sanitization                   │
└────────────────────────────────────────┘
                  ▼
Layer 5: Data Access Security
┌────────────────────────────────────────┐
│ - Parameterized Queries                │
│ - Row-Level Security                   │
│ - User Ownership Checks                │
│ - Audit Logging                        │
└────────────────────────────────────────┘
                  ▼
Layer 6: Data Storage Security
┌────────────────────────────────────────┐
│ - Encryption at Rest (AES-256)         │
│ - Encryption in Transit (TLS)          │
│ - Backup Encryption                    │
│ - Password Hashing (bcrypt)            │
└────────────────────────────────────────┘
```

## 10. Monitoring Dashboard Layout

```
┌──────────────────────────────────────────────────────────┐
│         TASK MANAGEMENT - SYSTEM DASHBOARD               │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  System Health:  ● Running    Uptime: 99.95%            │
│                                                          │
├─────────────────────┬────────────────────────────────────┤
│   API Metrics       │    Database Metrics                │
├─────────────────────┼────────────────────────────────────┤
│                     │                                    │
│  Requests/sec: 450  │    Connections: 45/100             │
│  Avg Response: 85ms │    Query Time: 12ms                │
│  Error Rate: 0.2%   │    Cache Hit: 87%                  │
│  P95 Latency: 120ms │    Disk Usage: 45%                 │
│                     │                                    │
│  ┌────────────────┐ │    ┌──────────────────┐          │
│  │ Request Rate   │ │    │ DB Performance   │          │
│  │                │ │    │                  │          │
│  │     /\    /\   │ │    │  ──────────      │          │
│  │    /  \  /  \  │ │    │        ──        │          │
│  │___/____\/____\_│ │    │___________───────│          │
│  └────────────────┘ │    └──────────────────┘          │
│                     │                                    │
├─────────────────────┴────────────────────────────────────┤
│   Business Metrics                                       │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Active Users: 1,234       Tasks Created Today: 5,678   │
│  Tasks Completed: 3,456    Avg Completion Time: 2.3d    │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Task Creation Trend                               │  │
│  │                                         /\        │  │
│  │                                   /\   /  \       │  │
│  │                              /\  /  \_/    \      │  │
│  │  ___________________________/  \/          \___  │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
├──────────────────────────────────────────────────────────┤
│   Alerts & Notifications                                 │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ⚠ High memory usage on API-Server-2 (85%)              │
│  ✓ Backup completed successfully                         │
│  ℹ Scheduled maintenance in 2 days                       │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

**Document Version**: 1.0
**Last Updated**: October 6, 2025
**Author**: Time Agent 3
**Purpose**: Visual reference for system architecture and design decisions
