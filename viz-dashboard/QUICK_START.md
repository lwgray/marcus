# Quick Start Guide - Marcus Visualization Dashboard

## 🚀 Get Running in 2 Minutes

```bash
cd viz-dashboard
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## 🎮 Try This First

1. **Click the Play button** (▶) at the bottom
2. **Watch the magic happen**:
   - Network Graph: Nodes pulse blue as agents work
   - Swim Lanes: Bars fill up as tasks progress
   - Metrics: Speedup factor shows parallelization power

3. **Switch between views** using the top tabs:
   - 🔗 Network Graph - Task dependencies
   - 📊 Agent Swim Lanes - Resource timeline
   - 💬 Conversations - Message threads

4. **Adjust playback speed** (bottom right): Try 5x to see it fast!

## 🎯 What You're Seeing

**Project**: E-Commerce Platform MVP
**Agents**: 5 AI agents with different skills
**Tasks**: 10 interconnected tasks
**Duration**: 220 minutes of parallel work
**Speedup**: **5.5x faster** than single agent

## 📊 Key Metrics to Notice

Look at the right sidebar:
- **Speedup Factor**: 5.5x (the big green number)
- **Max Concurrent**: 5 agents working at once
- **Questions**: Only 2 questions asked (high autonomy!)
- **Blockers**: 2 blockers, both resolved quickly

## 🎨 Color Guide

- **Gray**: Not started yet
- **Blue** (pulsing): Currently working
- **Green**: Completed
- **Red**: Blocked

## ⌨️ Keyboard Shortcuts

- `Space` - Play/Pause
- `R` - Reset to start
- `←` - Skip back 5 seconds
- `→` - Skip forward 5 seconds

## 🎬 Best Demo Moments

### Moment 1: Initial Parallelization (0-30 min)
Set speed to 2x and watch:
- Agent-4 starts database work
- Agent-5 starts DevOps work **simultaneously**
- Zero wait time!

### Moment 2: Agent Question (97 min)
Pause at 97 minutes, switch to Conversations:
- Agent-3 asks "Should I implement pagination?"
- Marcus answers in 2 minutes
- Agent continues immediately

### Moment 3: Maximum Parallelization (180-200 min)
Switch to Swim Lanes, watch around 180 minutes:
- 4-5 agents working at once
- Frontend building while backend finishing
- DevOps configuring infrastructure in parallel

## 🔍 Interactive Features

**Network Graph**:
- Drag nodes to rearrange
- Scroll to zoom
- Click tasks to highlight

**Swim Lanes**:
- Hover over bars to see task names
- Click bars to select tasks
- Look for ❓ (questions) and 🚫 (blockers)

**Conversations**:
- Click messages to highlight
- Scroll to see all messages
- Notice threaded replies (indented)

## 📈 Understanding the Speedup

**Sequential (1 agent)**:
- 119 minutes of actual work
- All tasks done one-by-one
- Agent-1 → Agent-2 → Agent-3 → ...

**Parallel (5 agents)**:
- 220 minutes total duration
- BUT 119 minutes of work done!
- Many tasks running simultaneously
- **Result: 5.5x faster!**

## 💡 What Makes This Cool?

1. **Real-time coordination** - Watch agents communicate with Marcus
2. **Automatic parallelization** - Marcus assigns tasks based on dependencies
3. **Autonomy levels** - Senior agents need less help than juniors
4. **Visual proof** - See parallel execution happening live
5. **Based on real data** - Mock data mirrors actual Marcus structures

## 🎓 Demo Tips

### For a 2-Minute Demo
1. Start on Network Graph
2. Hit Play at 5x speed
3. Point out pulsing blue nodes
4. Show the 5.5x speedup in metrics
5. Done!

### For a 5-Minute Demo
1. Follow the DEMO_GUIDE.md walkthrough
2. Show all 3 layers
3. Explain autonomy scores
4. Answer questions

### For a Deep Dive
1. Pick interesting moments (see above)
2. Pause and explain what's happening
3. Show the conversations behind decisions
4. Compare parallel vs sequential execution

## 🆘 Troubleshooting

**Nothing showing?**
- Check browser console (F12)
- Make sure you ran `npm install`
- Try `http://localhost:3000` not `https`

**Playback not smooth?**
- Reduce speed to 1x or 2x
- Close other tabs
- Reload the page

**Want to customize?**
- Edit `src/data/mockDataGenerator.ts`
- Change task names, agents, timeline
- Rebuild with `npm run dev`

## 📚 More Documentation

- **README.md** - Full project documentation
- **DEMO_GUIDE.md** - Detailed presentation guide
- **IMPLEMENTATION_SUMMARY.md** - Technical details

## 🎉 Have Fun!

This dashboard shows something most people never see: the **hidden coordination** that makes multi-agent systems work. Enjoy exploring! 🚀

---

**Built for Marcus - Showcasing the Power of AI Agent Parallelization**
