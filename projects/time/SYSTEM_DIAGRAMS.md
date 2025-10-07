# System Architecture Diagrams

This document contains visual representations of the Task Management & Calendar Integration Platform architecture.

## Table of Contents
1. [High-Level System Architecture](#high-level-system-architecture)
2. [Component Interaction Flows](#component-interaction-flows)
3. [Database Entity Relationship Diagram](#database-entity-relationship-diagram)
4. [Calendar Sync Flow](#calendar-sync-flow)
5. [Authentication Flow](#authentication-flow)
6. [Time Tracking Flow](#time-tracking-flow)
7. [Deployment Architecture](#deployment-architecture)

---

## 1. High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            CLIENT TIER                                   │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │  Web Client  │    │Mobile Client │    │  CLI Client  │              │
│  │   (React)    │    │ (React Native│    │   (Python)   │              │
│  │              │    │   iOS/Android)│   │              │              │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘              │
│         │                   │                    │                      │
│         └───────────────────┼────────────────────┘                      │
└─────────────────────────────┼─────────────────────────────────────────┘
                              │
                              │ HTTPS/WSS
                              │
┌─────────────────────────────┼─────────────────────────────────────────┐
│                       API GATEWAY TIER                                  │
│                              │                                          │
│  ┌──────────────────────────┴───────────────────────────┐              │
│  │            Nginx Reverse Proxy                        │              │
│  │  • SSL Termination                                    │              │
│  │  • Rate Limiting (100 req/min per user)               │              │
│  │  • Request Routing                                    │              │
│  │  • Load Balancing                                     │              │
│  │  • CORS Handling                                      │              │
│  └──────────────────────────┬───────────────────────────┘              │
└─────────────────────────────┼─────────────────────────────────────────┘
                              │
                              │
┌─────────────────────────────┼─────────────────────────────────────────┐
│                      APPLICATION TIER                                   │
│         ┌────────────────────┴────────────────────┐                    │
│         │                                          │                    │
│  ┌──────▼──────┐   ┌────────────┐   ┌────────────▼─────┐              │
│  │    Task     │   │  Calendar  │   │   Time Tracking  │              │
│  │   Service   │   │  Service   │   │     Service      │              │
│  │  (FastAPI)  │   │ (FastAPI)  │   │    (FastAPI)     │              │
│  └──────┬──────┘   └─────┬──────┘   └────────┬─────────┘              │
│         │                │                     │                        │
│  ┌──────▼──────┐   ┌────▼──────┐   ┌─────────▼────────┐              │
│  │  Analytics  │   │   Auth    │   │   Notification   │              │
│  │   Service   │   │  Service  │   │     Service      │              │
│  │  (FastAPI)  │   │ (FastAPI) │   │    (FastAPI)     │              │
│  └──────┬──────┘   └────┬──────┘   └─────────┬────────┘              │
│         │                │                     │                        │
│         └────────────────┼─────────────────────┘                        │
└──────────────────────────┼──────────────────────────────────────────────┘
                           │
                           │
┌──────────────────────────┼──────────────────────────────────────────────┐
│                   BACKGROUND WORKERS                                     │
│         ┌─────────────────┴──────────────────┐                          │
│         │                                     │                          │
│  ┌──────▼────────┐   ┌─────────────────┐   ┌▼──────────────┐           │
│  │  Sync Worker  │   │ Analytics Worker│   │ Email Worker  │           │
│  │   (Celery)    │   │    (Celery)     │   │   (Celery)    │           │
│  └───────────────┘   └─────────────────┘   └───────────────┘           │
└──────────────────────────┼──────────────────────────────────────────────┘
                           │
                           │
┌──────────────────────────┼──────────────────────────────────────────────┐
│                       DATA TIER                                          │
│         ┌─────────────────┴──────────────────┐                          │
│         │                                     │                          │
│  ┌──────▼──────────┐   ┌──────────────┐    ┌▼─────────────┐            │
│  │   PostgreSQL    │   │    Redis     │    │  RabbitMQ    │            │
│  │   (Primary DB)  │   │   (Cache +   │    │ (Message     │            │
│  │  • Users        │   │    Queue)    │    │   Broker)    │            │
│  │  • Tasks        │   │              │    │              │            │
│  │  • Time Entries │   │              │    │              │            │
│  │  • Calendar     │   │              │    │              │            │
│  └─────────────────┘   └──────────────┘    └──────────────┘            │
└──────────────────────────┼──────────────────────────────────────────────┘
                           │
                           │
┌──────────────────────────┼──────────────────────────────────────────────┐
│                  EXTERNAL INTEGRATIONS                                   │
│         ┌─────────────────┴──────────────────┐                          │
│         │                                     │                          │
│  ┌──────▼────────┐   ┌──────────────┐   ┌───▼──────────┐               │
│  │    Google     │   │  Microsoft   │   │     iCal     │               │
│  │   Calendar    │   │   Outlook    │   │   (CalDAV)   │               │
│  │     API       │   │  Graph API   │   │              │               │
│  └───────────────┘   └──────────────┘   └──────────────┘               │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Interaction Flows

### 2.1 Task Creation with Calendar Sync Flow

```
┌──────┐                ┌──────┐         ┌──────┐         ┌──────┐         ┌──────┐
│Client│                │ Task │         │ DB   │         │Queue │         │Sync  │
│      │                │Service│        │      │         │      │         │Worker│
└──┬───┘                └──┬───┘         └──┬───┘         └──┬───┘         └──┬───┘
   │                       │                │                │                │
   │ POST /api/v1/tasks    │                │                │                │
   ├──────────────────────►│                │                │                │
   │                       │                │                │                │
   │                       │ Validate input │                │                │
   │                       ├────────────────┤                │                │
   │                       │                │                │                │
   │                       │ INSERT task    │                │                │
   │                       ├───────────────►│                │                │
   │                       │                │                │                │
   │                       │ Task created   │                │                │
   │                       │◄───────────────┤                │                │
   │                       │                │                │                │
   │                       │ Queue sync job │                │                │
   │                       ├────────────────────────────────►│                │
   │                       │                │                │                │
   │ 201 Created (task)    │                │                │                │
   │◄──────────────────────┤                │                │                │
   │                       │                │                │ Process job    │
   │                       │                │                ├───────────────►│
   │                       │                │                │                │
   │                       │                │                │ Create calendar│
   │                       │                │                │    event       │
   │                       │                │                │◄──────────────►│
   │                       │                │                │  (Google API)  │
   │                       │                │                │                │
   │                       │                │   Update task  │                │
   │                       │                │◄───────────────┤                │
   │                       │                │ calendar_event_│                │
   │                       │                │      id        │                │
   └───────────────────────┴────────────────┴────────────────┴────────────────┘
```

### 2.2 Time Tracking Flow

```
┌──────┐         ┌──────┐         ┌──────┐         ┌──────┐
│Client│         │ Time │         │ DB   │         │Analytics│
│      │         │Service│        │      │         │ Worker  │
└──┬───┘         └──┬───┘         └──┬───┘         └──┬───┘
   │                │                │                │
   │ POST /time/start│               │                │
   ├───────────────►│                │                │
   │                │                │                │
   │                │ Check for active│               │
   │                │ entry (user_id)│                │
   │                ├───────────────►│                │
   │                │                │                │
   │                │ No active entry│                │
   │                │◄───────────────┤                │
   │                │                │                │
   │                │ INSERT entry   │                │
   │                │ (start_time=now)│               │
   │                ├───────────────►│                │
   │                │                │                │
   │ 201 Created    │                │                │
   │◄───────────────┤                │                │
   │                │                │                │
   │  ... time passes ...            │                │
   │                │                │                │
   │ POST /time/stop/{id}            │                │
   ├───────────────►│                │                │
   │                │                │                │
   │                │ UPDATE entry   │                │
   │                │ (end_time=now) │                │
   │                ├───────────────►│                │
   │                │                │                │
   │                │ TRIGGER updates│                │
   │                │ task.actual_dur│                │
   │                │◄───────────────┤                │
   │                │                │                │
   │                │ Queue analytics│                │
   │                │   update job   ├───────────────►│
   │                │                │                │
   │ 200 OK (entry) │                │                │
   │◄───────────────┤                │                │
   └────────────────┴────────────────┴────────────────┘
```

---

## 3. Database Entity Relationship Diagram

```
┌─────────────────────────┐
│        USERS            │
│─────────────────────────│
│ PK  id (UUID)           │
│ U   email               │
│ U   username            │
│     password_hash       │
│     full_name           │
│     timezone            │
│     preferences (JSON)  │
│     created_at          │
│     is_active           │
└───────────┬─────────────┘
            │ 1
            │
            │ N
┌───────────▼─────────────┐
│       PROJECTS          │
│─────────────────────────│
│ PK  id (UUID)           │
│ FK  user_id ───────────┐│
│     name               ││
│     description        ││
│     color              ││
│     is_archived        ││
└────────────────────────┘│
            │             │
            │ 1           │
            │             │
            │ N           │
┌───────────▼─────────────┴───────────────────────────┐
│                   TASKS                              │
│──────────────────────────────────────────────────────│
│ PK  id (UUID)                                        │
│ FK  user_id ────────────────────────────────────────┐│
│ FK  project_id                                      ││
│ FK  parent_task_id (self-reference)                 ││
│     title                                           ││
│     description                                     ││
│     status (ENUM)                                   ││
│     priority (ENUM)                                 ││
│     due_date                                        ││
│     estimated_duration                              ││
│     actual_duration (calculated)                    ││
│     calendar_event_id                               ││
│     recurrence_rule                                 ││
│     created_at                                      ││
│     completed_at                                    ││
└───────┬─────────────────────────────────────────────┘│
        │                                              │
        │ N                                            │
        │                                              │
┌───────▼─────────────┐                               │
│     TASK_TAGS       │                               │
│ (Junction Table)    │                               │
│─────────────────────│                               │
│ PK  task_id ────────┤                               │
│ PK  tag_id          │                               │
└─────┬───────────────┘                               │
      │                                                │
      │ N                                              │
      │                                                │
┌─────▼───────────────┐                               │
│        TAGS         │                               │
│─────────────────────│                               │
│ PK  id (UUID)       │                               │
│ FK  user_id ────────┼───────────────────────────────┘
│ U   name (per user) │
│     color           │
└─────────────────────┘

┌─────────────────────────────────────────────┐
│          CALENDAR_CONNECTIONS               │
│─────────────────────────────────────────────│
│ PK  id (UUID)                               │
│ FK  user_id ────────────────────────────────┤
│     provider (ENUM: GOOGLE/MS/ICAL)         │
│     provider_account_id                     │
│     access_token (encrypted)                │
│     refresh_token (encrypted)               │
│     token_expires_at                        │
│     calendar_id                             │
│     sync_enabled                            │
│     last_sync_at                            │
│     sync_status (ENUM)                      │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│           TIME_ENTRIES                      │
│─────────────────────────────────────────────│
│ PK  id (UUID)                               │
│ FK  user_id ────────────────────────────────┤
│ FK  task_id ─────────► TASKS               │
│     start_time                              │
│     end_time                                │
│     duration (calculated)                   │
│     description                             │
│     is_manual                               │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│           NOTIFICATIONS                     │
│─────────────────────────────────────────────│
│ PK  id (UUID)                               │
│ FK  user_id ────────────────────────────────┘
│ FK  related_task_id
│     type (ENUM)
│     channel (ENUM)
│     title
│     message
│     is_read
│     sent_at
└─────────────────────────────────────────────┘
```

**Key Relationships:**
- **User → Tasks**: One-to-Many (one user has many tasks)
- **User → Projects**: One-to-Many (one user has many projects)
- **User → Tags**: One-to-Many (one user has many tags)
- **User → Calendar Connections**: One-to-Many (one user can connect multiple calendars)
- **User → Time Entries**: One-to-Many (one user has many time entries)
- **Project → Tasks**: One-to-Many (one project has many tasks)
- **Task → Time Entries**: One-to-Many (one task can have multiple time entries)
- **Task → Task**: One-to-Many (parent-child relationship for subtasks)
- **Task ↔ Tags**: Many-to-Many (tasks can have multiple tags, tags apply to multiple tasks)

---

## 4. Calendar Sync Flow

### 4.1 Initial Calendar Connection

```
┌──────┐         ┌──────┐         ┌──────┐         ┌──────┐         ┌──────┐
│Client│         │Calendar│       │ OAuth│         │ DB   │         │Google│
│      │         │Service │       │Provider│       │      │         │  API │
└──┬───┘         └──┬───┘         └──┬───┘         └──┬───┘         └──┬───┘
   │                │                │                │                │
   │ POST /calendar/connect          │                │                │
   ├───────────────►│                │                │                │
   │                │                │                │                │
   │                │ Redirect to    │                │                │
   │                │ OAuth consent  │                │                │
   │◄───────────────┤                │                │                │
   │                │                │                │                │
   │ User authorizes│                │                │                │
   ├────────────────┼────────────────►│                │                │
   │                │                │                │                │
   │                │ Authorization  │                │                │
   │                │     code       │                │                │
   │◄───────────────┼────────────────┤                │                │
   │                │                │                │                │
   │ POST code      │                │                │                │
   ├───────────────►│                │                │                │
   │                │                │                │                │
   │                │ Exchange code  │                │                │
   │                │  for tokens    │                │                │
   │                ├────────────────►│                │                │
   │                │                │                │                │
   │                │ Access token + │                │                │
   │                │ Refresh token  │                │                │
   │                │◄───────────────┤                │                │
   │                │                │                │                │
   │                │ Encrypt & save │                │                │
   │                │ tokens         │                │                │
   │                ├───────────────────────────────►│                │
   │                │                │                │                │
   │                │ Set up webhook │                │                │
   │                │ (if supported) │                │                │
   │                ├────────────────────────────────────────────────►│
   │                │                │                │                │
   │                │ Queue initial  │                │                │
   │                │ sync job       │                │                │
   │                ├────────────────┤                │                │
   │                │                │                │                │
   │ 201 Created    │                │                │                │
   │◄───────────────┤                │                │                │
   └────────────────┴────────────────┴────────────────┴────────────────┘
```

### 4.2 Bidirectional Sync Process

```
┌──────────────────────────────────────────────────────────────────────┐
│                      SYNC WORKER PROCESS                             │
└──────────────────────────────────────────────────────────────────────┘

Every 15 minutes OR on webhook trigger:

1. Fetch calendar events from provider
   │
   ├─► Get events modified since last_sync_at
   │
   ├─► For each event:
   │   │
   │   ├─► Does event have task_id in metadata?
   │   │   │
   │   │   YES─► UPDATE existing task
   │   │   │     (title, due_date, description)
   │   │   │     Check for conflicts (compare timestamps)
   │   │   │     If conflict: notify user, apply last-write-wins
   │   │   │
   │   │   NO──► Is event type suitable for task?
   │   │         (not all-day, has time block, etc.)
   │   │         │
   │   │         YES─► CREATE new task
   │   │         │     Link task to event
   │   │         │
   │   │         NO──► Skip
   │
   └─► Update last_sync_at timestamp

2. Fetch tasks modified since last_sync_at
   │
   ├─► For each modified task:
   │   │
   │   ├─► Has calendar_event_id?
   │   │   │
   │   │   YES─► UPDATE calendar event
   │   │   │     (if sync_enabled and has due_date)
   │   │   │
   │   │   NO──► Should create calendar event?
   │   │         (has due_date and sync enabled)
   │   │         │
   │   │         YES─► CREATE calendar event
   │   │         │     Save event_id to task
   │   │         │
   │   │         NO──► Skip
   │
   └─► Update connection.last_sync_at

3. Handle deletions
   │
   ├─► Check for deleted calendar events
   │   └─► Unlink from tasks (set calendar_event_id = NULL)
   │       Optional: delete task if configured
   │
   └─► Check for deleted tasks
       └─► Delete calendar events if sync_delete_enabled

4. Update sync status
   │
   └─► connection.sync_status = 'SUCCESS' or 'FAILED'
       connection.sync_error = error message (if failed)
```

---

## 5. Authentication Flow

### 5.1 User Registration and Login

```
┌──────┐         ┌──────┐         ┌──────┐
│Client│         │ Auth │         │ DB   │
│      │         │Service│        │      │
└──┬───┘         └──┬───┘         └──┬───┘
   │                │                │
   │ POST /auth/register             │
   ├───────────────►│                │
   │ {email, pwd}   │                │
   │                │                │
   │                │ Validate input │
   │                │ Check email    │
   │                │ uniqueness     │
   │                ├───────────────►│
   │                │                │
   │                │ Hash password  │
   │                │ (bcrypt)       │
   │                │                │
   │                │ INSERT user    │
   │                ├───────────────►│
   │                │                │
   │                │ Generate JWT   │
   │                │ Access Token   │
   │                │ (exp: 1h)      │
   │                │                │
   │                │ Generate       │
   │                │ Refresh Token  │
   │                │ (exp: 30d)     │
   │                │                │
   │                │ Store refresh  │
   │                │ token hash     │
   │                ├───────────────►│
   │                │                │
   │ 201 Created    │                │
   │ {user, tokens} │                │
   │◄───────────────┤                │
   │                │                │
   │ Store tokens   │                │
   │ (localStorage/ │                │
   │  secure cookie)│                │
   │                │                │
   │ Subsequent requests include:   │
   │ Authorization: Bearer {token}  │
   │                │                │
   └────────────────┴────────────────┘
```

### 5.2 Token Refresh Flow

```
┌──────┐         ┌──────┐         ┌──────┐
│Client│         │ Auth │         │ DB   │
│      │         │Service│        │      │
└──┬───┘         └──┬───┘         └──┬───┘
   │                │                │
   │ POST /auth/refresh              │
   ├───────────────►│                │
   │ {refresh_token}│                │
   │                │                │
   │                │ Verify token   │
   │                │ signature      │
   │                │                │
   │                │ Check if       │
   │                │ revoked        │
   │                ├───────────────►│
   │                │                │
   │                │ Generate new   │
   │                │ access token   │
   │                │                │
   │                │ Optional:      │
   │                │ Rotate refresh │
   │                │ token          │
   │                │                │
   │ 200 OK         │                │
   │ {new_tokens}   │                │
   │◄───────────────┤                │
   └────────────────┴────────────────┘
```

---

## 6. Time Tracking Flow

### Start/Stop Timer Visualization

```
User Timeline:
───────────────────────────────────────────────────────────────────►
        │                                    │
     [START]                              [STOP]
        │                                    │
        ▼                                    ▼
   ┌────────────────────────────────────────┐
   │         TimeEntry Record               │
   │────────────────────────────────────────│
   │ start_time: 2025-10-06T09:00:00Z      │
   │ end_time:   2025-10-06T11:30:00Z      │
   │ duration:   9000 seconds (2.5 hours)   │
   │ task_id:    uuid-of-task              │
   └────────────────────────────────────────┘
        │
        │ (Trigger updates task.actual_duration)
        ▼
   ┌────────────────────────────────────────┐
   │          Task Record Updated           │
   │────────────────────────────────────────│
   │ actual_duration: 150 minutes           │
   │ (sum of all completed time entries)    │
   └────────────────────────────────────────┘
```

---

## 7. Deployment Architecture

### Production Kubernetes Deployment

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLOUD INFRASTRUCTURE                         │
│                      (AWS / GCP / Azure)                             │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                     Load Balancer (L7)                          │ │
│  │              SSL/TLS Termination + Health Checks                │ │
│  └──────────────────────────┬──────────────────────────────────────┘ │
│                             │                                        │
│  ┌──────────────────────────┼──────────────────────────────────────┐ │
│  │           Kubernetes Cluster (Multi-AZ)                         │ │
│  │                          │                                       │ │
│  │  ┌───────────────────────▼────────────────────────────────────┐ │ │
│  │  │                  Ingress Controller                         │ │ │
│  │  │                  (Nginx Ingress)                            │ │ │
│  │  └───────────────────────┬────────────────────────────────────┘ │ │
│  │                          │                                       │ │
│  │           ┌──────────────┼──────────────────┐                   │ │
│  │           │              │                  │                   │ │
│  │  ┌────────▼──────┐  ┌───▼────────┐  ┌──────▼───────┐          │ │
│  │  │  API Pods     │  │  API Pods  │  │  API Pods    │          │ │
│  │  │  (FastAPI)    │  │  (FastAPI) │  │  (FastAPI)   │          │ │
│  │  │  Replicas: 3+ │  │            │  │              │          │ │
│  │  │  HPA enabled  │  │            │  │              │          │ │
│  │  └────────┬──────┘  └────┬───────┘  └──────┬───────┘          │ │
│  │           │              │                  │                   │ │
│  │           └──────────────┼──────────────────┘                   │ │
│  │                          │                                       │ │
│  │  ┌───────────────────────▼────────────────────────────────────┐ │ │
│  │  │              Service Mesh (Optional: Istio)                 │ │ │
│  │  └───────────────────────┬────────────────────────────────────┘ │ │
│  │                          │                                       │ │
│  │           ┌──────────────┼──────────────────┐                   │ │
│  │           │              │                  │                   │ │
│  │  ┌────────▼──────┐  ┌───▼────────┐  ┌──────▼───────┐          │ │
│  │  │ Celery Worker │  │Redis Pod(s)│  │RabbitMQ Pod │          │ │
│  │  │  Pods         │  │            │  │             │          │ │
│  │  │  Replicas: 2+ │  │Persistence │  │Persistence  │          │ │
│  │  └───────────────┘  └────────────┘  └─────────────┘          │ │
│  │                                                                 │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                    Managed Database Services                     │ │
│  │  ┌──────────────────┐         ┌──────────────────┐             │ │
│  │  │  PostgreSQL RDS  │         │  Redis Cluster   │             │ │
│  │  │  • Primary       │         │  (ElastiCache)   │             │ │
│  │  │  • Read Replicas │         │                  │             │ │
│  │  │  • Auto Backup   │         │                  │             │ │
│  │  └──────────────────┘         └──────────────────┘             │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                    Monitoring & Logging                          │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │ │
│  │  │ Prometheus   │  │   Grafana    │  │     ELK      │          │ │
│  │  │   (Metrics)  │  │ (Dashboards) │  │   (Logs)     │          │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘          │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### Resource Allocation (Production)

**API Pods:**
- CPU: 500m - 2000m (with HPA)
- Memory: 512Mi - 2Gi
- Replicas: 3-10 (auto-scaling based on CPU/Memory)

**Worker Pods:**
- CPU: 250m - 1000m
- Memory: 512Mi - 1Gi
- Replicas: 2-5 (based on queue length)

**Database:**
- Instance: db.r5.xlarge or equivalent
- Storage: 100GB SSD (auto-scaling)
- Backup: Daily automated backups, 30-day retention

**Redis:**
- Instance: cache.r5.large or equivalent
- Memory: 8GB
- Replication: Enabled (1 primary + 1 replica)

---

## Appendix: Technology Stack Summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React 18 + TypeScript | Web client |
| API Gateway | Nginx | Reverse proxy, SSL, rate limiting |
| Backend API | FastAPI (Python 3.11+) | RESTful API services |
| Database | PostgreSQL 15 | Primary data store |
| Cache | Redis 7 | Session cache, job queue |
| Message Queue | RabbitMQ | Event bus, async processing |
| Background Jobs | Celery | Calendar sync, analytics |
| Container | Docker | Application packaging |
| Orchestration | Kubernetes | Container orchestration |
| CI/CD | GitHub Actions | Automated testing and deployment |
| Monitoring | Prometheus + Grafana | Metrics and dashboards |
| Logging | ELK Stack | Centralized logging |
| External APIs | Google Calendar, MS Graph | Calendar integrations |

---

**Document Version:** 1.0
**Last Updated:** 2025-10-06
**Author:** Time Agent 5
