# Progressive Feedback for Long-Running Operations

## Context

When Cato analyzes a Marcus project, the operation can take 2-3 minutes to complete. Instead of showing a static loading spinner, we want to display real-time progress feedback showing what's happening in the background.

## Problem Statement

**Current State**: Long-running operations (like project analysis) show a static loading indicator, which provides no feedback about what's happening or how long it will take.

**Desired State**: Users see progressive text output showing each step of the operation as it happens, similar to how build tools (npm, webpack) show real-time progress.

## Requirements

### 1. Real-Time Progress Display

**For Web UI (Cato Frontend):**
- Show a scrollable log/console area with timestamped entries
- Display each step as it completes (e.g., "✓ Loaded 47 tasks", "⟳ Analyzing dependencies...")
- Use Server-Sent Events (SSE) to stream progress from backend to frontend
- Keep the log visible and scrollable while operation is running
- Show clear visual indicator when operation completes

**For CLI (Marcus):**
- Use the `rich` Python library for terminal progress display
- Show progress bars, spinners, and status messages
- Display step-by-step completion with checkmarks
- Provide optional `--verbose` flag for detailed output
- Show summary table at the end

### 2. User Experience Principles

1. **Never show static spinner for >5 seconds** - Always show what's happening
2. **Concrete progress over vague** - "Loading 47/150 tasks" not "Loading..."
3. **Provide time estimates** when possible - "2 of 6 steps complete"
4. **Allow cancellation** - Users should be able to abort long operations
5. **Persist logs** - Keep operation logs available for review after completion

### 3. Technical Implementation Pattern

#### Backend (Python/FastAPI with SSE)

The backend should stream progress events to the frontend using Server-Sent Events:

```python
from fastapi.responses import StreamingResponse
import json
import asyncio

@app.get("/api/analysis/stream")
async def stream_analysis(project_id: str):
    """Stream analysis progress to frontend using Server-Sent Events."""

    async def event_generator():
        try:
            # Step 1: Load project
            yield f"data: {json.dumps({'type': 'log', 'message': '📂 Loading project data...'})}\n\n"
            await asyncio.sleep(0.1)  # Allow UI to update
            project = await load_project(project_id)
            yield f"data: {json.dumps({'type': 'log', 'message': f'✓ Loaded project: {project.name}'})}\n\n"

            # Step 2: Load tasks
            yield f"data: {json.dumps({'type': 'log', 'message': '📋 Loading tasks...'})}\n\n"
            tasks = await load_tasks(project_id)
            yield f"data: {json.dumps({'type': 'log', 'message': f'✓ Found {len(tasks)} tasks'})}\n\n"

            # Step 3: Load decisions
            yield f"data: {json.dumps({'type': 'log', 'message': '💡 Loading decisions...'})}\n\n"
            decisions = await load_decisions(project_id)
            yield f"data: {json.dumps({'type': 'log', 'message': f'✓ Found {len(decisions)} decisions'})}\n\n"

            # Step 4: Load artifacts
            yield f"data: {json.dumps({'type': 'log', 'message': '📎 Loading artifacts...'})}\n\n"
            artifacts = await load_artifacts(project_id)
            yield f"data: {json.dumps({'type': 'log', 'message': f'✓ Found {len(artifacts)} artifacts'})}\n\n"

            # Step 5: Analyze dependencies
            yield f"data: {json.dumps({'type': 'log', 'message': '🔗 Analyzing task dependencies...'})}\n\n"
            deps = await analyze_dependencies(tasks)
            yield f"data: {json.dumps({'type': 'log', 'message': f'✓ Mapped {len(deps)} dependencies'})}\n\n"

            # Step 6: Calculate metrics
            yield f"data: {json.dumps({'type': 'log', 'message': '📊 Calculating metrics...'})}\n\n"
            metrics = await calculate_metrics(project, tasks, decisions, artifacts)
            yield f"data: {json.dumps({'type': 'log', 'message': '✓ Metrics calculated'})}\n\n"

            # Complete
            yield f"data: {json.dumps({'type': 'complete', 'data': metrics})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Error: {str(e)}'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```

**Key Backend Patterns:**
- Use `async def event_generator()` to yield progress events
- Format events as SSE: `data: {json}\n\n`
- Include event types: `log`, `complete`, `error`
- Yield small sleep (`await asyncio.sleep(0.1)`) after each message to allow UI updates
- Return `StreamingResponse` with `text/event-stream` media type

#### Frontend (React/TypeScript with SSE)

The frontend should display the streamed logs in real-time:

```typescript
import React, { useState, useEffect, useRef } from 'react';

interface LogEntry {
  timestamp: Date;
  message: string;
  type: 'log' | 'complete' | 'error';
}

interface AnalysisProgressProps {
  projectId: string;
  onComplete?: (data: any) => void;
}

const AnalysisProgress: React.FC<AnalysisProgressProps> = ({ projectId, onComplete }) => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isComplete, setIsComplete] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new logs appear
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  useEffect(() => {
    const eventSource = new EventSource(
      `http://localhost:4301/api/analysis/stream?project_id=${projectId}`
    );

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'log') {
        setLogs(prev => [...prev, {
          timestamp: new Date(),
          message: data.message,
          type: 'log'
        }]);
      } else if (data.type === 'complete') {
        setIsComplete(true);
        eventSource.close();
        if (onComplete) {
          onComplete(data.data);
        }
      } else if (data.type === 'error') {
        setError(data.message);
        setIsComplete(true);
        eventSource.close();
      }
    };

    eventSource.onerror = (err) => {
      console.error('EventSource error:', err);
      setError('Connection lost. Please refresh and try again.');
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [projectId, onComplete]);

  return (
    <div className="analysis-progress">
      <h3>Analyzing Project...</h3>

      <div className="log-container">
        {logs.map((log, i) => (
          <div key={i} className="log-line">
            <span className="timestamp">
              {log.timestamp.toLocaleTimeString()}
            </span>
            <span className="message">{log.message}</span>
          </div>
        ))}
        <div ref={logsEndRef} />
      </div>

      {error && (
        <div className="error-message">
          ⚠️ {error}
        </div>
      )}

      {isComplete && !error && (
        <div className="complete-message">
          ✓ Analysis complete!
        </div>
      )}
    </div>
  );
};

export default AnalysisProgress;
```

**Key Frontend Patterns:**
- Use `EventSource` API for SSE connection
- Maintain array of log entries with timestamps
- Auto-scroll to bottom as new logs appear
- Handle `complete` and `error` events
- Clean up EventSource on unmount
- Show clear visual states (running, complete, error)

#### CSS Styling

```css
.analysis-progress {
  max-width: 800px;
  margin: 20px auto;
  font-family: 'Monaco', 'Courier New', monospace;
}

.log-container {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 16px;
  border-radius: 8px;
  max-height: 400px;
  overflow-y: auto;
  margin: 16px 0;
}

.log-line {
  padding: 4px 0;
  display: flex;
  gap: 12px;
}

.timestamp {
  color: #858585;
  font-size: 0.9em;
  min-width: 80px;
}

.message {
  color: #d4d4d4;
}

.complete-message {
  background: #1e7e34;
  color: white;
  padding: 12px;
  border-radius: 4px;
  text-align: center;
  font-weight: bold;
}

.error-message {
  background: #d32f2f;
  color: white;
  padding: 12px;
  border-radius: 4px;
  text-align: center;
}
```

### 4. Event Types and Messages

**Standard Event Format:**
```typescript
{
  type: 'log' | 'complete' | 'error',
  message: string,          // Human-readable message
  data?: any,               // Optional data payload (for 'complete')
  progress?: number,        // Optional 0-100 progress percentage
  stage?: string            // Optional stage identifier
}
```

**Example Messages:**
- Loading: `"📂 Loading project data..."`
- Success: `"✓ Loaded project: My Project Name"`
- Count: `"✓ Found 47 tasks"`
- Error: `"⚠️ Failed to load artifacts: Connection timeout"`
- Progress: `"⟳ Analyzing dependencies... (3/6 steps)"`

### 5. CLI Implementation (Bonus)

For Marcus CLI commands, use the `rich` library:

```python
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

async def analyze_project_cli(project_id: str):
    """Analyze project with CLI progress display."""

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:

        task = progress.add_task("[cyan]Analyzing project...", total=6)

        # Step 1
        progress.update(task, description="[cyan]Loading project data...")
        project = await load_project(project_id)
        progress.advance(task)
        console.print(f"✓ Loaded project: {project.name}")

        # Step 2
        progress.update(task, description="[cyan]Loading tasks...")
        tasks = await load_tasks(project_id)
        progress.advance(task)
        console.print(f"✓ Found {len(tasks)} tasks")

        # ... continue for all steps

    console.print("\n[bold green]✓ Analysis complete![/bold green]\n")
```

## Implementation Checklist

- [ ] Add SSE endpoint to Cato backend (`/api/analysis/stream`)
- [ ] Create `AnalysisProgress` React component
- [ ] Update project analyzer to yield progress events
- [ ] Add CSS styling for log display
- [ ] Implement auto-scroll for log container
- [ ] Add error handling for connection failures
- [ ] Test with slow network conditions
- [ ] Add cancel button (optional)
- [ ] Persist logs after completion (optional)
- [ ] Add CLI version with `rich` library (optional)

## Testing

**Manual Testing:**
1. Start a project analysis
2. Verify logs appear in real-time (not all at once)
3. Check auto-scroll works
4. Verify completion state shows correctly
5. Test error handling (disconnect during operation)
6. Check mobile responsiveness

**Performance Testing:**
- Verify UI remains responsive during streaming
- Check memory usage doesn't grow unbounded (limit log array size if needed)
- Test with projects of varying sizes (10 tasks vs 1000 tasks)

## Example User Experience

**Before (Bad UX):**
```
[Static spinner for 3 minutes]
```

**After (Good UX):**
```
Analyzing Project...

10:23:45  📂 Loading project data...
10:23:46  ✓ Loaded project: My App
10:23:46  📋 Loading tasks...
10:23:48  ✓ Found 47 tasks
10:23:48  💡 Loading decisions...
10:23:51  ✓ Found 23 decisions
10:23:51  📎 Loading artifacts...
10:24:15  ✓ Found 156 artifacts
10:24:15  🔗 Analyzing task dependencies...
10:24:42  ✓ Mapped 89 dependencies
10:24:42  📊 Calculating metrics...
10:24:45  ✓ Metrics calculated

✓ Analysis complete!
```

## References

- [Server-Sent Events (SSE) MDN Docs](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [Rich Python Library](https://github.com/Textualize/rich)
- [EventSource API](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)

## Questions to Consider

1. Should we allow users to download/export the logs?
2. Should we persist logs in database for later review?
3. Do we need a "verbose" vs "compact" mode toggle?
4. Should we add progress percentage (e.g., "Step 3 of 6 - 50%")?
5. Do we need to handle very long operations (>10 minutes) differently?
