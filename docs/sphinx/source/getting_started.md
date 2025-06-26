# Getting Started with Marcus

> **Time to first success**: 5 minutes  
> **What you'll achieve**: AI workers building real code for your projects

## Choose Your Path

<div class="path-selector">

### 🚀 I want to try it quickly
→ Jump to Quick Start section below

### 📚 I want to understand first  
→ Read the Overview section below

### 🛠️ I'm ready for production
→ See [Installation Guide](installation)

</div>

## Quick Start

Get up and running in 60 seconds:

```bash
# Clone and enter the project
git clone https://github.com/lwgray/pm-agent.git
cd pm-agent

# Run the automated setup
./start.sh

# Edit the created .env file with your API key
nano .env  # Add your ANTHROPIC_API_KEY

# Restart with your configuration
docker-compose restart

# Create your first AI-managed project!
./start.sh demo
```

That's it! You now have Marcus running with demo workers. Watch them build a Hello World API:

```bash
# See the magic happen
docker-compose logs -f pm-agent
```

## Overview

### What is Marcus?

Marcus is like a smart project manager for AI workers. It assigns coding tasks to AI agents (like Claude), monitors their progress, and helps them work together to build real software projects. Think of it as having a teacher who gives homework to AI students and makes sure they complete it properly!

### Why Use It?

- **🤖 Automated Development**: AI workers handle routine coding tasks
- **📊 Real Progress Tracking**: See exactly what's being built in real-time
- **🔄 Intelligent Task Management**: Tasks are assigned based on dependencies
- **🚫 No More Context Switching**: Each worker focuses on one task at a time
- **📈 Scalable**: Add more workers as your project grows

### How It Works

```{mermaid}
graph TB
    subgraph "Kanban Board (GitHub/Linear/Planka)"
        T1[Task: Create API]
        T2[Task: Build UI]
        T3[Task: Write Tests]
        T4[Task: Fix Bug]
    end
    
    subgraph "Mixed Team Members"
        H1[Human Dev 1<br/>Skills: React, UI]
        H2[Human Dev 2<br/>Skills: Python, API]
        AI1[AI Worker 1<br/>Skills: Testing, Docs]
        AI2[AI Worker 2<br/>Skills: Backend, DB]
    end
    
    subgraph "Marcus (AI Coordinator)"
        REG[Worker Registry]
        MATCH[AI Task Matcher]
        TRACK[Progress Tracker]
    end
    
    subgraph "Code Repository"
        CODE[Your Project Code]
    end
    
    H1 -->|"What should I work on?"| MATCH
    H2 -->|"request_next_task()"| MATCH
    AI1 -->|"request_next_task()"| MATCH
    AI2 -->|"request_next_task()"| MATCH
    
    MATCH -->|"Analyzes skills & available tasks"| T1
    MATCH -->|"Matches best task to worker"| T2
    MATCH -->|"Returns optimal assignment"| T3
    MATCH -->|"Considers dependencies"| T4
    
    H1 -.->|"Assigned: Build UI"| CODE
    H2 -.->|"Assigned: Create API"| CODE
    AI1 -.->|"Assigned: Write Tests"| CODE
    AI2 -.->|"Works on tasks"| CODE
    
    TRACK -->|"Updates status"| T1
    TRACK -->|"Monitors progress"| T2
    
    style Marcus fill:#f9f,stroke:#333,stroke-width:4px
    style H1 fill:#bbf,stroke:#333,stroke-width:2px
    style H2 fill:#bbf,stroke:#333,stroke-width:2px
    style AI1 fill:#bfb,stroke:#333,stroke-width:2px
    style AI2 fill:#bfb,stroke:#333,stroke-width:2px
```

1. **You and Marcus** collaborate to create tasks on your Kanban board (GitHub Projects, Linear, or Planka)
2. **Workers** (both human and AI) request work when they're available
3. **Marcus** intelligently matches the best available task to each worker based on their skills
4. **Workers** complete tasks and update progress, while Marcus tracks everything on the Kanban board

## Full Installation

### System Requirements

- **OS**: Linux, macOS, or Windows 10+
- **Python**: 3.8 or higher (3.11 recommended)
- **Docker**: 20.10 or higher (recommended)
- **Memory**: 4GB RAM minimum
- **Disk**: 1GB free space

### Step 1: Install Dependencies

<tabs>
<tab label="macOS">

```bash
# Install Homebrew if needed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Docker Desktop
brew install --cask docker

# Install Python (optional, for non-Docker setup)
brew install python@3.11
```

</tab>
<tab label="Linux">

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Python (optional, for non-Docker setup)
sudo apt update
sudo apt install python3.11 python3-pip
```

</tab>
<tab label="Windows">

1. Install [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
2. Enable WSL2 backend in Docker settings
3. Install [Python 3.11](https://www.python.org/downloads/) (optional)
4. Restart your computer

</tab>
</tabs>

### Step 2: Get Marcus

```bash
# Clone the repository
git clone https://github.com/lwgray/pm-agent.git
cd pm-agent

# Make start script executable
chmod +x start.sh
```

### Step 3: Configure Your Environment

The first run creates a `.env` file:

```bash
./start.sh
```

Edit `.env` with your settings:

```text
# Required: AI Configuration
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Choose your task board (github, linear, or planka)
KANBAN_PROVIDER=github

# GitHub Configuration (if using GitHub)
GITHUB_TOKEN=ghp_your_token_here
GITHUB_OWNER=your_username
GITHUB_REPO=your_repo_name

# Optional: Additional AI providers
OPENAI_API_KEY=sk-your-openai-key
```

#### Getting Your API Keys

**Anthropic API Key** (Required):
1. Visit [console.anthropic.com](https://console.anthropic.com)
2. Sign up or log in
3. Go to API Keys → Create Key
4. Copy and paste into `.env`

**GitHub Token** (If using GitHub):
1. Go to GitHub → Settings → Developer settings
2. Personal access tokens → Generate new token
3. Select scopes: `repo`, `project`
4. Generate and copy token

### Step 4: Verify Installation

```bash
# Test your setup
./start.sh demo

# Check the logs
docker-compose logs pm-agent

# You should see:
# ✅ Connected to GitHub successfully
# ✅ AI worker initialized
# ✅ Ready to process tasks
```

## Your First Project

### 1. Create a Simple API Project

Let's build a "Hello World" API to see Marcus in action:

```bash
# Start Marcus with visualization
./start.sh full

# In another terminal, create tasks
docker-compose exec pm-agent python << 'EOF'
from scripts.quick_start import create_hello_world_project
create_hello_world_project()
EOF
```

### 2. Watch AI Workers Build

Open the visualization dashboard:
🌐 [http://localhost:4298](http://localhost:4298)

You'll see:
- Tasks being assigned to workers
- Real-time progress updates
- Code being generated

### 3. Check the Results

```bash
# View generated files
ls -la output/hello-world-api/

# See what was built
cat output/hello-world-api/server.js

# The AI workers even create documentation!
cat output/hello-world-api/README.md
```

### 4. Test the Generated Code

```bash
cd output/hello-world-api
npm install
npm start

# In another terminal:
curl http://localhost:3000/hello
# Returns: {"message": "Hello, World!"}
```

## Real-World Example: Todo App

Let's build something more substantial - a complete Todo application:

```bash
# Create comprehensive Todo app tasks
docker-compose exec pm-agent python projects/todo_app/create_minimal_todo_cards_v2.py

# Watch the workers build it
docker-compose logs -f pm-agent
```

This creates tasks for:
- 📁 Project setup and structure
- 🗄️ Database models
- 🔌 REST API endpoints
- 🔐 Authentication
- ✅ Tests
- 📚 Documentation

The AI workers will build each component, creating a production-ready application!

## Understanding Task Flow

### How Tasks Move Through the System

```{mermaid}
sequenceDiagram
    participant U as You/Team
    participant KB as Kanban Board
    participant M as Marcus
    participant AI as AI Engine
    participant W as Worker (Human/AI)
    participant GH as GitHub/Code Repo
    
    Note over U,GH: Task Creation & Setup
    U->>KB: Create task with requirements
    U->>M: "New tasks available"
    
    Note over W,GH: Worker Requests Work (Pull-based)
    W->>M: register_agent(skills, capacity)
    W->>M: request_next_task()
    M->>KB: Fetch available tasks
    KB-->>M: List of open tasks
    M->>AI: match_task_to_agent(tasks, worker_skills)
    AI-->>M: Best match + confidence score
    M->>AI: generate_instructions(task, worker)
    AI-->>M: Contextual instructions
    M-->>W: Task assignment + instructions
    M->>KB: Move task to "In Progress"
    
    Note over W,GH: Work Execution
    W->>W: Work on task
    W->>M: report_task_progress(25%)
    M->>KB: Update task progress
    W->>M: report_task_progress(50%)
    W->>GH: Commit code changes
    W->>M: report_task_progress(75%)
    
    Note over W,GH: Blocker Handling (if needed)
    W->>M: report_blocker("Can't access API")
    M->>AI: analyze_blocker(issue)
    AI-->>M: Suggested solutions
    M-->>W: Resolution steps
    M->>KB: Add blocker comment
    W->>W: Apply solution
    
    Note over W,GH: Completion & Verification
    W->>M: report_task_progress(100%)
    M->>GH: Verify implementation (if GitHub)
    GH-->>M: Code analysis results
    M->>KB: Move task to "Done"
    W->>M: request_next_task()
    
    Note over U,GH: Continuous Flow
    U->>KB: Review completed work
    U->>KB: Create new tasks as needed
```

### Task Priorities

Marcus intelligently prioritizes tasks:

1. **Dependencies First**: Database before API endpoints
2. **Blocking Issues**: Resolves blockers immediately  
3. **Parallel Work**: Independent tasks run simultaneously
4. **Critical Path**: Focuses on tasks that unblock others

## Common Workflows

### Starting Fresh Each Day

```bash
# Start Marcus
./start.sh

# Check overnight progress
docker-compose exec pm-agent pm-status

# Review completed work
git log --oneline -10
```

### Adding New Features

```bash
# Create a new task
docker-compose exec pm-agent pm-task create \
  "Add user profile endpoints to the API"

# Watch it get built
docker-compose logs -f pm-agent | grep "profile"
```

### Debugging Issues

```bash
# See why a task is blocked
docker-compose exec pm-agent pm-task show <task-id>

# Check worker status
docker-compose exec pm-agent pm-worker list

# View detailed logs
docker-compose logs --tail=100 pm-agent
```

## Best Practices

### 1. Write Clear Task Descriptions

**Good**:
```
"Create REST API endpoint GET /api/users that returns paginated user list with fields: id, name, email, created_at. Include query parameters for page and limit."
```

**Too Vague**:
```
"Make users endpoint"
```

### 2. Break Down Large Features

Instead of: "Build user management system"

Create separate tasks:
- "Create user database model"
- "Build user registration endpoint"  
- "Add user authentication"
- "Create user profile endpoints"

### 3. Use Task Dependencies

```python
# When creating related tasks
create_task("Create database schema", labels=["database"])
create_task("Build API endpoints", depends_on=["database"])
```

### 4. Monitor and Iterate

- Review generated code regularly
- Provide feedback through new tasks
- Let workers fix their own bugs

## What's Next?

### Learn More
- 📖 Core Concepts - Deep dive into how Marcus works
- 🎓 [Todo App Tutorial](tutorials/beginner_todo_app_tutorial) - Build a complete application step-by-step
- 🔧 [Configuration Guide](configuration) - Customize Marcus for your needs

### Explore Advanced Features
- 🤖 [Custom AI Workers](tutorials/custom_workers) - Create specialized workers
- 📊 [Monitoring & Analytics](user_guide/monitoring_progress) - Track productivity
- 🔄 CI/CD Integration - Automate your workflow

### Get Help
- 💬 [Join our Discord](https://discord.gg/pm-agent)
- 🐛 [Report Issues](https://github.com/lwgray/pm-agent/issues)
- 📧 [Email Support](mailto:support@marcus.ai)

## Troubleshooting Quick Fixes

### "Workers not picking up tasks"
```bash
# Check task board connection
docker-compose exec pm-agent python scripts/test_connection.py

# Verify workers are running
docker-compose ps
```

### "API Key errors"
```bash
# Ensure .env is loaded
docker-compose down
docker-compose up -d

# Check environment
docker-compose exec pm-agent env | grep API_KEY
```

### "Port already in use"
```bash
# Find what's using the port
lsof -i :4298  # or :8000

# Use a different port
PM_AGENT_PORT=4299 ./start.sh full
```

---

🎉 **Welcome to Marcus!** You're now ready to build amazing things with AI-powered development.

> **Remember**: Marcus augments your development process - always review and understand the generated code before using it in production.