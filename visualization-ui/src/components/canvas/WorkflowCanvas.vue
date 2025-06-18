<template>
  <div class="workflow-canvas h-full w-full" @drop="onDrop" @dragover="onDragOver">
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
      <Background variant="dots" :gap="20" :size="1" />
      <Controls />
      <MiniMap />
    </VueFlow>
  </div>
</template>

<script setup>
import { ref, computed, markRaw } from 'vue'
import { storeToRefs } from 'pinia'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls' 
import { MiniMap } from '@vue-flow/minimap'
import { useWorkflowStore } from '@/stores/workflow'

// Node Components
import PMAgentNode from './nodes/PMAgentNode.vue'
import WorkerNode from './nodes/WorkerNode.vue'
import KanbanNode from './nodes/KanbanNode.vue'
import DecisionNode from './nodes/DecisionNode.vue'
import KnowledgeNode from './nodes/KnowledgeNode.vue'

const workflowStore = useWorkflowStore()
const { nodes, edges } = storeToRefs(workflowStore)
const { project } = useVueFlow()

// Node types mapping - mark components as raw to avoid reactivity
const nodeTypes = {
  'pm-agent': markRaw(PMAgentNode),
  'worker': markRaw(WorkerNode),
  'kanban': markRaw(KanbanNode),
  'decision': markRaw(DecisionNode),
  'knowledge': markRaw(KnowledgeNode)
}

console.log('WorkflowCanvas - Current nodes:', nodes.value)
console.log('WorkflowCanvas - Node types:', nodeTypes)

// Drag and drop handlers
const onDrop = (event) => {
  event.preventDefault()
  
  const nodeDataStr = event.dataTransfer?.getData('application/vueflow')
  if (!nodeDataStr) return
  
  const nodeData = JSON.parse(nodeDataStr)
  const position = project({ 
    x: event.clientX - event.target.getBoundingClientRect().left, 
    y: event.clientY - event.target.getBoundingClientRect().top
  })
  
  const newNode = workflowStore.addNode({
    type: nodeData.type,
    label: nodeData.label,
    position,
    data: nodeData.data || {}
  })
  
  // Auto-connect worker to PM Agent
  if (nodeData.type === 'worker') {
    workflowStore.addEdge({
      source: newNode.id,
      target: 'pm-agent'
    })
  }
}

const onDragOver = (event) => {
  event.preventDefault()
  event.dataTransfer.dropEffect = 'move'
}

// Event handlers
const onNodeClick = (event) => {
  const node = event.node
  workflowStore.setSelectedNode(node)
}

const onEdgeClick = (event) => {
  // Could show edge details/data
  console.log('Edge clicked:', event.edge)
}

const onConnect = (connection) => {
  workflowStore.addEdge(connection)
}

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