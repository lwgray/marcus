# n8n-Style Visualization for PM Agent

## Overview

The PM Agent visualization system is built using Vue 3, Pinia, and Vue Flow, inspired by n8n's workflow editor. It provides a real-time, interactive canvas for visualizing the data flow between PM Agent, Claude Workers, and the Kanban Board.

## Architecture

### Technology Stack
- **Frontend Framework**: Vue 3 with Composition API
- **State Management**: Pinia
- **Flow Visualization**: Vue Flow (Vue.js port of React Flow)
- **Real-time Communication**: Socket.IO
- **Styling**: Tailwind CSS
- **Build Tool**: Vite

### Project Structure
```
visualization-ui/
├── src/
│   ├── components/
│   │   ├── canvas/
│   │   │   ├── WorkflowCanvas.vue      # Main canvas component
│   │   │   └── nodes/                  # Custom node components
│   │   │       ├── PMAgentNode.vue
│   │   │       ├── WorkerNode.vue
│   │   │       ├── KanbanNode.vue
│   │   │       ├── DecisionNode.vue
│   │   │       └── KnowledgeNode.vue
│   │   ├── sidebar/
│   │   │   ├── NodePalette.vue         # Drag-and-drop node palette
│   │   │   ├── FilterPanel.vue         # Event filters
│   │   │   ├── NodeDetailsPanel.vue    # Node inspector
│   │   │   └── MetricsPanel.vue        # System metrics
│   │   ├── EventLog.vue                # Real-time event stream
│   │   ├── ExecutionControls.vue       # Playback controls
│   │   └── ConnectionStatus.vue        # WebSocket status
│   ├── stores/
│   │   ├── workflow.js                 # Canvas state management
│   │   ├── websocket.js               # WebSocket connection
│   │   └── events.js                  # Event history
│   ├── composables/
│   │   └── useCanvasOperations.js     # Canvas utilities
│   ├── App.vue                        # Root component
│   ├── main.js                        # App entry point
│   └── style.css                      # Global styles
├── package.json
├── vite.config.js
├── tailwind.config.js
└── postcss.config.js
```

## Key Features

### 1. Interactive Canvas
- **Drag-and-Drop**: Add nodes by dragging from the palette
- **Pan and Zoom**: Navigate large workflows
- **Minimap**: Overview of the entire canvas
- **Controls**: Zoom in/out, fit to view

### 2. Real-Time Data Flow
- **Animated Connections**: Visual feedback for active data flows
- **Live Updates**: Nodes update as events occur
- **Progress Tracking**: Worker progress bars
- **Status Indicators**: Color-coded node states

### 3. Node Types

#### PM Agent Node
- Shows decision count, confidence metrics
- Displays thinking/deciding states
- Central hub for worker connections

#### Worker Nodes
- Dynamic creation on registration
- Task assignment visualization
- Progress tracking
- Skill display

#### Kanban Node
- Task metrics (total, in progress, completed)
- Connection status
- Sync indicators

#### Decision Nodes
- Auto-created for decisions
- Confidence scores
- Rationale display
- Time-limited display

#### Knowledge Base Node
- Graph statistics
- Relationship counts
- Update status

### 4. Execution Controls
- Play/Pause execution
- Step-by-step mode
- Playback speed control
- Live status indicator

### 5. Event System
- Filtered event log
- Real-time updates
- Event statistics
- Clear history

## Installation & Setup

```bash
# Navigate to visualization UI directory
cd visualization-ui

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## Configuration

### WebSocket Connection
The WebSocket connection is configured in `vite.config.js` to proxy to the PM Agent server:

```javascript
server: {
  proxy: {
    '/socket.io': {
      target: 'http://localhost:8080',
      ws: true,
      changeOrigin: true
    }
  }
}
```

### Custom Node Styling
Node colors are defined in `tailwind.config.js`:

```javascript
colors: {
  'pm-primary': '#9b59b6',
  'worker-primary': '#3498db',
  'kanban-primary': '#2ecc71',
  'decision-primary': '#f39c12',
  'knowledge-primary': '#e74c3c'
}
```

## Usage

### Starting the System

1. **Start PM Agent Server** (with logging):
   ```bash
   python pm_agent_mcp_server_logged.py
   ```

2. **Start Visualization UI**:
   ```bash
   cd visualization-ui
   npm run dev
   ```

3. **Open Browser**:
   Navigate to `http://localhost:3000`

### Interacting with the Canvas

#### Adding Nodes
1. Drag from the node palette
2. Drop onto the canvas
3. Nodes auto-connect to relevant targets

#### Viewing Node Details
1. Click on any node
2. Details appear in right sidebar
3. Shows connections, metrics, and data

#### Filtering Events
1. Use filter checkboxes in left sidebar
2. Toggle event types on/off
3. View event statistics

## Data Flow Visualization

### Connection Animation
When data flows between components:
1. Edge becomes animated with dashed line
2. Color changes based on data type
3. Message count increments
4. Returns to normal after 2 seconds

### Data Type Colors
- **Request**: Blue (#3498db)
- **Response**: Green (#2ecc71)
- **Decision**: Orange (#f39c12)
- **Error**: Red (#e74c3c)
- **Update**: Purple (#9b59b6)

## Extending the System

### Adding New Node Types

1. Create node component in `src/components/canvas/nodes/`:
```vue
<template>
  <div class="custom-node">
    <Handle type="source" :position="Position.Right" />
    <Handle type="target" :position="Position.Left" />
    <!-- Node content -->
  </div>
</template>

<script setup>
import { Handle, Position } from '@vue-flow/core'
// Component logic
</script>
```

2. Register in `WorkflowCanvas.vue`:
```javascript
const nodeTypes = {
  'custom': 'custom'
}
```

3. Add to node palette in `NodePalette.vue`

### Custom Event Handlers

Add new event handlers in `websocket.js`:
```javascript
socket.value.on('custom_event', (data) => {
  // Handle custom event
  workflowStore.updateNode(data.nodeId, data.updates)
})
```

### Styling Customization

Modify styles in:
- `src/style.css` for Vue Flow overrides
- Component `<style>` blocks for component-specific styles
- `tailwind.config.js` for theme customization

## Performance Considerations

- **Node Limit**: Auto-remove old decision nodes after 30 seconds
- **Event History**: Limited to 1000 events in memory
- **Animation**: Hardware-accelerated CSS transforms
- **Rendering**: Vue Flow uses virtualization for large graphs

## Future Enhancements

1. **Save/Load Workflows**: Persist canvas state
2. **Advanced Layouts**: Force-directed, hierarchical
3. **Data Inspection**: Click edges to see payload
4. **Export**: Generate reports, screenshots
5. **Mobile Support**: Touch-friendly controls
6. **Dark/Light Theme**: Toggle UI themes