Creating Effective Tasks
========================

This guide helps you write tasks that AI agents can successfully complete.

Understanding AI Agent Capabilities
-----------------------------------

AI agents work best with:

* **Clear, specific requirements** - Avoid ambiguous language
* **Defined success criteria** - How to know when the task is complete
* **Appropriate scope** - Tasks that can be completed in 2-8 hours
* **Technical context** - Include relevant technical details

Task Structure
--------------

Good Task Example
~~~~~~~~~~~~~~~~~

**Title**: Implement user authentication API endpoints

**Description**::

   Create REST API endpoints for user authentication using FastAPI.
   
   Requirements:
   - POST /auth/register - Create new user account
   - POST /auth/login - Authenticate user and return JWT token
   - GET /auth/me - Get current user info (requires authentication)
   - POST /auth/logout - Invalidate user session
   
   Technical specs:
   - Use PostgreSQL for user storage
   - Passwords must be hashed using bcrypt
   - JWT tokens should expire after 24 hours
   - Include input validation using Pydantic models
   - Return appropriate HTTP status codes
   
   Success criteria:
   - All endpoints are functional
   - Unit tests cover all endpoints
   - API documentation is updated
   - Error handling for common scenarios

**Labels**: backend, api, authentication, python

Poor Task Example
~~~~~~~~~~~~~~~~~

**Title**: Make login work

**Description**: We need users to be able to log in

**Why this is poor**:

* Too vague - no technical details
* No success criteria
* Missing implementation details
* No context about the technology stack

Task Sizing Guidelines
----------------------

**Small Tasks (2-4 hours)**
   * Single endpoint or component
   * Bug fixes with clear reproduction steps
   * Adding tests to existing code
   * Documentation updates

**Medium Tasks (4-8 hours)**
   * Feature with multiple endpoints
   * Complex UI component with state management
   * Database schema changes with migrations
   * Integration with external service

**Large Tasks (Should be broken down)**
   * Entire subsystems
   * Major architectural changes
   * Features requiring multiple specialties

Using Labels Effectively
------------------------

Labels help PM Agent match tasks to the right workers:

**Skill Labels**
   * ``python``, ``javascript``, ``typescript``
   * ``react``, ``vue``, ``angular``
   * ``postgresql``, ``mongodb``, ``redis``
   * ``docker``, ``kubernetes``, ``aws``

**Task Type Labels**
   * ``backend``, ``frontend``, ``fullstack``
   * ``api``, ``database``, ``ui``
   * ``testing``, ``documentation``, ``devops``
   * ``bugfix``, ``feature``, ``refactor``

**Priority Labels**
   * ``priority-high``, ``priority-medium``, ``priority-low``
   * ``urgent``, ``blocking``

Dependencies and Prerequisites
------------------------------

When tasks depend on each other, make it clear:

**Good Dependency Description**::

   Prerequisites:
   - Task #23 (Database schema) must be completed first
   - Requires the /api/users endpoints from Task #24
   - Uses the authentication middleware from Task #25

**Include Context**::

   Related files:
   - Backend API: src/api/auth.py
   - Database models: src/models/user.py
   - Tests: tests/api/test_auth.py
   
   Existing patterns:
   - Follow the same structure as src/api/products.py
   - Use the BaseModel class from src/models/base.py

Providing Examples
------------------

Including examples helps AI agents understand expectations:

**API Response Example**::

   Expected response for GET /auth/me:
   {
     "id": "123e4567-e89b-12d3-a456-426614174000",
     "email": "user@example.com",
     "name": "John Doe",
     "created_at": "2024-01-15T10:30:00Z",
     "role": "user"
   }

**Code Pattern Example**::

   Follow this pattern for endpoint definition:
   
   @router.post("/register", response_model=UserResponse)
   async def register(
       user_data: UserCreate,
       db: Session = Depends(get_db)
   ) -> UserResponse:
       # Implementation here
       pass

Common Pitfalls to Avoid
------------------------

1. **Assuming Knowledge**
   
   ❌ "Implement caching like we discussed"
   
   ✅ "Implement Redis caching with 1-hour TTL for user profiles"

2. **Mixing Multiple Features**
   
   ❌ "Add user auth and also fix the dashboard"
   
   ✅ Create separate tasks for each feature

3. **Unclear Acceptance Criteria**
   
   ❌ "Make it work well"
   
   ✅ "Response time under 200ms for 95% of requests"

4. **Missing Error Scenarios**
   
   ❌ "Handle user login"
   
   ✅ "Handle user login with specific errors for: invalid credentials, locked account, expired password"

Task Templates
--------------

Backend API Task
~~~~~~~~~~~~~~~~

::

   Title: [Feature] - [Specific component]
   
   Description:
   Implement [what] for [purpose].
   
   Endpoints:
   - METHOD /path - Description
   - METHOD /path - Description
   
   Requirements:
   - Requirement 1
   - Requirement 2
   
   Technical Details:
   - Database: [tables/collections involved]
   - Authentication: [required/optional]
   - Validation: [specific rules]
   
   Success Criteria:
   - [ ] All endpoints return correct data
   - [ ] Error cases handled with appropriate status codes
   - [ ] Unit tests achieve 80% coverage
   - [ ] API documentation updated

Frontend Component Task
~~~~~~~~~~~~~~~~~~~~~~~

::

   Title: Create [Component Name] component
   
   Description:
   Build a [description] component that [purpose].
   
   Requirements:
   - Visual: [description or link to design]
   - Behavior: [interactions and state changes]
   - Responsiveness: [breakpoints to support]
   
   Props/Inputs:
   - propName: type - description
   - propName: type - description
   
   Technical Details:
   - Framework: [React/Vue/etc]
   - State Management: [Redux/Context/etc]
   - Styling: [CSS modules/Styled Components/etc]
   
   Success Criteria:
   - [ ] Matches design specifications
   - [ ] Handles all interaction states
   - [ ] Responsive on mobile/tablet/desktop
   - [ ] Unit tests for logic
   - [ ] Storybook story created

Tips for GitHub Issues
----------------------

When using GitHub as your task board:

1. **Use Issue Templates**
   Create templates for common task types

2. **Link Related Issues**
   Use GitHub's linking syntax: ``Depends on #123``

3. **Add Milestones**
   Group related tasks into milestones

4. **Use Projects**
   Organize tasks into columns for better visualization

5. **Include Code Blocks**
   Use markdown code blocks for examples

Monitoring Task Progress
------------------------

Once you've created tasks:

1. **Watch for Assignment**
   PM Agent will assign tasks to workers based on skills

2. **Check Progress Comments**
   Workers report progress at 25%, 50%, 75%, and completion

3. **Respond to Blockers**
   If a worker reports a blocker, provide additional context

4. **Review Completion**
   Verify the task meets your success criteria

Next Steps
----------

* Review :doc:`/templates/index` for project templates
* Try the :doc:`/tutorials/todo_app_example` to see tasks in action
* Read :doc:`monitoring_progress` to track your project