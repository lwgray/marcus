# Automated Project Scoring Guide

Quick guide to scoring and comparing Marcus vs Single Agent implementations.

## Quick Start

### 1. Score Marcus Implementation

```bash
python experiments/score_project.py \
    --project-dir ./datetime-api-marcus \
    --output-file ./marcus-score.json
```

### 2. Score Single Agent Implementation

```bash
python experiments/score_project.py \
    --project-dir ./datetime-api-single-agent \
    --output-file ./single-agent-score.json
```

### 3. Compare Results

```bash
python experiments/compare_scores.py \
    --marcus ./marcus-score.json \
    --single ./single-agent-score.json \
    --time-marcus 21.37 \
    --time-single 80.5 \
    --output ./comparison-report.md
```

---

## What Gets Scored

### Functionality (25 points)
- ✓ Application runs without errors
- ✓ Tests exist and pass
- ✓ Test coverage percentage

### Code Quality (20 points)
- ✓ Documentation coverage (docstrings)
- ✓ Code complexity (file sizes)
- ✓ Code organization

### Completeness (20 points)
- ✓ All required deliverables present
- ✓ No stub/placeholder code (TODOs, pass, NotImplemented)
- ✓ Both endpoints implemented

### Project Structure (15 points)
- ✓ Logical directory organization
- ✓ Appropriate number of files
- ✓ Configuration separated from code

### Documentation (12 points)
- ✓ PROJECT_SUCCESS.md exists and is comprehensive
- ✓ API documentation with examples
- ✓ Setup instructions

### Usability (8 points)
- ✓ Single-command startup
- ✓ Dependencies managed (requirements.txt)
- ✓ Example requests provided

---

## Interpreting Scores

### Overall Score Ranges
- **90-100**: Excellent - Production-quality
- **75-89**: Good - Solid implementation
- **60-74**: Acceptable - Works but has issues
- **40-59**: Poor - Significant problems
- **0-39**: Failing - Non-functional

### Quality/Time Ratio
Higher is better. Shows points earned per minute spent.

```
Quality/Time = Total_Score / Time_Minutes

Example:
Marcus: 87 points / 21.37 min = 4.07 pts/min
Single: 75 points / 80.50 min = 0.93 pts/min
```

Marcus is **4.4x more efficient** in this example.

---

## Example Workflow

### Full Experiment with Scoring

```bash
# 1. Run Marcus (already done in your case)
# Marcus completed DateTime API in 21.37 minutes

# 2. Run Single Agent experiment
# Track time carefully!
START_TIME=$(date +%s)

# Paste prompt from experiments/single-agent-datetime-api-prompt-v2.md
# to your single agent (Claude Code, etc.)

END_TIME=$(date +%s)
ELAPSED=$(( (END_TIME - START_TIME) / 60 ))
echo "Single agent took: $ELAPSED minutes"

# 3. Score both implementations
cd /path/to/marcus/implementation
python ~/dev/marcus/experiments/score_project.py \
    --project-dir . \
    --output-file ~/marcus-score.json

cd /path/to/single-agent/implementation
python ~/dev/marcus/experiments/score_project.py \
    --project-dir . \
    --output-file ~/single-score.json

# 4. Generate comparison report
python ~/dev/marcus/experiments/compare_scores.py \
    --marcus ~/marcus-score.json \
    --single ~/single-score.json \
    --time-marcus 21.37 \
    --time-single $ELAPSED \
    --output ~/comparison-report.md

# 5. View results
cat ~/comparison-report.md
```

---

## Score Output Format

### JSON Score File

```json
{
  "project_name": "datetime-api-marcus",
  "total_score": 87.0,
  "total_possible": 100,
  "percentage": 87.0,
  "categories": [
    {
      "category": "Functionality",
      "points_earned": 23.0,
      "points_possible": 25,
      "percentage": 92.0,
      "details": {
        "has_main_file": true,
        "test_files_count": 5,
        "app_runs_score": 10
      }
    },
    ...
  ],
  "metadata": {
    "project_directory": "./datetime-api-marcus",
    "python_files_analyzed": 12
  }
}
```

### Comparison Report (Markdown)

The comparison report includes:
- Overall scores and winner
- Time comparison
- Quality/time ratio
- Category-by-category breakdown
- Strengths and weaknesses
- Detailed analysis
- Recommendations

---

## Tips for Fair Comparison

1. **Same Environment**
   - Use same Python version
   - Same machine/resources
   - Same time of day (for consistency)

2. **Clean Implementations**
   - Delete and recreate project directories
   - Fresh start for both approaches
   - No pre-existing code

3. **Accurate Timing**
   - Use actual stopwatch
   - Record START and END timestamps
   - See experiments/TIMING-INSTRUCTIONS.md

4. **Multiple Runs**
   - Run experiment 3 times
   - Average the scores
   - Report variance

5. **Blind Scoring**
   - Score projects without knowing which is which
   - Have someone else score for objectivity

---

## Troubleshooting

### "No Python files found"
Make sure you're pointing to the actual project directory with `.py` files.

### "Score seems too low"
The scorer is conservative. It can't run tests or the application itself, so it uses heuristics. Manual verification recommended.

### "Missing category details"
This is normal if the project doesn't have certain features (e.g., no config file = 0 points for that subcategory).

### "Comparison report looks wrong"
Double-check:
- Are JSON files from correct projects?
- Are time values accurate?
- Did both projects actually complete?

---

## Manual Verification Checklist

After automated scoring, manually verify:

- [ ] Both endpoints actually work when you run them
- [ ] All tests actually pass
- [ ] Documentation instructions actually work
- [ ] No critical bugs missed by automated scoring
- [ ] Code quality passes your personal review

The automated scorer catches ~80% of quality issues. Human review catches the rest.

---

## Extending the Rubric

To add new scoring criteria:

1. Edit `experiments/PROJECT-SCORING-RUBRIC.md`
2. Update `score_project.py`:
   - Add new method to `ProjectScorer` class
   - Call it in `score_project()`
3. Update `compare_scores.py` if needed for reporting
4. Update this guide

---

## Questions?

- Rubric details: See `experiments/PROJECT-SCORING-RUBRIC.md`
- Timing guidelines: See `experiments/TIMING-INSTRUCTIONS.md`
- Experiment protocol: See `experiments/EXPERIMENT-PROTOCOL.md`
