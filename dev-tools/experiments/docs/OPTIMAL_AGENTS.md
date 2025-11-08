# Optimal Agent Configuration for Experiments

## The Problem

When running Marcus experiments, you face a critical timing issue:

1. **Static Configuration**: Experiments require pre-configured agent counts in `config.yaml`
2. **Dynamic Dependencies**: Actual task parallelism depends on dependency graph
3. **The Gap**: If you spawn 18 agents but only 5 can work immediately:
   - 13 agents get "no tasks available"
   - Without smart wait times, they poll repeatedly
   - Agents may exceed retry limits and die
   - Resources wasted on idle LLM instances ($$$)
   - Agents exit before their dependencies resolve

**Example Scenario:**

```
Time 0:00 → Project created with 100 tasks
         → 18 agents spawned
         → Only 8 root tasks (no dependencies)
         → 10 agents immediately blocked

Time 0:05 → 10 agents retry (no tasks available)
Time 0:10 → 10 agents retry again
Time 0:15 → 10 agents retry again (3rd attempt)
Time 0:20 → 10 agents give up and exit ❌

Time 0:30 → First wave of 8 tasks complete
         → 15 new tasks now available
         → But only 8 agents left! 😱
```

## The Solution: Test First

Use `test_optimal_agents.py` to determine optimal configuration **before** running experiments.

### Workflow

#### 1. Create Experiment Structure

```bash
cd /Users/lwgray/dev/worktrees/independent-tasks/experiments
python run_experiment.py --init ~/experiments/my-project
```

#### 2. Configure Initial Setup

Edit `~/experiments/my-project/config.yaml` with reasonable guesses:

```yaml
project_name: "My Project"
project_spec_file: "project_spec.md"

agents:
  - id: "agent_backend"
    name: "Backend Developer"
    role: "backend"
    skills: ["python", "fastapi"]
    subagents: 5  # Initial guess
```

Edit `~/experiments/my-project/project_spec.md` with detailed requirements.

#### 3. Test Optimal Agent Count

```bash
python test_optimal_agents.py ~/experiments/my-project
```

**What this does:**
1. Creates the project in Marcus/Planka (generates tasks)
2. Analyzes task dependency graph with CPM algorithm
3. Calculates maximum parallelism at each time point
4. Shows optimal agent count and timeline

**Example Output:**

```
═══════════════════════════════════════════════════════════════════
OPTIMAL AGENT ANALYSIS
═══════════════════════════════════════════════════════════════════

📊 Project Analysis:
   Total tasks: 87
   Critical path: 12.50 hours
   Max parallelism: 12 tasks can run simultaneously
   Efficiency gain: 85.6% vs single agent

✅ RECOMMENDED: 12 agents
   (Based on peak parallelism - agents will idle during low-demand periods)

⚙️  Current config.yaml: 18 total agents
   - Backend Developer: 5 subagents + 1 main = 6 total
   - Frontend Developer: 6 subagents + 1 main = 7 total
   - QA Engineer: 4 subagents + 1 main = 5 total

⚠️  WARNING: You have 6 more agents than needed
   Extra agents will be idle, wasting resources

📈 Parallelism Timeline:
   (Shows how many tasks can run at different time points)

   Time (h) │ Tasks │ Utilization
   ─────────┼───────┼────────────
      0.00  │    8  │  67% ██████
      2.50  │   12  │ 100% ██████████
      5.00  │   10  │  83% ████████
      7.50  │    6  │  50% █████
     10.00  │    4  │  33% ███
     12.50  │    1  │   8% █
```

#### 4. Update Configuration

The script offers to auto-update your `config.yaml`:

```bash
💾 Update config.yaml with optimal settings? [y/N]: y
✅ Backed up original to: config.yaml.backup
✅ Updated config.yaml with optimal agent configuration

🚀 Ready to run experiment:
   python run_experiment.py ~/experiments/my-project
```

**Updated config.yaml:**

```yaml
agents:
  - id: "agent_backend"
    name: "Backend Developer"
    role: "backend"
    skills: ["python", "fastapi"]
    subagents: 4  # Reduced from 5

  - id: "agent_frontend"
    name: "Frontend Developer"
    role: "frontend"
    skills: ["react", "typescript"]
    subagents: 4  # Reduced from 6

  - id: "agent_qa"
    name: "QA Engineer"
    role: "qa"
    skills: ["pytest", "testing"]
    subagents: 2  # Reduced from 4

# Total: 12 agents (4+1 + 4+1 + 2+1)
```

#### 5. Run Experiment with Optimal Configuration

```bash
python run_experiment.py ~/experiments/my-project
```

Now you spawn exactly the right number of agents!

## Understanding the Analysis

### Critical Path

**Definition**: The longest chain of dependent tasks

**Example:**
```
Task A (2h) → Task B (3h) → Task C (1h) = 6 hours critical path
Task D (4h) ↗

Max parallelism: 2 (Task A+D can run in parallel)
```

Even with 100 agents, you can't finish faster than 6 hours due to dependencies.

### Max Parallelism

**Definition**: Maximum number of tasks that can run simultaneously at any point

**Why it matters:**
- More agents than max parallelism = wasted resources
- Fewer agents than max parallelism = missed opportunity

Marcus uses **peak parallelism** strategy:
- Provision for maximum concurrent tasks
- Accept that agents idle during low-demand periods
- Better than bottlenecks (can't dynamically scale agents)

### Utilization Timeline

Shows how agent utilization changes over project lifetime:

```
Time 0-2h:   67% utilization (8/12 agents working)
Time 2-5h:  100% utilization (12/12 agents working)  ← Peak demand
Time 5-8h:   83% utilization (10/12 agents working)
Time 8-12h:  50% utilization (6/12 agents working)
Time 12h+:   33% utilization (4/12 agents working)
```

**Key insight**: Peak happens mid-project when most dependencies are resolved.

## The Connection to Smart Wait Times

Even with optimal agent count, agents still experience waiting periods:

**Scenario 1: Early Project (Low Utilization)**
- 8/12 agents working
- 4 agents get "no tasks available"
- Need to wait ~2 hours for first wave to complete

**Scenario 2: Between Dependency Waves**
- Task A completes at 2:15
- Task B depends on A, starts immediately
- Task C depends on B, must wait ~3 hours

**Without smart wait times:**
```python
response = {"success": False, "message": "No suitable tasks available"}
# Agent doesn't know how long to wait!
# Might retry every 10 seconds (wasteful)
# Might give up after 3 retries (premature)
```

**With smart wait times:**
```python
response = {
    "success": False,
    "message": "No suitable tasks available",
    "wait_seconds": 270  # 4.5 minutes based on Memory data
}
# Agent knows: "Wait ~4.5 minutes, then retry"
# Reduces pointless API calls
# Prevents premature exits
```

## Best Practices

### 1. Always Test First

❌ **Don't:**
```bash
# Guess agent count
vim config.yaml  # "Hmm, maybe 20 agents?"
python run_experiment.py ~/experiments/my-project
# 15 agents die waiting, 5 agents overloaded
```

✅ **Do:**
```bash
# Test first
python test_optimal_agents.py ~/experiments/my-project
# Update config.yaml with recommendation
python run_experiment.py ~/experiments/my-project
```

### 2. Match Agent Skills to Task Labels

Optimal count assumes agents can handle assigned tasks:

```yaml
# Backend tasks labeled: python, api, database
agents:
  - role: "backend"
    skills: ["python", "fastapi", "postgresql"]  # ✅ Matches labels

# Frontend tasks labeled: react, typescript, ui
agents:
  - role: "frontend"
    skills: ["react", "typescript", "tailwind"]  # ✅ Matches labels
```

If skills don't match, agents won't be assigned eligible tasks!

### 3. Monitor First Run

Watch terminal windows during first run:
- Are agents getting tasks?
- How long do "no tasks available" periods last?
- Do agents complete work and request next task?

If agents die prematurely, you likely need:
1. Smart wait times (being implemented)
2. Longer retry timeouts
3. Better skill matching

### 4. Iterate on Complex Projects

For projects with >150 tasks:
1. Test with simplified spec first
2. Validate optimal count makes sense
3. Expand spec gradually
4. Re-test if adding major features

## FAQ

### Q: Why not just spawn 50 agents to be safe?

**A: Cost and coordination overhead**
- Each agent is a Claude Code instance ($$$)
- Idle agents still poll Marcus (~1 request/30s)
- More agents = more git conflicts to resolve
- More terminal windows to monitor

Optimal means "enough to handle peak demand, not more."

### Q: What if my project has 200 tasks but max parallelism is 5?

**A: You only need 5 agents!**

Many tasks are sequential:
```
Foundation (20 tasks) → Auth (30 tasks) → API (50 tasks) → Tests (100 tasks)
```

Even with 200 tasks, if max 5 can run simultaneously, 5 agents is optimal.

### Q: Can I run multiple experiments with the same Marcus instance?

**A: Yes, but be careful with agent count**

If Marcus has 2 projects:
- Project A: 10 optimal agents
- Project B: 8 optimal agents
- Total: 18 agents pulling from different projects

Marcus coordinates, but monitor resource usage.

### Q: What if test says 25 agents but I can only afford 10?

**A: Run with fewer agents**

The project will take longer (closer to critical path + overhead), but it will still complete. You'll see more "no tasks available" responses as agents wait for work.

With smart wait times, this is viable. Without them, agents might die.

### Q: How often should I re-test?

**A: When project scope changes significantly**

Re-test if you:
- Add major new features (10+ tasks)
- Change dependency structure
- Modify task granularity
- See poor utilization in experiments

## Implementation Status

### ✅ Completed
- CPM-based optimal agent calculation (`scheduler.py`)
- MCP tool `get_optimal_agent_count`
- Test script `test_optimal_agents.py`

### 🚧 In Progress
- Smart wait times in `request_next_task` response
- Memory system training data collection

### 📋 Future Work
- Dynamic agent spawning (spawn optimal count automatically)
- Real-time utilization monitoring
- Adaptive retry strategies based on utilization
- Agent pool management (spawn more if utilization >90%)

## Related Documentation

- [Experiments README](README.md) - Main experiments documentation
- [Scheduler CPM](../src/marcus_mcp/coordinator/scheduler.py) - Algorithm details
- [Memory System](../src/core/memory.py) - Task duration learning
- [Task Assignment](../src/marcus_mcp/tools/task.py) - request_next_task implementation

## Need Help?

If you encounter issues:
1. Check Marcus server logs
2. Review agent terminal windows for errors
3. Use `diagnose_project` MCP tool for gridlock detection
4. Report issues at [GitHub](https://github.com/lwgray/marcus/issues)
