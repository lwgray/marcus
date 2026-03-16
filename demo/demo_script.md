# Demo Script: 12-Minute Beat-by-Beat Narration

**CONTEXT:** This is your demo during Slide 5. The slide just says "Let's build something." You've switched to your demo environment. The audience is watching your screen.

**ENVIRONMENT SETUP (BEFORE YOU START):**
- Marcus running locally via Docker
- Cato visualization open in browser
- Kanban board (Planka) open in separate tab
- Terminal visible but not cluttered
- Screen resolution tested for projector (1080p minimum)
- Pomodoro timer demo tested 3+ times in this exact environment

**BACKUP PLAN:** Pre-recorded video of this exact demo on second laptop, ready to switch if live demo fails.

---

## MINUTE 1-2: Project Setup & Task Generation

### What You Do:
1. Open Marcus interface (terminal or web UI)
2. Type the project description clearly so audience can read it

### What You Say:

> "Alright, let's build a Pomodoro timer web app. I'm going to tell Marcus what I want in plain English, and watch how it coordinates multiple agents to build it."

**[Type into Marcus]:**
```
Project: Build a Pomodoro timer web app
Build Level: Standard
Description: 25-minute work sessions with 5-minute breaks,
start/stop/reset controls, visual timer display, sound notifications
```

**[Hit enter/submit]**

> "Marcus is now analyzing this goal and breaking it down into tasks."

**[Wait 5-10 seconds for tasks to appear on the Kanban board]**

### What You Say When Tasks Appear:

> "There we go. Marcus created six tasks:"

**[Point to each task on screen as you read them]:**

1. Set up project structure and dependencies
2. Build core timer logic
3. Create UI components
4. Add sound notification system
5. Write tests
6. Integration and final review

> "Notice these aren't vague categories - they're specific, actionable work items. And Marcus has already figured out the dependencies."

---

## MINUTE 2-4: Show Dependency Graph

### What You Do:
Switch to Cato dependency graph view

### What You Say:

> "Let me show you that dependency structure in Cato."

**[Open Cato dependency graph]**

> "See this flow? Project structure has to be done first - nothing else can start without it. Then timer logic. The UI depends on the timer logic being complete - you can't build a user interface for an API that doesn't exist yet. Sound notifications can happen in parallel with the UI. Tests come after implementation. Finally, integration review."

**[Point to the arrows connecting nodes as you explain]**

> "Marcus built this dependency graph automatically. Agents will never get a task they don't have the context to complete."

---

## MINUTE 4-5: Agent Registration & Task Assignment

### What You Do:
Show agents registering with Marcus (if visible in your setup) or describe what's happening

### What You Say:

> "Now agents are registering with Marcus and declaring their capabilities. One agent says 'I do backend work.' Another says 'I handle frontend UI.' A third says 'I write tests.'"

**[If you can show this happening, point to it. If not, continue:]**

> "Marcus assigns tasks based on those capabilities. Backend agent gets the timer logic task. Frontend agent gets the UI. Test agent gets the testing work. Each agent only sees the task that fits them."

---

## MINUTE 5-7: Parallel Execution - Swim Lane View

### What You Do:
Switch to Cato swim lane view (agents working in parallel)

### What You Say:

> "This is where it gets interesting. Watch the swim lane view."

**[Cato swim lane should show multiple agents working simultaneously on different tasks]**

> "Agent 1 is working on project structure. Agent 2 just picked up the timer logic task - but notice it's waiting because it depends on structure being done first."

**[Wait for structure task to complete]**

> "There - structure is done. Now Agent 2 can start on timer logic."

**[Point to the parallel work happening]**

> "Now we've got Agent 2 building the timer logic and Agent 3 starting on the UI - wait, no, the UI task is still blocked because it depends on timer logic. Marcus won't assign it until the dependency is met."

**[This demonstrates the dependency enforcement in real-time]**

---

## MINUTE 8-9: THE PAUSE MOMENT (Most Important 90 Seconds)

### What You Do:
1. Stop the demo mid-execution
2. Click into a task that is currently in progress
3. Slowly scroll through the board state
4. Let the audience read what's on screen

### What You Say:

> "Let me pause here for a second and show you something important."

**[Click into the currently active task - show the task detail view]**

> "This is the task Agent 2 is working on right now - building the timer logic. Look at what this agent can see."

**[Scroll through the artifacts and context from previous tasks]**

> "Here's the project structure that Agent 1 built. Here's the package.json. Here's the folder layout. Here are the architectural decisions that were made and why - all logged as artifacts on the board."

**[Pause. Point to the screen.]**

> "This is everything any agent in this system knows. Complete context. No direct communication needed. The board is the shared memory."

**[Five full seconds of silence. Let them read what's on screen. This is critical - don't rush it.]**

> "If this agent fails right now, another agent can pick up this exact task tomorrow with full context. Nothing is lost. Everything is recoverable."

**[Resume the demo]**

---

## MINUTE 10-11: Build Completes - Dependency Graph Playback

### What You Do:
1. Wait for build to complete (or fast-forward if pre-recorded)
2. Switch back to Cato dependency graph
3. Use the playback feature to show execution timeline

### What You Say:

> "Alright, the build is done. Let me show you the execution timeline."

**[Open Cato dependency graph with playback controls]**

> "This is the dependency graph we saw at the beginning. Now I can play back how work actually flowed through it."

**[Start the timeline playback - nodes should light up in sequence as tasks complete]**

> "Structure completed first - 2 minutes. Timer logic started immediately after, took 3 minutes. UI and sound notifications happened in parallel once timer logic was done. Tests ran after everything else. Total execution time: 11 minutes with three agents working in parallel."

**[Point to the timeline]**

> "If this was a single agent working sequentially, it would have taken closer to 25 minutes. That's the parallelism paying off - but only because Marcus coordinated the dependencies correctly."

---

## MINUTE 11-12: Audit Trail - Complete Observability

### What You Do:
1. Click on a completed task (pick the timer logic task)
2. Show the full communication log between Marcus and the agent

### What You Say:

> "Now the most important part - the audit trail."

**[Click into the completed timer logic task]**

> "I can click into any task, any node, any moment in the execution timeline and see exactly what happened."

**[Scroll through the communication log]**

> "Here's every message between Marcus and the agent. 'Task assigned.' Progress report: 'Setting up timer state management.' Another progress report: 'Implementing start/stop/reset functions.' Artifact delivered: 'Here's the timer.js file I built.'"

**[Point to the artifact]**

> "Every architectural decision is logged. Every piece of code is published as an artifact. The next agent inherited all of this."

**[Final point]**

> "And here's why this matters: if something had gone wrong - if the UI agent couldn't find the timer API, if the tests failed, if the build broke - I could come to this exact view and tell you why. Was it a bad instruction from Marcus? Or was it an agent that received a good instruction and chose not to follow it?"

**[Pause. Let that sink in.]**

> "With Marcus and Cato together, you can always answer that question."

**[End demo. Advance to Slide 6.]**

---

## Demo Technical Notes

### If the Demo Fails Live:

**Stay calm. Have your backup video ready.**

> "Network's being flaky. Let me switch to a recording I made earlier."

Switch to pre-recorded video without apologizing or dwelling on it. The audience doesn't care if it's live or recorded - they care that you can show them how it works.

### Timing Adjustments:

- **If ahead of schedule:** Spend more time in the pause moment (Minute 8-9). Let the audience ask questions if appropriate.
- **If behind schedule:** Skip the dependency graph playback (Minute 10-11) and go straight to the audit trail. The audit trail is more important.

### What to Avoid:

❌ Don't explain every technical detail of how Marcus works internally
❌ Don't debug live if something goes wrong - switch to backup
❌ Don't read code line-by-line - point to artifacts and move on
❌ Don't let the demo go longer than 12 minutes total

### What to Emphasize:

✅ The dependency structure Marcus builds automatically
✅ Agents working in parallel (swim lane view is visually compelling)
✅ The pause moment - this is your mic drop
✅ The audit trail - this is what sets Marcus apart from everything else

### Practice Notes:

**Run this demo 10+ times before the talk.**

- Practice the pause moment until it feels natural, not rehearsed
- Know where to click without hunting for buttons
- Time yourself - if it's running longer than 12 minutes, cut something
- Have the backup video ready and know how to switch to it in under 5 seconds

**The demo is 48% of your talk time. It should be tight, confident, and visually compelling.**

---

## Post-Demo Transition

When the demo ends, pause for 2-3 seconds. Let the audience absorb what they just saw. Then:

> "That's Marcus and Cato working together. Now let me tell you why this pattern matters."

**[Advance to Slide 6: Why This Matters]**
