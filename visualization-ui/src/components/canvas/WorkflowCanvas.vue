<!-- 
  WorkflowCanvas Component
  
  Purpose: Main canvas for visualizing and interacting with the Marcus workflow.
  Provides a drag-and-drop interface for creating nodes and connections between them.
  
  Features:
  - Drag and drop node creation from NodePalette
  - Interactive node positioning and connection
  - Zoom and pan controls
  - Minimap for navigation
  - Auto-connection of worker nodes to Marcus
  
  Dependencies:
  - @vue-flow/core for flow diagram functionality
  - Pinia workflow store for state management
-->
<template>
  <div class="workflow-canvas h-full w-full" @drop="onDrop" @dragover="onDragOver">
    <!-- Main VueFlow component for rendering the flow diagram -->
    <VueFlow
      v-model:nodes="nodes"
      v-model:edges="edges"
      :node-types="nodeTypes"
      :default-viewport="{ x: 0, y: 0, zoom: 1 }"
      :min-zoom="0.5"
      :max-zoom="2"
      @node-click="onNodeClick"
      @edge-click="onEdgeClick"
      @connect="onConnect"
      @nodes-change="onNodesChange"
      @edges-change="onEdgesChange"
      class="vue-flow"
    >
      <!-- Grid background for visual alignment -->
      <Background variant="dots" :gap="20" :size="1" />
      <!-- Zoom and pan controls -->
      <Controls />
      <!-- Minimap for overview navigation -->
      <MiniMap />
    </VueFlow>
  </div>
</template>

<script setup>
/**
 * WorkflowCanvas - Main canvas component for Marcus workflow visualization
 * 
 * This component manages the interactive flow diagram where users can:
 * - Add nodes by dragging from the NodePalette
 * - Connect nodes to define workflow relationships
 * - Select nodes to view and edit details
 * - Navigate using zoom, pan, and minimap controls
 */

import { ref, computed, markRaw } from 'vue'
import { storeToRefs } from 'pinia'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls' 
import { MiniMap } from '@vue-flow/minimap'
import { useWorkflowStore } from '@/stores/workflow'

// Node Components - Each represents a different node type in the workflow
import PMAgentNode from './nodes/PMAgentNode.vue'
import WorkerNode from './nodes/WorkerNode.vue'
import KanbanNode from './nodes/KanbanNode.vue'
import DecisionNode from './nodes/DecisionNode.vue'
import KnowledgeNode from './nodes/KnowledgeNode.vue'

// Store instance for workflow state management
const workflowStore = useWorkflowStore()

// Reactive references to nodes and edges from the store
const { nodes, edges } = storeToRefs(workflowStore)

// VueFlow utility for projecting screen coordinates to flow coordinates
const { project } = useVueFlow()

/**
 * Node type registry - Maps node type strings to their corresponding Vue components
 * Components are marked as raw to prevent unnecessary reactivity overhead
 * 
 * @type {Object.<string, Component>}
 */
const nodeTypes = {
  'pm-agent': markRaw(PMAgentNode),
  'worker': markRaw(WorkerNode),
  'kanban': markRaw(KanbanNode),
  'decision': markRaw(DecisionNode),
  'knowledge': markRaw(KnowledgeNode)
}

// Debug logging for development
console.log('WorkflowCanvas - Current nodes:', nodes.value)
console.log('WorkflowCanvas - Node types:', nodeTypes)

/**
 * Handles drop events when dragging nodes from the NodePalette
 * Creates a new node at the drop position and auto-connects workers to Marcus
 * 
 * @param {DragEvent} event - The drop event containing node data
 */
const onDrop = (event) => {
  event.preventDefault()
  
  // Extract node data from the drag transfer
  const nodeDataStr = event.dataTransfer?.getData('application/vueflow')
  if (!nodeDataStr) return
  
  const nodeData = JSON.parse(nodeDataStr)
  
  // Convert screen coordinates to flow coordinates
  const position = project({ 
    x: event.clientX - event.target.getBoundingClientRect().left, 
    y: event.clientY - event.target.getBoundingClientRect().top
  })
  
  // Create the new node in the store
  const newNode = workflowStore.addNode({
    type: nodeData.type,
    label: nodeData.label,
    position,
    data: nodeData.data || {}
  })
  
  // Auto-connect worker nodes to the Marcus node
  if (nodeData.type === 'worker') {
    workflowStore.addEdge({
      source: newNode.id,
      target: 'pm-agent'
    })
  }
}

/**
 * Handles dragover events to enable dropping
 * 
 * @param {DragEvent} event - The dragover event
 */
const onDragOver = (event) => {
  event.preventDefault()
  event.dataTransfer.dropEffect = 'move'
}

/**
 * Handles node click events
 * Updates the selected node in the store for display in NodeDetailsPanel
 * 
 * @param {Object} event - VueFlow node click event
 * @param {Object} event.node - The clicked node data
 * 
 * @emits {store} setSelectedNode - Updates selected node in workflow store
 */
const onNodeClick = (event) => {
  const node = event.node
  workflowStore.setSelectedNode(node)
}

/**
 * Handles edge click events
 * Currently logs the edge data, could be extended to show edge details
 * 
 * @param {Object} event - VueFlow edge click event
 * @param {Object} event.edge - The clicked edge data
 */
const onEdgeClick = (event) => {
  // Could show edge details/data in future implementation
  console.log('Edge clicked:', event.edge)
}

/**
 * Handles connection events when user connects two nodes
 * Creates a new edge in the workflow
 * 
 * @param {Object} connection - Connection data with source and target node IDs
 * @param {string} connection.source - Source node ID
 * @param {string} connection.target - Target node ID
 * @param {string} [connection.sourceHandle] - Optional source handle ID
 * @param {string} [connection.targetHandle] - Optional target handle ID
 * 
 * @emits {store} addEdge - Creates new edge in workflow store
 */
const onConnect = (connection) => {
  workflowStore.addEdge(connection)
}

/**
 * Handles node change events (position, selection, removal)
 * Currently only handles position updates to keep store in sync
 * 
 * @param {Array<Object>} changes - Array of change objects from VueFlow
 * @param {string} changes[].type - Type of change (position, select, remove)
 * @param {string} changes[].id - ID of the affected node
 * @param {Object} [changes[].position] - New position for position changes
 */
const onNodesChange = (changes) => {
  // Handle node position updates
  changes.forEach(change => {
    if (change.type === 'position' && change.position) {
      const node = nodes.value.find(n => n.id === change.id)
      if (node) {
        node.position = change.position
      }
    }
  })
}

/**
 * Handles edge change events (selection, removal, updates)
 * Currently just logs changes for debugging
 * 
 * @param {Array<Object>} changes - Array of edge change objects from VueFlow
 */
const onEdgesChange = (changes) => {
  // Handle edge updates
  console.log('Edges changed:', changes)
}
</script>

<style scoped>
.workflow-canvas {
  position: relative;
}
</style>