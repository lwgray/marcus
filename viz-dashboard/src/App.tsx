import { useEffect } from 'react';
import { useVisualizationStore } from './store/visualizationStore';
import NetworkGraphView from './components/NetworkGraphView';
import AgentSwimLanesView from './components/AgentSwimLanesView';
import ConversationView from './components/ConversationView';
import TimelineControls from './components/TimelineControls';
import MetricsPanel from './components/MetricsPanel';
import TaskDetailPanel from './components/TaskDetailPanel';
import './App.css';

function App() {
  const currentLayer = useVisualizationStore((state) => state.currentLayer);
  const setCurrentLayer = useVisualizationStore((state) => state.setCurrentLayer);
  const selectedTaskId = useVisualizationStore((state) => state.selectedTaskId);
  const dataMode = useVisualizationStore((state) => state.dataMode);
  const isLoading = useVisualizationStore((state) => state.isLoading);
  const loadError = useVisualizationStore((state) => state.loadError);
  const projects = useVisualizationStore((state) => state.projects);
  const selectedProjectId = useVisualizationStore((state) => state.selectedProjectId);
  const autoRefreshEnabled = useVisualizationStore((state) => state.autoRefreshEnabled);
  const taskView = useVisualizationStore((state) => state.taskView);
  const loadData = useVisualizationStore((state) => state.loadData);
  const loadProjects = useVisualizationStore((state) => state.loadProjects);
  const setSelectedProject = useVisualizationStore((state) => state.setSelectedProject);
  const refreshData = useVisualizationStore((state) => state.refreshData);
  const startAutoRefresh = useVisualizationStore((state) => state.startAutoRefresh);
  const stopAutoRefresh = useVisualizationStore((state) => state.stopAutoRefresh);
  const setTaskView = useVisualizationStore((state) => state.setTaskView);

  // Load projects and data on mount
  useEffect(() => {
    const mode = (import.meta.env.VITE_DATA_MODE || 'mock') as 'live' | 'mock';

    // Load projects first (only relevant for live mode)
    if (mode === 'live') {
      loadProjects().then(() => {
        // Projects loaded, now load data with default project
        const selectedId = useVisualizationStore.getState().selectedProjectId;
        loadData(mode, selectedId || undefined);
      });
    } else {
      loadData(mode);
    }
  }, []);

  const handleToggleDataMode = async () => {
    const newMode = dataMode === 'live' ? 'mock' : 'live';

    // If switching to live mode, load projects first
    if (newMode === 'live') {
      await loadProjects();
      const selectedId = useVisualizationStore.getState().selectedProjectId;
      await loadData(newMode, selectedId || undefined);
    } else {
      await loadData(newMode);
    }
  };

  const handleProjectChange = async (event: React.ChangeEvent<HTMLSelectElement>) => {
    const projectId = event.target.value || null;
    await setSelectedProject(projectId);
  };

  const handleToggleAutoRefresh = () => {
    if (autoRefreshEnabled) {
      stopAutoRefresh();
    } else {
      startAutoRefresh();
    }
  };

  const handleToggleTaskView = async () => {
    const newView = taskView === 'subtasks' ? 'parents' : 'subtasks';
    await setTaskView(newView);
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-top">
          <h1>Marcus - Multi-Agent Parallelization Visualization</h1>
          <div className="header-controls">
            {dataMode === 'live' && projects.length > 0 && (
              <select
                className="project-selector"
                value={selectedProjectId || ''}
                onChange={handleProjectChange}
                disabled={isLoading}
                title="Select project to visualize"
              >
                <option value="">All Projects</option>
                {projects.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.name}
                  </option>
                ))}
              </select>
            )}
            {dataMode === 'live' && (
              <button
                className="task-view-toggle"
                onClick={handleToggleTaskView}
                disabled={isLoading}
                title={taskView === 'subtasks' ? 'Switch to parent tasks view' : 'Switch to subtasks view'}
              >
                {taskView === 'subtasks' ? '📝 Subtasks' : '📦 Parent Tasks'}
              </button>
            )}
            <button
              className="data-mode-toggle"
              onClick={handleToggleDataMode}
              disabled={isLoading}
            >
              {isLoading ? '⏳ Loading...' : dataMode === 'live' ? '🟢 Live Data' : '🔵 Mock Data'}
            </button>
            {dataMode === 'live' && (
              <button
                className={`auto-refresh-toggle ${autoRefreshEnabled ? 'enabled' : ''}`}
                onClick={handleToggleAutoRefresh}
                disabled={isLoading}
                title={autoRefreshEnabled ? 'Auto-refresh enabled (5s)' : 'Enable auto-refresh'}
              >
                {autoRefreshEnabled ? '🔄 Auto (5s)' : '⏸️ Manual'}
              </button>
            )}
            <button
              className="refresh-button"
              onClick={refreshData}
              disabled={isLoading || dataMode === 'mock'}
              title="Refresh live data now"
            >
              🔄 Refresh Now
            </button>
          </div>
        </div>
        {loadError && (
          <div className="error-banner">
            ⚠️ Error loading data: {loadError}. Falling back to mock data.
          </div>
        )}
        <div className="layer-tabs">
          <button
            className={currentLayer === 'network' ? 'active' : ''}
            onClick={() => setCurrentLayer('network')}
          >
            🔗 Network Graph
          </button>
          <button
            className={currentLayer === 'swimlanes' ? 'active' : ''}
            onClick={() => setCurrentLayer('swimlanes')}
          >
            📊 Agent Swim Lanes
          </button>
          <button
            className={currentLayer === 'conversations' ? 'active' : ''}
            onClick={() => setCurrentLayer('conversations')}
          >
            💬 Conversations
          </button>
        </div>
      </header>

      <div className="app-content">
        <div className="visualization-container">
          {currentLayer === 'network' && <NetworkGraphView />}
          {currentLayer === 'swimlanes' && <AgentSwimLanesView />}
          {currentLayer === 'conversations' && <ConversationView />}
        </div>

        {selectedTaskId && <TaskDetailPanel />}

        <MetricsPanel />
      </div>

      <TimelineControls />
    </div>
  );
}

export default App;
