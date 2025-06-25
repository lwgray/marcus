# Product Specification Template

## Technical Overview

**Project Name:** [Your Project Name]  
**Specification Version:** 1.0  
**Date:** [Current Date]  
**Tech Lead:** [Name]  
**Related PRD:** [Link to PRD]

## Architecture Overview

### System Architecture
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend   │────▶│  Database   │
│   (React)   │     │  (Python)   │     │ (PostgreSQL)│
└─────────────┘     └─────────────┘     └─────────────┘
       │                    │                    │
       └────────────────────┴────────────────────┘
                            │
                    ┌───────────────┐
                    │ External APIs │
                    └───────────────┘
```

### Technology Stack

#### Frontend
- **Framework:** [e.g., React 18.x]
- **State Management:** [e.g., Redux Toolkit]
- **UI Library:** [e.g., Material-UI]
- **Build Tool:** [e.g., Vite]
- **Testing:** [e.g., Jest, React Testing Library]

#### Backend
- **Language:** [e.g., Python 3.11]
- **Framework:** [e.g., FastAPI]
- **ORM:** [e.g., SQLAlchemy]
- **Testing:** [e.g., pytest]

#### Database
- **Primary:** [e.g., PostgreSQL 15]
- **Caching:** [e.g., Redis]
- **Search:** [e.g., Elasticsearch]

#### Infrastructure
- **Hosting:** [e.g., AWS, GCP, Azure]
- **Container:** [e.g., Docker]
- **Orchestration:** [e.g., Kubernetes]
- **CI/CD:** [e.g., GitHub Actions]

## API Specification

### Authentication
```yaml
POST /api/auth/login
Content-Type: application/json

Request:
{
  "email": "user@example.com",
  "password": "secure_password"
}

Response:
{
  "access_token": "jwt_token",
  "refresh_token": "refresh_token",
  "user": {
    "id": "user_id",
    "email": "user@example.com",
    "role": "user"
  }
}
```

### Core Endpoints

#### Resource 1: [e.g., Tasks]
```yaml
# List all
GET /api/tasks
Query params: ?page=1&limit=20&status=active

# Get single
GET /api/tasks/{id}

# Create
POST /api/tasks
Body: { "title": "...", "description": "..." }

# Update
PUT /api/tasks/{id}
Body: { "title": "...", "status": "..." }

# Delete
DELETE /api/tasks/{id}
```

#### Resource 2: [e.g., Users]
[Repeat structure as above]

## Database Schema

### Tables

#### users
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### tasks
```sql
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    priority INTEGER DEFAULT 0,
    due_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Indexes
```sql
CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_due_date ON tasks(due_date);
```

## Frontend Specifications

### Component Structure
```
src/
├── components/
│   ├── common/
│   │   ├── Header.jsx
│   │   ├── Footer.jsx
│   │   └── Layout.jsx
│   ├── auth/
│   │   ├── LoginForm.jsx
│   │   └── RegisterForm.jsx
│   └── tasks/
│       ├── TaskList.jsx
│       ├── TaskItem.jsx
│       └── TaskForm.jsx
├── pages/
│   ├── Home.jsx
│   ├── Dashboard.jsx
│   └── Profile.jsx
├── services/
│   ├── api.js
│   └── auth.js
└── store/
    ├── index.js
    └── slices/
        ├── authSlice.js
        └── taskSlice.js
```

### State Management
```javascript
// Example Redux store structure
{
  auth: {
    user: { id, email, role },
    isAuthenticated: boolean,
    loading: boolean
  },
  tasks: {
    items: [],
    selectedTask: {},
    filters: { status, priority },
    loading: boolean,
    error: null
  }
}
```

## Security Specifications

### Authentication & Authorization
- **Method:** JWT with refresh tokens
- **Token Expiry:** Access: 15 min, Refresh: 7 days
- **Storage:** HttpOnly cookies for web, Secure storage for mobile

### API Security
- Rate limiting: 100 requests/minute per IP
- CORS configuration: Whitelist specific origins
- Input validation: All inputs sanitized and validated
- SQL injection prevention: Parameterized queries

### Data Security
- Encryption at rest: AES-256
- Encryption in transit: TLS 1.3
- PII handling: Comply with GDPR/CCPA
- Audit logging: All data access logged

## Performance Specifications

### Frontend Performance
- Initial load: < 3 seconds
- Time to interactive: < 5 seconds
- Lighthouse score: > 90
- Bundle size: < 500KB gzipped

### Backend Performance
- API response time: p95 < 200ms
- Database query time: p95 < 50ms
- Concurrent requests: 1000/second
- Memory usage: < 512MB per instance

### Caching Strategy
- Browser cache: Static assets (1 year)
- CDN cache: Images and media
- Redis cache: Session data, frequent queries
- Database cache: Query result caching

## Testing Specifications

### Unit Tests
- Coverage target: 80%
- Frameworks: Jest (Frontend), pytest (Backend)
- Run on: Every commit

### Integration Tests
- API endpoint testing
- Database transaction testing
- External service mocking

### E2E Tests
- Framework: Cypress/Playwright
- Critical user flows covered
- Run on: Pull requests

## Deployment Specifications

### Environments
1. **Development:** Local development
2. **Staging:** Mirror of production
3. **Production:** Live environment

### CI/CD Pipeline
```yaml
stages:
  - lint
  - test
  - build
  - deploy

lint:
  - ESLint for frontend
  - Black/flake8 for backend

test:
  - Unit tests
  - Integration tests
  - E2E tests (staging only)

build:
  - Docker image creation
  - Asset optimization

deploy:
  - Blue-green deployment
  - Health checks
  - Rollback capability
```

## Monitoring & Logging

### Application Monitoring
- **APM:** [e.g., DataDog, New Relic]
- **Error Tracking:** [e.g., Sentry]
- **Uptime Monitoring:** [e.g., Pingdom]

### Logging
- **Format:** JSON structured logs
- **Levels:** DEBUG, INFO, WARN, ERROR
- **Retention:** 30 days
- **Aggregation:** [e.g., ELK stack]

### Metrics
- Response times
- Error rates
- User activity
- Resource utilization

## Migration & Rollback

### Database Migrations
- Tool: [e.g., Alembic, Flyway]
- Strategy: Forward-only migrations
- Rollback: Via compensating migrations

### Feature Flags
- System: [e.g., LaunchDarkly]
- Gradual rollout capability
- A/B testing support

---

## PM Agent Metadata

### Task Generation Hints
```yaml
pm_agent:
  estimated_tasks: 150
  parallel_work_possible: true
  critical_path:
    - database_setup
    - auth_implementation
    - core_api_endpoints
  agent_requirements:
    backend: 2
    frontend: 1
    devops: 1
    qa: 1
```