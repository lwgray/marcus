# False Positive Monitoring Guide

## Overview

This guide provides explicit instructions for monitoring false positive recovery rates over a 2-week period after deploying aggressive timeout settings (90s initial timeout).

## Background

### What is a False Positive Recovery?

A **false positive** occurs when Marcus recovers a task from an agent that is still actively working on it. This happens when:

1. The lease expires (e.g., 90 seconds with no progress update)
2. Marcus recovers the task and reassigns it
3. The original agent was still working and reports progress shortly after recovery

False positives are disruptive because they:
- Interrupt productive work
- Waste agent time (work gets discarded)
- Can demoralize agents
- Reduce overall system efficiency

### Target False Positive Rate

- **Excellent**: < 3% (current goal with aggressive settings)
- **Acceptable**: 3-5% (monitor closely)
- **Concerning**: 5-10% (consider tuning)
- **Unacceptable**: > 10% (requires immediate tuning)

### Why Aggressive Timeouts?

Marcus uses aggressive 90-second timeouts because:
- You **cannot spawn agents on demand** (no agent pool)
- Recovery means waiting for existing agent to finish OR crashed agent to restart
- This can take **minutes to hours**
- Fast detection of actual failures is critical

The trade-off: accepting slightly higher false positive risk (target 3-5%) in exchange for faster failure detection.

## Monitoring Schedule

### Week 1: Baseline Assessment

**Days 1-7**: Establish baseline false positive rate

```bash
# Run daily monitoring (every 24 hours)
python scripts/monitor_false_positives.py --days 7 --output reports/fp_week1.json
```

**What to check:**
- False positive rate
- Total recovery events
- Time of day patterns
- Task type patterns

**Action thresholds:**
- If FP rate > 10%: **Adjust immediately** (don't wait for Week 2)
- If FP rate 5-10%: **Monitor closely**, prepare to adjust
- If FP rate < 5%: **Continue monitoring**

### Week 2: Trend Analysis

**Days 8-14**: Confirm trends and make final tuning decisions

```bash
# Run monitoring with full 14-day window
python scripts/monitor_false_positives.py --days 14 --output reports/fp_week2.json
```

**What to check:**
- Is FP rate stable, increasing, or decreasing?
- Are false positives clustered (specific tasks, times, agents)?
- Do patterns suggest systematic issues?

**Decision criteria:**
- If FP rate < 3%: **KEEP aggressive settings** ✅
- If FP rate 3-5%: **KEEP but continue monitoring** ⚠️
- If FP rate 5-10%: **TUNE moderately** (increase to 100-110s) 📊
- If FP rate > 10%: **TUNE conservatively** (increase to 120s) 🔴

## Daily Monitoring Routine

### Step 1: Run the Monitoring Script

```bash
cd /Users/lwgray/dev/marcus

# Basic monitoring (last 7 days)
python scripts/monitor_false_positives.py

# With custom output
python scripts/monitor_false_positives.py --days 7 --output reports/fp_$(date +%Y%m%d).json

# Full 14-day analysis
python scripts/monitor_false_positives.py --days 14 --output reports/fp_full.json
```

### Step 2: Review the Output

The script produces a summary report:

```
======================================================================
FALSE POSITIVE RECOVERY ANALYSIS
======================================================================

Analysis Period: 7 days
Start: 2026-03-12T14:00:00+00:00
End: 2026-03-19T14:00:00+00:00

----------------------------------------------------------------------
SUMMARY
----------------------------------------------------------------------
Total Recoveries: 45
False Positives: 2
True Positives: 43
False Positive Rate: 4.44% 🟡 Moderate

----------------------------------------------------------------------
RECOMMENDATION
----------------------------------------------------------------------
Action: MONITOR
Current Timeout: 90s (aggressive)
Suggested: Keep current: 90s, consider 100s if rate increases

False positive rate is acceptable (4.4%). Continue monitoring for
another week. Consider slightly increasing if rate trends upward.
```

### Step 3: Log Results

Create a monitoring log file to track trends:

```bash
# Create monitoring log directory
mkdir -p logs/monitoring

# Append daily results
echo "$(date +%Y-%m-%d) - FP Rate: $(python scripts/monitor_false_positives.py | grep 'False Positive Rate' | awk '{print $4}')" >> logs/monitoring/fp_tracking.log
```

### Step 4: Interpret Results

**Understanding the output:**

1. **Total Recoveries**: Number of tasks recovered from agents
   - High count: Many timeouts occurring (expected during testing)
   - Low count: Few failures (good, but might not be testing enough)

2. **False Positives**: Recoveries where agent was still working
   - Look at details: Why did agent not report progress in time?
   - Check time deltas: How quickly did agent respond after recovery?

3. **False Positive Rate**: Percentage of recoveries that were premature
   - This is your key metric for tuning decisions

4. **Recommendation**: Automated guidance based on current rate
   - Follow these recommendations unless you have specific context

## Tuning Actions

### If False Positive Rate is Too High (> 5%)

#### Option 1: Increase Initial Timeout (Recommended)

Edit `src/core/assignment_lease.py`:

```python
# Change from:
default_lease_hours: float = 0.025,  # 90 seconds (aggressive)

# To (moderate):
default_lease_hours: float = 0.028,  # 100 seconds

# Or (conservative):
default_lease_hours: float = 0.033,  # 120 seconds
```

#### Option 2: Adjust Grace Period

```python
# Change from:
grace_period_minutes: float = 0.5,  # 30 seconds

# To:
grace_period_minutes: float = 0.67,  # 40 seconds
```

#### Option 3: Modify Progressive Timeout Phases

In `calculate_adaptive_timeout()` method:

```python
# Phase 1: Unproven (no updates yet)
if update_count == 0:
    return (70, 25)  # Increased from (60, 20)

# Phase 2: Working (first update)
if update_count == 1:
    return (100, 30)  # Increased from (90, 30)
```

### After Making Changes

1. **Restart Marcus** to apply new settings
2. **Reset monitoring period** (start fresh 2-week window)
3. **Document the change** in monitoring log:
   ```bash
   echo "$(date +%Y-%m-%d) - TUNING: Increased timeout from 90s to 100s due to 7.2% FP rate" >> logs/monitoring/fp_tracking.log
   ```

## Advanced Analysis

### Identifying Patterns

If you have false positives, look for patterns:

1. **Time-based patterns**:
   ```bash
   # Extract timestamps from false positives
   jq '.false_positive_details[].recovery.timestamp' reports/fp_full.json

   # Check if FPs cluster at specific times (e.g., heavy load periods)
   ```

2. **Task-based patterns**:
   ```bash
   # Check which tasks are recovered
   jq '.false_positive_details[].recovery.task_id' reports/fp_full.json | sort | uniq -c

   # Are certain task types more prone to false positives?
   ```

3. **Agent-based patterns**:
   ```bash
   # Check which agents are affected
   jq '.false_positive_details[].recovery.agent_id' reports/fp_full.json | sort | uniq -c

   # Is one agent consistently slow to report progress?
   ```

### Manual Verification

To manually verify a suspected false positive:

1. Find the recovery event in logs:
   ```bash
   grep "Recovering task task-123" logs/conversations/*.jsonl
   ```

2. Check if agent reported progress after recovery:
   ```bash
   grep -A 10 "Recovering task task-123" logs/conversations/*.jsonl | grep progress
   ```

3. Examine the time gap:
   - If agent reported progress < 2 minutes after recovery: **Likely false positive**
   - If agent reported progress > 5 minutes after recovery: **Likely legitimate timeout**
   - If no subsequent progress: **Legitimate timeout** ✓

## Troubleshooting

### No Recovery Events Found

**Possible causes:**
1. Log directory path incorrect
2. Logs not in expected JSONL format
3. No actual recovery events in time window
4. Agent hasn't crashed or timed out yet

**Solutions:**
```bash
# Verify logs exist
ls -lh logs/conversations/*.jsonl | head -5

# Check log format
head -1 logs/conversations/*.jsonl | jq .

# Manually search for recovery events
grep -i "recover" logs/conversations/*.jsonl | head -5
```

### Script Reports 100% False Positive Rate

**Possible causes:**
1. Log format doesn't match expected patterns
2. Progress updates not being detected
3. Recovery events not being parsed correctly

**Solutions:**
1. Check log entry format in `_process_log_entry()`
2. Update pattern matching for your actual log structure
3. Add debug logging to see what's being extracted

### Conflicting Recommendations

If daily reports show varying recommendations:

1. **Look at the trend**, not individual days
2. Calculate **7-day rolling average** FP rate
3. Make decisions based on **sustained patterns**, not outliers

## Success Criteria

After 2 weeks, you should have:

1. ✅ **Stable FP rate** (not increasing over time)
2. ✅ **FP rate < 5%** (acceptable for aggressive settings)
3. ✅ **Understanding of patterns** (when/why FPs occur)
4. ✅ **Documented baseline** (for future comparison)
5. ✅ **Tuning decision made** (keep, adjust moderately, or adjust aggressively)

## Next Steps

### If FP Rate is Acceptable (< 5%)

1. **Continue monthly monitoring** to detect degradation
2. **Set up automated alerts** if FP rate exceeds 7%
3. **Document in runbook** for operations team

### If FP Rate Requires Tuning

1. **Apply timeout adjustments** (see Tuning Actions above)
2. **Restart 2-week monitoring** with new settings
3. **Compare results** to baseline

### Long-term Monitoring

After initial 2-week period:

```bash
# Weekly check (Fridays)
python scripts/monitor_false_positives.py --days 7 --output reports/fp_weekly.json

# Monthly review (First Monday of month)
python scripts/monitor_false_positives.py --days 30 --output reports/fp_monthly_$(date +%Y%m).json
```

## Summary

### Quick Reference

| FP Rate | Status | Action | Timeline |
|---------|--------|--------|----------|
| < 3% | 🟢 Excellent | Keep current settings | Monthly monitoring |
| 3-5% | 🟡 Acceptable | Continue monitoring | Weekly checks |
| 5-10% | 🟠 Concerning | Plan to tune | Tune within 1 week |
| > 10% | 🔴 Unacceptable | Tune immediately | Adjust within 24 hours |

### Key Commands

```bash
# Daily monitoring
python scripts/monitor_false_positives.py --days 7

# Weekly summary
python scripts/monitor_false_positives.py --days 7 --output reports/fp_week1.json

# Full 2-week analysis
python scripts/monitor_false_positives.py --days 14 --output reports/fp_full.json

# Track trends
echo "$(date +%Y-%m-%d) - FP Rate: X.X%" >> logs/monitoring/fp_tracking.log
```

### Contact and Support

If you encounter issues with monitoring:
1. Check script logs in `logs/monitoring/`
2. Review log format expectations in script docstrings
3. Create GitHub issue with monitoring report attached

## Appendix: Log Format Requirements

The monitoring script expects conversation logs in JSONL format with:

```json
{
  "timestamp": "2026-03-19T14:23:45.123456+00:00",
  "content": "Recovering task task-123 from agent agent-456",
  "agent_id": "agent-456",
  "task_id": "task-123"
}
```

**Minimum required fields:**
- `timestamp`: ISO format with timezone
- `content`: Log message text

**Optional but helpful:**
- `agent_id`: Agent identifier
- `task_id`: Task identifier

The script uses pattern matching on `content` if structured fields aren't present.
