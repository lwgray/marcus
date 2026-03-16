# Single Agent Trial Experiment

This experiment framework runs **isolated single-agent trials** to establish baseline performance metrics for comparison with multi-agent experiments.

## Purpose

Compare single-agent vs multi-agent performance on the same task to determine if multi-agent coordination provides measurable benefits.

## How It Works

### Trial Isolation
- Each trial runs in a **separate directory**
- Each uses a **fresh LLM instance** (no shared context)
- No cross-contamination between trials

### Metrics Tracked
- **Success/Failure** - Did the agent complete the task?
- **Duration** - How long did it take?
- **Token Usage** - How many tokens were consumed?
- **Quality Scores** - LLM judge evaluates output (0-100)

### Evaluation Criteria (LLM Judge)
- **Completeness** (40 pts) - All features implemented
- **Functionality** (30 pts) - Game works correctly
- **Code Quality** (20 pts) - Well-structured, documented
- **User Experience** (10 pts) - Intuitive, responsive
- **Passing**: ≥80/100

## Usage

### 1. Run 20 Trials

**IMPORTANT**: Trials MUST run OUTSIDE the Marcus directory to avoid contamination!

A timestamped experiment folder is automatically created for each run.

```bash
# Serial execution (safe, slower - ~28 min for 20 trials)
python experiments/run_single_agent_trials.py \
  experiments/snake_game_single_agent_prompt.md \
  --output-dir ~/trials \
  --num-trials 20

# PARALLEL execution (fast! - ~2 min for 20 trials)
python experiments/run_single_agent_trials.py \
  experiments/snake_game_single_agent_prompt.md \
  --output-dir ~/trials \
  --num-trials 20 \
  --parallel

# Parallel with custom worker count
python experiments/run_single_agent_trials.py \
  experiments/snake_game_single_agent_prompt.md \
  --output-dir ~/trials \
  --num-trials 20 \
  --parallel \
  --max-workers 5

# Custom experiment name
python experiments/run_single_agent_trials.py \
  experiments/snake_game_single_agent_prompt.md \
  --output-dir ~/trials \
  --name "snake_v2" \
  --num-trials 20 \
  --parallel
```

**Parallel vs Serial**:
- **Serial**: One trial at a time, ~85s per trial = 28 min for 20 trials
- **Parallel**: All at once (up to max_workers), ~85-120s total for 20 trials

**Validation** (requires Node.js + Puppeteer):
```bash
# Run trials WITH validation (tests if games actually work)
python experiments/run_single_agent_trials.py \
  experiments/snake_game_single_agent_prompt.md \
  --output-dir ~/trials \
  --num-trials 20 \
  --parallel \
  --validate
```

The `--validate` flag:
- ✅ Checks if HTML/JS files exist
- ✅ Validates JavaScript syntax
- ✅ Loads page in headless browser
- ✅ Detects JavaScript runtime errors
- ✅ Reports if game actually works

**Setup for validation**:
```bash
npm install -g puppeteer
# or
yarn global add puppeteer
```

### 2. Evaluate Existing Experiment

```bash
# Use the FULL PATH to the specific experiment folder
python experiments/run_single_agent_trials.py \
  experiments/snake_game_single_agent_prompt.md \
  --output-dir ~/trials/snake_game_single_agent_20260314_153000 \
  --evaluate-only
```

### 3. Quick Test (5 trials in parallel)

```bash
# Creates ~/trials/snake_game_single_agent_20260314_155000/
python experiments/run_single_agent_trials.py \
  experiments/snake_game_single_agent_prompt.md \
  --output-dir ~/trials \
  --num-trials 5 \
  --parallel
```

## Output Structure

**Location**: Outside Marcus directory (e.g., `~/trials/`)

Each run creates a **timestamped experiment folder**:

```
~/trials/                                    # Base directory (OUTSIDE marcus)
├── snake_game_single_agent_20260314_153000/  # First run (timestamped)
│   ├── trial_results.json                   # Raw trial data
│   ├── evaluations.json                     # LLM judge scores
│   ├── trial_001/                           # First trial (isolated)
│   │   ├── prompt.md                        # Copy of the prompt
│   │   ├── trial.log                        # Full Claude CLI output
│   │   ├── result.json                      # Trial metadata
│   │   ├── index.html                       # Generated files
│   │   ├── snake.js
│   │   ├── styles.css
│   │   └── design.md                        # Design doc (if created)
│   ├── trial_002/                           # Second trial
│   │   └── ...
│   └── trial_020/                           # Last trial
│       └── ...
│
└── snake_game_single_agent_20260314_160000/  # Second run (new timestamp)
    ├── trial_results.json
    └── trial_001/
        └── ...
```

## Results Analysis

### trial_results.json
```json
{
  "num_trials": 20,
  "summary": {
    "successful_trials": 18,
    "success_rate": 0.90,
    "average_duration_seconds": 145.3
  },
  "trials": [...]
}
```

### evaluations.json
```json
[
  {
    "trial_dir": "trial_001",
    "completeness_score": 35,
    "functionality_score": 28,
    "code_quality_score": 18,
    "user_experience_score": 8,
    "total_score": 89,
    "passing": true,
    "feedback": "Fully functional snake game with clean code"
  },
  ...
]
```

## Comparison with Multi-Agent

After running both experiments:

| Metric | Single Agent | Multi-Agent (2) |
|--------|-------------|-----------------|
| Success Rate | ?% | 92% |
| Avg Duration | ?s | ?s |
| Avg Quality Score | ?/100 | ?/100 |
| Pass Rate (≥80) | ?% | ?% |

## Next Steps

1. **If single-agent ≈ multi-agent**: Task is too simple
   - Try more complex tasks (full-stack app, API + frontend + DB)
   - Need tasks that benefit from parallelization

2. **If multi-agent > single-agent**: Confirms benefits
   - Document the specific advantages
   - Identify what types of coordination helped

3. **Statistical Significance**:
   - With 20 trials, you can calculate confidence intervals
   - Determine if differences are statistically significant
