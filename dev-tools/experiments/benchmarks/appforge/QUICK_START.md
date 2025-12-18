# AppForge Benchmark - Quick Start Guide

Get Marcus running on AppForge benchmarks in **under 30 minutes**.

---

## Prerequisites (5 minutes)

### 1. Check Python Version
```bash
python --version  # Should be Python 3.11+
```

### 2. Install Docker
```bash
# macOS
brew install --cask docker

# Linux (Ubuntu/Debian)
sudo apt-get install docker.io

# Verify installation
docker --version
docker ps  # Should run without errors
```

### 3. Pull AppForge Docker Image
```bash
docker pull zenithfocuslight/appforge:latest
```

**Note**: This is the official AppForge evaluation image. It includes the Android emulator, test harness, and compilation tools needed for benchmarking.

---

## Installation (10 minutes)

### 1. Install Marcus Dependencies
```bash
cd /path/to/marcus  # Your Marcus installation directory
pip install -r requirements.txt
```

### 2. Clone Modern AppForge Fork

**Why?** Original AppForge uses 2021 tooling (Gradle 7.2, Java 8). Marcus generates modern Android code. The modern fork (2024 tooling) compiles Marcus code directly without adaptation.

```bash
cd ~/dev
git clone https://github.com/lwgray/AppForge_Bench AppForge_Bench_Modern
cd AppForge_Bench_Modern
git checkout modernize-toolchain-2024
```

**What changed in the modern fork:**
- Gradle 7.2 → 8.9
- Android Gradle Plugin 7.1.2 → 8.7
- Java 8 → 17
- API Level 31 → 34
- Added Kotlin support (1.9.22)
- Material Components with flexible theming (supports AI-generated colors)

See [MODERNIZATION.md](https://github.com/lwgray/AppForge_Bench/blob/modernize-toolchain-2024/MODERNIZATION.md) for details.

### 3. Install AppForge Tool Dependencies
```bash
cd /path/to/marcus/dev-tools/experiments/benchmarks/appforge
pip install -r requirements.txt

# CRITICAL: Install UI testing dependencies
pip install uiautomator2 opencv-python
```

**Important**: `uiautomator2` and `opencv-python` are required for test execution. Without them, tests will appear to run but produce empty logs with 2-3 second durations instead of actual test execution (60+ seconds).

### 4. Install AppForge Library
```bash
cd ~/dev/AppForge_Bench_Modern
pip install -e .
```

---

## Run Your First Benchmark (15 minutes)

### Step 1: Start Marcus MCP Server

**Terminal 1** - Start Marcus server:
```bash
cd /Users/lwgray/dev/marcus
python -m src.mcp_server.http_server
```

Keep this terminal open. You should see:
```
Marcus MCP Server running on http://localhost:4298
```

### Step 2: Run AppForge Benchmark

**Terminal 2** - Run benchmark:
```bash
cd /Users/lwgray/dev/marcus/dev-tools/experiments/benchmarks/appforge

# Run Calculator app benchmark (Task 63)
python appforge_runner.py --task-id 63 --num-agents 5
```

This will:
1. Convert AppForge task 63 to Marcus format
2. Wait for you to start Marcus experiment
3. Monitor progress every 30 seconds
4. Evaluate with AppForge tests when complete

### Step 3: Start Marcus Experiment

**Terminal 3** - After appforge_runner.py is waiting, start Marcus:
```bash
cd /Users/lwgray/dev/marcus

# appforge_runner.py will show the experiment directory
# Example: ~/appforge_benchmarks/experiments/task_63_agents_5
python dev-tools/experiments/run_experiment.py \
    ~/appforge_benchmarks/experiments/task_63_agents_5
```

### Step 4: Wait for Results

Watch Terminal 2 for progress updates:
```
Waiting for Marcus to complete...
  ✓ Project created
  Project ID: abc-123
  Tasks created: 8
  Polling Marcus every 30s (timeout: 3600s)...

  [Poll 1] 0/8 done, 0 in progress, 8 todo
  [Poll 2] 2/8 done, 3 in progress, 3 todo
  ...
  [Poll 8] 8/8 done, 0 in progress, 0 todo

  ✓ All tasks completed! (8/8)

[3/4] Evaluating with AppForge tests...
```

### Step 5: View Results

Results saved to:
```
~/appforge_benchmarks/results/task_63_agents_5.json
```

---

## What Just Happened?

1. **Task Conversion**: AppForge task 63 (Calculator) converted to Marcus format
2. **Marcus Execution**: 5 agents collaborated to build Android app
3. **Completion Detection**: Tool monitored Marcus via MCP server
4. **AppForge Evaluation**: Generated app tested in Docker Android emulator
5. **Results**: Metrics saved (compile, test_pass, crash, functional_success)

---

## Next Steps

### Run More Benchmarks

**Different task**:
```bash
python appforge_runner.py --task-id 45 --num-agents 5  # Unit Converter
```

**Compare agent configurations**:
```bash
python appforge_runner.py --task-id 63 --agents 1,3,5,10
```

**Run a suite**:
```bash
python appforge_runner.py --suite configs/example_suite.yaml
```

### View Results

```bash
# Generate HTML report
python reporter.py --results-dir ~/appforge_benchmarks/results

# Open in browser
open appforge_report.html
```

---

## Troubleshooting

### Problem: "Cannot connect to Marcus MCP server"

**Solution**: Make sure Marcus server is running in Terminal 1:
```bash
cd /Users/lwgray/dev/marcus
python -m src.mcp_server.http_server
```

### Problem: "Docker daemon not running"

**Solution**: Start Docker Desktop or Docker service:
```bash
# macOS: Open Docker Desktop app

# Linux:
sudo systemctl start docker
```

### Problem: "AppForge module not found"

**Solution**: Install AppForge library:
```bash
cd ~/dev/AppForge
pip install -e .
```

### Problem: "Timeout waiting for project creation"

**Solution**: Check Terminal 3 (Marcus experiment). Look for errors in logs.

### Problem: "Port 5900 already in use"

**Solution**: Kill existing Android emulator containers:
```bash
docker ps -a | grep android | awk '{print $1}' | xargs docker rm -f
```

---

## File Locations

### Input Files
- **Task specs**: Cached in `~/appforge_benchmarks/cache/`
- **Marcus configs**: `~/appforge_benchmarks/experiments/task_*/`

### Output Files
- **Results JSON**: `~/appforge_benchmarks/results/task_*_agents_*.json`
- **Marcus logs**: `~/appforge_benchmarks/experiments/task_*/logs/`
- **Implementation**: `~/appforge_benchmarks/experiments/task_*/implementation/`
- **HTML reports**: Current directory (`appforge_report.html`)

---

## Understanding Results

### Result JSON Structure
```json
{
  "task_id": 63,
  "num_agents": 5,
  "compile": true,           // ✓ APK compiled successfully
  "test_pass": true,          // ✓ Passed functional tests
  "crash": false,             // ✓ No crashes during stress test
  "functional_success": false, // ✗ Not all tests passed (80%)
  "pass_rate": 0.80,
  "duration_seconds": 1245.3
}
```

### Metrics Explained

- **Compile**: Did the generated code compile into a valid APK?
- **Test Pass**: Did it pass AppForge's automated functional tests?
- **Crash**: Did it crash during stress testing?
- **Functional Success**: Compiled + all tests passed + no crash

---

## Phase 1 Validation Checklist

Complete these 3 tasks to validate your setup:

- [ ] Task 63 (Calculator) - Beginner
- [ ] Task 45 (Unit Converter) - Intermediate
- [ ] Task 12 (Weather App) - Advanced

**Expected Results**:
- At least 1 task should compile
- 0-1 tasks may fully succeed (this is normal!)
- If 0 tasks compile, check Docker logs

---

## Ready for More?

**Comprehensive Testing Plan**: See [TESTING_PLAN.md](TESTING_PLAN.md)
- Phase 1: Validation (3 tasks) - ✓ You just completed this!
- Phase 2: Representative sampling (15-20 tasks) - 1-2 weeks
- Phase 3: Full evaluation (101 tasks) - 4-6 weeks

**Leaderboard Submission**: See [LEADERBOARD_SUBMISSION.md](LEADERBOARD_SUBMISSION.md)
- How to format results
- How to contact AppForge team
- How to publish on your website

---

## Questions?

- **AppForge Issues**: https://github.com/AppForge-Bench/AppForge/issues
- **Marcus Issues**: https://github.com/yourusername/marcus/issues
- **Documentation**: [README.md](README.md)

---

**Last Updated**: 2025-12-17
