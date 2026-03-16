# Critical: Accurate Timing Instructions

## The Problem

First experiment reported ~80 minutes, but observer noted it "finished fairly quickly."
This makes the data unreliable and comparison invalid.

## Solution: Precise Timing

### Required Tools
1. **Stopwatch** (phone, computer, or physical)
2. **Notebook** or text file for timestamps
3. **Clock sync** - Verify your system time is accurate

### Timing Protocol

#### BEFORE Starting
```
□ Open stopwatch/timer
□ Open text file for recording times
□ Clear workspace
□ Have prompt ready
□ Take a breath
```

#### START Timer
**EXACTLY when you:**
- Paste the prompt into the agent
- Press Enter/Submit
- Agent begins processing

**Record:**
```
START: [timestamp]
Example: START: 2025-10-23 10:15:32
```

#### DURING Execution
**Record each subtask completion:**
```
SUBTASK 1.1 COMPLETE: [timestamp]
SUBTASK 1.2 COMPLETE: [timestamp]
...
```

This lets you verify timing later and catch anomalies.

#### STOP Timer
**EXACTLY when:**
- Agent states "PROJECT COMPLETE"
- Agent finishes subtask 6.5
- All deliverables shown

**Record:**
```
END: [timestamp]
Example: END: 2025-10-23 10:47:18
```

#### CALCULATE
```
Total Time = END - START
Example: 10:47:18 - 10:15:32 = 31 minutes 46 seconds
```

### What NOT to Include in Time

❌ Don't stop timer for:
- Reading agent output
- Scrolling to see code
- Verifying tests pass
- Agent thinking/processing
- Brief pauses between subtasks

✅ Only stop timer for:
- Taking a break (restart when resuming)
- System crash (note and restart)
- Your intervention (note and measure separately)

### Common Timing Mistakes

**Mistake 1: Estimating After the Fact**
```
❌ "It took about 30 minutes"
✅ "START: 10:15:32, END: 10:47:18 = 31:46"
```

**Mistake 2: Including Setup Time**
```
❌ Started timer while reading prompt
✅ Started timer when agent began processing
```

**Mistake 3: Forgetting to Record**
```
❌ Relying on memory
✅ Writing down every checkpoint
```

**Mistake 4: Pausing for Everything**
```
❌ Stopped timer while scrolling
✅ Only pause for actual breaks/interventions
```

### Verification Checklist

Before declaring results valid:
- [ ] Have exact START timestamp
- [ ] Have exact END timestamp
- [ ] Calculated total elapsed time
- [ ] Recorded subtask checkpoints (optional but recommended)
- [ ] No estimated times used
- [ ] Timer was running continuously (except noted breaks)

### Data Quality Standards

**VALID Timing** ✅:
```
START: 2025-10-23 10:15:32
SUBTASK 1.1: 10:18:45 (3:13 elapsed)
SUBTASK 1.2: 10:22:10 (6:38 elapsed)
...
END: 2025-10-23 10:47:18
TOTAL: 31 minutes 46 seconds
```

**INVALID Timing** ❌:
```
Started around 10:15am
Finished around 10:45am
Total: ~30 minutes
```

### Template for Recording

Copy this to your tracking sheet:

```
EXPERIMENT RUN #___

Agent: _______________
Date: _______________

START: _______________ (exact timestamp)

CHECKPOINTS:
1.1: ___
1.2: ___
1.3: ___
2.1: ___
2.2: ___
2.3: ___
2.4: ___
3.1: ___
3.2: ___
3.3: ___
4.1: ___
4.2: ___
4.3: ___
4.4: ___
5.1: ___
5.2: ___
5.3: ___
5.4: ___
6.1: ___
6.2: ___
6.3: ___
6.4: ___
6.5: ___

END: _______________ (exact timestamp)

TOTAL TIME: _______________ (calculated)

BREAKS/PAUSES (if any):
- None
OR
- Pause at ___, resumed at ___, duration: ___

INTERVENTIONS (if any):
- None
OR
- At ___, reason: ___, duration: ___

VERIFICATION:
□ Exact start time recorded
□ Exact end time recorded
□ Total time calculated accurately
□ No estimates used
□ Timer ran continuously (or breaks documented)

VALID: □ Yes □ No

If NO, explain: _______________
```

---

## Pro Tips

1. **Use System Time**: Most OSes show time. Better than external timer.
   - Windows: Bottom right corner
   - Mac: Top right corner
   - Linux: System tray

2. **Screen Recording**: Consider recording the screen (optional)
   - Provides undeniable proof of timing
   - Can review later if needed
   - No need to manually note each timestamp

3. **Two Devices**: Use phone stopwatch + computer for redundancy

4. **Speak Timestamps**: If screen recording, speak timestamps aloud:
   - "Starting now, 10:15:32"
   - "Subtask 1.1 complete, 10:18:45"

---

## Why This Matters

**Marcus baseline is precisely measured**: 21.37 minutes from database logs

**Single agent must be equally precise** to be a fair comparison.

A difference of even 5-10 minutes changes the interpretation:
- 25 minutes: Comparable to Marcus
- 35 minutes: Marcus has clear advantage
- 45+ minutes: Marcus significantly faster

**Sloppy timing = invalid experiment = wasted effort**

---

## If You Realize Timing Was Bad

**DON'T:**
- Estimate the time
- Average multiple runs
- Use "felt like X minutes"

**DO:**
- Mark the run as INVALID
- Rerun with proper timing
- Learn from the mistake

**Scientific integrity > Getting results quickly**
