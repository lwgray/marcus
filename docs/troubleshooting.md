# PM Agent Troubleshooting Guide

This guide helps you diagnose and fix common issues with PM Agent.

## Common Issues

### 1. Connection Issues

#### "Connection refused" or "Cannot connect to Kanban MCP"
**Symptoms:**
- PM Agent hangs on startup
- Timeout errors when connecting
- "Connection refused" errors

**Solutions:**
1. **Check Planka is running:**
   ```bash
   # Check if Planka is accessible
   curl http://localhost:3333
   
   # Check if port 3333 is in use
   lsof -i :3333
   ```

2. **Verify Kanban MCP path:**
   ```bash
   # Check if kanban-mcp exists
   ls /Users/lwgray/dev/kanban-mcp/dist/index.js
   
   # Test kanban-mcp directly
   node /Users/lwgray/dev/kanban-mcp/dist/index.js
   ```

3. **Check Node.js installation:**
   ```bash
   which node
   node --version  # Should be 16+
   ```

4. **Fix in code:**
   ```python
   # In mcp_kanban_client_refactored.py
   self._node_path = "/opt/homebrew/bin/node"  # Update to your path
   ```

#### "Protocol version mismatch"
**Symptoms:**
- Error about protocol versions not matching
- MCP client expects different version than server

**Solution:**
```bash
# Downgrade MCP client to match kanban-mcp
pip install mcp==1.1.0
```

### 2. Board/Project Issues

#### "No board found"
**Symptoms:**
- PM Agent can't find a board
- Board ID is None/null

**Solutions:**
1. **Run board selector:**
   ```bash
   python select_task_master_board.py
   ```

2. **Create board manually:**
   ```bash
   python direct_create_tasks.py
   ```

3. **Check config file:**
   ```bash
   cat config_pm_agent.json
   # Ensure board_id is set
   ```

#### "Project not found"
**Symptoms:**
- Invalid project ID
- 404 errors from Planka

**Solution:**
1. **Get correct project ID from Planka URL:**
   ```
   http://localhost:3333/projects/1533678301472621705/...
                                  ^^^^^^^^^^^^^^^^^^^^
                                  This is your project ID
   ```

2. **Update configuration:**
   ```json
   {
     "project_id": "correct-project-id-here"
   }
   ```

### 3. Task Assignment Issues

#### "No tasks available"
**Symptoms:**
- Workers always get "no tasks" response
- Board has tasks but none are assigned

**Causes & Solutions:**
1. **Tasks in wrong list:**
   - Move tasks to "To Do" or "Backlog" list
   - PM Agent only assigns tasks from these lists

2. **Tasks already assigned:**
   - Check if tasks have assignees in Planka
   - Clear assignments for tasks to be picked up

3. **No matching skills:**
   - Ensure task labels match worker skills
   - Add appropriate labels (backend, frontend, etc.)

#### "Task assignment fails"
**Symptoms:**
- Worker gets task but can't update status
- Progress reports fail

**Solution:**
```python
# Debug task assignment
async def debug_task_assignment():
    # List all tasks
    tasks = await kanban_client.get_available_tasks()
    for task in tasks:
        print(f"Task: {task.name}")
        print(f"  ID: {task.id}")
        print(f"  Labels: {task.labels}")
        print(f"  Assigned: {task.assigned_to}")
```

### 4. Worker Agent Issues

#### "Agent not registered"
**Symptoms:**
- request_next_task fails with "agent not registered"
- Agent status not found

**Solution:**
```python
# Always register before requesting tasks
result = await session.call_tool("register_agent", {
    "agent_id": "my_agent",
    "name": "My Agent",
    "role": "Developer",
    "skills": ["python"]
})

# Verify registration
if not result.get("success"):
    print(f"Registration failed: {result}")
```

#### "Worker hanging or not progressing"
**Symptoms:**
- Worker stops requesting tasks
- No progress updates

**Debug steps:**
1. **Add logging:**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   
   async def work_cycle(self):
       logging.info(f"Starting work cycle for {self.agent_id}")
       # ... rest of code
   ```

2. **Add timeout handling:**
   ```python
   try:
       result = await asyncio.wait_for(
           session.call_tool("request_next_task", {...}),
           timeout=30.0
       )
   except asyncio.TimeoutError:
       logging.error("Task request timed out")
   ```

### 5. Performance Issues

#### "PM Agent slow to respond"
**Symptoms:**
- Long delays in task assignment
- Timeouts on API calls

**Solutions:**
1. **Check system resources:**
   ```bash
   # CPU and memory usage
   top
   
   # Disk space
   df -h
   ```

2. **Optimize Planka:**
   - Archive old boards
   - Limit active tasks per board (<100)
   - Clean up completed tasks

3. **Check AI API:**
   - Verify Anthropic API key is valid
   - Check API rate limits
   - Monitor API response times

### 6. AI/Claude Integration Issues

#### "AI instructions not generating"
**Symptoms:**
- Tasks assigned without instructions
- Fallback instructions always used

**Solutions:**
1. **Check API key:**
   ```bash
   echo $ANTHROPIC_API_KEY
   ```

2. **Test AI engine:**
   ```python
   from src.integrations.ai_analysis_engine import AIAnalysisEngine
   
   ai = AIAnalysisEngine()
   await ai.initialize()
   
   result = await ai._call_claude("Test prompt")
   print(result)
   ```

3. **Check rate limits:**
   - Monitor API usage in Anthropic console
   - Implement exponential backoff

## Debugging Tools

### 1. Connection Test Script
```python
# test_connection.py
import asyncio
from src.integrations.mcp_kanban_client_refactored import MCPKanbanClient

async def test_connection():
    client = MCPKanbanClient()
    try:
        async with client.connect() as conn:
            print("✅ Connection successful!")
            print(f"Project: {client.project_id}")
            print(f"Board: {client.board_id}")
    except Exception as e:
        print(f"❌ Connection failed: {e}")

asyncio.run(test_connection())
```

### 2. PM Agent Health Check
```python
# health_check.py
import asyncio
import aiohttp

async def check_pm_agent():
    checks = {
        "planka": "http://localhost:3333",
        "pm_agent": "http://localhost:8765/health"  # If implemented
    }
    
    async with aiohttp.ClientSession() as session:
        for name, url in checks.items():
            try:
                async with session.get(url, timeout=5) as resp:
                    status = "✅ OK" if resp.status == 200 else f"❌ {resp.status}"
                    print(f"{name}: {status}")
            except Exception as e:
                print(f"{name}: ❌ {e}")

asyncio.run(check_pm_agent())
```

### 3. Task Inspector
```python
# inspect_tasks.py
async def inspect_tasks():
    client = MCPKanbanClient()
    client.project_id = "your-project-id"
    
    async with client.connect() as conn:
        # Get all lists
        lists = await client.get_lists()
        
        for list_item in lists:
            print(f"\nList: {list_item['name']}")
            
            # Get cards in list
            cards = await client.get_cards_in_list(list_item['id'])
            for card in cards:
                print(f"  - {card['name']}")
                print(f"    ID: {card['id']}")
                print(f"    Labels: {card.get('labels', [])}")
```

## Log Analysis

### Enable Debug Logging
```python
# In your agent or PM Agent startup
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pm_agent.log'),
        logging.StreamHandler()
    ]
)
```

### Common Log Patterns to Look For
```bash
# Connection issues
grep -i "connection\|timeout\|refused" pm_agent.log

# Task assignment issues  
grep -i "no tasks\|assignment\|available" pm_agent.log

# Error patterns
grep -i "error\|exception\|failed" pm_agent.log

# Worker activity
grep "agent_id" pm_agent.log | tail -20
```

## Recovery Procedures

### 1. Full System Reset
```bash
# 1. Stop all processes
pkill -f pm_agent
pkill -f kanban-mcp

# 2. Clear any locks/temp files
rm -f /tmp/pm_agent_*

# 3. Reset configuration
cp config_pm_agent.json config_pm_agent.backup.json
python select_task_master_board.py

# 4. Restart
python start_pm_agent_task_master.py
```

### 2. Board Cleanup
```python
# cleanup_board.py
async def cleanup_board():
    # Archive completed tasks
    # Remove stuck assignments
    # Reset task positions
    pass
```

### 3. Worker Recovery
```python
# For stuck workers
async def recover_worker(agent_id):
    # Get current status
    status = await get_agent_status(agent_id)
    
    if status.get("current_task"):
        # Force complete or unassign
        await report_task_progress(
            agent_id=agent_id,
            task_id=status["current_task"]["task_id"],
            status="blocked",
            message="Worker recovery - releasing task"
        )
```

## Getting Help

If you're still experiencing issues:

1. **Check the logs** with debug enabled
2. **Verify all prerequisites** are met
3. **Try the minimal test cases** in this guide
4. **Report issues** with:
   - Full error messages
   - PM Agent version
   - Python version
   - Operating system
   - Steps to reproduce