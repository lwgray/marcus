<!--
  NodeDetailsPanel Component
  
  Purpose: Displays detailed information about a selected node in the workflow.
  Shows node-specific properties, metrics, and connections to other nodes.
  
  Features:
  - Dynamic content based on node type (worker, pm-agent, decision)
  - Worker node: status, skills, current task with progress
  - Marcus node: decision metrics and confidence scores
  - Decision node: decision details with confidence and rationale
  - Connection information showing linked nodes
  
  Props:
  - node: The selected node object containing type, id, and data
-->
<template>
  <div class="node-details-panel p-4">
    <!-- Header with node label and close button -->
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-medium">{{ node.data.label }}</h3>
      <button
        @click="workflowStore.setSelectedNode(null)"
        class="p-1 hover:bg-gray-700 rounded transition-colors"
      >
        <!-- Close icon (X) -->
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
        </svg>
      </button>
    </div>
    
    <!-- Worker node specific content -->
    <div v-if="node.type === 'worker'" class="space-y-4">
      <!-- Basic worker information -->
      <div>
        <h4 class="text-sm font-medium text-gray-400 mb-2">Worker Information</h4>
        <div class="space-y-2 text-sm">
          <div class="flex justify-between">
            <span class="text-gray-500">ID:</span>
            <span class="font-mono text-xs">{{ node.id }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-500">Status:</span>
            <span :class="getStatusClass(node.data.status)">{{ node.data.status }}</span>
          </div>
          <div v-if="node.data.role" class="flex justify-between">
            <span class="text-gray-500">Role:</span>
            <span>{{ node.data.role }}</span>
          </div>
        </div>
      </div>
      
      <!-- Worker skills section -->
      <div v-if="node.data.skills && node.data.skills.length">
        <h4 class="text-sm font-medium text-gray-400 mb-2">Skills</h4>
        <div class="flex flex-wrap gap-1">
          <span
            v-for="skill in node.data.skills"
            :key="skill"
            class="px-2 py-1 bg-blue-500/20 text-blue-300 rounded text-xs"
          >
            {{ skill }}
          </span>
        </div>
      </div>
      
      <!-- Current task with progress bar -->
      <div v-if="node.data.currentTask">
        <h4 class="text-sm font-medium text-gray-400 mb-2">Current Task</h4>
        <div class="p-3 bg-dark-surface rounded-lg">
          <div class="font-medium text-sm mb-1">{{ node.data.taskName || node.data.currentTask }}</div>
          <div v-if="node.data.progress !== undefined" class="mt-2">
            <div class="flex justify-between text-xs mb-1">
              <span>Progress</span>
              <span>{{ node.data.progress }}%</span>
            </div>
            <div class="h-2 bg-gray-700 rounded-full overflow-hidden">
              <div 
                class="h-full bg-blue-500 transition-all duration-500"
                :style="{ width: `${node.data.progress}%` }"
              />
            </div>
          </div>
          <div v-if="node.data.lastUpdate" class="mt-2 text-xs text-gray-500">
            {{ node.data.lastUpdate }}
          </div>
        </div>
      </div>
    </div>
    
    <!-- Marcus node specific content -->
    <div v-else-if="node.type === 'pm-agent'" class="space-y-4">
      <div>
        <h4 class="text-sm font-medium text-gray-400 mb-2">Marcus Metrics</h4>
        <div class="grid grid-cols-2 gap-3">
          <!-- Decisions today metric -->
          <div class="p-3 bg-dark-surface rounded-lg">
            <div class="text-2xl font-bold text-pm-primary">{{ node.data.metrics?.decisionsToday || 0 }}</div>
            <div class="text-xs text-gray-500">Decisions Today</div>
          </div>
          <!-- Average confidence metric -->
          <div class="p-3 bg-dark-surface rounded-lg">
            <div class="text-2xl font-bold text-green-400">{{ Math.round((node.data.metrics?.avgConfidence || 0) * 100) }}%</div>
            <div class="text-xs text-gray-500">Avg Confidence</div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Decision node specific content -->
    <div v-else-if="node.type === 'decision'" class="space-y-4">
      <div>
        <h4 class="text-sm font-medium text-gray-400 mb-2">Decision Details</h4>
        <div class="p-3 bg-dark-surface rounded-lg text-sm">
          <div class="mb-2">{{ node.data.decision }}</div>
          <div class="text-xs text-gray-500">
            <div>Confidence: {{ Math.round((node.data.confidence || 0) * 100) }}%</div>
            <div v-if="node.data.rationale" class="mt-1">Rationale: {{ node.data.rationale }}</div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Connection information (shown for all node types) -->
    <div class="mt-6">
      <h4 class="text-sm font-medium text-gray-400 mb-2">Connections</h4>
      <div class="space-y-1 text-xs">
        <div v-for="edge in connectedEdges" :key="edge.id" class="flex items-center gap-2">
          <span class="text-gray-500">{{ edge.source === node.id ? 'To' : 'From' }}:</span>
          <span>{{ getNodeLabel(edge.source === node.id ? edge.target : edge.source) }}</span>
          <span v-if="edge.data?.messageCount" class="text-gray-600">({{ edge.data.messageCount }} messages)</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * NodeDetailsPanel - Displays detailed information about a selected workflow node
 * 
 * This component renders different content based on the node type:
 * - Worker nodes: Shows status, skills, and current task progress
 * - Marcus nodes: Displays decision metrics and confidence scores
 * - Decision nodes: Shows decision details with confidence and rationale
 * 
 * All node types show their connections to other nodes in the workflow.
 */

import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useWorkflowStore } from '@/stores/workflow'

/**
 * Component props
 * @prop {Object} node - The selected node object
 * @prop {string} node.id - Unique node identifier
 * @prop {string} node.type - Node type (worker, pm-agent, decision)
 * @prop {Object} node.data - Node-specific data including label, status, metrics, etc.
 */
const props = defineProps({
  node: {
    type: Object,
    required: true
  }
})

// Store instance for workflow state management
const workflowStore = useWorkflowStore()

// Reactive references to workflow nodes and edges
const { edges, nodes } = storeToRefs(workflowStore)

/**
 * Computed property that finds all edges connected to the selected node
 * Used to display connection information in the UI
 * 
 * @returns {Array<Object>} Array of edge objects where source or target matches the node ID
 */
const connectedEdges = computed(() => {
  return edges.value.filter(edge => 
    edge.source === props.node.id || edge.target === props.node.id
  )
})

/**
 * Gets the display label for a node by its ID
 * Falls back to showing the ID if no label is found
 * 
 * @param {string} nodeId - The ID of the node to get the label for
 * @returns {string} The node's label or its ID as fallback
 */
const getNodeLabel = (nodeId) => {
  const node = nodes.value.find(n => n.id === nodeId)
  return node?.data?.label || nodeId
}

/**
 * Returns the appropriate CSS class for a node status
 * Used to color-code status text based on the current state
 * 
 * @param {string} status - The status value (available, working, blocked, idle, active)
 * @returns {string} Tailwind CSS class for text color
 */
const getStatusClass = (status) => {
  const classes = {
    available: 'text-green-400',
    working: 'text-blue-400',
    blocked: 'text-red-400',
    idle: 'text-gray-400',
    active: 'text-green-400'
  }
  return classes[status] || 'text-gray-400'
}
</script>