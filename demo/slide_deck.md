# Marcus + Cato: Conference Slide Deck
**25-Minute Talk Structure**

---

## SLIDE 1: Title Slide (2 minutes)

### Visual:
- Title: **Marcus + Cato**
- Subtitle: **Coordination & Observability for Multi-Agent AI**
- Your name: Lawrence Gray
- Role: Sr. Machine Learning Educator, Blue River Technology
  Adjunct Professor, Georgetown University
- Bottom: `github.com/lwgray/marcus` • `marcus-ai.dev`

### What You Say:

> "Six months ago, I was watching Claude grind through a task that was taking way too long. I thought: 'If one agent takes an hour, shouldn't two agents take thirty minutes?'
>
> That question led me to build something I'm calling Marcus and Cato. Today I want to show you why the answer wasn't what I expected - and what I learned about coordination and observability in multi-agent systems."

**[Pause. Let it settle. Then advance to next slide.]**

---

## SLIDE 2: The Problem (3 minutes total)

### Visual:
Split screen - two diagrams side by side:

**LEFT SIDE: "Coordination Chaos"**
- Diagram: Multiple agents with arrows connecting them directly
- Arrows going everywhere, crisscrossing
- Label key issues:
  - Context overflow
  - Opaque decisions
  - No recovery when failure happens

**RIGHT SIDE: "The Black Box"**
- Diagram: Multi-agent pipeline as a black box
- Inputs on left, outputs on right
- Big question mark in the middle
- Label: "When it fails, you can't tell why"

### What You Say:

**[Point to left diagram]**

> "The first problem every AI engineer runs into: coordination chaos. When agents communicate directly with each other, three things happen reliably:
>
> One - context windows overflow. Agents lose track of what was decided earlier.
>
> Two - communication becomes opaque. You can't see what agents said to each other or why they made the decisions they made.
>
> Three - there's no recovery. If an agent fails mid-task, the context it held dies with it."

**[90 seconds. Then point to right diagram]**

> "The second problem: even when multi-agent systems work, you can't see inside them. When something fails in your pipeline, can you tell me whether it was a bad instruction or an agent that ignored a good one?
>
> Most systems today cannot answer that question."

**[90 seconds total. Advance.]**

---

## SLIDE 3: The Insight (2 minutes)

### Visual:
Side-by-side comparison:

**BEFORE:**
- Agents with direct communication lines between them
- Label: "Direct Agent Communication"
- Visual chaos - lots of arrows

**AFTER:**
- Agents all connecting to a central board in the middle
- Label: "Board-Mediated Coordination"
- Clean, organized, star-pattern connections
- The board is labeled: "Shared Memory • Context • Artifacts"

### What You Say:

> "So I asked a different question. What if agents never talked to each other at all?"

**[Pause. Three full seconds. Let the room sit with that.]**

> "What if they communicated through a shared board - the same way software developers have coordinated for decades using Kanban?
>
> Each agent registers, pulls a task, does the work, and publishes what they built as artifacts on the board. The next agent picks up with full context - not from a conversation, but from the board.
>
> No agent ever needs to talk to another agent. The board is the coordination mechanism. The board is the shared memory."

**[Point to the AFTER diagram]**

> "If everything goes through the board, everything is visible. And if everything is visible, everything is debuggable."

**[Advance.]**

---

## SLIDE 4: Meet Marcus & Cato (1 minute)

### Visual:
Two sections, clean and minimal:

**Marcus**
- Subtitle: "AI Agent Coordination Platform"
- Icon or symbol: Coordinated task flow
- One line: "Board-mediated coordination with dependency tracking"

**Cato**
- Subtitle: "Observability & Visualization Layer"
- Icon or symbol: Dashboard/visibility
- One line: "Complete audit trail of every agent action"

**Bottom of slide:**
- **Open Source • MIT License**
- `github.com/lwgray/marcus`

### What You Say:

> "I built two systems. Marcus coordinates. Cato watches.
>
> Marcus is named after Marcus Aurelius - the Stoic philosopher who believed each part of a system should know its role and serve the whole with discipline.
>
> Cato is named after Cato the Younger - who believed nothing in any system should be hidden from scrutiny.
>
> Together they make multi-agent AI something you can actually trust in production.
>
> Both are open source today. Let me show you how they work."

**[Advance immediately to demo slide.]**

---

## SLIDE 5: Demo Slide (12 minutes - DEMO TIME)

### Visual:
Simple, centered text:

**"Let's build something."**

That's it. Nothing else on the slide.

### What You Do:
Switch to live demo or pre-recorded video.

*[See demo_script.md for complete 12-minute beat-by-beat narration]*

**Key moments:**
1. Enter project description: "Build a Pomodoro timer web app"
2. Watch tasks appear on board
3. Show dependency graph
4. Switch to Cato swim lane view - agents working in parallel
5. **THE PAUSE MOMENT** - Stop mid-execution, click into active task, show board state
6. Resume, let build complete
7. Show Cato dependency graph playback
8. Click completed task, show full audit trail

**At the end of demo, advance to next slide.**

---

## SLIDE 6: Why This Matters (3 minutes)

### Visual:
Three numbered points, each with an icon or visual anchor:

**1. Observability Isn't Optional**
- Production AI systems need audit trails

**2. Coordination Is The Bottleneck**
- Agents are getting smarter, but can't work together reliably

**3. This Pattern Scales**
- Beyond code: research, content, autonomous systems

### What You Say:

> "Three reasons this pattern matters:
>
> **First - Observability isn't optional anymore.** If you're deploying AI agents in production, you need to know what they did and why. Marcus gives you a complete audit trail of every decision, every artifact, every piece of context that changed hands. When something goes wrong, you can diagnose it.
>
> **Second - Coordination is the bottleneck, not capability.** The models are getting better every month. But they still can't work together reliably at scale. Board-mediated coordination solves that - it's a pattern that scales without breaking down as you add more agents.
>
> **Third - This pattern scales beyond code.** Research pipelines where multiple AI systems need to analyze data and build on each other's findings. Content creation workflows where agents handle research, drafting, and editing in sequence. Autonomous systems where perception, planning, and decision-making components need to coordinate with full accountability.
>
> Anywhere you need intelligent components to work together reliably with observable behavior - this pattern applies."

**[Advance to close.]**

---

## SLIDE 7: The Close (2 minutes)

### Visual:
Clean, centered:

**Marcus + Cato**

**Open Source • MIT License**

**github.com/lwgray/marcus**

**marcus-ai.dev**

Bottom corner: Your name and contact info

### What You Say:

> "Both systems are open source today. MIT License - free to use, fork, and contribute.
>
> The GitHub link is on screen. If you try it, I want to hear what breaks. And if you're working on multi-agent coordination problems - or just curious about this approach - I'd love to talk more after the session."

**[Pause. Smile.]**

> "Thank you."

**[STOP. Don't summarize. Don't recap. Let the demo be the mic drop.]**

---

## Slide Design Guidelines

**Font Sizes for Projector Readability:**
- Title text: 60pt minimum
- Body text: 32pt minimum
- Code/terminal text: 28pt minimum with high contrast

**Color Palette:**
- Dark background (reduces projector glare)
- High contrast text (white or light blue on dark)
- Accent color for key terms (gold/orange for emphasis)

**Visual Hierarchy:**
- One idea per slide
- Maximum 3 bullet points per slide
- Use whitespace - don't fill every inch
- Diagrams > Text whenever possible

**Timing Markers:**
- Slide 1: 0:00 - 2:00
- Slide 2: 2:00 - 5:00
- Slide 3: 5:00 - 7:00
- Slide 4: 7:00 - 8:00
- Slide 5: 8:00 - 20:00 (DEMO)
- Slide 6: 20:00 - 23:00
- Slide 7: 23:00 - 25:00

**Total: 25 minutes**
