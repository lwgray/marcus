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
  const loadData = useVisualizationStore((state) => state.loadData);
  const refreshData = useVisualizationStore((state) => state.refreshData);

  // Load data on mount
  useEffect(() => {
    const mode = (import.meta.env.VITE_DATA_MODE || 'mock') as 'live' | 'mock';
    loadData(mode);
  }, []);

  const handleToggleDataMode = async () => {
    const newMode = dataMode === 'live' ? 'mock' : 'live';
    await loadData(newMode);
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-top">
          <h1>Marcus - Multi-Agent Parallelization Visualization</h1>
          <div className="header-controls">
            <button
              className="data-mode-toggle"
              onClick={handleToggleDataMode}
              disabled={isLoading}
            >
              {isLoading ? '⏳ Loading...' : dataMode === 'live' ? '🟢 Live Data' : '🔵 Mock Data'}
            </button>
            <button
              className="refresh-button"
              onClick={refreshData}
              disabled={isLoading || dataMode === 'mock'}
              title="Refresh live data"
            >
              🔄 Refresh
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
