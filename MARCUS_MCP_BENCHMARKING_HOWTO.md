# How to Benchmark Marcus MCP Server: Testing Guide for Coding Agents

## Overview

Marcus is a Model Context Protocol (MCP) server that coordinates software development by receiving commands from coding agents (like Claude, GPT-4, etc.). This guide explains how to benchmark Marcus's performance as an MCP orchestration layer.

## Understanding Marcus as an MCP Server

### Architecture
```
[Claude/GPT-4 Agent] --MCP--> [Marcus Server] ---> [Planka Board]
                                    |
                                    v
                              [Task Analysis]
                              [Agent Matching]  
                              [Progress Tracking]
```

### Key Points
- Marcus is NOT an agent itself - it's a coordination server
- Coding agents connect to Marcus via MCP protocol
- Marcus manages task state on kanban boards (Planka, GitHub, etc.)
- Agents request work and report progress through MCP commands

## Prerequisites

1. **Marcus MCP Server Running**
```bash
cd /path/to/marcus
python -m marcus.mcp.server --port 3333
```

2. **MCP-Compatible Coding Agent**
- Claude with MCP tools enabled
- Custom agent using MCP client library
- Test harness that simulates MCP requests

3. **Kanban Board Setup**
- Planka instance with test project
- Board ID configured in marcus.config.json

## Test Scenario 1: MCP Command Performance

### What This Tests
- MCP request/response latency
- Command processing throughput
- Concurrent agent handling

### Setup Test Client
```python
# mcp_benchmark_client.py
from marcus.mcp import MCPTestClient
import asyncio
import time

async def benchmark_mcp_commands():
    client = MCPTestClient("localhost:3333")
    
    # Test 1: Request task assignment
    start = time.time()
    response = await client.send_command({
        "method": "marcus.request_task",
        "params": {
            "agent_id": "test-agent-1",
            "capabilities": ["python", "testing"]
        }
    })
    latency = (time.time() - start) * 1000
    print(f"Task request latency: {latency:.2f}ms")
    
    # Test 2: Report progress
    await client.send_command({
        "method": "marcus.update_progress",
        "params": {
            "task_id": response["task_id"],
            "progress": 50,
            "message": "Halfway complete"
        }
    })
    
    # Test 3: Complete task
    await client.send_command({
        "method": "marcus.complete_task",
        "params": {
            "task_id": response["task_id"],
            "results": {"tests_passed": True}
        }
    })

# Run benchmark
asyncio.run(benchmark_mcp_commands())
```

### Expected Performance
- Task request: < 100ms latency
- Progress update: < 50ms latency  
- Task completion: < 75ms latency

## Test Scenario 2: Multi-Agent Coordination

### What This Tests
- Concurrent agent handling
- Task distribution fairness
- Coordination overhead

### Simulate Multiple Agents
```python
# multi_agent_test.py
import asyncio
from marcus.mcp import MCPTestClient

async def simulate_agent(agent_id, num_tasks):
    client = MCPTestClient("localhost:3333")
    completed = 0
    
    for _ in range(num_tasks):
        # Request task
        task = await client.send_command({
            "method": "marcus.request_task",
            "params": {"agent_id": agent_id}
        })
        
        # Simulate work
        await asyncio.sleep(1)  # Simulate 1 second of work
        
        # Complete task
        await client.send_command({
            "method": "marcus.complete_task",
            "params": {
                "task_id": task["task_id"],
                "results": {"completed_by": agent_id}
            }
        })
        completed += 1
    
    return completed

async def run_multi_agent_test():
    # Create 10 agents, each trying to complete 5 tasks
    agents = [simulate_agent(f"agent-{i}", 5) for i in range(10)]
    
    start = time.time()
    results = await asyncio.gather(*agents)
    duration = time.time() - start
    
    print(f"Total tasks completed: {sum(results)}")
    print(f"Time taken: {duration:.2f}s")
    print(f"Tasks per second: {sum(results)/duration:.2f}")
```

### Metrics to Track
- Tasks distributed per agent (should be roughly equal)
- Total throughput (tasks/second)
- Any failed task requests
- Queue wait times

## Test Scenario 3: MCP Protocol Compliance

### What This Tests
- Correct MCP message format handling
- Error response compliance
- Protocol version compatibility

### Protocol Test Suite
```python
# mcp_protocol_test.py
async def test_mcp_compliance():
    client = MCPTestClient("localhost:3333")
    
    # Test 1: Invalid method
    response = await client.send_command({
        "method": "marcus.invalid_method",
        "params": {}
    })
    assert response["error"]["code"] == -32601  # Method not found
    
    # Test 2: Missing required params
    response = await client.send_command({
        "method": "marcus.request_task",
        "params": {}  # Missing agent_id
    })
    assert response["error"]["code"] == -32602  # Invalid params
    
    # Test 3: Batch requests
    batch_response = await client.send_batch([
        {"method": "marcus.get_status", "params": {}},
        {"method": "marcus.list_tasks", "params": {"status": "pending"}}
    ])
    assert len(batch_response) == 2
```

## Test Scenario 4: Real Coding Agent Integration

### What This Tests
- End-to-end workflow with actual coding agents
- Task completion quality
- Human-AI handoff effectiveness

### Setup with Claude
```python
# In your Claude MCP configuration
{
    "mcpServers": {
        "marcus": {
            "command": "python",
            "args": ["-m", "marcus.mcp.server"],
            "env": {
                "MARCUS_CONFIG": "/path/to/marcus.config.json"
            }
        }
    }
}
```

### Test Workflow
1. Create test project with 20 varied tasks in Planka
2. Connect Claude to Marcus MCP server
3. Have Claude request and complete tasks
4. Measure:
   - Time to complete all tasks
   - Success rate
   - Quality of completions
   - Any coordination failures

## Test Scenario 5: Stress Testing

### What This Tests
- Maximum concurrent agents supported
- Performance degradation under load
- Resource usage (CPU, memory)

### Load Test Script
```bash
# marcus_load_test.sh
#!/bin/bash

# Start Marcus with monitoring
python -m marcus.mcp.server --metrics-port 9090 &
MARCUS_PID=$!

# Launch agent simulators
for i in {1..100}; do
    python mcp_agent_simulator.py --agent-id "load-test-$i" &
done

# Monitor for 10 minutes
sleep 600

# Collect metrics
curl http://localhost:9090/metrics > load_test_metrics.txt

# Cleanup
kill $MARCUS_PID
killall python mcp_agent_simulator.py
```

### Metrics to Monitor
- MCP request queue depth
- Response time percentiles (p50, p95, p99)
- Memory usage growth
- CPU utilization
- Database connection pool usage

## Benchmarking Against Alternatives

### vs Direct Agent Coordination
Compare Marcus MCP coordination with agents talking directly to each other:

```python
# Benchmark: Marcus coordination
marcus_time = await benchmark_with_marcus(num_agents=5, num_tasks=50)

# Benchmark: Direct agent-to-agent
direct_time = await benchmark_direct_coordination(num_agents=5, num_tasks=50)

print(f"Marcus advantage: {(direct_time/marcus_time - 1) * 100:.1f}% faster")
```

### vs Traditional Task Assignment
Compare with human-managed task boards:

1. Set up identical task sets
2. Measure time from task creation to completion
3. Track assignment accuracy (right agent for the job)
4. Compare coordination overhead

### vs Other MCP Servers
If other MCP orchestration servers exist:

1. Implement same MCP methods
2. Run identical workloads
3. Compare latency, throughput, and reliability

## Collecting Results

### Metrics Export
```python
# Marcus exposes Prometheus metrics
import requests

metrics = requests.get("http://localhost:9090/metrics").text
# Parse metrics for:
# - marcus_mcp_requests_total
# - marcus_mcp_request_duration_seconds
# - marcus_tasks_assigned_total
# - marcus_agents_active
```

### Generate Report
```python
# benchmark_report.py
from marcus.benchmarking import BenchmarkReport

report = BenchmarkReport()
report.add_scenario("MCP Performance", mcp_results)
report.add_scenario("Multi-Agent", multi_agent_results)
report.add_scenario("Load Test", load_test_results)
report.generate_pdf("marcus_benchmark_results.pdf")
```

## Common MCP Benchmarking Pitfalls

### 1. Not Testing Concurrent Access
❌ Don't: Test with single agent
✅ Do: Always test with multiple concurrent agents

### 2. Ignoring Network Latency
❌ Don't: Only test on localhost
✅ Do: Test with realistic network conditions

### 3. Unrealistic Task Simulation
❌ Don't: Use instant task completion
✅ Do: Simulate realistic work durations

### 4. Missing Error Scenarios
❌ Don't: Only test happy path
✅ Do: Test agent failures, disconnections, invalid requests

## Debugging Performance Issues

### Enable Debug Logging
```bash
MARCUS_LOG_LEVEL=DEBUG python -m marcus.mcp.server
```

### Profile MCP Handler
```python
# In marcus/mcp/handlers.py
import cProfile

profiler = cProfile.Profile()
profiler.enable()
# ... handle MCP request ...
profiler.disable()
profiler.dump_stats("mcp_profile.stats")
```

### Monitor MCP Queue
```bash
# Check if requests are queueing
curl http://localhost:8000/api/mcp/queue/status
```

## Publishing Results

When sharing Marcus MCP benchmarks:

1. **Specify MCP Version**: Marcus implements MCP v1.0
2. **Document Agent Types**: Which coding agents were tested
3. **Include Task Complexity**: Not all tasks are equal
4. **Share Raw MCP Logs**: For reproducibility
5. **Compare Fairly**: Same tasks, same agents, different coordinators

## Quick Start Checklist

- [ ] Marcus MCP server running
- [ ] Test agents can connect via MCP
- [ ] Planka board has test tasks
- [ ] Monitoring enabled (Prometheus/Grafana)
- [ ] Baseline metrics recorded
- [ ] Load test scripts ready
- [ ] Results collection automated

Remember: Marcus's value isn't just raw MCP performance, but intelligent coordination that improves project outcomes through better task-agent matching and progress tracking.