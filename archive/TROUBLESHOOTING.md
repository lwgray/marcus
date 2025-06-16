# Troubleshooting Guide: tests/setup_test_project.py

## Common Issues and Solutions

### 1. **Import Path Issues**
**Error**: `ModuleNotFoundError: No module named 'src'`

**Solution**:
```bash
# Make sure you're in the project root
cd /Users/lwgray/dev/pm-agent

# Add current directory to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or run with explicit path
python -m tests.setup_test_project
```

### 2. **Missing Dependencies** 
**Error**: `ModuleNotFoundError: No module named 'mcp'`

**Solution**:
```bash
# Install dependencies
pip install -r requirements.txt

# Or create virtual environment first
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. **MCP Server Connection Issues**
**Error**: `Failed to connect to MCP server`

**Check**:
1. Is kanban-mcp server running?
```bash
cd ../kanban-mcp
npm start
# or 
node dist/index.js
```

2. Check environment variables:
```bash
echo $KANBAN_MCP_COMMAND
echo $KANBAN_MCP_ARGS
```

3. Test MCP server directly:
```bash
cd ../kanban-mcp
node dist/index.js
```

### 4. **API Tool Call Errors**
**Error**: `page and perPage are required for get_projects action`

**Fix**: Use the corrected script `fix_setup_script.py` which includes proper pagination.

### 5. **Planka Server Not Running**
**Error**: `Connection refused to localhost:3333`

**Solution**:
```bash
# Start Planka server
cd /path/to/planka
docker-compose up -d

# Or check if running
curl http://localhost:3333
```

### 6. **Missing Test Project**
**Error**: `Task Master Test project not found`

**Solution**:
1. Log into Planka at http://localhost:3333
2. Create a project named exactly "Task Master Test"
3. Create at least one board in the project

## Step-by-Step Debugging

### 1. Check Prerequisites
```bash
# 1. Check Python environment
python --version  # Should be 3.8+

# 2. Check if in correct directory
pwd  # Should be /Users/lwgray/dev/pm-agent

# 3. Check dependencies
pip list | grep mcp
pip list | grep anthropic

# 4. Check environment variables
echo $ANTHROPIC_API_KEY
echo $KANBAN_MCP_COMMAND
echo $KANBAN_MCP_ARGS
```

### 2. Test MCP Connection Manually
```bash
# Test the kanban MCP server
cd ../kanban-mcp
node dist/index.js

# Should start and wait for input
# Press Ctrl+C to exit
```

### 3. Run Fixed Setup Script
```bash
# Use the corrected version
python fix_setup_script.py
```

### 4. Run Tests
```bash
# If setup succeeds, run the integration tests
pytest tests/integration/test_real_kanban_integration.py -v -s
```

## Quick Fixes

### Fix 1: Update Original Script
Replace the problematic lines in `tests/setup_test_project.py`:

**Replace this:**
```python
boards = await client._call_tool("mcp_kanban_project_board_manager", {
    "action": "get_boards"
})
```

**With this:**
```python
boards = await client._call_tool("mcp_kanban_project_board_manager", {
    "action": "get_boards",
    "page": 1,
    "perPage": 25
})
```

### Fix 2: Environment Setup
Create a `.env.local` file:
```bash
# Copy example and customize
cp .env.example .env.local

# Edit with your settings
ANTHROPIC_API_KEY=your-key-here
KANBAN_MCP_COMMAND=node
KANBAN_MCP_ARGS=../kanban-mcp/dist/index.js
PLANKA_BASE_URL=http://localhost:3333
PLANKA_AGENT_EMAIL=demo@demo.demo
PLANKA_AGENT_PASSWORD=demo
```

### Fix 3: Alternative Test Command
```bash
# Run with explicit module path
python -m pytest tests.integration.test_real_kanban_integration -v -s

# Or run setup directly
cd tests && python setup_test_project.py
```

## Final Test
After applying fixes, this should work:
```bash
cd /Users/lwgray/dev/pm-agent
source venv/bin/activate  # if using virtual env
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python tests/setup_test_project.py
```
