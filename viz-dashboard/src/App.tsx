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

  return (
    <div className="app">
      <header className="app-header">
        <h1>Marcus - Multi-Agent Parallelization Visualization</h1>
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
