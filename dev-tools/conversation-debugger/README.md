# Marcus Conversation Debugger (Interactive v2)

A Flask-based web application for visualizing and debugging conversations between Marcus and worker agents.

## Features

- 🔄 **Auto-refresh** - Updates every 5 seconds automatically
- 🎯 **Smart Filtering** - Filter by project, worker, time range, and event type
- 📊 **Live Statistics** - See conversation counts and active workers
- 🎨 **Interactive UI** - HTMX-powered for smooth updates without page reloads
- 📱 **Responsive Design** - Works on desktop and mobile
- 🔍 **Expandable Details** - Click to view full metadata for any conversation

## Quick Start

### 1. Install Dependencies

```bash
cd tools/conversation_debugger
pip install -r requirements.txt
```

### 2. Run the Server

```bash
python app.py
```

The server will start at: **http://127.0.0.1:5001**

### 3. Open in Browser

Navigate to: http://127.0.0.1:5001

## Usage

### Filters

- **Project** - Select which project to view (currently shows all)
- **Time Range** - Choose from 1 hour to 30 days of history
- **Worker** - Filter by specific worker ID or view all
- **Event Type** - Filter by conversation type:
  - 🤖 Marcus → Worker (task assignments, responses)
  - 👷 Worker → Marcus (task requests, progress updates)
  - 🧠 Marcus Decisions (decision logs with rationale)
  - 💭 Marcus Thinking (internal reasoning)

### Navigation

- **Auto-refresh** - Conversations update every 5 seconds
- **Manual Refresh** - Click the "🔄 Refresh Now" button
- **Expand Details** - Click "🔍 View Full Details" on any conversation to see complete metadata

### Understanding the Timeline

Each conversation card shows:

- **Direction** - Who sent the message (Marcus or Worker)
- **Timestamp** - When the message was sent (relative time)
- **Event Type** - Type of conversation
- **Message** - The actual message content
- **Quick Metadata** - Important info like task ID, status, progress
- **Full Details** - Complete JSON metadata (expandable)

## Color Coding

- **Blue border** - Marcus → Worker conversations
- **Green border** - Worker → Marcus conversations
- **Purple badges** - Task IDs
- **Yellow badges** - Status information
- **Green badges** - Progress percentages
- **Red badges** - Priority levels

## Log Location

The debugger reads from: `logs/conversations/conversations_*.jsonl`

Make sure Marcus is running and logging conversations to see data!

## Troubleshooting

### No conversations showing up?

1. Check that Marcus is running and has logged some conversations
2. Verify the log directory exists: `logs/conversations/`
3. Try increasing the time range filter
4. Check the browser console for errors

### Port already in use?

Change the port in `app.py`:

```python
app.run(debug=True, port=5002, host="127.0.0.1")  # Use 5002 instead
```

### Auto-refresh not working?

- Make sure JavaScript is enabled in your browser
- Check the browser console for HTMX errors
- Try manually refreshing with the button

## Technical Details

### Architecture

- **Backend**: Flask (Python)
- **Frontend**: HTML + Tailwind CSS + HTMX
- **Data Source**: JSON Lines log files
- **Auto-refresh**: HTMX polling every 5 seconds

### API Endpoints

- `GET /` - Main conversation viewer page
- `GET /api/conversations` - Get conversation data (JSON)
  - Query params: `hours`, `worker_id`, `filter_type`, `limit`
- `GET /api/stats` - Get conversation statistics (JSON)

### File Structure

```
conversation_debugger/
├── app.py                          # Main Flask application
├── requirements.txt                # Python dependencies
├── templates/
│   ├── base.html                  # Base template with layout
│   └── index.html                 # Main conversation viewer
├── static/
│   └── styles.css                 # Custom CSS styles
└── README.md                      # This file
```

## Future Enhancements (Version 3)

See GitHub issue for planned advanced features:

- 🔍 Full-text search across all conversations
- 🔌 WebSocket real-time updates (instant, not polling)
- 📥 Export conversations (JSON, Markdown, CSV)
- 🧵 Thread/conversation grouping by task
- 📊 Decision flow visualization
- 📈 Metrics dashboard
- ⌨️  Keyboard shortcuts

## License

Part of the Marcus project.
