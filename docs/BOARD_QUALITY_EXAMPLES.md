# Board Quality Examples

## 🔴 Poor Quality Board (Score: 0.2)

```
BACKLOG
├── Fix bug
├── Add feature  
├── Update UI
├── Test stuff
├── Deploy
└── Documentation
```

**Problems**:
- No descriptions
- No labels or metadata
- Vague titles
- No dependencies
- No time estimates
- No clear organization

## 🟡 Basic Quality Board (Score: 0.5)

```
BACKLOG
├── Frontend Tasks
│   ├── Create login form
│   │   └── Labels: [frontend]
│   └── Build dashboard
│       └── Labels: [frontend]
├── Backend Tasks  
│   ├── User authentication API
│   │   └── Labels: [backend]
│   └── Database setup
│       └── Labels: [backend, database]
└── Deploy to production
    └── Labels: [deployment]
```

**Improvements**:
- Some organization by component
- Basic labels added
- Clearer titles

**Still Missing**:
- Descriptions
- Time estimates
- Dependencies
- Priorities
- Acceptance criteria

## 🟢 Good Quality Board (Score: 0.75)

```
SPRINT 1 - FOUNDATION
├── [TASK-001] Setup Development Environment
│   ├── Description: Configure Docker, install dependencies, setup IDE
│   ├── Labels: [phase:setup, type:configuration, complexity:simple]
│   ├── Priority: High
│   ├── Estimate: 4 hours
│   └── Assigned: @developer1
│
├── [TASK-002] Design Database Schema
│   ├── Description: Create ERD for user, product, and order tables...
│   ├── Labels: [phase:planning, component:database, type:design]
│   ├── Priority: High
│   ├── Estimate: 6 hours
│   ├── Dependencies: [TASK-001]
│   └── Acceptance Criteria:
│       ├── [ ] ERD documented
│       ├── [ ] Relationships defined
│       └── [ ] Reviewed by team
│
└── [TASK-003] Implement User Authentication
    ├── Description: JWT-based auth with refresh tokens...
    ├── Labels: [phase:development, component:backend, type:feature, skill:nodejs]
    ├── Priority: High
    ├── Estimate: 16 hours
    ├── Dependencies: [TASK-001, TASK-002]
    └── Sub-tasks:
        ├── Create user model
        ├── Build auth endpoints
        └── Add JWT middleware
```

**Strengths**:
- Clear descriptions
- Multiple relevant labels
- Time estimates
- Dependencies mapped
- Some acceptance criteria
- Organized by phases

## 🌟 Excellent Quality Board (Score: 0.95)

```
PROJECT: E-Commerce Platform MVP
Total Tasks: 47 | Estimated: 380 hours | Timeline: 6 weeks

PHASE 1: FOUNDATION (Week 1)
├── [EPIC-001] Development Environment Setup
│   ├── [TASK-001] Configure Development Environment
│   │   ├── Description: Set up standardized dev environment with Docker Compose 
│   │   │   for all services (frontend, backend, database, cache). Include hot
│   │   │   reloading, debugging capabilities, and seed data scripts.
│   │   ├── Labels: [phase:setup, type:configuration, complexity:moderate, team:all]
│   │   ├── Priority: Urgent (Blocking all development)
│   │   ├── Estimate: 8 hours
│   │   ├── Acceptance Criteria:
│   │   │   ├── [ ] Docker Compose runs all services
│   │   │   ├── [ ] Hot reload works for frontend/backend
│   │   │   ├── [ ] README with setup instructions
│   │   │   ├── [ ] Seed data loads successfully
│   │   │   └── [ ] All team members can run locally
│   │   ├── Attachments: [docker-architecture.png, dev-setup-guide.md]
│   │   └── Comments:
│   │       └── "Using Docker 24.x for M1 Mac compatibility" - @techlead
│   │
│   └── [TASK-002] Setup CI/CD Pipeline
│       ├── Description: Implement GitHub Actions for automated testing, linting,
│       │   and deployment to staging. Include quality gates for coverage (>80%),
│       │   linting passes, and all tests green.
│       ├── Labels: [phase:setup, type:infrastructure, skill:devops, complexity:complex]
│       ├── Priority: High
│       ├── Estimate: 12 hours
│       ├── Dependencies: [TASK-001]
│       ├── Risk: "GitHub Actions minutes limit on free tier"
│       └── Mitigation: "Use self-hosted runners if needed"

PHASE 2: CORE FEATURES (Week 2-3)
├── [EPIC-002] User Management System
│   ├── [TASK-010] Database Schema for Users
│   │   ├── Description: Design and implement user tables with proper constraints,
│   │   │   indexes, and relationships. Support social auth and email/password.
│   │   ├── Labels: [phase:development, component:database, type:implementation]
│   │   ├── Priority: High
│   │   ├── Estimate: 6 hours
│   │   ├── Dependencies: [TASK-001]
│   │   ├── Acceptance Criteria:
│   │   │   ├── [ ] Users table with proper fields
│   │   │   ├── [ ] Social auth provider table
│   │   │   ├── [ ] Indexes on email, username
│   │   │   ├── [ ] Migration scripts tested
│   │   │   └── [ ] Rollback plan documented
│   │   └── Related PRs: [#23, #24]
│   │
│   ├── [TASK-011] User Registration API
│   │   ├── Description: RESTful endpoint for user registration with validation,
│   │   │   email verification, and rate limiting. Implement proper error handling
│   │   │   and security measures (password hashing, SQL injection prevention).
│   │   ├── Labels: [phase:development, component:backend, type:feature, 
│   │   │           skill:nodejs, security:high]
│   │   ├── Priority: High
│   │   ├── Estimate: 10 hours
│   │   ├── Dependencies: [TASK-010]
│   │   ├── Acceptance Criteria:
│   │   │   ├── [ ] POST /api/auth/register endpoint
│   │   │   ├── [ ] Input validation (email, password strength)
│   │   │   ├── [ ] Email verification flow
│   │   │   ├── [ ] Rate limiting (5 attempts/hour)
│   │   │   ├── [ ] Unit tests with 90% coverage
│   │   │   ├── [ ] API documentation in OpenAPI format
│   │   │   └── [ ] Security review passed
│   │   ├── Test Cases: [registration-tests.md]
│   │   └── Blockers:
│   │       └── "Waiting for email service decision (SendGrid vs AWS SES)" - @pm

PHASE 3: PRODUCT CATALOG (Week 3-4)
├── [EPIC-003] Product Management
│   └── ... (similar detail level)

WORKFLOW RULES:
- No task moves to "In Progress" without acceptance criteria
- All PRs require code review + passing tests
- Deploy to staging after each epic completion
- Production deploy only after full phase completion

METRICS TRACKING:
- Average task completion: 1.2 days
- Estimation accuracy: 85%
- Velocity: 65 hours/week (team of 3)
- Quality score trend: 0.6 → 0.75 → 0.95
```

**Excellence Factors**:
- Comprehensive descriptions with context
- Rich label taxonomy
- Accurate time estimates
- Clear dependency chains
- Detailed acceptance criteria
- Risk assessment and mitigation
- Attachments and documentation links
- Progress tracking and blockers
- Team assignments
- Related PRs and commits
- Workflow rules defined
- Metrics tracking

## Key Differences Summary

| Aspect | Poor | Basic | Good | Excellent |
|--------|------|-------|------|-----------|
| **Descriptions** | None | None | Present | Detailed with context |
| **Labels** | None | 1 per task | 2-3 per task | 4-5 semantic labels |
| **Estimates** | None | None | Hours defined | Accurate with history |
| **Dependencies** | None | Implicit | Some mapped | Fully mapped |
| **Organization** | Random | By component | By phase | Epics + phases |
| **Acceptance Criteria** | None | None | Some tasks | All tasks |
| **Risk Management** | None | None | None | Identified + mitigated |
| **Documentation** | None | None | Basic | Comprehensive |
| **Metrics** | None | None | None | Tracked + analyzed |

## How Marcus Helps

- **Poor → Basic**: Marcus adds basic labels and groups tasks
- **Basic → Good**: Marcus enriches with descriptions, estimates, and dependencies  
- **Good → Excellent**: Marcus suggests acceptance criteria, identifies risks, and optimizes workflow
- **Excellent boards**: Marcus focuses on coordination and optimization rather than enrichment