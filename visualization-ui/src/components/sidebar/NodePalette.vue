<template>
  <div class="node-palette">
    <h3 class="text-sm font-medium text-gray-400 mb-3">Add Nodes</h3>
    
    <div class="space-y-2">
      <div
        v-for="nodeType in availableNodes"
        :key="nodeType.type"
        @dragstart="onDragStart($event, nodeType)"
        :draggable="true"
        class="node-item p-3 bg-dark-surface border border-dark-border rounded-lg cursor-move hover:border-gray-600 transition-colors"
      >
        <div class="flex items-center gap-2">
          <div 
            class="w-8 h-8 rounded flex items-center justify-center"
            :style="{ background: nodeType.color }"
          >
            <svg class="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
              <path v-if="nodeType.type === 'worker'" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"/>
              <path v-else-if="nodeType.type === 'decision'" fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
              <path v-else d="M10 2a6 6 0 00-6 6v3.586l-.707.707A1 1 0 004 14h12a1 1 0 00.707-1.707L16 11.586V8a6 6 0 00-6-6z"/>
            </svg>
          </div>
          <div>
            <div class="font-medium text-sm">{{ nodeType.label }}</div>
            <div class="text-xs text-gray-500">{{ nodeType.description }}</div>
          </div>
        </div>
      </div>
    </div>
    
    <div class="mt-4 p-3 bg-gray-800 rounded-lg text-xs text-gray-400">
      <p>Drag nodes to the canvas to add them.</p>
      <p class="mt-1">Connect nodes by dragging from handles.</p>
    </div>
  </div>
</template>

<script setup>
import { useWorkflowStore } from '@/stores/workflow'

const workflowStore = useWorkflowStore()

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
    description: 'PM Agent decision point',
    color: '#f39c12'
  }
]

const onDragStart = (event, nodeType) => {
  event.dataTransfer.setData('application/vueflow', JSON.stringify(nodeType))
  event.dataTransfer.effectAllowed = 'move'
}
</script>