# Marcus on AppForge: Comprehensive Testing Plan

## Executive Summary

This document outlines a structured testing protocol for evaluating Marcus (multi-agent software development system) on the AppForge benchmark suite. AppForge consists of 101 real-world Android app development tasks designed to evaluate LLM-based code generation systems.

**Key Objectives:**
1. Validate Marcus's Android development capabilities
2. Establish baseline performance metrics
3. Generate publishable results for website and research community
4. Potentially submit results to AppForge leaderboard

**Expected Timeline:**
- Phase 1 (Validation): 1-2 days
- Phase 2 (Representative Sampling): 1-2 weeks
- Phase 3 (Full Evaluation): 4-6 weeks

---

## Background: AppForge Benchmark

### What is AppForge?

AppForge is a benchmark suite of 101 real-world Android application development tasks extracted from F-Droid repositories. Each task requires:

1. **Code Generation**: Create complete Android app source code
2. **Compilation**: Generate valid APK file
3. **Functional Testing**: Pass automated UI/functional tests
4. **Stress Testing**: Handle edge cases without crashes

### Current State-of-the-Art Performance

From the AppForge research paper (arXiv:2510.07740v1):

| Model | Functional Success Rate | Compilation Rate | Test Pass Rate |
|-------|------------------------|------------------|----------------|
| **GPT-5** | 18.8% | 60.4% | 31.2% |
| GPT-4o | 9.9% | 35.6% | 27.7% |
| Claude Sonnet 3.5 | 7.9% | 27.7% | 28.6% |
| GPT-4 Turbo | 4.0% | 18.8% | 20.0% |

**Key Insights:**
- Even best models achieve <20% success rate
- ~40% of compilation errors are Android resource linking issues
- Lower LOC tasks (<400 lines) have higher success rates
- Iterative refinement with feedback improves results by ~2-5%

### Evaluation Metrics

AppForge reports four primary metrics:

1. **Compilation Rate**: Percentage of tasks that compile into valid APK
2. **Test Pass Rate**: Percentage of compiled apps passing functional tests
3. **Crash Rate**: Percentage of apps crashing during stress testing
4. **Functional Success Rate**: Percentage of tasks with both compilation AND all tests passed

---

## Phase 1: Validation (1-2 Days)

### Objective
Verify that Marcus + AppForge integration works correctly before large-scale evaluation.

### Tasks to Run

Select **3 tasks** across difficulty levels:

| Task ID | App Name | Difficulty | LOC Range | Rationale |
|---------|----------|------------|-----------|-----------|
| **63** | Calculator | Beginner | 200-300 | Simple UI, arithmetic logic |
| **45** | Unit Converter | Intermediate | 300-400 | Multiple screens, data handling |
| **12** | Weather App | Advanced | 500-700 | API integration, async operations |

### Agent Configurations

Test with **single agent configuration**:
- 5 agents (Marcus default)

### Success Criteria

✅ All 3 tasks complete without tool crashes
✅ AppForge evaluation runs successfully
✅ Results saved in expected JSON format
✅ All metrics (compile, test_pass, crash, success) recorded

### Expected Outcomes

- **Best case**: 1-2 tasks compile, 0-1 task fully succeeds
- **Worst case**: 0 tasks compile (indicates integration issue)
- **Likely**: 1 task compiles, 0 tasks fully succeed (typical for first attempt)

### Time Estimate

- Per task: 1-2 hours (Marcus execution) + 30 minutes (evaluation)
- Total: **6-9 hours** (run sequentially)

---

## Phase 2: Representative Sampling (1-2 Weeks)

### Objective
Establish baseline Marcus performance across representative task distribution.

### Task Selection Strategy

Select **15-20 tasks** using stratified sampling:

#### By Difficulty Level
- **Beginner** (37% of benchmark): 6-7 tasks
- **Intermediate** (48% of benchmark): 7-9 tasks
- **Advanced** (15% of benchmark): 2-4 tasks

#### By LOC (Lines of Code)
Based on paper's Figure 6 showing LOC vs success rate correlation:
- **Low LOC** (<300): 5-6 tasks (higher expected success)
- **Medium LOC** (300-500): 7-8 tasks
- **High LOC** (>500): 3-4 tasks (lower expected success)

#### By App Category
Ensure diverse functionality:
- **Utilities** (calculators, converters): 4-5 tasks
- **Productivity** (notes, to-do): 3-4 tasks
- **Data/Network** (weather, API clients): 3-4 tasks
- **Media** (image viewers, music players): 2-3 tasks
- **Games** (simple games): 1-2 tasks

### Agent Configuration Experiments

Test **3 agent configurations** per task:
1. **Single Agent** (1 agent): Baseline for comparison
2. **Small Team** (3 agents): Collaboration vs coordination overhead
3. **Standard Team** (5 agents): Marcus default configuration

**Why test multiple configurations?**
- Validate whether multi-agent provides advantage for Android development
- Understand coordination overhead vs parallel work benefits
- Inform optimal configuration for full evaluation

### Data Collection

For each task/configuration combination, record:

```json
{
  "task_id": 63,
  "task_name": "Calculator",
  "difficulty": "beginner",
  "num_agents": 5,
  "agent_configuration": ["android_dev_1", "android_dev_2", "backend_dev", "qa_engineer", "tech_lead"],
  "execution_time_seconds": 1245.3,
  "compile": true,
  "compile_error_type": null,
  "test_pass": true,
  "tests_run": 10,
  "tests_passed": 8,
  "crash": false,
  "functional_success": false,
  "logs": "...",
  "artifacts": {
    "generated_files": 42,
    "total_loc": 387,
    "apk_size_mb": 2.1
  },
  "timestamp": "2025-12-17T10:30:00Z"
}
```

### Analysis Tasks

After completing Phase 2:

1. **Performance Summary**:
   - Overall compilation rate
   - Overall functional success rate
   - Performance by difficulty level
   - Performance by LOC range
   - Performance by agent configuration

2. **Error Analysis**:
   - Categorize compilation errors (Android resource linking, syntax, dependency issues)
   - Identify common test failures
   - Document crash patterns

3. **Agent Collaboration Analysis**:
   - Compare single vs multi-agent performance
   - Identify coordination bottlenecks
   - Document agent specialization effectiveness

### Success Criteria

✅ Complete 15-20 tasks across all difficulty levels
✅ Compile rate > 15% (reasonable baseline)
✅ Identify top 3 error types preventing compilation
✅ Statistical significance in agent configuration comparison
✅ Reproducible results (variance < 10% on re-runs)

### Time Estimate

- Per task: 1-2 hours (Marcus) + 30 minutes (evaluation) = 1.5-2.5 hours
- Per configuration: 3 configurations × 1.5-2.5 hours = 4.5-7.5 hours
- Total: **15-20 tasks × 4.5-7.5 hours = 67-150 hours**
- Parallelization: Can run 3-5 tasks simultaneously (reduce to 2-3 weeks)

---

## Phase 3: Full Evaluation (4-6 Weeks)

### Objective
Comprehensive evaluation on all 101 AppForge tasks for official leaderboard submission.

### Task Coverage

Run **all 101 tasks** with best-performing agent configuration from Phase 2.

### Agent Configuration

Use **single optimal configuration** identified in Phase 2:
- Likely: 5 agents (unless Phase 2 shows different configuration performs better)

### Data Collection

Same JSON format as Phase 2, but for all 101 tasks.

### Analysis Tasks

1. **Official Metrics** (for leaderboard):
   - **Compilation Rate**: % of 101 tasks that compile
   - **Test Pass Rate**: % of compiled tasks passing all tests
   - **Crash Rate**: % of apps crashing during stress tests
   - **Functional Success Rate**: % of 101 tasks fully succeeding

2. **Deep Analysis**:
   - Performance by task difficulty
   - Performance by LOC
   - Performance by app category
   - Error patterns and frequency
   - Time efficiency metrics

3. **Comparative Analysis**:
   - Marcus vs GPT-5 (current best)
   - Marcus vs Claude Sonnet 3.5 (baseline)
   - Multi-agent vs single-agent systems

### Success Criteria

✅ All 101 tasks evaluated
✅ Results match AppForge leaderboard format
✅ Reproducible with variance < 5%
✅ Comprehensive error analysis
✅ Publication-ready report

### Time Estimate

- Per task: 1.5-2.5 hours (using optimal config from Phase 2)
- Total: **101 tasks × 1.5-2.5 hours = 150-250 hours**
- Parallelization: 5 concurrent tasks = **30-50 hours wall-clock time**
- With overhead and reruns: **4-6 weeks**

---

## Leaderboard Submission

### Current Status

**⚠️ Submission Process Not Yet Documented**

As of December 2025, AppForge's leaderboard submission process is **not publicly documented**:
- No submission format found on https://appforge-bench.github.io/leaderboard/
- No contribution guidelines in GitHub repository
- No documented API or submission endpoint

### Recommended Approach

1. **Contact AppForge Team**:
   - Check AppForge website for contact information
   - Email authors from research paper (arXiv:2510.07740v1)
   - Ask about submission format and requirements

2. **Prepare Results in Standard Format**:

   Even without official format, prepare comprehensive results:

   ```json
   {
     "system_name": "Marcus",
     "system_version": "1.0.0",
     "system_description": "Multi-agent collaborative software development system",
     "evaluation_date": "2025-12-17",
     "evaluator": "Your Name/Organization",
     "
": {
       "compilation_rate": 0.XX,
       "test_pass_rate": 0.XX,
       "crash_rate": 0.XX,
       "functional_success_rate": 0.XX
     },
     "task_results": [
       {
         "task_id": 0,
         "compile": true,
         "test_pass": false,
         "crash": false,
         "functional_success": false,
         "execution_time_seconds": 1245.3
       },
       // ... all 101 tasks
     ],
     "methodology": {
       "agent_count": 5,
       "agent_configuration": "...",
       "llm_model": "claude-sonnet-4.5",
       "timeout_per_task": 3600,
       "retry_on_failure": false
     }
   }
   ```

3. **Document Evaluation Methodology**:
   - Agent architecture and configuration
   - LLM models used
   - Timeouts and resource limits
   - Any modifications to AppForge evaluation scripts
   - Reproducibility instructions

4. **Publish Independently**:
   While waiting for official leaderboard submission:
   - Publish results on Marcus website
   - Create technical report or blog post
   - Share on Twitter/social media with #AppForge hashtag
   - Consider submitting to arXiv as technical report

### What to Include in Website Publication

**Minimum Reportable Results** (after Phase 2):

```markdown
# Marcus on AppForge Benchmark (Initial Evaluation)

**Evaluated Tasks**: 15-20 representative tasks
**Agent Configuration**: 5 agents (default)
**Evaluation Date**: December 2025

## Preliminary Results

| Metric | Marcus (5 agents) | GPT-5 (baseline) | Claude Sonnet 3.5 |
|--------|-------------------|------------------|-------------------|
| Compilation Rate | XX.X% | 60.4% | 27.7% |
| Test Pass Rate | XX.X% | 31.2% | 28.6% |
| Functional Success Rate | XX.X% | 18.8% | 7.9% |

**Status**: Initial evaluation on representative task sample. Full 101-task evaluation in progress.
```

**Comprehensive Results** (after Phase 3):

```markdown
# Marcus on AppForge Benchmark (Full Evaluation)

**Evaluated Tasks**: All 101 tasks
**Agent Configuration**: 5 agents (default)
**Evaluation Date**: December 2025
**Reproducibility**: Full code and methodology available

## Official Results

| Metric | Marcus | GPT-5 | Claude Sonnet 3.5 | GPT-4o |
|--------|--------|-------|-------------------|--------|
| **Compilation Rate** | XX.X% | 60.4% | 27.7% | 35.6% |
| **Test Pass Rate** | XX.X% | 31.2% | 28.6% | 27.7% |
| **Crash Rate** | XX.X% | XX.X% | XX.X% | XX.X% |
| **Functional Success Rate** | XX.X% | 18.8% | 7.9% | 9.9% |

## Performance by Difficulty

| Difficulty | Tasks | Compilation | Success Rate |
|------------|-------|-------------|--------------|
| Beginner | 37 | XX.X% | XX.X% |
| Intermediate | 48 | XX.X% | XX.X% |
| Advanced | 15 | XX.X% | XX.X% |

## Key Findings

1. **Multi-Agent Advantage**: [Describe whether multiple agents helped]
2. **Common Failure Modes**: [Top 3 error types]
3. **Strengths**: [What Marcus excels at]
4. **Limitations**: [Where Marcus struggles]

## Reproducibility

Full evaluation code and results available at:
https://github.com/yourusername/marcus/tree/main/dev-tools/experiments/benchmarks/appforge
```

---

## Resource Requirements

### Compute Resources

**Per Task Estimates**:
- Marcus execution: 1-2 hours CPU time
- AppForge evaluation: 30 minutes Docker + emulator
- Disk space: ~500MB per task (logs, APK, artifacts)

**Total Requirements**:

| Phase | Tasks | Config | Total Hours | Disk Space | Parallel Jobs |
|-------|-------|--------|-------------|------------|---------------|
| Phase 1 | 3 | 1 | 6-9 hours | 1.5 GB | 1 |
| Phase 2 | 20 | 3 | 67-150 hours | 30 GB | 3-5 |
| Phase 3 | 101 | 1 | 150-250 hours | 50 GB | 5-10 |

**Hardware Recommendations**:
- **CPU**: 16+ cores (for parallel execution)
- **RAM**: 32+ GB (Docker emulators are memory-intensive)
- **Disk**: 100+ GB available
- **Docker**: 4+ GB RAM allocated per container

### Financial Costs

**LLM API Costs** (estimated):
- Per task: $0.50-$2.00 (depends on Marcus complexity and LLM pricing)
- Phase 1: $5-$10
- Phase 2: $30-$120 (20 tasks × 3 configs)
- Phase 3: $50-$200 (101 tasks × 1 config)

**Total estimated cost**: $85-$330

---

## Risk Mitigation

### Risk 1: High Failure Rate

**Risk**: Marcus achieves <5% success rate (below baselines)

**Mitigation**:
- Analyze error types in Phase 1
- Implement iterative refinement (feed compilation errors back to Marcus)
- Adjust agent prompts/instructions based on error patterns
- Consider task-specific agent specialization

### Risk 2: Infrastructure Issues

**Risk**: Docker/Android emulator instability

**Mitigation**:
- Implement robust retry logic
- Monitor container health
- Use alternative emulator images if needed
- Run evaluation on dedicated server (not development machine)

### Risk 3: Time Overruns

**Risk**: Phase 3 takes >6 weeks

**Mitigation**:
- Set hard timeouts per task (2 hours max)
- Skip tasks with known Marcus incompatibilities
- Prioritize getting results over perfection
- Consider reducing to 50-task subset if necessary

### Risk 4: Leaderboard Submission Unclear

**Risk**: No clear submission process

**Mitigation**:
- Publish results independently
- Contact AppForge team early (during Phase 2)
- Prepare comprehensive technical report as alternative to leaderboard
- Focus on website publication as primary goal

---

## Timeline Summary

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| **Phase 1: Validation** | 1-2 days | Working integration, 3 task results |
| **Phase 2: Sampling** | 1-2 weeks | 15-20 task results, initial publication |
| **Phase 3: Full Eval** | 4-6 weeks | 101 task results, leaderboard submission |
| **Publication** | Ongoing | Blog post, technical report, leaderboard entry |

**Total Time**: 5-8 weeks from start to full publication

---

## Deliverables Checklist

### After Phase 1
- ✅ 3 task results (JSON format)
- ✅ Integration validation report
- ✅ Error analysis (if failures occur)

### After Phase 2
- ✅ 15-20 task results (JSON format)
- ✅ Statistical analysis of results
- ✅ Agent configuration comparison
- ✅ Initial website publication (preliminary results)
- ✅ Blog post or technical writeup

### After Phase 3
- ✅ 101 task results (JSON format)
- ✅ Official metrics report
- ✅ Comprehensive error analysis
- ✅ Comparison to baseline models
- ✅ Full website publication
- ✅ Leaderboard submission package (format TBD)
- ✅ Technical report or arXiv paper
- ✅ Open-source evaluation code

---

## Next Steps

### Immediate Actions (This Week)

1. **Verify Integration**:
   ```bash
   cd dev-tools/experiments/benchmarks/appforge
   python appforge_runner.py --task-id 63 --num-agents 5
   ```

2. **Contact AppForge Team**:
   - Email authors from paper
   - Ask about leaderboard submission process
   - Request expected result format

3. **Setup Infrastructure**:
   - Ensure Docker resources allocated
   - Test Android emulator stability
   - Setup parallel execution environment

### Phase 1 Execution (Next Week)

1. Run 3 validation tasks
2. Analyze results and errors
3. Adjust integration if needed
4. Document lessons learned

### Phase 2 Planning (Weeks 2-3)

1. Finalize task selection (15-20 tasks)
2. Prepare agent configurations
3. Setup parallel execution
4. Begin systematic evaluation

---

## Appendix: Task Selection for Phase 2

### Recommended 20-Task Subset

Based on LOC analysis and difficulty distribution:

#### Beginner Tasks (7 tasks)
- Task 63: Calculator (LOC: ~300)
- Task 5: Flashlight (LOC: ~200)
- Task 18: Tip Calculator (LOC: ~250)
- Task 27: Simple Notes (LOC: ~350)
- Task 42: Counter App (LOC: ~200)
- Task 55: Random Number Generator (LOC: ~180)
- Task 71: RGB Color Mixer (LOC: ~300)

#### Intermediate Tasks (9 tasks)
- Task 45: Unit Converter (LOC: ~380)
- Task 8: To-Do List (LOC: ~450)
- Task 22: Expense Tracker (LOC: ~520)
- Task 34: BMI Calculator (LOC: ~320)
- Task 48: Currency Converter (LOC: ~410)
- Task 59: Stopwatch (LOC: ~280)
- Task 67: Shopping List (LOC: ~440)
- Task 78: Habit Tracker (LOC: ~390)
- Task 89: Password Generator (LOC: ~350)

#### Advanced Tasks (4 tasks)
- Task 12: Weather App (LOC: ~650)
- Task 29: News Reader (LOC: ~720)
- Task 51: Chat Application (LOC: ~850)
- Task 93: Music Player (LOC: ~780)

**Rationale**: This selection covers all difficulty levels, spans LOC ranges from 180-850, and includes diverse app categories (utilities, productivity, data/network, media).

---

## Questions?

For questions about this testing plan, contact:
- Marcus Team: [your contact info]
- AppForge Team: [from paper]

Last updated: 2025-12-17
