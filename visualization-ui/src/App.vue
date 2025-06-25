<template>
  <div class="app-container h-screen flex flex-col bg-[#1a1a1a] text-gray-200">
    <!-- Header -->
    <header class="h-14 bg-dark-surface border-b border-dark-border flex items-center px-4">
      <h1 class="text-xl font-light text-pm-primary">Marcus Visualization</h1>
      <div class="ml-auto flex items-center gap-4">
        <ConnectionStatus />
        <button 
          @click="workflowStore.clearCanvas"
          class="px-3 py-1 text-sm bg-gray-700 hover:bg-gray-600 rounded transition-colors"
        >
          Clear Canvas
        </button>
      </div>
    </header>

    <!-- Main Layout -->
    <div class="flex-1 flex overflow-hidden">
      <!-- Left Sidebar -->
      <aside class="w-64 bg-dark-surface border-r border-dark-border p-4 overflow-y-auto">
        <NodePalette />
        <FilterPanel class="mt-6" />
      </aside>

      <!-- Canvas Area -->
      <main class="flex-1 relative">
        <WorkflowCanvas />
        <ExecutionControls />
      </main>

      <!-- Right Sidebar -->
      <aside class="w-80 bg-dark-surface border-l border-dark-border flex flex-col">
        <!-- Tab Navigation -->
        <div class="flex border-b border-dark-border">
          <button
            v-for="tab in rightSidebarTabs"
            :key="tab.id"
            @click="activeRightTab = tab.id"
            :class="[
              'flex-1 py-2 px-4 text-sm transition-colors',
              activeRightTab === tab.id
                ? 'bg-dark-hover text-pm-primary border-b-2 border-pm-primary'
                : 'text-gray-400 hover:text-gray-200'
            ]"
          >
            {{ tab.label }}
          </button>
        </div>
        
        <div class="flex-1 overflow-hidden flex flex-col">
          <NodeDetailsPanel v-if="selectedNode && activeRightTab === 'details'" :node="selectedNode" />
          <MetricsPanel v-else-if="activeRightTab === 'metrics'" />
          <HealthAnalysisPanel v-else-if="activeRightTab === 'health'" />
        </div>
        <EventLog class="h-48 border-t border-dark-border" />
      </aside>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useWorkflowStore } from '@/stores/workflow'
import { useWebSocketStore } from '@/stores/websocket'

// Components
import WorkflowCanvas from '@/components/canvas/WorkflowCanvas.vue'
import NodePalette from '@/components/sidebar/NodePalette.vue'
import FilterPanel from '@/components/sidebar/FilterPanel.vue'
import NodeDetailsPanel from '@/components/sidebar/NodeDetailsPanel.vue'
import MetricsPanel from '@/components/sidebar/MetricsPanel.vue'
import EventLog from '@/components/EventLog.vue'
import ExecutionControls from '@/components/ExecutionControls.vue'
import ConnectionStatus from '@/components/ConnectionStatus.vue'
import HealthAnalysisPanel from '@/components/HealthAnalysisPanel.vue'

const workflowStore = useWorkflowStore()
const wsStore = useWebSocketStore()
const { selectedNode } = storeToRefs(workflowStore)

// Tab navigation for right sidebar
const activeRightTab = ref('metrics')
const rightSidebarTabs = [
  { id: 'details', label: 'Details' },
  { id: 'metrics', label: 'Metrics' },
  { id: 'health', label: 'Health' }
]

onMounted(() => {
  console.log('App mounted successfully')
  // Initialize WebSocket connection
  wsStore.connect()
})
</script>