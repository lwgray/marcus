import { useVisualizationStore } from '../store/visualizationStore';
import { getTaskStateAtTime } from '../utils/timelineUtils';
import './TaskDetailPanel.css';

const TaskDetailPanel = () => {
  const selectedTaskId = useVisualizationStore((state) => state.selectedTaskId);
  const selectTask = useVisualizationStore((state) => state.selectTask);
  const data = useVisualizationStore((state) => state.data);
  const currentTime = useVisualizationStore((state) => state.currentTime);
  const messages = useVisualizationStore((state) => state.getMessagesUpToCurrentTime());

  const task = data.tasks.find(t => t.id === selectedTaskId);

  if (!task) return null;

  const startTime = new Date(data.metadata.start_time).getTime();
  const currentAbsTime = startTime + currentTime;
  const taskState = getTaskStateAtTime(task, currentAbsTime);

  // Get messages related to this task
  const taskMessages = messages.filter(m => m.task_id === task.id);

  // Get assignment message
  const assignmentMsg = taskMessages.find(m => m.type === 'task_assignment');

  // Get questions
  const questions = taskMessages.filter(m => m.type === 'question');

  // Get blockers
  const blockers = taskMessages.filter(m => m.type === 'blocker');

  // Get status updates
  const statusUpdates = taskMessages.filter(m => m.type === 'status_update');

  const agent = data.agents.find(a => a.id === task.assigned_to);

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const diffMinutes = Math.round((date.getTime() - startTime) / 60000);
    return `${diffMinutes}m`;
  };

  const getStatusColor = () => {
    switch (taskState.status) {
      case 'todo': return '#64748b';
      case 'in_progress': return '#3b82f6';
      case 'done': return '#10b981';
      case 'blocked': return '#ef4444';
      default: return '#64748b';
    }
  };

  return (
    <div className="task-detail-panel">
      <div className="panel-header">
        <div className="header-content">
          <h3>{task.name}</h3>
          <button className="close-btn" onClick={() => selectTask(null)}>
            ✕
          </button>
        </div>
        <div className="task-meta">
          <span
            className="status-badge"
            style={{ backgroundColor: getStatusColor() }}
          >
            {taskState.status.replace('_', ' ').toUpperCase()}
          </span>
          <span className="progress-badge">
            {taskState.progress}% Complete
          </span>
        </div>
      </div>

      <div className="panel-content">
        {/* About Task */}
        <section className="detail-section">
          <h4>📋 About Task</h4>
          <p className="task-description">{task.description}</p>

          <div className="task-details">
            <div className="detail-row">
              <span className="label">Task ID:</span>
              <span className="value">{task.id}</span>
            </div>
            <div className="detail-row">
              <span className="label">Assigned To:</span>
              <span className="value">{agent ? agent.name : 'Unassigned'}</span>
            </div>
            <div className="detail-row">
              <span className="label">Priority:</span>
              <span className="value priority-{task.priority}">{task.priority.toUpperCase()}</span>
            </div>
            <div className="detail-row">
              <span className="label">Estimated Hours:</span>
              <span className="value">{task.estimated_hours}h</span>
            </div>
            <div className="detail-row">
              <span className="label">Actual Hours:</span>
              <span className="value">{task.actual_hours.toFixed(1)}h</span>
            </div>
            {task.dependencies.length > 0 && (
              <div className="detail-row">
                <span className="label">Dependencies:</span>
                <span className="value">{task.dependencies.join(', ')}</span>
              </div>
            )}
            {task.labels.length > 0 && (
              <div className="detail-row">
                <span className="label">Labels:</span>
                <div className="labels">
                  {task.labels.map(label => (
                    <span key={label} className="label-tag">{label}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </section>

        {/* Instructions */}
        {assignmentMsg && (
          <section className="detail-section">
            <h4>📝 Instructions from Marcus</h4>
            <div className="instruction-card">
              <div className="instruction-meta">
                <span>Assigned at {formatTime(assignmentMsg.timestamp)}</span>
              </div>
              <p className="instruction-text">{assignmentMsg.message}</p>
            </div>
          </section>
        )}

        {/* Status Updates */}
        {statusUpdates.length > 0 && (
          <section className="detail-section">
            <h4>📊 Status Updates ({statusUpdates.length})</h4>
            <div className="updates-list">
              {statusUpdates.map(msg => (
                <div key={msg.id} className="update-item">
                  <div className="update-time">{formatTime(msg.timestamp)}</div>
                  <div className="update-message">{msg.message}</div>
                  {msg.metadata.progress !== undefined && (
                    <div className="update-progress">
                      Progress: {msg.metadata.progress}%
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Questions */}
        {questions.length > 0 && (
          <section className="detail-section">
            <h4>❓ Questions ({questions.length})</h4>
            <div className="questions-list">
              {questions.map(q => {
                const answer = taskMessages.find(
                  m => m.parent_message_id === q.id && m.type === 'answer'
                );
                return (
                  <div key={q.id} className="question-item">
                    <div className="question-header">
                      <span className="question-time">{formatTime(q.timestamp)}</span>
                      {q.metadata.blocking && (
                        <span className="blocking-badge">Blocking</span>
                      )}
                    </div>
                    <div className="question-text">Q: {q.message}</div>
                    {answer && (
                      <div className="answer-text">
                        A: {answer.message}
                        {answer.metadata.response_time && (
                          <span className="response-time">
                            (responded in {answer.metadata.response_time}s)
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* Blockers */}
        {blockers.length > 0 && (
          <section className="detail-section">
            <h4>🚫 Blockers ({blockers.length})</h4>
            <div className="blockers-list">
              {blockers.map(b => {
                const resolution = taskMessages.find(
                  m => m.parent_message_id === b.id && m.type === 'answer'
                );
                return (
                  <div key={b.id} className="blocker-item">
                    <div className="blocker-header">
                      <span className="blocker-time">{formatTime(b.timestamp)}</span>
                      <span className="blocker-badge">BLOCKER</span>
                    </div>
                    <div className="blocker-text">{b.message}</div>
                    {resolution && (
                      <div className="resolution-text">
                        Resolution: {resolution.message}
                        {resolution.metadata.response_time && (
                          <span className="response-time">
                            (resolved in {resolution.metadata.response_time}s)
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* Timeline */}
        <section className="detail-section">
          <h4>⏱️ Timeline</h4>
          <div className="timeline-info">
            <div className="timeline-row">
              <span className="label">Started:</span>
              <span className="value">{formatTime(task.created_at)}</span>
            </div>
            <div className="timeline-row">
              <span className="label">
                {taskState.status === 'done' ? 'Completed:' : 'Last Update:'}
              </span>
              <span className="value">{formatTime(task.updated_at)}</span>
            </div>
            <div className="timeline-row">
              <span className="label">Duration:</span>
              <span className="value">
                {Math.round((new Date(task.updated_at).getTime() -
                  new Date(task.created_at).getTime()) / 60000)}m
              </span>
            </div>
          </div>
        </section>

        {/* All Conversations */}
        <section className="detail-section">
          <h4>💬 All Conversations ({taskMessages.length})</h4>
          <div className="conversation-list">
            {taskMessages.map(msg => (
              <div key={msg.id} className="conversation-item">
                <div className="conversation-header">
                  <span className="from-to">
                    {msg.from === 'marcus' ? '🤖' : '👤'} {msg.from} → {msg.to}
                  </span>
                  <span className="conversation-time">{formatTime(msg.timestamp)}</span>
                </div>
                <div className="conversation-message">{msg.message}</div>
                <span className="conversation-type">{msg.type.replace('_', ' ')}</span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
};

export default TaskDetailPanel;
