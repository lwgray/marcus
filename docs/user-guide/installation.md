# =� Installing Marcus

> **Time to complete**: 5-15 minutes
> **Difficulty**: Beginner friendly

## <� Choose Your Installation Method

### Quick Install (Recommended for Most Users)

The fastest way to get Marcus running:

```bash
# Download and start Marcus with one command
curl -sSL https://raw.githubusercontent.com/lwgray/pm-agent/main/setup.sh | bash
```

This script will:
-  Check system requirements
-  Install dependencies
-  Set up configuration files
-  Start Marcus

### Manual Installation

For more control over the setup process, follow the steps below.

## =� System Requirements

### Minimum Requirements
- **Operating System**: Linux, macOS 10.15+, or Windows 10+ (with WSL2)
- **Python**: 3.8 or higher
- **Node.js**: 18.0 or higher
- **Docker**: 20.10 or higher
- **Memory**: 4GB RAM
- **Storage**: 2GB free space

### Recommended Requirements
- **Memory**: 8GB RAM or more
- **Storage**: 10GB free space
- **CPU**: 4 cores or more

## =� Step-by-Step Installation

### Step 1: Install Prerequisites

#### On macOS

```bash
# Install Homebrew if you don't have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install required tools
brew install python@3.11 node@18 git

# Install Docker Desktop
brew install --cask docker
```

#### On Ubuntu/Debian

```bash
# Update package list
sudo apt update

# Install Python and pip
sudo apt install python3.11 python3-pip python3-venv -y

# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install nodejs -y

# Install Docker
curl -fsSL https://get.docker.com | bash
sudo usermod -aG docker $USER
```

#### On Windows

1. **Install WSL2** (Windows Subsystem for Linux):
   ```powershell
   wsl --install
   ```

2. **Install Docker Desktop for Windows**:
   - Download from [Docker's website](https://www.docker.com/products/docker-desktop/)
   - Enable WSL2 integration in Docker Desktop settings

3. **Inside WSL2 Ubuntu**, follow the Ubuntu instructions above

### Step 2: Clone Marcus

```bash
# Clone the repository
git clone https://github.com/lwgray/pm-agent.git
cd pm-agent

# Create Python virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Verify installation
python -c "import marcus; print('Marcus modules loaded successfully')"
```

### Step 4: Set Up Kanban Provider

Marcus needs a kanban board to manage tasks. Choose one:

#### Option A: Planka (Local, No Account Needed)

```bash
# Clone kanban-mcp (includes Planka)
cd ..
git clone https://github.com/bradrisse/kanban-mcp.git
cd kanban-mcp

# Install and build
npm install
npm run build

# Start Planka
npm run up

# Return to Marcus directory
cd ../pm-agent
```

Planka will be available at http://localhost:3333
- Default login: `demo@demo.demo` / `demo`

#### Option B: GitHub Projects (Cloud)

1. Create a GitHub personal access token:
   - Go to https://github.com/settings/tokens
   - Click "Generate new token (classic)"
   - Select scopes: `repo`, `project`
   - Copy the token

2. Create or select a GitHub repository for your project

#### Option C: Linear (Cloud)

1. Get your Linear API key:
   - Go to Linear settings
   - Navigate to API
   - Create a personal API key

### Step 5: Configure Marcus

```bash
# Copy example configuration
cp .env.example .env

# Edit configuration
nano .env  # Or use your preferred editor
```

Add your configuration:

```bash
# AI Provider Configuration
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Kanban Provider (planka, github, or linear)
KANBAN_PROVIDER=planka

# For Planka (default)
PLANKA_URL=http://localhost:3333
PLANKA_USERNAME=demo@demo.demo
PLANKA_PASSWORD=demo

# For GitHub
# GITHUB_TOKEN=your-github-token
# GITHUB_OWNER=your-username
# GITHUB_REPO=your-repo-name

# For Linear
# LINEAR_API_KEY=your-linear-api-key
# LINEAR_TEAM_ID=your-team-id
```

### Step 6: Verify Installation

```bash
# Run verification script
python scripts/utilities/test_setup.py
```

You should see:
```
 Python environment OK
 Configuration files found
 Dependencies installed
 Kanban provider configured
 Marcus ready to start!
```

### Step 7: Initialize Your First Project

```bash
# Set up initial board and tasks
python scripts/setup/configure_board.py

# Or use the interactive setup
python scripts/quick_start.py
```

## =� Starting Marcus

### As MCP Server (For Claude Desktop/Code)

```bash
# Start the MCP server
python marcus.py
```

### As Standalone Service

```bash
# Start Marcus server
python scripts/start_marcus_task_master.py
```

### With Demo Workers

```bash
# Run demo with simulated workers
python scripts/demo_marcus.sh
```

## =3 Docker Installation (Alternative)

For a fully containerized setup:

```bash
# Using docker-compose
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f marcus
```

##  Post-Installation Checklist

- [ ] All dependencies installed
- [ ] Configuration file created and filled
- [ ] Kanban provider accessible
- [ ] API keys added
- [ ] Verification script passes
- [ ] Can start Marcus without errors

## =' Troubleshooting Common Issues

### "Python not found" or Wrong Version

```bash
# Check Python version
python3 --version

# Create alias if needed
alias python=python3
alias pip=pip3
```

### "Permission denied" Errors

```bash
# Make scripts executable
chmod +x scripts/*.py
chmod +x *.sh

# Fix Docker permissions (Linux)
sudo usermod -aG docker $USER
newgrp docker
```

### "Cannot connect to Docker daemon"

```bash
# Start Docker service
sudo systemctl start docker  # Linux
open -a Docker  # macOS

# Verify Docker is running
docker ps
```

### "Module not found" Errors

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Planka Connection Issues

```bash
# Check if Planka is running
docker ps | grep planka

# Restart Planka
cd ../kanban-mcp
npm run down
npm run up
```

## <
 Environment Variables Reference

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key | Yes | - |
| `KANBAN_PROVIDER` | Board provider (planka/github/linear) | Yes | planka |
| `PLANKA_URL` | Planka server URL | If using Planka | http://localhost:3333 |
| `PLANKA_USERNAME` | Planka login email | If using Planka | demo@demo.demo |
| `PLANKA_PASSWORD` | Planka password | If using Planka | demo |
| `GITHUB_TOKEN` | GitHub personal access token | If using GitHub | - |
| `GITHUB_OWNER` | GitHub username/org | If using GitHub | - |
| `GITHUB_REPO` | GitHub repository name | If using GitHub | - |
| `LINEAR_API_KEY` | Linear API key | If using Linear | - |
| `PM_AGENT_PORT` | Port for Marcus server | No | 3000 |
| `LOG_LEVEL` | Logging verbosity (DEBUG/INFO/WARN) | No | INFO |

## = Updating Marcus

```bash
# Pull latest changes
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart services
docker-compose restart  # If using Docker
# Or restart your Python processes
```

## <� Next Steps

Congratulations! Marcus is now installed. Here's what to do next:

1. **Quick Start Tutorial** - Create your first AI-assisted project in 5 minutes
   ```bash
   python docs/quick-start.md
   ```

2. **Configure Your First Project** - Set up tasks and workers
   - Read [Configuration Guide](configuration.md)
   - See [Creating Tasks](creating_tasks.rst)

3. **Connect AI Workers** - Start building with AI assistance
   - [Claude Desktop Setup](claude-desktop-setup.md)
   - [Worker Agents Guide](worker-agents.md)

## =� Tips for Success

- **Start Small**: Begin with a simple project to understand the workflow
- **Use Planka First**: It's the easiest to set up and requires no external accounts
- **Check Logs**: If something goes wrong, logs are in the `logs/` directory
- **Join Community**: Get help and share experiences with other users

## <� Getting Help

- =� [Troubleshooting Guide](troubleshooting.md) - Detailed solutions
- =� [GitHub Discussions](https://github.com/lwgray/pm-agent/discussions) - Ask questions
- = [Issue Tracker](https://github.com/lwgray/pm-agent/issues) - Report bugs
- =� Email: support@marcus.ai

---

Ready to start building? Head to the [Quick Start Guide](quick-start.md) to create your first AI-powered project!
