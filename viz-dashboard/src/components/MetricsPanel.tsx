import { useVisualizationStore } from '../store/visualizationStore';
import './MetricsPanel.css';

const MetricsPanel = () => {
  const metrics = useVisualizationStore((state) => state.metrics);
  const data = useVisualizationStore((state) => state.data);
  const activeAgents = useVisualizationStore((state) => state.getActiveAgentsAtCurrentTime());

  return (
    <div className="metrics-panel">
      <div className="panel-header">
        <h3>📊 Metrics Dashboard</h3>
      </div>

      <div className="metrics-content">
        {/* Project Overview */}
        <div className="metric-section">
          <h4>Project Overview</h4>
          <div className="metric-item">
            <span className="metric-label">Project Name</span>
            <span className="metric-value">{data.metadata.project_name}</span>
          </div>
          <div className="metric-item">
            <span className="metric-label">Total Duration</span>
            <span className="metric-value">{data.metadata.total_duration_minutes}m</span>
          </div>
          <div className="metric-item">
            <span className="metric-label">Tasks Completed</span>
            <span className="metric-value highlight">
              {metrics.completedTasks}/{metrics.totalTasks}
            </span>
          </div>
          <div className="metric-item">
            <span className="metric-label">Completion Rate</span>
            <span className="metric-value highlight">
              {metrics.completionRate.toFixed(1)}%
            </span>
          </div>
        </div>

        {/* Parallelization Metrics */}
        <div className="metric-section highlight-section">
          <h4>⚡ Parallelization</h4>
          <div className="metric-item large">
            <span className="metric-label">Speedup Factor</span>
            <span className="metric-value speedup">
              {metrics.speedupFactor}x
            </span>
          </div>
          <div className="metric-item">
            <span className="metric-label">Max Concurrent Tasks</span>
            <span className="metric-value">{metrics.maxConcurrent}</span>
          </div>
          <div className="metric-item">
            <span className="metric-label">Single Agent Time</span>
            <span className="metric-value">{metrics.singleAgentDurationMinutes}m</span>
          </div>
          <div className="metric-item">
            <span className="metric-label">Multi Agent Time</span>
            <span className="metric-value highlight">
              {metrics.multiAgentDurationMinutes}m
            </span>
          </div>
        </div>

        {/* Time Metrics */}
        <div className="metric-section">
          <h4>⏱️ Time Metrics</h4>
          <div className="metric-item">
            <span className="metric-label">Total Estimated</span>
            <span className="metric-value">{metrics.totalEstimatedHours.toFixed(1)}h</span>
          </div>
          <div className="metric-item">
            <span className="metric-label">Total Actual</span>
            <span className="metric-value">{metrics.totalActualHours.toFixed(1)}h</span>
          </div>
          <div className="metric-item">
            <span className="metric-label">Estimate Accuracy</span>
            <span className={`metric-value ${metrics.estimateAccuracy > 90 && metrics.estimateAccuracy < 110 ? 'good' : 'warning'}`}>
              {metrics.estimateAccuracy.toFixed(1)}%
            </span>
          </div>
        </div>

        {/* Communication Metrics */}
        <div className="metric-section">
          <h4>💬 Communication</h4>
          <div className="metric-item">
            <span className="metric-label">Total Messages</span>
            <span className="metric-value">{metrics.totalMessages}</span>
          </div>
          <div className="metric-item">
            <span className="metric-label">Blockers</span>
            <span className={`metric-value ${metrics.blockerMessages > 0 ? 'warning' : 'good'}`}>
              {metrics.blockerMessages}
            </span>
          </div>
        </div>

        {/* Active Agents */}
        <div className="metric-section">
          <h4>👥 Currently Active</h4>
          {activeAgents.length > 0 ? (
            activeAgents.map(agent => (
              <div key={agent.id} className="active-agent-item">
                <span className="agent-icon">🔵</span>
                <span className="agent-name">{agent.name}</span>
                <span className="agent-role">{agent.role}</span>
              </div>
            ))
          ) : (
            <div className="no-active-agents">No active agents at this time</div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MetricsPanel;
