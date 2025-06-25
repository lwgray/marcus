Real World Examples
===================

Complete examples of using PM Agent for real projects.

E-Commerce Platform
-------------------

Building a full e-commerce platform with PM Agent coordinating multiple AI workers.

Project Overview
~~~~~~~~~~~~~~~~

**Goal**: Create a modern e-commerce platform with:

* Product catalog with search
* Shopping cart and checkout
* User accounts and authentication
* Admin dashboard
* Payment processing
* Order management

**Tech Stack**:

* Backend: Python FastAPI
* Frontend: React with TypeScript
* Database: PostgreSQL
* Cache: Redis
* Payment: Stripe
* Deployment: Docker + AWS

Project Structure
~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   # .pm-agent.yaml
   pm_agent:
     project_type: "e-commerce"
     complexity: "high"
     team_size: "5-8"
     preferred_agents:
       - backend_developer
       - frontend_developer
       - database_specialist
       - devops_engineer
       - testing_specialist

Task Breakdown
~~~~~~~~~~~~~~

**Phase 1: Foundation (Week 1)**

1. **Setup and Architecture**::

      Title: Set up FastAPI project with Docker
      
      Description:
      Initialize e-commerce backend project with proper structure.
      
      Requirements:
      - FastAPI with uvicorn
      - PostgreSQL + Redis connections  
      - Docker compose for local development
      - Project structure:
        - src/api/ (endpoints)
        - src/models/ (database models)
        - src/services/ (business logic)
        - src/utils/ (helpers)
      - Environment configuration
      - Basic health check endpoint
      
      Labels: backend, setup, docker, python

2. **Database Schema**::

      Title: Design and implement e-commerce database schema
      
      Description:
      Create comprehensive database schema for e-commerce platform.
      
      Tables needed:
      - users (id, email, password_hash, role, created_at)
      - products (id, name, description, price, sku, stock)
      - categories (id, name, parent_id, slug)
      - product_categories (product_id, category_id)
      - carts (id, user_id, created_at, updated_at)
      - cart_items (id, cart_id, product_id, quantity)
      - orders (id, user_id, status, total, created_at)
      - order_items (id, order_id, product_id, quantity, price)
      - addresses (id, user_id, type, street, city, postal_code)
      - payments (id, order_id, method, status, amount)
      
      Include:
      - Proper indexes for performance
      - Foreign key constraints
      - Migration scripts
      - Seed data for testing
      
      Labels: database, postgresql, schema

**Phase 2: Core Features (Week 2)**

3. **Product Management API**::

      Title: Implement product CRUD API with search
      
      Description:
      Create comprehensive product management endpoints.
      
      Endpoints:
      - GET /api/products (pagination, filtering, sorting)
      - GET /api/products/{id} (with related data)
      - GET /api/products/search (full-text search)
      - POST /api/products (admin only)
      - PUT /api/products/{id} (admin only)
      - DELETE /api/products/{id} (soft delete)
      
      Features:
      - Advanced filtering (price range, category, in stock)
      - Full-text search on name and description
      - Sorting by price, name, popularity
      - Include category information
      - Cache popular queries in Redis
      
      Labels: backend, api, products, search

4. **Shopping Cart System**::

      Title: Build shopping cart API with session support
      
      Description:
      Implement shopping cart functionality for both authenticated and guest users.
      
      Requirements:
      - Support guest carts (session-based)
      - Merge guest cart on login
      - Real-time stock validation
      - Price calculations with taxes
      - Cart abandonment tracking
      
      Endpoints:
      - GET /api/cart
      - POST /api/cart/items
      - PUT /api/cart/items/{id}
      - DELETE /api/cart/items/{id}
      - POST /api/cart/merge (for guest->user)
      
      Labels: backend, api, cart, redis

**Phase 3: Frontend Development (Week 3)**

5. **Product Listing Page**::

      Title: Create responsive product listing with filters
      
      Description:
      Build product catalog page with advanced filtering.
      
      Features:
      - Grid/list view toggle
      - Filters sidebar (category, price, availability)
      - Sort options (price, name, newest)
      - Pagination or infinite scroll
      - Quick add to cart
      - Loading skeletons
      
      Components:
      - ProductGrid component
      - ProductCard component
      - FilterSidebar component
      - SortDropdown component
      - Pagination component
      
      Labels: frontend, react, typescript, ui

6. **Shopping Cart UI**::

      Title: Build shopping cart interface with real-time updates
      
      Description:
      Create cart page and mini-cart components.
      
      Requirements:
      - Mini cart dropdown in header
      - Full cart page with:
        - Product images and details
        - Quantity adjustment
        - Remove items
        - Price calculations
        - Shipping estimate
        - Promo code input
      - Real-time stock validation
      - Optimistic UI updates
      - Persist cart in localStorage
      
      Labels: frontend, react, cart, state-management

**Phase 4: User Management (Week 4)**

7. **Authentication System**::

      Title: Implement JWT authentication with refresh tokens
      
      Description:
      Build secure authentication system.
      
      Features:
      - Registration with email verification
      - Login with JWT tokens
      - Refresh token rotation
      - Password reset flow
      - OAuth integration (Google, Facebook)
      - Session management
      - Rate limiting
      
      Security:
      - Bcrypt password hashing
      - Secure cookie storage
      - CSRF protection
      - Input validation
      
      Labels: backend, authentication, security, jwt

**Phase 5: Order Processing (Week 5)**

8. **Checkout Flow**::

      Title: Create multi-step checkout process
      
      Description:
      Build complete checkout experience.
      
      Steps:
      1. Shipping address (with address validation)
      2. Shipping method selection
      3. Payment information
      4. Order review
      5. Confirmation
      
      Features:
      - Guest checkout option
      - Save addresses for users
      - Multiple payment methods
      - Order summary sidebar
      - Mobile-optimized
      
      Labels: frontend, checkout, payment, ux

9. **Payment Integration**::

      Title: Integrate Stripe payment processing
      
      Description:
      Implement secure payment processing.
      
      Requirements:
      - Stripe Elements integration
      - Support cards and wallets
      - 3D Secure handling
      - Webhook processing
      - Refund capabilities
      - Payment receipt emails
      
      Security:
      - PCI compliance
      - Tokenization
      - Fraud detection
      
      Labels: backend, payment, stripe, integration

Worker Assignment Strategy
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Optimal worker configuration for this project
   
   workers = {
       "backend_specialist": {
           "count": 2,
           "skills": ["python", "fastapi", "postgresql", "redis"],
           "focus": ["api", "database", "integration"]
       },
       "frontend_specialist": {
           "count": 2,
           "skills": ["react", "typescript", "css", "state-management"],
           "focus": ["ui", "ux", "components"]
       },
       "fullstack_developer": {
           "count": 1,
           "skills": ["python", "react", "docker", "testing"],
           "focus": ["integration", "deployment"]
       },
       "devops_engineer": {
           "count": 1,
           "skills": ["docker", "aws", "ci/cd", "monitoring"],
           "focus": ["infrastructure", "deployment"]
       }
   }

Results and Metrics
~~~~~~~~~~~~~~~~~~~

**Development Timeline**:

* Week 1: Foundation complete, 15 tasks
* Week 2: Core APIs ready, 20 tasks
* Week 3: Frontend MVP, 18 tasks
* Week 4: User system, 12 tasks
* Week 5: Checkout complete, 15 tasks

**Total**: 80 tasks, 5 weeks, 6 AI workers

**Success Metrics**:

* 95% task completion rate
* 12% blocker rate (mostly integration issues)
* 4.2 hours average task completion
* 85% test coverage achieved

SaaS Application
----------------

Building a project management SaaS platform.

Project Overview
~~~~~~~~~~~~~~~~

**Goal**: Create a project management tool with:

* Multi-tenant architecture
* Real-time collaboration
* Kanban and Gantt views
* Time tracking
* Reporting and analytics
* Integrations (Slack, GitHub)

Key Tasks
~~~~~~~~~

**Multi-Tenant Setup**::

   Title: Implement multi-tenant database architecture
   
   Description:
   Set up PostgreSQL with row-level security for multi-tenancy.
   
   Requirements:
   - Tenant isolation using RLS policies
   - Shared app, separate data approach
   - Tenant provisioning system
   - Subdomain routing
   - Data migration tools
   
   Technical:
   - Use PostgreSQL RLS
   - Tenant context middleware
   - Connection pooling per tenant
   - Backup strategy per tenant
   
   Labels: backend, database, architecture, security

**Real-Time Collaboration**::

   Title: Add WebSocket support for real-time updates
   
   Description:
   Implement real-time collaboration features.
   
   Features:
   - Live cursor positions
   - Real-time card updates
   - User presence indicators
   - Typing indicators
   - Conflict resolution
   
   Stack:
   - Socket.io for WebSocket
   - Redis for pub/sub
   - Operational Transform for conflicts
   
   Labels: backend, websocket, real-time, collaboration

API Microservice
----------------

Building a standalone API service.

Project Overview
~~~~~~~~~~~~~~~~

**Goal**: Create a weather data API service with:

* RESTful and GraphQL endpoints
* Multiple data source aggregation
* Caching and rate limiting
* API key management
* Usage analytics
* Documentation

Architecture Tasks
~~~~~~~~~~~~~~~~~~

**API Gateway Setup**::

   Title: Implement API gateway with rate limiting
   
   Description:
   Build API gateway for managing access and limits.
   
   Features:
   - API key validation
   - Rate limiting per key
   - Request/response logging
   - Error standardization
   - CORS handling
   
   Implementation:
   - Use FastAPI middleware
   - Redis for rate limit counters
   - PostgreSQL for API keys
   - Structured logging
   
   Labels: backend, api, gateway, infrastructure

Mobile App Backend
------------------

Building a backend for a mobile fitness app.

Project Overview
~~~~~~~~~~~~~~~~

**Goal**: Create backend for fitness tracking app:

* User profiles and goals
* Workout tracking
* Progress analytics
* Social features
* Push notifications
* Offline sync support

Mobile-Specific Tasks
~~~~~~~~~~~~~~~~~~~~~

**Offline Sync System**::

   Title: Implement offline-first sync mechanism
   
   Description:
   Build sync system for mobile app offline support.
   
   Requirements:
   - Conflict resolution strategy
   - Incremental sync
   - Data compression
   - Sync status tracking
   - Retry mechanism
   
   Technical:
   - Use CRDT for conflict-free sync
   - Sync endpoints with pagination
   - WebSocket for real-time sync
   - SQLite schema for mobile
   
   Labels: backend, mobile, sync, architecture

Lessons Learned
---------------

**1. Task Sizing**
   - 4-6 hour tasks work best
   - Break complex features into steps
   - Include setup in first tasks

**2. Dependencies**
   - Explicitly state dependencies
   - Order tasks logically
   - Account for integration time

**3. Worker Specialization**
   - Specialized workers are more efficient
   - Full-stack workers good for integration
   - Mix of specialists and generalists

**4. Documentation**
   - Include API examples in tasks
   - Reference existing patterns
   - Document decisions in tasks

**5. Testing Strategy**
   - Include test requirements in tasks
   - Separate testing tasks for complex features
   - Integration tests as separate tasks

Best Practices Summary
----------------------

1. **Start with Architecture**
   - Define structure early
   - Create scaffolding tasks
   - Document conventions

2. **Phase Development**
   - Group related features
   - Complete phases before moving on
   - Test at phase boundaries

3. **Handle Integration**
   - Plan integration points
   - Create specific integration tasks
   - Test early and often

4. **Monitor Progress**
   - Daily progress reviews
   - Address blockers quickly
   - Adjust task sizes based on data

5. **Iterate and Improve**
   - Refine task templates
   - Update estimates
   - Document patterns that work

Next Steps
----------

* Choose a project type similar to yours
* Adapt the task templates
* Start with a small phase
* Scale up based on results
* Share your experiences!