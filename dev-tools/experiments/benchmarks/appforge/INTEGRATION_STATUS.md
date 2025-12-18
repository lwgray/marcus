# AppForge Integration Status

## What I Learned

After exploring the AppForge repository, I discovered:

### AppForge Architecture

AppForge is **not** just test files - it's a complete Python evaluation framework:

1. **AppForge Python Package** (`/tmp/AppForge/AppForge/`)
   - `appforge.py`: Main `AppForge` class that manages everything
   - `evaluate_app.py`: The actual test runner (runs inside Docker)
   - `tasks/tasks.json`: All 101 task specifications

2. **How AppForge Works:**
   ```python
   from AppForge import AppForge

   # Initialize with Docker
   evaluator = AppForge(
       runs="my_run",
       use_docker=True,
       docker_name='zenithfocuslight/appforge:latest',
       docker_port=6080
   )

   # Get task description
   task_spec = evaluator.description(task_id=63)
   # Returns: {"task": "Currency", "features": "...", "api_version": "Android 12", "device": "Nexus 4"}

   # Compile the app (from Marcus-generated code)
   compile_error = evaluator.compile_json_based_on_template(changed_files, task_id)

   # Run tests
   result = evaluator.test(task_id)
   # Returns: {"compile": 1, "pass": 1, "pass_rate": 1.0, ...}

   # Cleanup
   evaluator.clean_up()
   ```

3. **What Their Test Does:**
   - Starts Android emulator in Docker
   - Installs the APK
   - Runs automated UI tests (clicks, typing, navigation)
   - Returns pass/fail + detailed results

## What I Did

### ✅ COMPLETED - Ready for Testing!

1. **[task_converter.py](task_converter.py)** - ✅ COMPLETE
   - Fetches from real AppForge `tasks.json`
   - Uses `app_key` and `refined_features` fields
   - Generates proper project_spec.md with detailed feature descriptions

2. **[evaluator.py](evaluator.py)** - ✅ COMPLETE
   - Uses AppForge library with `compile_folder()` method
   - Handles Docker + Android emulator automatically
   - Returns structured results (compile, pass_rate, all_pass, duration)
   - Saves logs and artifacts

3. **[appforge_runner.py](appforge_runner.py)** - ✅ COMPLETE
   - Main CLI orchestrator
   - **MCP-based completion detection** via `query_project_history`
   - Polls Marcus every 30s to check task status
   - Detects completion, timeouts, and stuck states
   - Proper async/await implementation

4. **[reporter.py](reporter.py)** - ✅ COMPLETE
   - HTML report generation
   - Works as-is

5. **docker_runner.py** - ✅ DELETED
   - No longer needed - AppForge handles Docker

6. **Supporting files:** - ✅ COMPLETE
   - requirements.txt (with AppForge + MCP)
   - README.md
   - Example configs
   - .gitignore

### 🎯 Status: READY FOR TESTING

## Next Steps

### 1. Install AppForge Library

The tool needs the AppForge Python package:

```bash
cd /tmp/AppForge
pip install -e .
```

Or add to `requirements.txt`:
```
git+https://github.com/AppForge-Bench/AppForge.git
```

### 2. Update Integration Approach

**Current (Placeholder):**
```python
# docker_runner.py - runs Docker manually
container_id = start_android_emulator()
result = run_appforge_test(...)  # TODO
```

**Proper (Using AppForge):**
```python
# Use AppForge library
from AppForge import AppForge

evaluator = AppForge(
    runs=f"marcus_task_{task_id}",
    base_folder=Path.home() / "appforge_benchmarks" / "runs",
    use_docker=True
)

# AppForge handles:
# - Docker management
# - Emulator startup
# - App compilation
# - Test execution
# - Result parsing
```

### 3. ✅ SOLVED: Format Conversion

**Problem:** Marcus generates full Android projects, AppForge expects JSON changes.

**Solution:** Use AppForge's `compile_folder()` method!

AppForge has a built-in method that accepts directory paths:

```python
from AppForge import AppForge

evaluator = AppForge("marcus_run", use_docker=True)

# Pass Marcus's implementation directory directly
compile_error = evaluator.compile_folder(
    implementation_dir,  # Marcus's full Android project
    task_id
)

# AppForge internally:
# 1. Compares folder to their template
# 2. Extracts differences
# 3. Compiles the APK
```

**No format conversion needed!** See [FORMAT_CONVERSION_ANALYSIS.md](FORMAT_CONVERSION_ANALYSIS.md) for details.

### 4. ✅ SOLVED: Marcus Completion Detection

**Implemented:** HTTP connection to existing Marcus server via Inspector pattern

```python
from worker.inspector import Inspector

# Connect to existing Marcus MCP server via HTTP
client = Inspector(connection_type="http")

async with client.connect(url="http://localhost:4298/mcp") as session:
    # Authenticate as benchmark worker
    await session.call_tool(
        "authenticate",
        arguments={
            "client_id": f"appforge_benchmark_{task_id}",
            "client_type": "worker",
            "role": "benchmark",
            "metadata": {
                "benchmark_type": "appforge",
                "task_id": task_id,
                "connection": "http"
            },
        },
    )

    # Poll Marcus every 30s
    result = await session.call_tool(
        "mcp__marcus__query_project_history",
        arguments={
            "project_id": project_id,
            "query_type": "summary"
        }
    )

    # Check task counts
    task_counts = data["task_counts"]
    if task_counts["DONE"] == task_counts["total"]:
        # All tasks complete!
        return True
```

**Features:**
- Connects to EXISTING Marcus server (not a new subprocess instance)
- Uses Inspector pattern with HTTP connection
- Polls every 30s (configurable)
- Shows live progress updates
- Detects completion, timeouts, and stuck states
- No manual intervention needed
- Authenticates as benchmark worker with proper metadata

## How to Use

### Prerequisites

1. **Install AppForge** (user already has this at `~/dev/AppForge`):
   ```bash
   cd ~/dev/AppForge
   pip install -e .
   ```

2. **Install dependencies:**
   ```bash
   cd dev-tools/experiments/benchmarks/appforge
   pip install -r requirements.txt
   ```

3. **Ensure Docker is running** (for Android emulator):
   ```bash
   docker ps  # Should show running containers
   ```

### Running Benchmarks

**Single benchmark:**
```bash
python appforge_runner.py --task-id 63 --num-agents 5
```

**Compare different agent counts:**
```bash
python appforge_runner.py --task-id 63 --agents 1,3,5,10
```

**Run benchmark suite:**
```bash
python appforge_runner.py --suite configs/example_suite.yaml
```

**Test evaluation only (skip Marcus):**
```bash
python appforge_runner.py --task-id 63 --skip-marcus
```

### Expected Output

```
======================================================================
AppForge Benchmark - Task 63
======================================================================
Agents: 5

[1/4] Converting AppForge task to Marcus format...
  ✓ Fetched task 63: Currency Converter

[2/4] Running Marcus...
  Starting Marcus experiment in: ~/appforge_benchmarks/experiments/task_63_agents_5
  This will open a tmux session with multiple agent panes

Waiting for Marcus to complete...
  ✓ Project created
  Project ID: abc-123
  Tasks created: 8
  Polling Marcus every 30s (timeout: 3600s)...

  [Poll 1] 0/8 done, 0 in progress, 8 todo
  [Poll 2] 2/8 done, 3 in progress, 3 todo
  [Poll 3] 5/8 done, 2 in progress, 1 todo
  [Poll 4] 8/8 done, 0 in progress, 0 todo

  ✓ All tasks completed! (8/8)

[3/4] Evaluating with AppForge tests...
=============================================================
AppForge Benchmark Evaluation - Task 63
=============================================================
Implementation: ~/appforge_benchmarks/experiments/task_63_agents_5/implementation
Timeout: 1800s

[1/4] Initializing AppForge with Docker...
  ✓ Docker container started
  ✓ Android emulator ready

[2/4] Compiling Marcus-generated Android app...
  ✓ Compilation successful

[3/4] Running AppForge automated UI tests...

[4/4] Cleaning up Docker container...
  ✓ Docker container stopped

Total duration: 127.3s

=============================================================
Evaluation Results
=============================================================
Compiled: ✓
Pass Rate: 90.0%
All Tests Passed: ✗

[4/4] Saving results...
  ✓ Results saved to: ~/appforge_benchmarks/results/task_63_agents_5.json

======================================================================
Benchmark Complete
======================================================================
Task ID: 63
Agents: 5
Compiled: ✓
All Tests Passed: ✗
Pass Rate: 90.0%
Duration: 127.3s
Results: ~/appforge_benchmarks/results/task_63_agents_5.json
```

## Current Tool Status

**✅ COMPLETE - Ready for Testing:**
- ✅ Task conversion (reads real AppForge tasks.json)
- ✅ Config generation for Marcus
- ✅ AppForge integration (compile_folder + test)
- ✅ Marcus completion detection (MCP polling)
- ✅ Report generation
- ✅ CLI interface
- ✅ Docker management (handled by AppForge)

**🎯 Next Step:** Test with task 63

## Implementation Details

See companion documents:
- [FORMAT_CONVERSION_ANALYSIS.md](FORMAT_CONVERSION_ANALYSIS.md) - Why no conversion needed
- [README.md](README.md) - User-facing setup and usage guide
