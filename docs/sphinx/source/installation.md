# Installation Guide

> **Time to first success**: 5 minutes  
> **What you'll achieve**: A fully configured Marcus managing AI workers on your projects

## System Requirements

Before installing Marcus, ensure your system meets these requirements:

### Minimum Requirements

- **Operating System**: Linux, macOS, or Windows 10/11
- **Python**: 3.8 or higher (3.11 recommended)
- **Memory**: 4GB RAM minimum (8GB recommended)
- **Disk Space**: 1GB free space
- **Docker**: 20.10 or higher (for containerized deployment)
- **Internet**: Required for AI API calls

### Supported Platforms

| Platform | Supported | Notes |
|----------|-----------|-------|
| macOS (Apple Silicon) |  | Fully tested on M1/M2/M3 |
| macOS (Intel) |  | Fully supported |
| Linux (Ubuntu/Debian) |  | Primary development platform |
| Linux (RHEL/CentOS) |  | Tested on CentOS 8+ |
| Windows 10/11 |  | WSL2 recommended |
| Windows (Native) | � | Use Docker Desktop |

## Installation Methods

### Method 1: Docker Installation (Recommended)

The easiest way to get started with Marcus is using Docker.

#### Step 1: Install Docker

<tabs>
<tab label="macOS">

```bash
# Install Docker Desktop for Mac
brew install --cask docker

# Or download from:
# https://www.docker.com/products/docker-desktop/
```

</tab>
<tab label="Linux">

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

</tab>
<tab label="Windows">

1. Install [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
2. Enable WSL2 backend in Docker Desktop settings
3. Restart your computer

</tab>
</tabs>

#### Step 2: Clone the Repository

```bash
git clone https://github.com/lwgray/pm-agent.git
cd pm-agent
```

#### Step 3: Run the Setup Script

```bash
# Make the script executable
chmod +x start.sh

# Run the setup
./start.sh
```

This creates a `.env` file with all required configuration options.

#### Step 4: Configure Your Environment

Edit the `.env` file with your API keys:

```bash
# Open in your preferred editor
nano .env  # or vim, code, etc.
```

Required configurations:

```text
# Choose your task board provider
KANBAN_PROVIDER=github  # or 'linear' or 'planka'

# AI Configuration (required)
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# GitHub Configuration (if using GitHub)
GITHUB_TOKEN=your_github_token_here
GITHUB_OWNER=your_github_username
GITHUB_REPO=your_repo_name
```

#### Step 5: Start Marcus

```bash
# Start core Marcus
./start.sh

# Or start with visualization UI
./start.sh full
```

### Method 2: Python Installation (Advanced)

For developers who want more control over the installation.

#### Step 1: Install Python

<tabs>
<tab label="macOS">

```bash
# Using Homebrew
brew install python@3.11

# Verify installation
python3.11 --version
```

</tab>
<tab label="Linux">

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip

# RHEL/CentOS
sudo dnf install python3.11 python3.11-pip
```

</tab>
<tab label="Windows">

1. Download Python from [python.org](https://www.python.org/downloads/)
2. During installation, check "Add Python to PATH"
3. Open Command Prompt and verify:

```powershell
python --version
```

</tab>
</tabs>

#### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python3.11 -m venv pm-agent-env

# Activate it
# On macOS/Linux:
source pm-agent-env/bin/activate

# On Windows:
pm-agent-env\Scripts\activate
```

#### Step 3: Install Marcus

```bash
# Clone the repository
git clone https://github.com/lwgray/pm-agent.git
cd pm-agent

# Install dependencies
pip install -r requirements.txt
```

#### Step 4: Configure Environment

Create a `.env` file in the project root:

```bash
# Copy the template
cp .env.example .env

# Edit with your settings
nano .env
```

#### Step 5: Run Marcus

```bash
# Start the MCP server
python marcus_mcp_server.py
```

## Configuration

### API Keys

Marcus requires API keys for AI services and your chosen task board.

#### Anthropic API Key (Required)

1. Visit [console.anthropic.com](https://console.anthropic.com)
2. Create an account or sign in
3. Navigate to API Keys
4. Create a new key with a descriptive name
5. Copy and add to your `.env` file

#### GitHub Token (If using GitHub)

1. Go to GitHub Settings � Developer settings � Personal access tokens
2. Click "Generate new token (classic)"
3. Select scopes:
   - `repo` (full control)
   - `project` (if using GitHub Projects)
4. Generate and copy the token

#### Linear API Key (If using Linear)

1. Go to Linear Settings � API
2. Create a personal API key
3. Copy the key and your Team ID
4. Add both to your `.env` file

### Task Board Selection

Choose your task board provider in `.env`:

```text
KANBAN_PROVIDER=github  # Recommended for most users
```

| Provider | Best For | Setup Time | Cost |
|----------|----------|------------|------|
| GitHub | Open source, individuals | 2 minutes | Free |
| Linear | Teams, startups | 3 minutes | Paid |
| Planka | Self-hosted, privacy | 5 minutes | Free* |

*Note: Planka is AGPL licensed and can only be used locally.

## Verification

### Check Installation

After installation, verify everything is working:

```bash
# Docker installation
docker-compose ps

# Python installation
python -c "import mcp; print('MCP installed successfully')"
```

### Test Marcus

Run a simple test:

```bash
# Docker
docker-compose exec pm-agent python -c "print('Marcus is ready!)"

# Python
python scripts/test_connection.py
```

### Verify API Connections

```bash
# Test your configuration
./start.sh demo
```

This runs Marcus with mock workers to verify your setup.

## Troubleshooting

### Common Issues

#### "Docker command not found"

**Solution**: Ensure Docker is installed and running:
```bash
docker --version
docker ps
```

#### "API Key not found"

**Solution**: Check your `.env` file:
```bash
# Verify the file exists
ls -la .env

# Check for required keys
grep "ANTHROPIC_API_KEY" .env
```

#### "Permission denied" on Linux

**Solution**: Add execute permissions:
```bash
chmod +x start.sh
sudo chown -R $USER:$USER .
```

#### "Port already in use"

**Solution**: Check for conflicting services:
```bash
# Find what's using the port
lsof -i :8000  # or the port number shown in error

# Stop Marcus if running
docker-compose down
```

### Platform-Specific Issues

#### macOS: "Cannot connect to Docker daemon"

```bash
# Ensure Docker Desktop is running
open -a Docker

# Wait for it to start, then retry
```

#### Windows: "Scripts disabled on this system"

Run in PowerShell as Administrator:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### Linux: "docker: command not found" after installation

```bash
# Reload your shell configuration
source ~/.bashrc
# Or log out and back in
```

## Next Steps

<� **Congratulations!** Marcus is now installed and ready to use.

### Quick Start Guide
� Continue to our [5-minute quickstart](quick_start) to create your first AI-managed project

### Learn the Concepts
� Read Core Concepts to understand how Marcus works

### Configure Your Workspace
� See [Configuration Guide](configuration) for advanced settings

### Get Help
- =� [Join our Discord](https://discord.gg/pm-agent)
- = [Report Issues](https://github.com/lwgray/pm-agent/issues)
- =� [Email Support](mailto:support@marcus.ai)

---

> **Pro Tip**: Keep your `.env` file secure and never commit it to version control. Use `.env.example` as a template for your team.