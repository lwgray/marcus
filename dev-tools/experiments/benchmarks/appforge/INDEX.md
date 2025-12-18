# AppForge Benchmark Integration - Complete Documentation Index

All documentation for evaluating Marcus on AppForge benchmarks and publishing results.

---

## 🚀 Getting Started (Start Here!)

| Document | Purpose | Time | Audience |
|----------|---------|------|----------|
| **[SUMMARY.md](SUMMARY.md)** | **Overview of everything** | 10 min | Everyone |
| **[QUICK_START.md](QUICK_START.md)** | **Get running in 30 minutes** | 30 min | First-time users |

Start with SUMMARY.md for the big picture, then follow QUICK_START.md to run your first benchmark.

---

## 📖 Core Documentation

### For Users

| Document | Purpose | When to Read |
|----------|---------|--------------|
| [README.md](README.md) | Main documentation and usage guide | After quick start |
| [TESTING_PLAN.md](TESTING_PLAN.md) | 3-phase evaluation strategy | Before Phase 2 |
| [LEADERBOARD_SUBMISSION.md](LEADERBOARD_SUBMISSION.md) | How to submit results | After Phase 2 |
| [WEBSITE_TEMPLATE.md](WEBSITE_TEMPLATE.md) | Templates for publishing | When ready to publish |

### For Developers

| Document | Purpose | When to Read |
|----------|---------|--------------|
| [INTEGRATION_STATUS.md](INTEGRATION_STATUS.md) | Technical implementation details | Understanding architecture |
| [FORMAT_CONVERSION_ANALYSIS.md](FORMAT_CONVERSION_ANALYSIS.md) | Why no format conversion needed | Understanding AppForge integration |

---

## 🛠️ Tools & Scripts

| File | Purpose | Usage |
|------|---------|-------|
| [appforge_runner.py](appforge_runner.py) | Main CLI orchestrator | `python appforge_runner.py --task-id 63` |
| [task_converter.py](task_converter.py) | Convert AppForge to Marcus | Called by appforge_runner.py |
| [evaluator.py](evaluator.py) | Run AppForge tests | Called by appforge_runner.py |
| [reporter.py](reporter.py) | Generate HTML reports | `python reporter.py --results-dir ~/results` |
| [validate_results.py](validate_results.py) | Validate submission format | `python validate_results.py results.json` |

---

## 📋 Quick Reference

### Phase 1: Validation (This Week)

**Goal**: Verify integration works

**Time**: 1-2 days

**Read**:
1. [QUICK_START.md](QUICK_START.md) - Setup guide
2. [README.md](README.md) sections 1-3 - Basic usage

**Run**:
```bash
python appforge_runner.py --task-id 63  # Calculator
python appforge_runner.py --task-id 45  # Unit Converter
python appforge_runner.py --task-id 12  # Weather App
```

**Deliverable**: 3 task results, working integration

---

### Phase 2: Representative Sampling (Weeks 2-3)

**Goal**: Publishable initial results

**Time**: 1-2 weeks

**Read**:
1. [TESTING_PLAN.md](TESTING_PLAN.md) Phase 2 - Task selection
2. [WEBSITE_TEMPLATE.md](WEBSITE_TEMPLATE.md) Template 1 - Preliminary results

**Run**:
```bash
# Run 15-20 tasks with multiple agent configs
python appforge_runner.py --task-id [ID] --agents 1,3,5
```

**Deliverable**: 15-20 task results, initial website publication

---

### Phase 3: Full Evaluation (Weeks 4-8)

**Goal**: Comprehensive results and leaderboard submission

**Time**: 4-6 weeks

**Read**:
1. [TESTING_PLAN.md](TESTING_PLAN.md) Phase 3 - Full evaluation
2. [LEADERBOARD_SUBMISSION.md](LEADERBOARD_SUBMISSION.md) - Submission guide
3. [WEBSITE_TEMPLATE.md](WEBSITE_TEMPLATE.md) Template 2 - Comprehensive results

**Run**:
```bash
# Run all 101 tasks
python appforge_runner.py --suite configs/full_benchmark.yaml
```

**Deliverable**: 101 task results, comprehensive publication, leaderboard submission

---

## 📊 Understanding Your Results

### Result Metrics

- **Compilation Rate**: % of tasks that compile into valid APK
- **Test Pass Rate**: % of compiled tasks passing functional tests
- **Crash Rate**: % of apps crashing during stress testing
- **Functional Success Rate**: % of tasks fully succeeding (compile + all tests passed + no crash)

### Expected Performance

| Phase | Tasks | Expected Compile Rate | Expected Success Rate |
|-------|-------|----------------------|----------------------|
| Phase 1 | 3 | 33-67% (1-2 tasks) | 0-33% (0-1 task) |
| Phase 2 | 15-20 | 20-40% | 5-15% |
| Phase 3 | 101 | 20-60% | 5-20% |

**Note**: Even 5% success rate is meaningful - GPT-4 Turbo only achieves 4%!

---

## 🎯 Common Tasks

### Run a Single Benchmark

```bash
python appforge_runner.py --task-id 63 --num-agents 5
```

### Compare Agent Configurations

```bash
python appforge_runner.py --task-id 63 --agents 1,3,5,10
```

### Run a Suite of Benchmarks

```bash
python appforge_runner.py --suite configs/example_suite.yaml
```

### Validate Results for Submission

```bash
python validate_results.py results/marcus_v1.0_appforge_results.json
```

### Generate HTML Report

```bash
python reporter.py --results-dir ~/appforge_benchmarks/results
open appforge_report.html
```

---

## 🔧 Troubleshooting

### Quick Fixes

| Problem | Solution | Document |
|---------|----------|----------|
| Can't connect to Marcus MCP | Start server: `python -m src.mcp_server.http_server` | [QUICK_START.md](QUICK_START.md) |
| Docker not running | Start Docker Desktop | [QUICK_START.md](QUICK_START.md) |
| AppForge module not found | `pip install -e ~/dev/AppForge` | [QUICK_START.md](QUICK_START.md) |
| Timeout waiting for project | Check Marcus experiment logs | [README.md](README.md) |
| Port 5900 in use | Kill containers: `docker ps -a \| grep android \| xargs docker rm -f` | [README.md](README.md) |

### Detailed Troubleshooting

See [README.md](README.md) section "Troubleshooting" for comprehensive solutions.

---

## 📦 Configuration Files

### Provided Examples

| File | Purpose | Usage |
|------|---------|-------|
| [configs/example_calculator.yaml](configs/example_calculator.yaml) | Single task example | Learning configuration format |
| [configs/example_suite.yaml](configs/example_suite.yaml) | Multi-task suite | Running multiple tasks |

### Creating Your Own

Template:
```yaml
marcus_root: "/path/to/marcus"

tasks:
  - id: 63
    name: "Calculator"

marcus_configs:
  - agents: 5

docker:
  image: "zenithfocuslight/appforge:latest"
```

See [README.md](README.md) section "Configuration Files" for details.

---

## 📈 Publication Workflow

### 1. After Phase 1 (Days 1-2)

**Optional**: Blog post announcement

```markdown
"We're evaluating Marcus on AppForge. Initial testing on 3 tasks shows [brief summary]."
```

Template: [WEBSITE_TEMPLATE.md](WEBSITE_TEMPLATE.md) Template 3

---

### 2. After Phase 2 (Weeks 2-3)

**Required**: Initial results publication

**Steps**:
1. Run 15-20 representative tasks
2. Analyze results
3. Use [WEBSITE_TEMPLATE.md](WEBSITE_TEMPLATE.md) Template 1
4. Publish on website
5. Share on social media

**Deliverables**:
- Results page on website
- Blog post or technical writeup
- Social media announcement

---

### 3. After Phase 3 (Weeks 6-8)

**Required**: Comprehensive results publication

**Steps**:
1. Complete all 101 tasks
2. Run validation: `python validate_results.py results.json`
3. Use [WEBSITE_TEMPLATE.md](WEBSITE_TEMPLATE.md) Template 2
4. Contact AppForge team (see [LEADERBOARD_SUBMISSION.md](LEADERBOARD_SUBMISSION.md))
5. Publish comprehensive results
6. Submit to leaderboard (if process available)
7. Optional: arXiv technical report

**Deliverables**:
- Comprehensive results page
- Technical report PDF
- Leaderboard submission
- arXiv paper (optional)
- Social media announcement

---

## 🎓 Learning Path

### New to AppForge?

1. Read [SUMMARY.md](SUMMARY.md) (10 min) - Big picture
2. Read AppForge paper sections 1-3 (15 min) - Background
3. Follow [QUICK_START.md](QUICK_START.md) (30 min) - First benchmark
4. Read [TESTING_PLAN.md](TESTING_PLAN.md) Phase 1 (5 min) - Next steps

**Total time**: ~60 minutes to first successful benchmark

---

### Ready to Publish?

1. Complete Phase 2 evaluation
2. Read [WEBSITE_TEMPLATE.md](WEBSITE_TEMPLATE.md) (15 min)
3. Read [LEADERBOARD_SUBMISSION.md](LEADERBOARD_SUBMISSION.md) (10 min)
4. Draft publication using templates
5. Validate results: `python validate_results.py results.json`
6. Publish!

**Total time**: ~30 minutes to prepare publication

---

### Want to Contribute?

1. Read [INTEGRATION_STATUS.md](INTEGRATION_STATUS.md) - Architecture
2. Read [FORMAT_CONVERSION_ANALYSIS.md](FORMAT_CONVERSION_ANALYSIS.md) - Technical details
3. Check open issues on GitHub
4. Submit PRs with improvements

---

## 📚 External Resources

### AppForge

- **Website**: https://appforge-bench.github.io/
- **Paper**: https://arxiv.org/abs/2510.07740
- **GitHub**: https://github.com/AppForge-Bench/AppForge
- **Leaderboard**: https://appforge-bench.github.io/leaderboard/

### Marcus

- **Documentation**: [../../docs/](../../docs/)
- **GitHub**: [Your repository]
- **Website**: [Your website]

### Tools

- **AppForge**: https://github.com/AppForge-Bench/AppForge
- **Gradle**: https://gradle.org/
- **Android SDK**: https://developer.android.com/

---

## ❓ FAQ

### General

**Q: Do I need to run all 101 tasks?**
A: No! Start with 3 (Phase 1), then 15-20 (Phase 2), then all 101 (Phase 3) if desired.

**Q: How long does each task take?**
A: 1.5-2.5 hours per task (Marcus + evaluation). But you can parallelize!

**Q: What if my results are poor?**
A: Publish anyway! Negative results are valuable. Focus on lessons learned.

**Q: Can I submit to leaderboard?**
A: Submission process unclear. See [LEADERBOARD_SUBMISSION.md](LEADERBOARD_SUBMISSION.md) for alternatives.

### Technical

**Q: Why three terminals?**
A: Terminal 1 (Marcus MCP server), Terminal 2 (AppForge runner), Terminal 3 (Marcus experiment).

**Q: Can I run multiple benchmarks in parallel?**
A: Yes! Run 3-5 in parallel to reduce wall-clock time.

**Q: How do I stop a running benchmark?**
A: Ctrl+C in Terminal 2 (appforge_runner.py), then clean up Docker containers.

**Q: Where are results stored?**
A: `~/appforge_benchmarks/results/task_*_agents_*.json`

### Publication

**Q: When should I publish?**
A: After Phase 2 (preliminary) and Phase 3 (comprehensive). Optional after Phase 1.

**Q: What if I can't contact AppForge team?**
A: Publish independently on your website. See [LEADERBOARD_SUBMISSION.md](LEADERBOARD_SUBMISSION.md).

**Q: Should I publish negative results?**
A: Yes! The community benefits from understanding what doesn't work.

**Q: Can I update results later?**
A: Yes! Publish preliminary results, then update with comprehensive evaluation.

---

## 📝 Document Status

| Document | Status | Last Updated |
|----------|--------|--------------|
| [SUMMARY.md](SUMMARY.md) | ✅ Complete | 2025-12-17 |
| [QUICK_START.md](QUICK_START.md) | ✅ Complete | 2025-12-17 |
| [README.md](README.md) | ✅ Complete | 2025-12-17 |
| [TESTING_PLAN.md](TESTING_PLAN.md) | ✅ Complete | 2025-12-17 |
| [LEADERBOARD_SUBMISSION.md](LEADERBOARD_SUBMISSION.md) | ✅ Complete | 2025-12-17 |
| [WEBSITE_TEMPLATE.md](WEBSITE_TEMPLATE.md) | ✅ Complete | 2025-12-17 |
| [INTEGRATION_STATUS.md](INTEGRATION_STATUS.md) | ✅ Complete | 2025-12-17 |
| [FORMAT_CONVERSION_ANALYSIS.md](FORMAT_CONVERSION_ANALYSIS.md) | ✅ Complete | Earlier |
| [INDEX.md](INDEX.md) | ✅ Complete | 2025-12-17 |
| appforge_runner.py | ✅ Complete (HTTP connection) | 2025-12-17 |
| task_converter.py | ✅ Complete | Earlier |
| validate_results.py | ✅ Complete | 2025-12-17 |
| evaluator.py | ⚠️ TODO | - |
| reporter.py | ⚠️ TODO | - |

---

## 🚦 Current Status

**Integration**: ✅ Complete and ready to test

**Documentation**: ✅ Comprehensive (9 documents)

**Testing**: ⏳ Phase 1 ready to start

**Publication**: ⏳ Awaiting results

---

## 🎯 Next Steps

### This Week (Phase 1)

1. [ ] Read [QUICK_START.md](QUICK_START.md)
2. [ ] Setup environment (Docker, dependencies)
3. [ ] Run Task 63 (Calculator)
4. [ ] Run Task 45 (Unit Converter)
5. [ ] Run Task 12 (Weather App)
6. [ ] Document any issues found
7. [ ] Email AppForge team about submission

### Next 2-3 Weeks (Phase 2)

1. [ ] Read [TESTING_PLAN.md](TESTING_PLAN.md) Phase 2
2. [ ] Select 15-20 representative tasks
3. [ ] Run with multiple agent configurations
4. [ ] Analyze results
5. [ ] Prepare publication using [WEBSITE_TEMPLATE.md](WEBSITE_TEMPLATE.md)
6. [ ] Publish preliminary results

### Next 4-8 Weeks (Phase 3)

1. [ ] Read [TESTING_PLAN.md](TESTING_PLAN.md) Phase 3
2. [ ] Run all 101 tasks
3. [ ] Validate results with validate_results.py
4. [ ] Prepare comprehensive publication
5. [ ] Submit to leaderboard (if available)
6. [ ] Optional: arXiv technical report

---

## 📞 Getting Help

### Documentation Issues

If documentation is unclear:
1. Check relevant document in this index
2. Search for keywords in [SUMMARY.md](SUMMARY.md)
3. Check [README.md](README.md) troubleshooting section
4. Create GitHub issue

### Technical Issues

If tool doesn't work:
1. Check [QUICK_START.md](QUICK_START.md) troubleshooting
2. Check [README.md](README.md) troubleshooting
3. Verify environment (Docker, dependencies)
4. Create GitHub issue with logs

### Publication Questions

If unsure about publishing:
1. Read [LEADERBOARD_SUBMISSION.md](LEADERBOARD_SUBMISSION.md)
2. Read [WEBSITE_TEMPLATE.md](WEBSITE_TEMPLATE.md)
3. Contact AppForge team
4. Create GitHub discussion

---

## 🤝 Contributing

Want to improve this integration?

1. **Documentation**: Submit PRs for unclear sections
2. **Code**: Implement evaluator.py, reporter.py
3. **Testing**: Run benchmarks and report issues
4. **Analysis**: Share insights from your evaluations

See [INTEGRATION_STATUS.md](INTEGRATION_STATUS.md) for technical details.

---

## 📄 License

Same as Marcus project license.

---

## 🙏 Acknowledgments

- **AppForge Team** for creating this valuable benchmark
- **Marcus Contributors** for the multi-agent framework
- **You** for conducting rigorous evaluations!

---

**Last Updated**: 2025-12-17

**Ready to start?** → [QUICK_START.md](QUICK_START.md)

**Questions?** → Create a GitHub issue or discussion
