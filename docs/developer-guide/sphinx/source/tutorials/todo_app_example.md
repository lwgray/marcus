# Test Project: Simple Todo API with Web Frontend

## Project Overview
A simple Todo application with REST API backend and web frontend. Perfect for testing Marcus because it requires multiple specialized workers and has clear, decomposable tasks.

## Architecture
- **Backend**: Python FastAPI REST API
- **Frontend**: React web app
- **Database**: SQLite (simple, no setup required)
- **Testing**: Pytest for backend, Jest for frontend
- **DevOps**: Docker compose for easy deployment

## Why This Is Perfect for Testing Marcus

1. **Multiple Skill Sets Required**:
   - Backend developer (Python, FastAPI, SQLite)
   - Frontend developer (React, JavaScript, CSS)
   - Testing engineer (Pytest, Jest)
   - DevOps engineer (Docker, deployment)

2. **Clear Task Boundaries**:
   - Each feature can be broken into backend and frontend tasks
   - Easy to track progress and dependencies
   - Natural blockers occur (e.g., frontend needs API endpoints)

3. **Incremental Development**:
   - Start with basic CRUD
   - Add features incrementally
   - Each feature is a complete workflow

## Task Breakdown for Planka

### Phase 1: Project Setup (Priority: High)
- [ ] **BACKEND-001**: Initialize Python project with FastAPI
  - Labels: `backend`, `python`, `setup`
  - Description: Create project structure, requirements.txt, basic FastAPI app
  
- [ ] **FRONTEND-001**: Initialize React project
  - Labels: `frontend`, `react`, `setup`
  - Description: Create React app with TypeScript, set up folder structure

- [ ] **DEVOPS-001**: Create Docker compose setup
  - Labels: `devops`, `docker`, `setup`
  - Description: Docker compose with services for API and frontend

### Phase 2: Core API (Priority: High)
- [ ] **BACKEND-002**: Create Todo model and database schema
  - Labels: `backend`, `database`, `python`
  - Description: SQLAlchemy model for todos, database initialization
  
- [ ] **BACKEND-003**: Implement CRUD endpoints
  - Labels: `backend`, `api`, `python`
  - Description: POST /todos, GET /todos, PUT /todos/{id}, DELETE /todos/{id}
  
- [ ] **BACKEND-004**: Add API documentation
  - Labels: `backend`, `documentation`
  - Description: Ensure Swagger/OpenAPI docs are properly configured

- [ ] **TEST-001**: Write backend unit tests
  - Labels: `testing`, `backend`, `pytest`
  - Description: Test all CRUD operations, edge cases

### Phase 3: Frontend Development (Priority: Medium)
- [ ] **FRONTEND-002**: Create Todo list component
  - Labels: `frontend`, `react`, `component`
  - Description: Display list of todos with styling
  
- [ ] **FRONTEND-003**: Add todo creation form
  - Labels: `frontend`, `react`, `form`
  - Description: Form to create new todos
  
- [ ] **FRONTEND-004**: Implement edit/delete functionality
  - Labels: `frontend`, `react`, `feature`
  - Description: Edit inline, delete with confirmation

- [ ] **FRONTEND-005**: Connect to backend API
  - Labels: `frontend`, `integration`, `api`
  - Description: Axios/Fetch integration with error handling

### Phase 4: Enhanced Features (Priority: Low)
- [ ] **BACKEND-005**: Add todo categories
  - Labels: `backend`, `feature`, `database`
  - Description: Add category field, filter by category
  
- [ ] **BACKEND-006**: Add due dates and priorities
  - Labels: `backend`, `feature`, `enhancement`
  - Description: Extend model with due_date and priority fields

- [ ] **FRONTEND-006**: Add filtering and sorting
  - Labels: `frontend`, `feature`, `ux`
  - Description: Filter by status, category, sort by date/priority

- [ ] **FRONTEND-007**: Add dark mode
  - Labels: `frontend`, `ui`, `enhancement`
  - Description: Implement dark mode toggle

### Phase 5: Testing & Deployment (Priority: Medium)
- [ ] **TEST-002**: Write frontend unit tests
  - Labels: `testing`, `frontend`, `jest`
  - Description: Test components and API integration

- [ ] **TEST-003**: Create E2E tests
  - Labels: `testing`, `e2e`, `automation`
  - Description: Cypress or Playwright tests for user workflows

- [ ] **DEVOPS-002**: Setup CI/CD pipeline
  - Labels: `devops`, `ci/cd`, `automation`
  - Description: GitHub Actions for testing and deployment

- [ ] **DEVOPS-003**: Deploy to cloud
  - Labels: `devops`, `deployment`, `cloud`
  - Description: Deploy to Railway/Render/Heroku

## Sample Task Creation Script