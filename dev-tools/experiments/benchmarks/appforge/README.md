# AppForge Benchmark Tool for Marcus

Standalone tool for evaluating Marcus on [AppForge Benchmarks](https://appforge-bench.github.io/) - Android app development challenges.

**Key Features:**
- 🎯 Automated benchmark execution
- 🔧 Uses modernized AppForge fork with 2024 Android toolchain
- 🐳 Docker-based Android emulator for reproducibility
- 📊 Automated evaluation and scoring
- 📈 HTML report generation
- 🔌 Zero Marcus source code changes (external tool)

**⚠️ Important**: This tool uses the modernized [AppForge_Bench_Modern](https://github.com/lwgray/AppForge_Bench) fork (Gradle 8.9, AGP 8.7, Java 17, API 34). The modern toolchain works directly with Marcus-generated code without any adaptation layer.

---

## Quick Start

**🚀 New to AppForge?** See [QUICK_START.md](QUICK_START.md) for a 30-minute guided setup.

### 1. Install Dependencies

**IMPORTANT**: AppForge requires UI testing dependencies in your Python environment:

```bash
# Install AppForge dependencies
cd dev-tools/experiments/benchmarks/appforge
pip install -r requirements.txt

# Install UI testing dependencies (REQUIRED for test execution)
pip install uiautomator2 opencv-python
```

**Note**: Without `uiautomator2` and `opencv-python`, tests will appear to run but produce empty logs with 2-3 second durations instead of actual test execution (60+ seconds).

### 2. Clone Modern AppForge Fork

```bash
cd ~/dev
git clone https://github.com/lwgray/AppForge_Bench AppForge_Bench_Modern
cd AppForge_Bench_Modern
git checkout modernize-toolchain-2024
```

**Why the modern fork?**
- Original AppForge (2021) uses Gradle 7.2, AGP 7.1.2, API 31
- Marcus generates modern Android code (Material Components, androidx)
- Modern fork (2024) uses Gradle 8.9, AGP 8.7, Java 17, API 34
- Direct compatibility - no adapter needed
- See [MODERNIZATION.md](https://github.com/lwgray/AppForge_Bench/blob/modernize-toolchain-2024/MODERNIZATION.md) in fork

### 3. Setup Docker

Install Docker and pull the AppForge evaluation image:

```bash
docker pull zenithfocuslight/appforge:latest
```

This image includes the Android emulator, AppForge test harness, and compilation tools.

### 4. Run Your First Benchmark

**Terminal 1** - Start Marcus MCP server:
```bash
cd /Users/lwgray/dev/marcus
python -m src.mcp_server.http_server
```

**Terminal 2** - Run benchmark:
```bash
cd dev-tools/experiments/benchmarks/appforge
python appforge_runner.py --task-id 63 --num-agents 5
```

**Terminal 3** - Start Marcus experiment when prompted:
```bash
python dev-tools/experiments/run_experiment.py \
    ~/appforge_benchmarks/experiments/task_63_agents_5
```

See [QUICK_START.md](QUICK_START.md) for detailed instructions.

---

## Usage

### Single Benchmark

```bash
python appforge_runner.py --task-id 63 --num-agents 5
```

**Options:**
- `--task-id`: AppForge task ID (e.g., 63 for Calculator app)
- `--num-agents`: Number of Marcus agents (default: 5)
- `--skip-marcus`: Skip Marcus execution (test evaluation only)

### Compare Agent Configurations

```bash
python appforge_runner.py --task-id 63 --agents 1,3,5,10
```

This runs the same task with 1, 3, 5, and 10 agents and compares results.

### Benchmark Suite

```bash
python appforge_runner.py --suite configs/example_suite.yaml
```

Run multiple tasks with multiple agent configurations.

### Generate Report

```bash
python reporter.py --results-dir ~/appforge_benchmarks/results
```

Creates `appforge_report.html` with summary statistics and detailed results.

---

## How It Works

### Architecture

```
appforge_runner.py
  ↓
  1. Convert AppForge task → Marcus format
     (task_converter.py extracts from task_info.json)
  ↓
  2. Run Marcus experiment
     (uses existing run_experiment.py)
  ↓
  3. Compile with Modern AppForge
     (Gradle 8.9, AGP 8.7 - NO ADAPTER NEEDED)
  ↓
  4. Evaluate with AppForge tests
     (docker_runner.py + evaluator.py)
  ↓
  5. Save results
     (JSON + HTML report)
```

### Workflow

1. **Task Conversion**:
   - Reads `task_info.json` from AppForge task directory
   - Extracts package name, permissions, description
   - Generates Marcus `project_spec.md` with complete requirements
   - Creates `config.yaml` with agent configuration

2. **Marcus Execution**: Runs Marcus multi-agent system using existing `run_experiment.py`

3. **Direct Compilation** (Modern Fork):
   - Marcus generates modern Android code (androidx, Material Components)
   - Modern AppForge fork compiles directly (Gradle 8.9, AGP 8.7, Java 17)
   - **No adapter needed** - tools are compatible by design
   - Supports non-deterministic generation (AI-generated colors, layouts)

4. **Evaluation**:
   - Starts Docker Android emulator
   - Installs generated APK
   - Runs AppForge functional tests (UI automation)
   - Collects pass/fail results, logs, screenshots

5. **Reporting**: Saves structured results and generates HTML report

### Why Modern Fork Matters

**Original AppForge (2021):**
- Gradle 7.2, AGP 7.1.2, Java 8, API 31
- Expects hardcoded resource names
- Required complex adapter to bridge gap

**Modern Fork (2024):**
- Gradle 8.9, AGP 8.7, Java 17, API 34
- Material Components with flexible theming
- Direct Marcus compatibility - cleaner, faster, more reliable

---

## File Structure

```
dev-tools/experiments/benchmarks/appforge/
├── README.md                    # This file
├── QUICK_START.md               # Detailed setup guide
├── requirements.txt             # Python dependencies
├── appforge_runner.py           # Main CLI entry point
├── task_converter.py            # AppForge task_info.json → Marcus format
├── docker_runner.py             # Docker/emulator management
├── evaluator.py                 # Compilation & test execution
├── reporter.py                  # Generate HTML reports
└── configs/
    ├── example_calculator.yaml  # Single task example
    └── example_suite.yaml       # Multi-task suite

# Modern AppForge fork (separate repo)
~/dev/AppForge_Bench_Modern/     # Cloned from github.com/lwgray/AppForge_Bench
├── MODERNIZATION.md             # What changed and why
├── compiler/
│   ├── build.py                 # Compilation with modern toolchain
│   └── templates/
│       └── empty_activity/      # Updated for 2024 (Gradle 8.9, AGP 8.7)
└── tasks/
    └── Mint_calculator/
        ├── task_info.json       # Package name, permissions, description
        └── functional_tests/    # UI test specifications

# Results stored outside Marcus
~/appforge_benchmarks/
├── cache/                       # Cached task specs
├── experiments/                 # Marcus experiment dirs
│   └── task_63_agents_5/
│       └── implementation/      # Marcus-generated Android code
└── results/                     # Benchmark results (JSON + HTML)
```

---

## Configuration Files

### Single Task Example

```yaml
# configs/example_calculator.yaml
marcus_root: "/path/to/marcus"

tasks:
  - id: 63
    name: "Calculator App"
    timeout: 1800

marcus_configs:
  - agents: 5

docker:
  image: "zenithfocuslight/appforge:latest"
  port: 6080
```

### Suite Example

```yaml
# configs/example_suite.yaml
marcus_root: "/path/to/marcus"

tasks:
  - id: 63
    name: "Calculator App"
  - id: 64
    name: "Weather App"

marcus_configs:
  - agents: 1
  - agents: 5
  - agents: 10
```

---

## Understanding Results

### Result JSON Structure

```json
{
  "task_id": 63,
  "num_agents": 5,
  "passed": true,
  "tests_run": 10,
  "tests_passed": 10,
  "duration_seconds": 1245.3,
  "timestamp": "2025-01-15T10:30:00Z",
  "logs": "...",
  "error": null
}
```

### HTML Report

The reporter generates an HTML dashboard with:
- Summary statistics (pass rate, avg duration)
- Detailed results table
- Pass/fail status for each benchmark

---

## Advanced Usage

### Testing Evaluation Only

Skip Marcus execution to test just the evaluation pipeline:

```bash
python appforge_runner.py --task-id 63 --skip-marcus
```

### Custom Output Directory

```bash
python appforge_runner.py \
    --task-id 63 \
    --output-dir ~/my-benchmarks/experiment-1
```

### Viewing Emulator (VNC)

Connect to the running emulator:

```bash
# Install VNC viewer
open vnc://localhost:5900
```

---

## Troubleshooting

### Docker Issues

**Problem**: "Cannot connect to Docker daemon"
```bash
# Start Docker Desktop or Docker service
sudo systemctl start docker
```

**Problem**: "Port 5900 already in use"
```bash
# Kill existing containers
docker ps -a | grep android | awk '{print $1}' | xargs docker rm -f
```

### Emulator Issues

**Problem**: "Emulator not ready within timeout"
- Increase timeout: `--timeout 600` (10 minutes)
- Check Docker resources (RAM, CPU)
- Try different emulator image

### Marcus Issues

**Problem**: "Marcus experiment failed"
- Check Marcus logs in experiment directory
- Verify `run_experiment.py` works standalone
- Check Marcus dependencies are installed

---

## Current Status & Limitations

### ✅ Working
- Modern AppForge fork compiles Marcus code directly (no adapter)
- Full AppForge test suite execution (UI automation)
- Docker-based evaluation environment
- Result collection and reporting

### ⚠️ Known Issues
1. **Package Name Extraction**: Task converter must read `package_name` from `task_info.json` and include in Marcus project spec
2. **Completion Detection**: Requires manual confirmation when Marcus finishes
3. **Parallel Execution**: Not yet implemented (run benchmarks sequentially)
4. **Dependency Documentation**: `uiautomator2` and `opencv-python` must be installed in your Python environment

---

## Why a Standalone Tool?

This tool is **intentionally separate** from Marcus core:

✅ **No Marcus maintenance burden**: Can be updated/removed independently
✅ **Optional dependency**: Don't need AppForge/Docker unless benchmarking
✅ **Simple interface**: Uses Marcus via CLI (subprocess calls)
✅ **Easy to extend**: Copy this pattern for other benchmarks (SWE-bench, etc.)

---

## Contributing

To add support for new AppForge tasks:

1. Add task ID to `configs/example_suite.yaml`
2. Test with `python appforge_runner.py --task-id NEW_ID`
3. Update this README with task details

---

## Testing Plan & Leaderboard Submission

For comprehensive evaluation guidance, see:

- **[TESTING_PLAN.md](TESTING_PLAN.md)** - Structured 3-phase evaluation protocol
- **[LEADERBOARD_SUBMISSION.md](LEADERBOARD_SUBMISSION.md)** - How to submit results

**Quick Summary:**
- **Phase 1** (1-2 days): Validate with 3 tasks
- **Phase 2** (1-2 weeks): Representative sampling (15-20 tasks)
- **Phase 3** (4-6 weeks): Full evaluation (101 tasks)

---

## References

- [AppForge Benchmarks](https://appforge-bench.github.io/)
- [AppForge Research Paper](https://arxiv.org/abs/2510.07740)
- [AppForge GitHub](https://github.com/AppForge-Bench/AppForge)
- [Marcus Documentation](../../docs/)

---

## License

Same as Marcus project license.
