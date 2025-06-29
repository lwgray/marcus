# Getting Started with Marcus

Welcome to Marcus! This guide will help you get up and running with your AI-powered project management system in just a few minutes.

## What is Marcus?

Marcus is an intelligent project coordination system that helps AI agents (like Claude) work together on software projects. Think of it as a smart project manager that:

- Assigns tasks to AI workers based on their capabilities
- Tracks progress and ensures work gets completed
- Helps workers overcome obstacles
- Coordinates multiple agents working on the same project

## Prerequisites

Before you begin, make sure you have:

1. **Git** installed on your system
2. **Docker** and **Docker Compose** (for the easiest setup)
3. **API Keys** for at least one AI service:
   - Anthropic Claude API key
   - OpenAI API key (optional)
   - Other LLM API keys (optional)

## Quick Start (5 minutes)

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-username/marcus.git
cd marcus
```

### Step 2: Set Up Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit the `.env` file with your API keys:

```bash
# Required
ANTHROPIC_API_KEY=your-claude-api-key-here

# Optional (for different AI providers)
OPENAI_API_KEY=your-openai-key-here

# Task Board Provider (choose one)
KANBAN_PROVIDER=github  # or 'linear' or 'planka'
GITHUB_TOKEN=your-github-token  # if using GitHub
```

### Step 3: Start Marcus

For basic usage:

```bash
./start.sh
```

For a demo with simulated workers:

```bash
./start.sh demo
```

For the full experience with visualization:

```bash
./start.sh full
```

### Step 4: Verify Installation

Check that Marcus is running:

```bash
docker-compose ps
```

You should see the PM Agent service running.

## Your First Project

### 1. Create a Project Board

Marcus works with task boards to manage projects. Based on your chosen provider:

- **GitHub**: Create a new GitHub Project
- **Linear**: Create a new Linear team/project
- **Planka**: Marcus will create boards automatically

### 2. Add Your First Task

Create a task on your board with:
- A clear title (e.g., "Create a TODO application backend")
- Description with requirements
- Labels for task type (`backend`, `frontend`, `database`, etc.)

### 3. Start an AI Worker

In a new terminal, start a worker agent:

```bash
# For Claude Desktop
python experiments/run_claude_agent.py

# For programmatic agents
python experiments/run_agent.py --agent-type claude
```

### 4. Watch the Magic

The AI worker will:
1. Register with Marcus
2. Request a task assignment
3. Work on the task autonomously
4. Report progress updates
5. Complete the task or ask for help if blocked

## Understanding the Workflow

```
[Task Board] → [Marcus PM Agent] → [AI Worker]
     ↑                                    ↓
     └──────── Progress Updates ←─────────┘
```

1. **You** create tasks on your task board
2. **Marcus** intelligently assigns tasks to workers
3. **Workers** complete tasks and report progress
4. **You** review completed work

## Next Steps

- Read [How Marcus Works](how-it-works.md) for a deeper understanding
- Explore [Configuration Options](reference/configuration_guide.md)
- Learn about [Different Providers](sphinx/source/user_guide/providers.md)
- Try the [TODO App Tutorial](sphinx/source/tutorials/beginner_todo_app_tutorial.md)

## Getting Help

If you run into issues:

1. Check the [Troubleshooting Guide](how-to/troubleshoot-common-issues.md)
2. Review [Common Questions](sphinx/source/reference/faq.md)
3. Join our community discussions
4. Open an issue on GitHub

## Tips for Success

1. **Start Small**: Begin with simple tasks to understand the workflow
2. **Clear Task Descriptions**: The clearer your task, the better the results
3. **Use Labels**: Help Marcus assign tasks to the right type of worker
4. **Monitor Progress**: Check in periodically to see how work is progressing
5. **Iterate**: Refine your task descriptions based on results

Welcome to the future of AI-assisted software development!