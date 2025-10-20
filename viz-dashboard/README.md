# Marcus Multi-Agent Parallelization Visualization Dashboard

An interactive visualization dashboard that reveals the hidden parallelization happening in Marcus' multi-agent task execution system. This dashboard provides three drilling layers showing task dependencies, resource utilization, and real-time agent-to-Marcus communication.

## 🎯 Features

### Three-Layer Drill-Down Architecture

#### Layer 1: Task Network Graph
- **Visual representation** of task dependencies as an interactive graph
- **D3.js force-directed layout** with automatic positioning
- **Real-time status coloring** (TODO, IN_PROGRESS, DONE, BLOCKED)
- **Pulsing animations** on active tasks to show parallelization
- **Click to select** tasks for detailed information
- **Zoom and pan** capabilities for large project exploration

#### Layer 2: Agent Swim Lanes
- **Timeline view** showing agent resource utilization over time
- **Horizontal bars** representing task execution periods
- **Message indicators** (💬 questions, 🚫 blockers) overlaid on tasks
- **Real-time progress** indicators showing completion percentage
- **Current time marker** tracking playback position
- **Visual parallelization** - see multiple agents working simultaneously

#### Layer 3: Conversation Threads
- **Complete message timeline** between Marcus and agents
- **Grouped conversations** by task for easy navigation
- **Message type badges** (Instruction, Question, Answer, Blocker, Status Update)
- **Response time tracking** for Marcus replies
- **Threaded message views** showing question/answer pairs
- **Metadata displays** (blocking status, progress updates, blocker resolution)

### Playback Controls
- **Timeline scrubber** for precise time navigation
- **Play/Pause** with adjustable speed (0.5x to 10x)
- **Keyboard shortcuts**:
  - `Space`: Play/Pause
  - `R`: Reset to beginning
  - `←/→`: Skip backward/forward 5 seconds
- **Time markers** showing project progress in minutes

### Metrics Dashboard
- **Parallelization speedup** - compare multi-agent vs single-agent execution
- **Task completion** statistics and progress
- **Communication metrics** - questions, blockers, response times
- **Agent autonomy scores** - showing self-sufficiency
- **Active agent tracking** - who's working at current time
- **Time estimation accuracy** - actual vs estimated hours

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ and npm

### Installation

```bash
cd viz-dashboard
npm install
```

### Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the dashboard.

### Build for Production

```bash
npm run build
npm run preview
```

## 📊 Mock Data

The dashboard comes with a realistic mock dataset simulating an **E-Commerce Platform MVP** project:

- **10 tasks** with real dependencies (DB schema → APIs → Frontend → DevOps)
- **5 agents** with varying skills and autonomy levels:
  - Backend Senior Agent (92% autonomy)
  - Frontend Expert Agent (88% autonomy)
  - Fullstack Junior Agent (65% autonomy - asks more questions)
  - Database Specialist Agent (95% autonomy)
  - DevOps Agent (85% autonomy)
- **~50 messages** showing realistic interactions:
  - Task requests and assignments
  - Progress updates
  - Questions from agents (especially junior)
  - Blockers and resolutions
- **220+ minutes** of simulated parallel execution
- **5.5x speedup** compared to single-agent sequential execution

### Mock Data Source

The mock data in `src/data/mockDataGenerator.ts` is based on Marcus' actual data structures:
- `Task` model from `src/core/models.py`
- `WorkerStatus` (Agent) from `src/core/models.py`
- `Message` format from `src/logging/conversation_logger.py`
- Event logging from `src/logging/agent_events.py`

## 🎨 Technology Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **D3.js** - Network graph visualization
- **Zustand** - State management
- **Framer Motion** - Animations (ready for use)
- **Vite** - Build tool and dev server

## 📁 Project Structure

```
viz-dashboard/
├── src/
│   ├── components/         # React components
│   │   ├── NetworkGraphView.tsx      # Layer 1: Task graph
│   │   ├── AgentSwimLanesView.tsx    # Layer 2: Timeline
│   │   ├── ConversationView.tsx      # Layer 3: Messages
│   │   ├── TimelineControls.tsx      # Playback controls
│   │   └── MetricsPanel.tsx          # Metrics sidebar
│   ├── data/               # Mock data generation
│   │   └── mockDataGenerator.ts
│   ├── store/              # Zustand state management
│   │   └── visualizationStore.ts
│   ├── App.tsx             # Main app component
│   ├── main.tsx            # React entry point
│   └── index.css           # Global styles
├── public/                 # Static assets
├── package.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```

## 🔧 State Management

The dashboard uses Zustand for centralized state management:

### Key State
- `currentTime` - Current playback position (milliseconds)
- `isPlaying` - Playback state
- `playbackSpeed` - 0.5x to 10x
- `currentLayer` - Active view (network | swimlanes | conversations)
- `selectedTaskId`, `selectedAgentId`, `selectedMessageId` - User selections

### Derived Getters
- `getVisibleTasks()` - Filtered tasks based on current settings
- `getMessagesUpToCurrentTime()` - Messages up to playback position
- `getActiveAgentsAtCurrentTime()` - Agents working at current time

## 🎯 Use Cases

### 1. Demonstrating Parallelization Value
Play the timeline and watch multiple agents work simultaneously, then show the **5.5x speedup** metric compared to single-agent execution.

### 2. Identifying Communication Patterns
Switch to Conversation view to see:
- Which agents ask more questions (autonomy analysis)
- Average response times from Marcus
- Blocker frequency and resolution times

### 3. Understanding Task Dependencies
Use Network Graph to:
- Visualize critical path through project
- Identify tasks that unlock parallelization opportunities
- See dependency chains and their impact

### 4. Resource Utilization Analysis
Agent Swim Lanes show:
- Idle time vs active time per agent
- Load balancing across the team
- Task duration accuracy vs estimates

### 5. Agent Performance Comparison
Metrics panel reveals:
- Autonomy scores (92% vs 65% for senior vs junior)
- Questions per task completed
- Task completion counts

## 🚧 Future Enhancements (V2)

- [ ] **Real-time data integration** - Connect to live Marcus instance
- [ ] **Comparison mode** - Side-by-side multi-agent vs single-agent simulation
- [ ] **Export capabilities** - Screenshots, video replay, data export
- [ ] **Advanced filtering** - Filter by agent, task type, time range
- [ ] **Search functionality** - Find specific messages or tasks
- [ ] **Heatmap view** - Communication intensity over time
- [ ] **Cost analysis** - Track token usage per conversation
- [ ] **Agent personality profiles** - Learning styles and patterns

## 📝 Testing

Tests can be added using Vitest:

```bash
npm run test
```

## 🤝 Contributing

This dashboard visualizes Marcus' multi-agent parallelization. To extend it:

1. **Add new metrics** in `calculateMetrics()` in `mockDataGenerator.ts`
2. **Create new views** as React components in `src/components/`
3. **Extend state** in `visualizationStore.ts`
4. **Customize styling** in component CSS files

## 📄 License

This visualization dashboard is part of the Marcus project.

## 🙏 Acknowledgments

Built to demonstrate the power of multi-agent parallelization in Marcus, showcasing how coordination between multiple AI agents can dramatically accelerate project completion.
