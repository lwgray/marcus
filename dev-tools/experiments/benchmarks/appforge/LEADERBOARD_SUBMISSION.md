# AppForge Leaderboard Submission Guide

This guide explains how to submit Marcus evaluation results to the AppForge leaderboard and publish results on your website.

---

## Current Status ⚠️

**As of December 2025**, the AppForge leaderboard submission process is **not publicly documented**:

- ❌ No submission API or endpoint found
- ❌ No contribution guidelines in GitHub repository
- ❌ No documented result format on leaderboard website

**This guide provides**:
1. Recommended steps to contact AppForge team
2. Standard result format to prepare
3. How to publish results independently on your website

---

## Step 1: Contact AppForge Team

### Who to Contact

**AppForge Research Team:**
- Check [AppForge website](https://appforge-bench.github.io/) for contact information
- Email authors from research paper: [arXiv:2510.07740v1](https://arxiv.org/abs/2510.07740)
- Create GitHub issue: https://github.com/AppForge-Bench/AppForge/issues

### What to Ask

```
Subject: Leaderboard Submission for Marcus Multi-Agent System

Hi AppForge Team,

We've been evaluating our multi-agent software development system (Marcus)
on the AppForge benchmark and would like to submit results to your leaderboard.

Could you please provide:
1. Official result format/schema for submissions
2. Submission process (email, API, pull request?)
3. Required metadata about our system
4. Any validation/reproducibility requirements

We plan to evaluate all 101 tasks and can provide:
- Full task-by-task results
- Execution logs and artifacts
- Reproducible evaluation code
- System architecture documentation

Looking forward to contributing to the benchmark!

Best regards,
[Your Name]
[Your Organization]
[Contact Info]
```

---

## Step 2: Prepare Results in Standard Format

While waiting for official format, prepare comprehensive results that can be easily adapted.

### Result Schema

Create a JSON file with the following structure:

```json
{
  "submission_metadata": {
    "system_name": "Marcus",
    "system_version": "1.0.0",
    "system_description": "Multi-agent collaborative software development system with specialized agents for Android development",
    "submission_date": "2025-12-17T00:00:00Z",
    "evaluator": "Your Name",
    "organization": "Your Organization",
    "contact_email": "your@email.com",
    "code_repository": "https://github.com/yourusername/marcus",
    "evaluation_code": "https://github.com/yourusername/marcus/tree/main/dev-tools/experiments/benchmarks/appforge"
  },

  "system_configuration": {
    "agent_count": 5,
    "agent_roles": [
      "Android Developer 1",
      "Android Developer 2",
      "Backend Developer",
      "QA Engineer",
      "Technical Lead"
    ],
    "llm_model": "claude-sonnet-4.5",
    "llm_provider": "Anthropic",
    "agent_coordination": "Multi-agent task decomposition with shared context",
    "code_generation_strategy": "Collaborative development with code review",
    "max_iterations": 1,
    "timeout_per_task_seconds": 3600,
    "retry_on_failure": false
  },

  "evaluation_environment": {
    "appforge_version": "1.0.0",
    "docker_image": "zenithfocuslight/appforge:latest",
    "android_api_level": 29,
    "evaluation_date_start": "2025-12-17T00:00:00Z",
    "evaluation_date_end": "2026-01-31T00:00:00Z",
    "compute_environment": "AWS EC2 c5.4xlarge (16 vCPU, 32GB RAM)"
  },

  "aggregate_metrics": {
    "total_tasks": 101,
    "compilation_rate": 0.356,
    "test_pass_rate": 0.278,
    "crash_rate": 0.089,
    "functional_success_rate": 0.099
  },

  "metrics_by_difficulty": {
    "beginner": {
      "task_count": 37,
      "compilation_rate": 0.459,
      "functional_success_rate": 0.135
    },
    "intermediate": {
      "task_count": 48,
      "compilation_rate": 0.333,
      "functional_success_rate": 0.083
    },
    "advanced": {
      "task_count": 15,
      "compilation_rate": 0.200,
      "functional_success_rate": 0.067
    }
  },

  "task_results": [
    {
      "task_id": 0,
      "task_name": "Calculator",
      "difficulty": "beginner",
      "compile": true,
      "compile_error_type": null,
      "test_pass": true,
      "tests_run": 10,
      "tests_passed": 8,
      "crash": false,
      "functional_success": false,
      "execution_time_seconds": 1245.3,
      "generated_files": 42,
      "total_loc": 387,
      "apk_size_mb": 2.1
    },
    // ... results for all 101 tasks
  ],

  "error_analysis": {
    "compilation_errors": {
      "android_resource_linking_failed": 18,
      "gradle_build_failed": 12,
      "missing_dependencies": 8,
      "syntax_errors": 5,
      "other": 7
    },
    "test_failures": {
      "ui_interaction_failed": 15,
      "assertion_failed": 11,
      "timeout": 6,
      "crash": 4,
      "other": 8
    }
  },

  "reproducibility": {
    "evaluation_script": "https://github.com/yourusername/marcus/blob/main/dev-tools/experiments/benchmarks/appforge/appforge_runner.py",
    "docker_image": "zenithfocuslight/appforge:latest",
    "random_seed": 42,
    "deterministic": false,
    "variance_across_runs": "< 5% on re-evaluation of 10 tasks"
  }
}
```

### File Naming Convention

Use descriptive filename:
```
marcus_v1.0_appforge_results_2025-12-17.json
```

---

## Step 3: Validation Checklist

Before submission, verify:

### Required Data
- ✅ All 101 task results included
- ✅ Aggregate metrics calculated correctly
- ✅ Error analysis categorized
- ✅ System configuration documented
- ✅ Reproducibility information provided

### Metric Calculations

**Compilation Rate**:
```python
compilation_rate = (tasks_compiled / total_tasks)
```

**Test Pass Rate**:
```python
test_pass_rate = (tasks_passed_tests / total_tasks)
```

**Crash Rate**:
```python
crash_rate = (tasks_crashed / total_tasks)
```

**Functional Success Rate**:
```python
functional_success_rate = (tasks_fully_succeeded / total_tasks)
# where fully_succeeded = compiled AND all_tests_passed AND no_crash
```

### Validation Script

Run validation before submission:

```python
#!/usr/bin/env python3
"""Validate AppForge results for submission."""

import json

def validate_results(results_file):
    """Validate AppForge results JSON."""
    with open(results_file) as f:
        data = json.load(f)

    # Check required fields
    required_fields = [
        "submission_metadata",
        "system_configuration",
        "aggregate_metrics",
        "task_results"
    ]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"

    # Validate task count
    assert len(data["task_results"]) == 101, \
        f"Expected 101 tasks, got {len(data['task_results'])}"

    # Validate metrics
    results = data["task_results"]
    compiled = sum(1 for r in results if r["compile"])
    passed = sum(1 for r in results if r["functional_success"])

    expected_compile_rate = compiled / 101
    expected_success_rate = passed / 101

    assert abs(data["aggregate_metrics"]["compilation_rate"] - expected_compile_rate) < 0.01
    assert abs(data["aggregate_metrics"]["functional_success_rate"] - expected_success_rate) < 0.01

    print("✅ Validation passed!")
    print(f"Compilation Rate: {expected_compile_rate:.1%}")
    print(f"Functional Success Rate: {expected_success_rate:.1%}")

if __name__ == "__main__":
    import sys
    validate_results(sys.argv[1])
```

Run:
```bash
python validate_results.py marcus_v1.0_appforge_results_2025-12-17.json
```

---

## Step 4: Publish on Your Website

While awaiting official leaderboard submission, publish results independently.

### Minimum Viable Publication

Create a webpage or blog post:

```markdown
# Marcus on AppForge Benchmark

**System**: Marcus v1.0 (Multi-Agent Software Development)
**Evaluation Date**: December 2025
**Tasks Evaluated**: 101 Android app development tasks

## Results

| Metric | Marcus | GPT-5 (SOTA) | Claude Sonnet 3.5 | GPT-4o |
|--------|--------|--------------|-------------------|--------|
| **Compilation Rate** | XX.X% | 60.4% | 27.7% | 35.6% |
| **Test Pass Rate** | XX.X% | 31.2% | 28.6% | 27.7% |
| **Functional Success Rate** | XX.X% | 18.8% | 7.9% | 9.9% |

## Performance by Difficulty

| Difficulty | Tasks | Compilation | Success Rate |
|------------|-------|-------------|--------------|
| Beginner | 37 | XX.X% | XX.X% |
| Intermediate | 48 | XX.X% | XX.X% |
| Advanced | 15 | XX.X% | XX.X% |

## Downloads

- [Full Results (JSON)](marcus_v1.0_appforge_results_2025-12-17.json)
- [Evaluation Code](https://github.com/yourusername/marcus/tree/main/dev-tools/experiments/benchmarks/appforge)
- [Technical Report (PDF)](marcus_appforge_technical_report.pdf)

## Reproducibility

Our evaluation is fully reproducible:
- Open-source evaluation code
- Documented system configuration
- Standard AppForge Docker environment
- Variance < 5% on re-runs

## Citation

If you use these results, please cite:

\`\`\`bibtex
@misc{marcus2025appforge,
  title={Marcus Multi-Agent System: Evaluation on AppForge Benchmark},
  author={Your Name},
  year={2025},
  url={https://yourwebsite.com/marcus-appforge}
}
\`\`\`

## Contact

Questions? Email: your@email.com
```

### Enhanced Publication

For more comprehensive publication, include:

1. **Methodology Section**:
   - Agent architecture diagram
   - Task decomposition strategy
   - Code generation process
   - Quality assurance approach

2. **Error Analysis**:
   - Top 5 failure modes
   - Compilation error breakdown
   - Test failure patterns
   - Lessons learned

3. **Comparative Analysis**:
   - Strengths vs baseline models
   - Multi-agent advantages
   - Coordination overhead analysis
   - Task complexity insights

4. **Interactive Results Viewer**:
   - Filter by difficulty/category
   - View individual task results
   - Compare configurations
   - Visualize error patterns

### Social Media Announcement

Post on Twitter/LinkedIn:

```
🎉 Excited to share Marcus's performance on @AppForgeBench!

📊 Results on 101 Android app development tasks:
- Compilation: XX.X%
- Functional Success: XX.X%

🤖 Multi-agent approach shows [strength/weakness]

Full results: [link]
Code: [github link]

#AppForge #MultiAgent #SoftwareDevelopment #LLM
```

---

## Step 5: Optional - Submit to arXiv

For maximum visibility, consider publishing technical report on arXiv:

### arXiv Submission

**Category**: cs.SE (Software Engineering) or cs.AI

**Title**: "Evaluating Multi-Agent Software Development Systems on AppForge Benchmark"

**Abstract Template**:
```
We evaluate Marcus, a multi-agent software development system, on the
AppForge benchmark suite of 101 real-world Android application development
tasks. Marcus employs [N] specialized agents that collaborate through
[coordination mechanism] to generate complete Android applications.

Our evaluation shows that Marcus achieves a compilation rate of XX.X% and
functional success rate of XX.X% on the benchmark, [comparing to/outperforming]
single-agent baselines. We analyze common failure modes, including [error types],
and discuss implications for multi-agent system design in software development.

Our evaluation code and full results are publicly available for reproducibility.
```

---

## Alternative Submission Paths

If official AppForge submission is unavailable:

### Option 1: GitHub Pull Request

Submit results via pull request to AppForge repository:

```bash
# Fork AppForge repository
git clone https://github.com/AppForge-Bench/AppForge.git
cd AppForge

# Create results directory (if doesn't exist)
mkdir -p community_results/

# Add your results
cp marcus_v1.0_appforge_results_2025-12-17.json community_results/

# Create pull request
git checkout -b add-marcus-results
git add community_results/marcus_v1.0_appforge_results_2025-12-17.json
git commit -m "Add Marcus v1.0 evaluation results"
git push origin add-marcus-results
```

### Option 2: Create Comparison Repository

Create standalone repository:

```
appforge-benchmark-results/
├── README.md
├── results/
│   ├── marcus_v1.0.json
│   ├── gpt5_baseline.json (from paper)
│   └── claude_sonnet_35_baseline.json (from paper)
├── analysis/
│   ├── comparison_table.md
│   ├── error_analysis.md
│   └── visualization.html
└── evaluation_code/
    └── ... (your appforge integration code)
```

This creates an independent resource that:
- Showcases Marcus results
- Provides comparative analysis
- Offers reusable evaluation code
- Can be cited in papers/posts

---

## Submission Checklist

Before final submission:

### Data Quality
- ✅ All 101 tasks evaluated
- ✅ Metrics calculated correctly
- ✅ Error analysis complete
- ✅ Reproducibility documented
- ✅ Results validated with script

### Documentation
- ✅ System description written
- ✅ Configuration documented
- ✅ Evaluation methodology explained
- ✅ Limitations acknowledged
- ✅ Contact information provided

### Files Prepared
- ✅ Full results JSON
- ✅ Summary report (PDF/Markdown)
- ✅ Evaluation code repository
- ✅ README with instructions
- ✅ License file

### Publication
- ✅ Website page created
- ✅ Blog post written
- ✅ Social media announced
- ✅ arXiv submission (optional)
- ✅ GitHub repository public

---

## Frequently Asked Questions

### Q: How long does evaluation take?

**A**: ~150-250 hours compute time for all 101 tasks. With 5 parallel jobs: 30-50 hours wall-clock time (4-6 weeks).

### Q: What if I don't have results for all 101 tasks?

**A**: Publish partial results clearly labeled as "Initial Evaluation" or "Representative Sample" with N tasks. Indicate full evaluation is in progress.

### Q: Can I submit multiple configurations?

**A**: Yes! Submit separate result files for different agent configurations (e.g., marcus_v1.0_5agents.json, marcus_v1.0_10agents.json) to compare approaches.

### Q: How do I handle non-deterministic results?

**A**: Run each task 2-3 times and report:
- Median/mean metrics
- Variance or standard deviation
- Pass rate across runs
- Note non-determinism in methodology

### Q: What if my results are lower than baselines?

**A**: Publish anyway! Negative results are valuable:
- Document what didn't work
- Analyze failure modes
- Suggest improvements
- Contribute to community knowledge

---

## Contact Information

### AppForge Team
- Website: https://appforge-bench.github.io/
- GitHub: https://github.com/AppForge-Bench/AppForge
- Paper: https://arxiv.org/abs/2510.07740

### Marcus Team
- Your contact info here

---

## Updates

This document will be updated when:
- Official submission process is announced
- Result format is standardized
- Leaderboard API becomes available

**Last Updated**: 2025-12-17

Check for updates at: https://github.com/yourusername/marcus/tree/main/dev-tools/experiments/benchmarks/appforge
