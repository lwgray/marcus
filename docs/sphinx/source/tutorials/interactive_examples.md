# Interactive PM Agent Examples

> **Time to complete**: 15-20 minutes per example  
> **Difficulty**: Beginner to Intermediate  
> **Prerequisites**: PM Agent installed and running

## What You'll Learn

These interactive examples will show you how to:
- Create different types of projects with PM Agent
- Understand task dependencies and worker coordination
- Experiment with various development scenarios
- See PM Agent handle real-world challenges

## Example 1: Quick API Endpoint

**What it demonstrates**: How PM Agent handles a simple, focused task

### Create the Task

```python
# Run this in PM Agent
docker-compose exec pm-agent python << 'EOF'
from pm_agent import create_task

# Create a single API endpoint task
task = create_task(
    title="Create Weather API Endpoint",
    description="""
    Create a GET /api/weather endpoint that:
    - Accepts a 'city' query parameter
    - Returns mock weather data in JSON format
    - Includes temperature, conditions, and humidity
    - Has proper error handling for missing city parameter
    """,
    labels=["backend", "api", "quick-task"]
)
print(f"Created task: {task.id}")
EOF
```

### Watch It Build

```bash
# Monitor the progress
docker-compose logs -f pm-agent | grep -i weather
```

**What happens**:
1. A backend worker picks up the task immediately
2. Creates a simple FastAPI endpoint
3. Implements the requirements exactly as specified
4. Reports completion with the file location

**Result**: A working weather API endpoint in ~2-3 minutes!

## Example 2: Full CRUD System

**What it demonstrates**: Coordinated multi-task development

### Create Related Tasks

```python
# Create a complete CRUD system
docker-compose exec pm-agent python << 'EOF'
from pm_agent import create_task_batch

tasks = create_task_batch([
    {
        "title": "Create Product Database Model",
        "description": "SQLAlchemy model for products with: id, name, price, description, stock_quantity",
        "labels": ["backend", "database"],
        "priority": "high"
    },
    {
        "title": "Build Product CRUD API",
        "description": "REST API with GET, POST, PUT, DELETE for products",
        "labels": ["backend", "api"],
        "depends_on": ["Create Product Database Model"]
    },
    {
        "title": "Add Product Search Endpoint",
        "description": "GET /products/search with query params for name and price range",
        "labels": ["backend", "api", "feature"],
        "depends_on": ["Build Product CRUD API"]
    },
    {
        "title": "Write Product API Tests",
        "description": "Pytest tests covering all CRUD operations and search",
        "labels": ["testing", "backend"],
        "depends_on": ["Build Product CRUD API", "Add Product Search Endpoint"]
    }
])

for task in tasks:
    print(f"Created: {task.title} (ID: {task.id})")
EOF
```

### Observe Task Flow

Open the visualization dashboard to see:
- Database model created first (no dependencies)
- CRUD API waits for model completion
- Search endpoint waits for CRUD API
- Tests wait for all features

**Key Learning**: PM Agent respects dependencies and parallelizes when possible!

## Example 3: Frontend Component Library

**What it demonstrates**: Frontend development and component reusability

### Create Component Tasks

```bash
# Create a reusable component library
docker-compose exec pm-agent python << 'EOF'
from pm_agent import create_task_batch

components = [
    "Button (primary, secondary, danger variants)",
    "Card (with header, body, footer slots)",  
    "Modal (with backdrop and close functionality)",
    "Alert (success, warning, error, info types)",
    "Spinner (loading indicator)",
    "Input (with validation states)"
]

tasks = []
for component in components:
    tasks.append({
        "title": f"Create {component.split('(')[0].strip()} Component",
        "description": f"React component: {component}",
        "labels": ["frontend", "component", "ui-library"]
    })

# Add Storybook setup
tasks.insert(0, {
    "title": "Setup Storybook",
    "description": "Configure Storybook for component documentation",
    "labels": ["frontend", "tooling"],
    "priority": "high"
})

# Add integration task
tasks.append({
    "title": "Create Component Demo Page",
    "description": "Demo page showing all components with examples",
    "labels": ["frontend", "documentation"],
    "depends_on": [f"Create {c.split('(')[0].strip()} Component" for c in components]
})

created_tasks = create_task_batch(tasks)
print(f"Created {len(created_tasks)} component tasks")
EOF
```

**What happens**:
- Storybook setup happens first
- Components are built in parallel
- Demo page waits for all components
- Each component includes proper TypeScript types

## Example 4: Handling Blockers

**What it demonstrates**: How PM Agent handles and recovers from issues

### Create a Challenging Task

```python
# Create a task that might encounter issues
docker-compose exec pm-agent python << 'EOF'
from pm_agent import create_task

task = create_task(
    title="Integrate with External Payment API",
    description="""
    Integrate with Stripe payment processing:
    - Set up Stripe SDK
    - Create payment intent endpoint
    - Handle webhooks for payment confirmation
    - Add refund functionality
    Note: This requires STRIPE_API_KEY environment variable
    """,
    labels=["backend", "integration", "payment"]
)
print(f"Created challenging task: {task.id}")
EOF
```

### Watch Blocker Handling

```bash
# Monitor how the worker handles missing API key
docker-compose logs -f pm-agent | grep -E "(blocker|STRIPE|payment)"
```

**What you'll see**:
1. Worker picks up the task
2. Realizes STRIPE_API_KEY is missing
3. Reports a blocker with specific details
4. Creates mock implementation with clear documentation
5. Completes task with notes about production requirements

**Key Learning**: Workers handle missing resources gracefully!

## Example 5: Microservices Architecture

**What it demonstrates**: Building distributed systems

### Create Microservices Project

```python
# Create a microservices setup
docker-compose exec pm-agent python << 'EOF'
from pm_agent import create_project_tasks

# Define microservices
services = {
    "user-service": {
        "description": "User management and authentication",
        "endpoints": ["/register", "/login", "/profile", "/logout"],
        "database": "PostgreSQL",
        "port": 3001
    },
    "product-service": {
        "description": "Product catalog and inventory",
        "endpoints": ["/products", "/categories", "/search", "/inventory"],
        "database": "MongoDB",
        "port": 3002
    },
    "order-service": {
        "description": "Order processing and tracking",
        "endpoints": ["/orders", "/cart", "/checkout", "/tracking"],
        "database": "PostgreSQL",
        "port": 3003
    },
    "notification-service": {
        "description": "Email and SMS notifications",
        "endpoints": ["/send-email", "/send-sms", "/templates"],
        "database": "Redis",
        "port": 3004
    }
}

tasks = []

# API Gateway first
tasks.append({
    "title": "Create API Gateway",
    "description": "Kong or Express gateway routing to all services",
    "labels": ["backend", "infrastructure", "gateway"],
    "priority": "high"
})

# Create tasks for each service
for service_name, config in services.items():
    # Service setup
    tasks.append({
        "title": f"Setup {service_name}",
        "description": f"{config['description']}. Database: {config['database']}, Port: {config['port']}",
        "labels": ["backend", "microservice", service_name]
    })
    
    # Service endpoints
    tasks.append({
        "title": f"Implement {service_name} endpoints",
        "description": f"Create endpoints: {', '.join(config['endpoints'])}",
        "labels": ["backend", "api", service_name],
        "depends_on": [f"Setup {service_name}"]
    })

# Docker compose for all services
tasks.append({
    "title": "Create Docker Compose Configuration",
    "description": "Docker compose with all services, databases, and gateway",
    "labels": ["devops", "docker"],
    "depends_on": [f"Setup {s}" for s in services.keys()]
})

# Integration tests
tasks.append({
    "title": "Write Integration Tests",
    "description": "End-to-end tests across all microservices",
    "labels": ["testing", "integration"],
    "depends_on": ["Create Docker Compose Configuration"]
})

created = create_project_tasks("E-Commerce Microservices", tasks)
print(f"Created {len(created)} tasks for microservices project")
EOF
```

**What happens**:
- Multiple specialized workers handle different services
- Services are built in parallel
- Gateway configuration waits for service information
- Docker compose ties everything together

## Example 6: Real-Time Features

**What it demonstrates**: WebSocket and real-time functionality

### Create Real-Time Chat

```python
# Create a real-time chat system
docker-compose exec pm-agent python << 'EOF'
from pm_agent import create_task_batch

tasks = create_task_batch([
    {
        "title": "Setup WebSocket Server",
        "description": "Socket.io or native WebSocket server for real-time communication",
        "labels": ["backend", "realtime", "websocket"],
        "priority": "high"
    },
    {
        "title": "Create Chat Room Logic",
        "description": "Room creation, joining, leaving, and message broadcasting",
        "labels": ["backend", "feature", "chat"],
        "depends_on": ["Setup WebSocket Server"]
    },
    {
        "title": "Build Chat UI Components",
        "description": "React components: ChatRoom, MessageList, MessageInput, UserList",
        "labels": ["frontend", "component", "chat"]
    },
    {
        "title": "Implement Chat Client",
        "description": "WebSocket client with reconnection logic and event handling",
        "labels": ["frontend", "realtime", "websocket"],
        "depends_on": ["Build Chat UI Components"]
    },
    {
        "title": "Add Message Persistence",
        "description": "Store messages in database, load history on join",
        "labels": ["backend", "database", "feature"],
        "depends_on": ["Create Chat Room Logic"]
    },
    {
        "title": "Connect Frontend to Backend",
        "description": "Wire up the complete chat system",
        "labels": ["integration", "fullstack"],
        "depends_on": ["Implement Chat Client", "Create Chat Room Logic"]
    }
])

print(f"Created {len(tasks)} tasks for real-time chat")
EOF
```

**Key Features Built**:
- WebSocket connection management
- Real-time message broadcasting
- User presence indicators
- Message history
- Reconnection handling

## Running Multiple Examples

You can run multiple examples simultaneously to see how PM Agent handles concurrent projects:

```bash
# Terminal 1: Start the API endpoint example
docker-compose exec pm-agent python scripts/examples/quick_api.py

# Terminal 2: Start the component library
docker-compose exec pm-agent python scripts/examples/component_library.py

# Terminal 3: Watch all workers
docker-compose logs -f pm-agent

# Terminal 4: View the dashboard
open http://localhost:4298
```

## Interactive Experiments

### Experiment 1: Task Priority

Create tasks with different priorities and observe scheduling:

```python
# High priority task
create_task("Fix Critical Security Bug", priority="critical", labels=["security"])

# Normal priority  
create_task("Add New Feature", priority="normal", labels=["feature"])

# Low priority
create_task("Update Documentation", priority="low", labels=["docs"])
```

### Experiment 2: Worker Specialization

Create tasks requiring different skills:

```python
# Python task
create_task("Create Python Data Pipeline", labels=["python", "data"])

# JavaScript task  
create_task("Build Node.js Microservice", labels=["javascript", "backend"])

# DevOps task
create_task("Setup Kubernetes Deployment", labels=["devops", "k8s"])
```

### Experiment 3: Failure Recovery

Create a task that will fail and see recovery:

```python
create_task(
    "Connect to Production Database",
    description="Connect to prod DB at invalid-host:5432",
    labels=["database", "testing-failure"]
)
```

## Tips for Creating Effective Tasks

1. **Be Specific**: Include exact requirements
   ```
   Good: "Create REST endpoint GET /users returning id, name, email with pagination"
   Bad: "Make users endpoint"
   ```

2. **Include Constraints**: Specify limitations
   ```
   "Build dashboard using only vanilla JavaScript (no frameworks)"
   ```

3. **Define Success Criteria**: What makes it complete?
   ```
   "Task complete when: endpoint returns 200, handles errors, has tests"
   ```

4. **Use Dependencies**: Let PM Agent optimize
   ```
   "depends_on": ["database-setup", "auth-system"]
   ```

## Summary

These interactive examples demonstrate:
- ✅ How PM Agent handles various project types
- ✅ Task dependency management
- ✅ Worker coordination and specialization
- ✅ Blocker handling and recovery
- ✅ Real-world development scenarios

## Next Steps

Try creating your own examples:
1. **Mobile App**: React Native todo list
2. **CLI Tool**: Command-line task manager
3. **Data Pipeline**: ETL process with Python
4. **Game**: Simple web-based game
5. **Analytics Dashboard**: Real-time metrics display

Remember: The key to PM Agent is clear task definition and letting the AI workers handle the implementation details!