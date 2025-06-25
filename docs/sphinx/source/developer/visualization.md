# Marcus Data Flow Visualization System

## Overview

The Marcus Visualization System provides real-time monitoring and analysis of the autonomous agent coordination system. It visualizes conversations, decisions, and knowledge relationships between Marcus, Claude Workers, and the Kanban Board.

## Architecture

The system consists of four main components:

### 1. Conversation Stream Processor (`src/visualization/conversation_stream.py`)
- Processes structured logs from the conversation logger
- Converts log entries into visualization events
- Maintains conversation history
- Provides real-time streaming to UI clients

### 2. Decision Visualizer (`src/visualization/decision_visualizer.py`)
- Tracks Marcus's decision-making process
- Generates decision trees showing alternatives considered
- Calculates decision analytics and confidence trends
- Identifies decision patterns

### 3. Knowledge Graph Builder (`src/visualization/knowledge_graph.py`)
- Builds graph of workers, tasks, skills, and decisions
- Tracks task assignments and dependencies
- Identifies skill gaps and resource allocation
- Provides worker recommendations

### 4. UI Server (`src/visualization/ui_server.py`)
- Web-based visualization interface
- Real-time WebSocket communication
- Interactive graph visualizations
- Metrics dashboard

## Installation

```bash
# Install visualization dependencies
pip install -r visualization_requirements.txt

# Install main project dependencies if not already done
pip install -r requirements.txt
```

## Usage

### Starting the Visualization Server

```bash
# Run the visualization server
python run_visualization.py

# Server will start at http://127.0.0.1:8080
```

### Prerequisites

1. Marcus server must be running and generating logs
2. Log directory must exist at `logs/conversations/`
3. Structured logging must be enabled (uses `ConversationLogger`)

### Running with Marcus

```bash
# Terminal 1: Start Marcus with logging
python pm_agent_mcp_server_logged.py

# Terminal 2: Start visualization server
python run_visualization.py

# Terminal 3: Run mock workers to generate activity
python scripts/mock_claude_worker_verbose.py
```

## Features

### Real-Time Conversation Flow
- Visual representation of messages between components
- Animated data flow showing active communications
- Color-coded nodes for different component types
- Interactive drag-and-drop layout

### Decision Tree Visualization
- Explore Marcus's decision-making process
- View alternatives considered
- See confidence scores and decision factors
- Track decision outcomes

### Knowledge Graph
- Visualize relationships between workers, tasks, and skills
- Identify skill gaps and resource bottlenecks
- Track task dependencies
- Monitor worker performance

### Metrics Dashboard
- Active workers count
- Tasks in progress
- Decision confidence trends
- System performance metrics

### Event Log
- Real-time event stream
- Filterable by event type
- Searchable history
- Export capabilities

## UI Controls

### Filters (Left Sidebar)
- **Event Types**: Toggle visibility of different event categories
- **View Options**: Control animation and display settings

### Main View Controls
- **Knowledge Graph**: Open interactive knowledge graph
- **Decision Tree**: View latest decision tree
- **Pause**: Pause/resume real-time updates
- **Clear**: Clear current view

### Metrics Panel (Right Sidebar)
- Live system metrics
- Confidence trend chart
- Performance indicators

## Data Flow

```
ConversationLogger → Log Files → ConversationStreamProcessor
                                           ↓
                                    Parse Events
                                           ↓
                     ┌─────────────────────┴─────────────────────┐
                     ↓                                           ↓
              DecisionVisualizer                          KnowledgeGraph
                     ↓                                           ↓
                     └─────────────────────┬─────────────────────┘
                                           ↓
                                      UI Server
                                           ↓
                                    WebSocket/HTTP
                                           ↓
                                     Web Browser
```

## Event Types

### Worker Events
- Registration
- Task requests
- Progress updates
- Blocker reports

### Marcus Events
- Internal thinking
- Decision making
- Task assignments
- System state updates

### Kanban Events
- Board queries
- Task updates
- Status changes

## Customization

### Adding New Event Types

1. Update `ConversationStreamProcessor._parse_log_entry()` to handle new event
2. Add event type to `EventType` enum
3. Update UI to handle new event visualization

### Modifying Visualizations

1. Edit `templates/index.html` for UI changes
2. Modify D3.js code for graph customization
3. Update CSS for styling changes

### Extending Analytics

1. Add new metrics to `DecisionVisualizer.get_decision_analytics()`
2. Create new graph relationships in `KnowledgeGraphBuilder`
3. Add API endpoints in `VisualizationServer`

## API Endpoints

### HTTP Endpoints
- `GET /` - Main visualization interface
- `GET /api/status` - Server status
- `GET /api/conversations/history` - Conversation history
- `GET /api/decisions/analytics` - Decision analytics
- `GET /api/knowledge/graph` - Knowledge graph data
- `GET /api/knowledge/statistics` - Graph statistics

### WebSocket Events
- `conversation_event` - New conversation event
- `decision_event` - Decision made
- `assignment_event` - Task assigned
- `blocker_event` - Blocker reported

## Performance Considerations

- Conversation history limited to 1000 events in memory
- Event log displays last 50 events
- Graph edges filtered to last 5 minutes
- File watching uses efficient OS-level monitoring

## Troubleshooting

### No events appearing
1. Check Marcus is using `ConversationLogger`
2. Verify log files exist in `logs/conversations/`
3. Check browser console for WebSocket errors

### Performance issues
1. Reduce history size in `ConversationStreamProcessor`
2. Increase edge filtering time window
3. Disable animations in UI

### Connection errors
1. Ensure server is running on correct port
2. Check firewall settings
3. Verify WebSocket support in browser

## Future Enhancements

As outlined in the PRD:
- Phase 2: Pattern recognition and anomaly detection
- Phase 3: Predictive analytics and optimization
- Performance optimization for large-scale deployments
- Mobile-responsive design
- Export capabilities for reports