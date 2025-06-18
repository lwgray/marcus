<template>
  <div class="execution-controls absolute bottom-4 left-4 flex items-center gap-2 bg-dark-surface/95 backdrop-blur p-2 rounded-lg border border-dark-border">
    <button
      @click="handlePlayPause"
      class="p-2 rounded hover:bg-gray-700 transition-colors"
      :class="{ 'text-green-400': !executionState.isRunning }"
    >
      <svg v-if="!executionState.isRunning || executionState.isPaused" class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd"/>
      </svg>
      <svg v-else class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
        <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd"/>
      </svg>
    </button>
    
    <button
      @click="workflowStore.stopExecution"
      class="p-2 rounded hover:bg-gray-700 transition-colors"
      :disabled="!executionState.isRunning"
      :class="{ 'opacity-50': !executionState.isRunning }"
    >
      <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 7a1 1 0 00-1 1v4a1 1 0 001 1h4a1 1 0 001-1V8a1 1 0 00-1-1H8z" clip-rule="evenodd"/>
      </svg>
    </button>
    
    <div class="h-6 w-px bg-dark-border"></div>
    
    <button
      @click="stepForward"
      class="p-2 rounded hover:bg-gray-700 transition-colors"
      :disabled="!executionState.isPaused"
      :class="{ 'opacity-50': !executionState.isPaused }"
    >
      <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
        <path d="M4.555 5.168A1 1 0 003 6v8a1 1 0 001.555.832L10 11.202V14a1 1 0 001.555.832l6-4a1 1 0 000-1.664l-6-4A1 1 0 0010 6v2.798L4.555 5.168z"/>
      </svg>
    </button>
    
    <div class="h-6 w-px bg-dark-border"></div>
    
    <div class="flex items-center gap-2 px-2">
      <label class="text-xs text-gray-400">Speed:</label>
      <input
        type="range"
        min="0.5"
        max="2"
        step="0.1"
        v-model="playbackSpeed"
        class="w-20 h-1 bg-gray-700 rounded-lg appearance-none cursor-pointer"
      />
      <span class="text-xs text-gray-300">{{ playbackSpeed }}x</span>
    </div>
    
    <div v-if="executionState.isRunning" class="ml-4 flex items-center gap-2">
      <div class="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
      <span class="text-xs text-gray-400">
        {{ executionState.isPaused ? 'Paused' : 'Running' }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useWorkflowStore } from '@/stores/workflow'

const workflowStore = useWorkflowStore()
const { executionState } = storeToRefs(workflowStore)

const playbackSpeed = ref(1)

const handlePlayPause = () => {
  if (!executionState.value.isRunning) {
    workflowStore.startExecution()
  } else if (executionState.value.isPaused) {
    executionState.value.isPaused = false
  } else {
    workflowStore.pauseExecution()
  }
}

const stepForward = () => {
  // Implement step-by-step execution
  console.log('Step forward')
}
</script>

<style scoped>
input[type="range"]::-webkit-slider-thumb {
  appearance: none;
  width: 12px;
  height: 12px;
  background: #3498db;
  cursor: pointer;
  border-radius: 50%;
}

input[type="range"]::-moz-range-thumb {
  width: 12px;
  height: 12px;
  background: #3498db;
  cursor: pointer;
  border-radius: 50%;
  border: none;
}
</style>