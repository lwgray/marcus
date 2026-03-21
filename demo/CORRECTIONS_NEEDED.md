# Corrections for Marcus + Cato Conference Talk
**Date:** March 19, 2026
**Conference:** John Deere Financial ML Ambassador Annual Conference
**Talk Date:** April 15, 2026 at 5pm

---

## CRITICAL CORRECTIONS

### 1. Slide 17 - "Beyond Code: Three Circles of Impact"

#### CURRENT (INCORRECT):
```
Software Development
Marcus coordinating 89 parallel agents to fix its own pre-commit errors
without a single conflict.
```

#### CORRECTED:
```
Software Development
Marcus has successfully coordinated multiple parallel agents on real-world
development tasks. The pattern scales.
```

---

### 2. Slide 19 - "Built for Production. Ready for the Real World."

#### REMOVE THIS LINE:
```
89 agents currently coordinating live in the public repository.
```

#### KEEP:
- MIT License (Free to use, fork, and build on)
- github.com/lwgray/marcus
- marcus-ai.dev
- "The hardest problems show up when real systems meet the real world. Help us find what breaks."

---

### 3. Verbatim Script - Slide 17 Section (Page 12)

#### CURRENT (INCORRECT):
```
The first circle: software development. Marcus has already coordinated
eighty-nine parallel agents to fix its own pre-commit errors — without
a single conflict. Eighty-nine. That commit is in the public repository.
You can read it today.
```

#### CORRECTED:
```
The first circle: software development. Marcus has successfully coordinated
multiple parallel agents on real-world development tasks without conflicts.
The architectural pattern works - whether it's the three agents you just saw
or scaling to more complex projects.
```

---

### 4. Slide 12 - Demo Prompt (TIMING ISSUE)

**PROBLEM:** Pomodoro timer demo takes 25 minutes - your demo slot is only 10-12 minutes.

**SOLUTION:** Use Snake game demo (8 minutes).

#### CURRENT (POMODORO):
```
Build a Pomodoro timer web app. Twenty-five minute work sessions.
Five minute breaks. Start, stop, reset controls. A visual timer display.
Sound notifications.
```

#### CORRECTED (SNAKE GAME):
```
Build a classic Snake game web app. Canvas-based rendering.
Keyboard controls. Score tracking. Game over detection.
Responsive gameplay with collision detection.
```

**Also update Slide 12 in the verbatim script to match the new prompt.**

---

## SNAKE GAME DEMO DETAILS

### Actual Task Breakdown (8-minute runtime)

When you give Marcus the Snake game prompt, it creates these 4 tasks:

1. **Design Game Core/Engine** (blocking task)
2. **Implement Start Game** (depends on #1)
3. **Implement Move Snake** (depends on #1, can parallel with #2)
4. **Test Move Snake** (depends on #2 and #3)

### Demo Flow (Slides 12-16)

**Slide 12 - Setup:**
- Type the Snake game prompt
- Marcus breaks it into 4 tasks
- Tasks appear on the Kanban board

**Slide 13 - Dependency Graph:**
> "See this structure? Design Game Core has to be done first. Nothing else starts without it. Then Start Game and Move Snake can run in parallel — two agents working simultaneously. Testing comes after the implementation. Marcus built this dependency graph automatically. No agent will ever receive a task it doesn't have the context to complete."

**Slide 14 - Parallel Execution:**
- Agent 1: Design Game Core (completes first)
- Agent 2: Implement Start Game (waits for #1, then starts)
- Agent 3: Implement Move Snake (waits for #1, runs parallel with #2)
- Then: Test Move Snake (waits for #2 and #3)

**Slide 15 - THE PAUSE MOMENT:**
- Stop mid-execution (during Move Snake implementation)
- Click into the task
- Show complete context on the board
- "This is everything any agent in this system knows. Complete context. No direct communication needed."

**Slide 16 - Audit Trail:**
- Build completes (~8 minutes total)
- Click into any completed task
- Show the full communication log
- "You can definitively answer why a system failed"

### Why This Demo Works
- ✅ Fits time slot (8 min demo in 10-12 min slot)
- ✅ Shows dependency management (task 1 blocks everything)
- ✅ Shows parallel execution (tasks 2 and 3 run simultaneously)
- ✅ Shows "the pause moment" (complete context visible)
- ✅ Shows audit trail (clickable, playable record)

---

## FILES TO UPDATE

1. **The_AI_Shared_State.pdf** (slides)
   - Slide 12: Change demo prompt to Snake game
   - Slide 17: Update "89 agents" text
   - Slide 19: Remove "89 agents" line

2. **marcus_cato_verbatim_final.pdf** (script)
   - Slide 12 section: Change demo prompt to Snake game
   - Slide 17 section: Update "89 agents" paragraph

---

## REASON FOR CHANGES

- **89 agents claim:** Not based on actual testing (max tested: 10 agents)
- **Pomodoro timing:** 25-minute runtime exceeds 10-12 minute demo slot
- **Credibility:** For a keynote teaching production-grade ML, claims must be defensible

---

## NEXT STEPS AFTER CORRECTIONS

1. ✅ Make these edits
2. ⬜ Test Snake game demo end-to-end (verify 8-minute runtime)
3. ⬜ Record backup video using Snake game demo
4. ⬜ Practice full talk (should be 28-30 minutes total)
5. ⬜ First practice run by March 25

**Timeline: 27 days until talk**
