<!--
  NodePalette Component
  
  Purpose: Provides a palette of draggable node types that users can add to the workflow canvas.
  Acts as the source for drag-and-drop node creation.
  
  Features:
  - Displays available node types with icons and descriptions
  - Drag-and-drop functionality to add nodes to canvas
  - Visual feedback on hover
  - Instructions for new users
  
  Available Node Types:
  - Worker: Claude AI agents that perform tasks
  - Decision: Marcus decision points in the workflow
-->
<template>
  <div class="node-palette">
    <h3 class="text-sm font-medium text-gray-400 mb-3">Add Nodes</h3>
    
    <!-- List of draggable node types -->
    <div class="space-y-2">
      <div
        v-for="nodeType in availableNodes"
        :key="nodeType.type"
        @dragstart="onDragStart($event, nodeType)"
        :draggable="true"
        class="node-item p-3 bg-dark-surface border border-dark-border rounded-lg cursor-move hover:border-gray-600 transition-colors"
      >
        <div class="flex items-center gap-2">
          <!-- Node type icon with colored background -->
          <div 
            class="w-8 h-8 rounded flex items-center justify-center"
            :style="{ background: nodeType.color }"
          >
            <!-- SVG icons for different node types -->
            <svg class="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
              <!-- Worker icon: person silhouette -->
              <path v-if="nodeType.type === 'worker'" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"/>
              <!-- Decision icon: checkmark -->
              <path v-else-if="nodeType.type === 'decision'" fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
              <!-- Default icon: bell -->
              <path v-else d="M10 2a6 6 0 00-6 6v3.586l-.707.707A1 1 0 004 14h12a1 1 0 00.707-1.707L16 11.586V8a6 6 0 00-6-6z"/>
            </svg>
          </div>
          <!-- Node type label and description -->
          <div>
            <div class="font-medium text-sm">{{ nodeType.label }}</div>
            <div class="text-xs text-gray-500">{{ nodeType.description }}</div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Usage instructions -->
    <div class="mt-4 p-3 bg-gray-800 rounded-lg text-xs text-gray-400">
      <p>Drag nodes to the canvas to add them.</p>
      <p class="mt-1">Connect nodes by dragging from handles.</p>
    </div>
  </div>
</template>

<script setup>
/**
 * NodePalette - Sidebar component for adding nodes to the workflow
 * 
 * Provides draggable node types that can be dropped onto the WorkflowCanvas
 * to create new nodes in the workflow diagram.
 */

import { useWorkflowStore } from '@/stores/workflow'

// Store instance for workflow state management
const workflowStore = useWorkflowStore()

/**
 * Available node types that can be added to the workflow
 * Each node type has:
 * @property {string} type - Unique identifier for the node type
 * @property {string} label - Display name for the node type
 * @property {string} description - Brief description of the node's purpose
 * @property {string} color - Background color for the node icon
 */
const availableNodes = [
  {
    type: 'worker',
    label: 'Claude Worker',
    description: 'Autonomous AI agent',
    color: '#3498db'
  },
  {
    type: 'decision',
    label: 'Decision',
    description: 'Marcus decision point',
    color: '#f39c12'
  }
]

/**
 * Handles the start of a drag operation when user drags a node type
 * Stores the node type data in the drag event for use when dropped
 * 
 * @param {DragEvent} event - The dragstart event
 * @param {Object} nodeType - The node type being dragged
 * @param {string} nodeType.type - Node type identifier
 * @param {string} nodeType.label - Node display label
 * @param {string} nodeType.description - Node description
 * @param {string} nodeType.color - Node color
 */
const onDragStart = (event, nodeType) => {
  // Store node data as JSON in the drag transfer
  event.dataTransfer.setData('application/vueflow', JSON.stringify(nodeType))
  // Set the allowed drag effect
  event.dataTransfer.effectAllowed = 'move'
}
</script>