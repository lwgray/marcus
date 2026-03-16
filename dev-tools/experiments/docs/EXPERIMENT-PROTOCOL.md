# DateTime API Experiment - Protocol for Fair Comparison

## Purpose
Compare single coding agent vs Marcus multi-agent system for prototype project completion.

---

## Test Setup

### Prerequisites
1. ✅ Marcus baseline already completed (21.37 minutes, 17 subtasks)
2. ☐ Single agent selected (Claude Code, GPT-4, etc.)
3. ☐ Clean workspace prepared
4. ☐ Timer ready
5. ☐ Tracking sheet printed/opened

### Important: No Time Budgets
**Time budgets have been removed from the single-agent prompt for fairness.**

Why?
- Time budgets are a Marcus-specific feature (learned from historical data)
- Single agents don't normally receive time guidance
- Providing them would give unfair advantage
- This tests natural pace vs Marcus's optimized pace

---

## Experiment Execution Steps

### Phase 1: Preparation (Do NOT start timer yet)
1. Create clean directory: `mkdir datetime-api-single-agent`
2. Open your coding agent (Claude Code, Cursor, etc.)
3. Open tracking sheet: `experiments/experiment-tracking-sheet.md`
4. Have prompt ready: `experiments/single-agent-datetime-api-prompt.md`

### Phase 2: Execution (START TIMER NOW)
1. **START TIMER** - Note exact start time
2. Paste the ENTIRE prompt from `single-agent-datetime-api-prompt.md`
3. Let the agent work through ALL 22 subtasks
4. After EACH subtask:
   - Verify deliverable was created
   - Check quality (not stub/placeholder)
   - Mark on tracking sheet
   - Let agent continue
5. **DO NOT** intervene unless agent gets stuck for >5 minutes
6. **DO NOT** accept partial implementations
7. **DO NOT** skip any subtasks
8. If agent skips a subtask, STOP and redirect it back

### Phase 3: Completion (STOP TIMER)
1. **STOP TIMER** when agent declares "PROJECT COMPLETE"
2. Note exact end time
3. Calculate total elapsed time
4. Count completed subtasks

### Phase 4: Validation
1. Verify all files created (21 expected)
2. Run all tests (must pass)
3. Test both endpoints (must work)
4. Review code quality
5. Calculate completion percentage

---

## Quality Standards (Same as Marcus)

### Acceptable ✅
- Working code that runs
- Tests that pass
- Documentation with actual content
- Error handling implemented
- Files in correct locations

### NOT Acceptable ❌
- Stub implementations (`pass`, `TODO`, `NotImplemented`)
- Empty documentation files
- Tests that don't run
- Placeholder comments instead of code
- Missing error handling

**If agent produces unacceptable quality, mark as FAILED and note in tracking sheet**

---

## Intervention Rules

### When to Intervene
1. Agent stuck for >5 minutes without progress
2. Agent explicitly asks for guidance
3. Agent attempting to skip subtasks
4. Agent creating stubs/placeholders

### When NOT to Intervene
1. Agent working slowly but making progress
2. Agent refactoring/improving code
3. Agent adding extra features (bonus!)
4. Agent debugging issues

### How to Intervene
- Minimal guidance only
- Redirect to specific subtask
- Don't write code for agent
- Note intervention in tracking sheet

---

## Common Pitfalls to Avoid

### ❌ Unfair Advantages
- Don't give agent extra context Marcus didn't have
- Don't accept lower quality than Marcus produced
- Don't skip subtasks that Marcus completed
- Don't help agent debug issues

### ✅ Fair Comparison
- Use exact same project description
- Require same deliverables
- Apply same quality standards
- Measure wall clock time accurately

---

## Timing Guidelines

### Start Timer When:
- You paste the prompt and press Enter
- Agent begins reading/processing the task

### Stop Timer When:
- Agent declares "PROJECT COMPLETE"
- OR agent has completed all 22 subtasks
- OR agent declares inability to continue

### Do NOT Stop Timer For:
- Agent thinking/processing
- Tests running
- Code compilation
- Agent debugging own issues

---

## Data Collection

### Required Metrics
- [ ] Total elapsed time (minutes)
- [ ] Subtasks completed (count)
- [ ] Files created (count)
- [ ] Tests passing (yes/no)
- [ ] Endpoints working (yes/no)
- [ ] Quality assessment (Full/Partial/Incomplete)

### Optional Metrics
- Average time per subtask
- Number of interventions needed
- Types of errors encountered
- Code quality score (subjective)

---

## Results Reporting

### Single Agent Results
```
Agent: [name/model]
Total Time: ___ minutes
Subtasks: ___ / 22 (___%)
Quality: [Full/Partial/Incomplete]
Winner: [Single Agent / Marcus / Tie]
```

### Marcus Results (Baseline)
```
System: Marcus Multi-Agent
Total Time: 21.37 minutes
Subtasks: 17 / 17 (100%)
Quality: Full
```

### Comparison
```
Speedup: [X]x faster/slower
Completion: [+/-]% vs Marcus
Quality: [Better/Same/Worse]
```

---

## Experiment Variations

### Prototype (Current)
- Subtasks: 22
- Target: <30 minutes
- Quality: Working MVP

### Standard (Next)
- Subtasks: 40-60
- Target: <60 minutes
- Quality: Production-ready

### Enterprise (Future)
- Subtasks: 80-120
- Target: <120 minutes
- Quality: Enterprise-grade

---

## Post-Experiment Analysis

After completing the experiment, analyze:

1. **Speed**: Was single agent faster or slower?
2. **Quality**: Was output better or worse?
3. **Completeness**: Did agent finish all subtasks?
4. **Scalability**: Would this scale to larger projects?
5. **Reliability**: Could you reproduce this result?

Write findings in tracking sheet's "Observations" section.

---

## Checklist Before Starting

- [ ] Marcus baseline data confirmed (21.37 min)
- [ ] Clean workspace created
- [ ] Prompt file ready
- [ ] Tracking sheet open
- [ ] Timer ready
- [ ] Understand quality standards
- [ ] Understand intervention rules
- [ ] Ready to be hands-off

**Only start experiment when ALL boxes checked**

---

## Emergency Stop Conditions

Stop experiment immediately if:
- Agent creates malicious/unsafe code
- System errors prevent continuation
- Agent stuck in infinite loop
- File system issues occur

Mark as INCOMPLETE and note reason.

---

## Good Luck!

Remember: This is a scientific experiment. Be objective, be fair, and let the data speak for itself.
