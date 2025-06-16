# MVP Task Assignment - Simplified Implementation

## Week 1 Tasks:

### Day 1: Fix MCP Integration
1. Remove broken `columnName` parameters from kanban calls
2. Fix pagination issues in project/board calls  
3. Test actual connection to your kanban MCP server
4. Verify basic CRUD operations work

### Day 2: Implement Agent Registration
```python
# Add to pm_agent_mcp_server.py
@self.server.tool()
async def register_agent(
    agent_id: str,
    name: str,
    role: str,
    skills: List[str]
) -> dict:
    """Simple agent registration"""
    self.agent_status[agent_id] = WorkerStatus(
        worker_id=agent_id,
        name=name,
        role=role,
        email=f"{agent_id}@company.com",
        current_tasks=[],
        completed_tasks_count=0,
        capacity=40,  # Default 40 hours/week
        skills=skills,
        availability={"monday": True, "tuesday": True, "wednesday": True, 
                     "thursday": True, "friday": True},
        performance_score=1.0
    )
    return {"success": True, "message": f"Agent {agent_id} registered"}
```

### Day 3: Simplify Task Assignment
```python
# Simplified version - no complex AI matching
async def _find_optimal_task_for_agent(self, agent_id: str) -> Optional[Task]:
    """MVP: Just return first available task"""
    available_tasks = await self.kanban_client.get_available_tasks()
    
    if not available_tasks:
        return None
    
    # MVP: Return highest priority task
    return max(available_tasks, key=lambda t: 
               {"urgent": 4, "high": 3, "medium": 2, "low": 1}[t.priority.value])
```

### Day 4-5: Test & Polish Basic Flow
1. Test full workflow: register agent → request task → assign task → report progress
2. Fix any remaining API issues
3. Add proper error handling
