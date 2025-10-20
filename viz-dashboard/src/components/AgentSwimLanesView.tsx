import { useVisualizationStore } from '../store/visualizationStore';
import { Task, TaskStatus } from '../data/mockDataGenerator';
import { getTaskStateAtTime } from '../utils/timelineUtils';
import './AgentSwimLanesView.css';

const AgentSwimLanesView = () => {
  const data = useVisualizationStore((state) => state.data);
  const currentTime = useVisualizationStore((state) => state.currentTime);
  const selectAgent = useVisualizationStore((state) => state.selectAgent);
  const selectTask = useVisualizationStore((state) => state.selectTask);

  const startTime = new Date(data.metadata.start_time).getTime();
  const endTime = new Date(data.metadata.end_time).getTime();
  const totalDuration = endTime - startTime;
  const currentAbsTime = startTime + currentTime;

  // Group tasks by agent
  const agentTasks = data.agents.map(agent => {
    const tasks = data.tasks.filter(t => t.assigned_to === agent.id);
    return { agent, tasks };
  });

  const getTaskPosition = (task: Task) => {
    const taskStart = new Date(task.created_at).getTime();
    const taskEnd = new Date(task.updated_at).getTime();
    const startPercent = ((taskStart - startTime) / totalDuration) * 100;
    const durationPercent = ((taskEnd - taskStart) / totalDuration) * 100;

    return {
      left: `${startPercent}%`,
      width: `${Math.max(durationPercent, 2)}%`,
    };
  };

  const getTaskColor = (status: TaskStatus) => {
    switch (status) {
      case TaskStatus.TODO: return '#64748b';
      case TaskStatus.IN_PROGRESS: return '#3b82f6';
      case TaskStatus.DONE: return '#10b981';
      case TaskStatus.BLOCKED: return '#ef4444';
      default: return '#64748b';
    }
  };

  // Get messages for task at current time
  const getMessagesForTask = (taskId: string) => {
    return data.messages.filter(m =>
      m.task_id === taskId &&
      new Date(m.timestamp).getTime() <= currentAbsTime
    );
  };

  const currentTimePosition = (currentTime / totalDuration) * 100;

  return (
    <div className="swimlanes-view">
      <div className="swimlanes-container">
        <div className="swimlanes-content">
          {/* Time axis */}
          <div className="time-axis">
            {Array.from({ length: 13 }, (_, i) => i * 30).map(minutes => (
              <div
                key={minutes}
                className="time-marker"
                style={{ left: `${(minutes / data.metadata.total_duration_minutes) * 100}%` }}
              >
                <span>{minutes}m</span>
              </div>
            ))}
          </div>

          {/* Current time indicator */}
          <div
            className="current-time-line"
            style={{ left: `${currentTimePosition}%` }}
          >
            <div className="time-label">{Math.round(currentTime / 60000)}m</div>
          </div>

          {/* Agent lanes */}
          {agentTasks.map(({ agent, tasks }) => (
            <div
              key={agent.id}
              className="agent-lane"
              onClick={() => selectAgent(agent.id)}
            >
              <div className="agent-info">
                <div className="agent-name">{agent.name}</div>
                <div className="agent-meta">
                  <span className="agent-role">{agent.role}</span>
                  <span className="agent-autonomy">
                    Autonomy: {(agent.autonomy_score * 100).toFixed(0)}%
                  </span>
                </div>
              </div>

              <div className="lane-timeline">
                {tasks.map(task => {
                  const messages = getMessagesForTask(task.id);
                  const questions = messages.filter(m => m.type === 'question');
                  const blockers = messages.filter(m => m.type === 'blocker');

                  // Get dynamic state based on current time
                  const taskState = getTaskStateAtTime(task, currentAbsTime);
                  const isActive = taskState.isActive;

                  return (
                    <div
                      key={task.id}
                      className={`task-bar ${isActive ? 'active' : ''}`}
                      style={{
                        ...getTaskPosition(task),
                        backgroundColor: getTaskColor(taskState.status),
                      }}
                      onClick={(e) => {
                        e.stopPropagation();
                        selectTask(task.id);
                      }}
                      title={task.name}
                    >
                      <div className="task-bar-content">
                        <span className="task-bar-name">{task.name}</span>
                        <span className="task-bar-progress">{taskState.progress}%</span>
                      </div>

                      {/* Message indicators */}
                      {questions.map((q, idx) => {
                        const qTime = new Date(q.timestamp).getTime();
                        const qPercent = ((qTime - new Date(task.created_at).getTime()) /
                          (new Date(task.updated_at).getTime() - new Date(task.created_at).getTime())) * 100;

                        return (
                          <div
                            key={idx}
                            className="message-indicator question"
                            style={{ left: `${qPercent}%` }}
                            title="Question asked"
                          >
                            ❓
                          </div>
                        );
                      })}

                      {blockers.map((b, idx) => {
                        const bTime = new Date(b.timestamp).getTime();
                        const bPercent = ((bTime - new Date(task.created_at).getTime()) /
                          (new Date(task.updated_at).getTime() - new Date(task.created_at).getTime())) * 100;

                        return (
                          <div
                            key={idx}
                            className="message-indicator blocker"
                            style={{ left: `${bPercent}%` }}
                            title="Blocker reported"
                          >
                            🚫
                          </div>
                        );
                      })}

                      {taskState.progress === 100 && (
                        <div className="completion-indicator" title="Task completed">
                          ✓
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default AgentSwimLanesView;
