import { create } from 'zustand';
import { SimulationData, Task, Agent, Message, generateMockData, calculateMetrics } from '../data/mockDataGenerator';

export type ViewLayer = 'network' | 'swimlanes' | 'conversations';

interface VisualizationState {
  // Data
  data: SimulationData;
  metrics: ReturnType<typeof calculateMetrics>;

  // Playback state
  currentTime: number; // milliseconds since simulation start
  isPlaying: boolean;
  playbackSpeed: number; // 0.5, 1, 2, 5, 10
  animationIntervalId: number | null;

  // View state
  currentLayer: ViewLayer;
  selectedTaskId: string | null;
  selectedAgentId: string | null;
  selectedMessageId: string | null;

  // Filter state
  showCompletedTasks: boolean;
  showBlockedTasks: boolean;
  filteredAgentIds: string[];

  // Actions
  setCurrentTime: (time: number) => void;
  play: () => void;
  pause: () => void;
  setPlaybackSpeed: (speed: number) => void;
  setCurrentLayer: (layer: ViewLayer) => void;
  selectTask: (taskId: string | null) => void;
  selectAgent: (agentId: string | null) => void;
  selectMessage: (messageId: string | null) => void;
  toggleShowCompletedTasks: () => void;
  toggleShowBlockedTasks: () => void;
  setFilteredAgentIds: (agentIds: string[]) => void;
  reset: () => void;

  // Derived getters
  getVisibleTasks: () => Task[];
  getMessagesUpToCurrentTime: () => Message[];
  getActiveAgentsAtCurrentTime: () => Agent[];
}

export const useVisualizationStore = create<VisualizationState>((set, get) => {
  const data = generateMockData();
  const metrics = calculateMetrics(data);

  const startTime = new Date(data.metadata.start_time).getTime();

  return {
    data,
    metrics,
    currentTime: 0,
    isPlaying: false,
    playbackSpeed: 1,
    animationIntervalId: null,
    currentLayer: 'network',
    selectedTaskId: null,
    selectedAgentId: null,
    selectedMessageId: null,
    showCompletedTasks: true,
    showBlockedTasks: true,
    filteredAgentIds: [],

    setCurrentTime: (time) => set({ currentTime: time }),

    play: () => {
      const current = get();

      // Clear any existing interval first
      if (current.animationIntervalId) {
        window.clearInterval(current.animationIntervalId);
      }

      set({ isPlaying: true });

      // Animation loop
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
      const currentAbsTime = startTime + state.currentTime;

      return state.data.messages.filter(msg => {
        const msgTime = new Date(msg.timestamp).getTime();
        return msgTime <= currentAbsTime;
      });
    },

    getActiveAgentsAtCurrentTime: () => {
      const state = get();
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
