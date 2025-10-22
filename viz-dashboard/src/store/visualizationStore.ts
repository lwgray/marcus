import { create } from 'zustand';
import { SimulationData, Task, Agent, Message, generateMockData, calculateMetrics } from '../data/mockDataGenerator';
import { fetchSimulationData, checkApiHealth, fetchProjects } from '../services/dataService';

export type ViewLayer = 'network' | 'swimlanes' | 'conversations';
export type DataMode = 'live' | 'mock';
export type TaskView = 'subtasks' | 'parents';

export interface Project {
  id: string;
  name: string;
  created_at: string;
  last_used?: string;
  description?: string;
}

interface VisualizationState {
  // Data
  data: SimulationData;
  metrics: ReturnType<typeof calculateMetrics>;
  dataMode: DataMode;
  isLoading: boolean;
  loadError: string | null;

  // Project filtering
  projects: Project[];
  selectedProjectId: string | null;
  activeProjectId: string | null;

  // Playback state
  currentTime: number; // milliseconds since simulation start
  isPlaying: boolean;
  playbackSpeed: number; // 0.5, 1, 2, 5, 10
  animationIntervalId: number | null;

  // Auto-refresh state
  autoRefreshEnabled: boolean;
  autoRefreshIntervalId: number | null;
  autoRefreshInterval: number; // milliseconds (default 5000 = 5 seconds)

  // View state
  currentLayer: ViewLayer;
  taskView: TaskView;
  selectedTaskId: string | null;
  selectedAgentId: string | null;
  selectedMessageId: string | null;

  // Filter state
  showCompletedTasks: boolean;
  showBlockedTasks: boolean;
  filteredAgentIds: string[];

  // Actions
  loadData: (mode?: DataMode, projectId?: string) => Promise<void>;
  loadProjects: () => Promise<void>;
  setSelectedProject: (projectId: string | null) => void;
  startAutoRefresh: () => void;
  stopAutoRefresh: () => void;
  setAutoRefreshInterval: (interval: number) => void;
  setCurrentTime: (time: number) => void;
  play: () => void;
  pause: () => void;
  setPlaybackSpeed: (speed: number) => void;
  setCurrentLayer: (layer: ViewLayer) => void;
  setTaskView: (view: TaskView) => void;
  selectTask: (taskId: string | null) => void;
  selectAgent: (agentId: string | null) => void;
  selectMessage: (messageId: string | null) => void;
  toggleShowCompletedTasks: () => void;
  toggleShowBlockedTasks: () => void;
  setFilteredAgentIds: (agentIds: string[]) => void;
  reset: () => void;
  refreshData: () => Promise<void>;

  // Derived getters
  getVisibleTasks: () => Task[];
  getMessagesUpToCurrentTime: () => Message[];
  getActiveAgentsAtCurrentTime: () => Agent[];
}

export const useVisualizationStore = create<VisualizationState>((set, get) => {
  const data = generateMockData();
  const metrics = calculateMetrics(data);

  return {
    data,
    metrics,
    dataMode: 'mock',
    isLoading: false,
    loadError: null,
    projects: [],
    selectedProjectId: null,
    activeProjectId: null,
    autoRefreshEnabled: false,
    autoRefreshIntervalId: null,
    autoRefreshInterval: 5000, // 5 seconds default
    currentTime: 0,
    isPlaying: false,
    playbackSpeed: 1,
    animationIntervalId: null,
    currentLayer: 'network',
    taskView: 'subtasks',
    selectedTaskId: null,
    selectedAgentId: null,
    selectedMessageId: null,
    showCompletedTasks: true,
    showBlockedTasks: true,
    filteredAgentIds: [],

    loadData: async (mode?: DataMode, projectId?: string) => {
      const dataMode = mode || (import.meta.env.VITE_DATA_MODE as DataMode) || 'mock';

      set({ isLoading: true, loadError: null });

      try {
        let newData: SimulationData;

        if (dataMode === 'live') {
          // Check if API is available
          const isApiHealthy = await checkApiHealth();

          if (!isApiHealthy) {
            console.warn('API not available, falling back to mock data');
            newData = generateMockData();
            set({ dataMode: 'mock' });
          } else {
            // Fetch live data from API
            console.log('Fetching live data from API...');
            const { taskView } = get();
            newData = await fetchSimulationData(projectId, taskView);
            set({ dataMode: 'live' });
          }
        } else {
          // Use mock data
          newData = generateMockData();
          set({ dataMode: 'mock' });
        }

        // Calculate metrics
        const newMetrics = calculateMetrics(newData);

        // Update store - preserve currentTime if animation is playing
        const currentState = get();
        set({
          data: newData,
          metrics: newMetrics,
          isLoading: false,
          currentTime: currentState.isPlaying ? currentState.currentTime : 0,
        });

        console.log(`Data loaded successfully in ${dataMode} mode`);

        // Start auto-refresh if in live mode and not already running
        const state = get();
        if (dataMode === 'live' && !state.autoRefreshEnabled) {
          get().startAutoRefresh();
        } else if (dataMode === 'mock' && state.autoRefreshEnabled) {
          get().stopAutoRefresh();
        }
      } catch (error) {
        console.error('Error loading data:', error);

        // Fallback to mock data on error
        const mockData = generateMockData();
        const mockMetrics = calculateMetrics(mockData);

        set({
          data: mockData,
          metrics: mockMetrics,
          dataMode: 'mock',
          isLoading: false,
          loadError: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    },

    refreshData: async () => {
      const { dataMode, selectedProjectId } = get();
      await get().loadData(dataMode, selectedProjectId || undefined);
    },

    loadProjects: async () => {
      try {
        const response = await fetchProjects();
        const projects = response.projects || [];
        const activeProjectId = response.active_project_id || null;

        set({
          projects,
          activeProjectId,
          // If no project selected yet, default to active project
          selectedProjectId: get().selectedProjectId || activeProjectId,
        });

        console.log(`Loaded ${projects.length} projects, active: ${activeProjectId}`);
      } catch (error) {
        console.error('Error loading projects:', error);
      }
    },

    setSelectedProject: async (projectId: string | null) => {
      set({ selectedProjectId: projectId });

      // Reload data with the new project filter
      const { dataMode } = get();
      if (dataMode === 'live') {
        await get().loadData(dataMode, projectId || undefined);
      }
    },

    startAutoRefresh: () => {
      const current = get();

      // Only enable for live data mode
      if (current.dataMode !== 'live') {
        console.log('Auto-refresh only available in live data mode');
        return;
      }

      // Clear any existing interval
      if (current.autoRefreshIntervalId) {
        window.clearInterval(current.autoRefreshIntervalId);
      }

      set({ autoRefreshEnabled: true });

      // Start polling
      const intervalId = window.setInterval(() => {
        const state = get();
        if (!state.autoRefreshEnabled || state.dataMode !== 'live') {
          get().stopAutoRefresh();
          return;
        }

        console.log('Auto-refreshing data...');
        get().refreshData();
      }, current.autoRefreshInterval);

      set({ autoRefreshIntervalId: intervalId });
      console.log(`Auto-refresh started (polling every ${current.autoRefreshInterval}ms)`);
    },

    stopAutoRefresh: () => {
      const current = get();
      if (current.autoRefreshIntervalId) {
        window.clearInterval(current.autoRefreshIntervalId);
      }
      set({ autoRefreshEnabled: false, autoRefreshIntervalId: null });
      console.log('Auto-refresh stopped');
    },

    setAutoRefreshInterval: (interval: number) => {
      set({ autoRefreshInterval: interval });

      // Restart auto-refresh with new interval if it's running
      const current = get();
      if (current.autoRefreshEnabled) {
        get().stopAutoRefresh();
        get().startAutoRefresh();
      }
    },

    setCurrentTime: (time) => set({ currentTime: time }),

    play: () => {
      const current = get();

      // Clear any existing interval first
      if (current.animationIntervalId) {
        window.clearInterval(current.animationIntervalId);
      }

      set({ isPlaying: true });

      // Animation loop - calculate from current data, not stale mock data
      const startTime = new Date(current.data.metadata.start_time).getTime();
      const endTime = new Date(current.data.metadata.end_time).getTime();
      const totalDuration = endTime - startTime;
      const targetPlaybackDuration = 150000; // 150 seconds at 1x speed (so 10x = 15 seconds)
      const tickInterval = 50; // 50ms per tick (20 ticks per second)
      const timePerTick = (totalDuration / targetPlaybackDuration) * tickInterval; // How much simulation time to advance per tick

      const animationInterval = window.setInterval(() => {
        const state = get();
        if (!state.isPlaying) {
          window.clearInterval(animationInterval);
          set({ animationIntervalId: null });
          return;
        }

        const newTime = state.currentTime + (timePerTick * state.playbackSpeed);

        if (newTime >= totalDuration) {
          set({ currentTime: totalDuration, isPlaying: false, animationIntervalId: null });
          window.clearInterval(animationInterval);
        } else {
          set({ currentTime: newTime });
        }
      }, tickInterval);

      set({ animationIntervalId: animationInterval });
    },

    pause: () => {
      const current = get();
      if (current.animationIntervalId) {
        window.clearInterval(current.animationIntervalId);
      }
      set({ isPlaying: false, animationIntervalId: null });
    },

    setPlaybackSpeed: (speed) => set({ playbackSpeed: speed }),

    setCurrentLayer: (layer) => set({ currentLayer: layer }),

    setTaskView: async (view) => {
      set({ taskView: view });

      // Reload data with the new task view
      const { dataMode, selectedProjectId } = get();
      if (dataMode === 'live') {
        await get().loadData(dataMode, selectedProjectId || undefined);
      }
    },

    selectTask: (taskId) => set({ selectedTaskId: taskId }),

    selectAgent: (agentId) => set({ selectedAgentId: agentId }),

    selectMessage: (messageId) => set({ selectedMessageId: messageId }),

    toggleShowCompletedTasks: () =>
      set((state) => ({ showCompletedTasks: !state.showCompletedTasks })),

    toggleShowBlockedTasks: () =>
      set((state) => ({ showBlockedTasks: !state.showBlockedTasks })),

    setFilteredAgentIds: (agentIds) => set({ filteredAgentIds: agentIds }),

    reset: () => {
      const current = get();
      if (current.animationIntervalId) {
        window.clearInterval(current.animationIntervalId);
      }
      set({
        currentTime: 0,
        isPlaying: false,
        animationIntervalId: null,
        selectedTaskId: null,
        selectedAgentId: null,
        selectedMessageId: null,
      });
    },

    getVisibleTasks: () => {
      const state = get();
      let tasks = state.data.tasks;

      if (!state.showCompletedTasks) {
        tasks = tasks.filter(t => t.status !== 'done');
      }

      if (!state.showBlockedTasks) {
        tasks = tasks.filter(t => t.status !== 'blocked');
      }

      if (state.filteredAgentIds.length > 0) {
        tasks = tasks.filter(t =>
          t.assigned_to && state.filteredAgentIds.includes(t.assigned_to)
        );
      }

      return tasks;
    },

    getMessagesUpToCurrentTime: () => {
      const state = get();
      const startTime = new Date(state.data.metadata.start_time).getTime();
      const currentAbsTime = startTime + state.currentTime;

      return state.data.messages.filter(msg => {
        const msgTime = new Date(msg.timestamp).getTime();
        return msgTime <= currentAbsTime;
      });
    },

    getActiveAgentsAtCurrentTime: () => {
      const state = get();
      const startTime = new Date(state.data.metadata.start_time).getTime();
      const currentAbsTime = startTime + state.currentTime;

      // Determine which agents have active tasks at current time
      const activeTasks = state.data.tasks.filter(task => {
        const taskStart = new Date(task.created_at).getTime();
        const taskEnd = new Date(task.updated_at).getTime();
        return taskStart <= currentAbsTime && taskEnd >= currentAbsTime &&
               task.status === 'in_progress';
      });

      const activeAgentIds = new Set(activeTasks.map(t => t.assigned_to).filter(Boolean));

      return state.data.agents.filter(agent => activeAgentIds.has(agent.id));
    },
  };
});
