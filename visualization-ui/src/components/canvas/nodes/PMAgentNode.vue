<!--
  PMAgentNode Component
  
  Purpose: Represents the central Marcus node in the workflow visualization.
  This is the main decision-making hub that coordinates all worker agents.
  
  Features:
  - Visual representation with icon and title
  - Connection handles for input/output edges
  - Sub-resource outputs (Decisions, Analysis, Memory, Tasks)
  - Animated status indicator when "thinking"
  - Multiple connection points for different types of outputs
  
  Props:
  - data: Node data containing status and other Marcus information
-->
<template>
  <div class="pm-agent-node">
    <!-- Main connection handles -->
    <Handle type="source" :position="Position.Right" :style="{ top: '50%' }" />
    <Handle type="target" :position="Position.Left" :style="{ top: '50%' }" />
    
    <!-- Main Node Content -->
    <div class="node-header">
      <div class="node-icon">
        <!-- Checkmark circle icon representing Marcus -->
        <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
        </svg>
      </div>
      <div class="node-info">
        <h3 class="node-title">Marcus</h3>
        <p class="node-subtitle">Project Manager</p>
      </div>
    </div>
    
    <!-- Sub-resources section with individual output handles -->
    <div class="sub-resources">
      <div class="sub-resource-item" v-for="resource in subResources" :key="resource.name">
        <!-- Individual handle for each sub-resource -->
        <Handle 
          :id="`${resource.name}-output`"
          type="source" 
          :position="Position.Bottom" 
          :style="{ left: `${resource.position}%`, bottom: '-8px' }"
          class="sub-handle"
        />
        <span class="sub-label">{{ resource.name }}</span>
        <div class="sub-icon">
          <component :is="resource.icon" />
        </div>
      </div>
    </div>
    
    <!-- Animated status indicator for thinking state -->
    <div v-if="data.status === 'thinking'" class="status-indicator thinking">
      <div class="pulse"></div>
    </div>
  </div>
</template>

<script setup>
/**
 * PMAgentNode - Visual representation of Marcus in the workflow
 * 
 * Marcus is the central coordinator that:
 * - Makes decisions about task assignment
 * - Analyzes project state
 * - Maintains project memory
 * - Manages task distribution
 * 
 * This node provides multiple connection points for different types of outputs
 * through its sub-resources.
 */

import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'

/**
 * Component props
 * @prop {Object} data - Node data from the workflow
 * @prop {string} data.status - Current status of Marcus (e.g., 'thinking', 'idle')
 * @prop {Object} data.metrics - Performance metrics for Marcus
 */
const props = defineProps({
  data: {
    type: Object,
    required: true
  }
})

/**
 * Icon component for Decisions sub-resource
 * Star icon representing decision-making capability
 */
const DecisionIcon = {
  template: `<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
    <path d="M8 0L10 4L14 4.5L11 7.5L11.5 11.5L8 9.5L4.5 11.5L5 7.5L2 4.5L6 4L8 0Z"/>
  </svg>`
}

/**
 * Icon component for Analysis sub-resource
 * Bar chart icon representing analytical capabilities
 */
const AnalysisIcon = {
  template: `<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
    <path d="M2 11h4v3H2zm5-7h4v10H7zm5-3h4v13h-4z"/>
  </svg>`
}

/**
 * Icon component for Memory sub-resource
 * Concentric circles icon representing memory/storage
 */
const MemoryIcon = {
  template: `<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
    <path d="M8 2a6 6 0 100 12A6 6 0 008 2zm0 10a4 4 0 110-8 4 4 0 010 8z"/>
    <circle cx="8" cy="8" r="2"/>
  </svg>`
}

/**
 * Icon component for Tasks sub-resource
 * List icon representing task management
 */
const TaskIcon = {
  template: `<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
    <path d="M2 3h12v2H2zm0 4h12v2H2zm0 4h8v2H2z"/>
  </svg>`
}

/**
 * Sub-resources configuration
 * Each resource represents a different output type from Marcus
 * 
 * @property {string} name - Display name of the sub-resource
 * @property {number} position - Horizontal position as percentage (0-100)
 * @property {Object} icon - Vue component for the resource icon
 */
const subResources = [
  { name: 'Decisions', position: 20, icon: DecisionIcon },
  { name: 'Analysis', position: 40, icon: AnalysisIcon },
  { name: 'Memory', position: 60, icon: MemoryIcon },
  { name: 'Tasks', position: 80, icon: TaskIcon }
]
</script>

<style scoped>
.pm-agent-node {
  min-width: 280px;
  background: #2a2a2a;
  border: 1px solid #444;
  border-radius: 12px;
  position: relative;
  padding-bottom: 60px;
}

.node-header {
  display: flex;
  align-items: center;
  padding: 16px;
  gap: 12px;
  border-bottom: 1px solid #333;
}

.node-icon {
  width: 48px;
  height: 48px;
  background: #9b59b6;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.node-info {
  flex: 1;
}

.node-title {
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  margin: 0;
}

.node-subtitle {
  font-size: 12px;
  color: #999;
  margin: 2px 0 0 0;
}

.sub-resources {
  display: flex;
  padding: 12px 8px;
  gap: 4px;
  position: relative;
}

.sub-resource-item {
  flex: 1;
  text-align: center;
  position: relative;
  padding: 8px 4px;
}

.sub-label {
  font-size: 10px;
  color: #888;
  display: block;
  margin-bottom: 4px;
}

.sub-icon {
  width: 32px;
  height: 32px;
  background: #333;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto;
  color: #666;
  border: 1px solid #444;
}

.sub-handle {
  width: 8px;
  height: 8px;
  background: #666;
  border: 2px solid #2a2a2a;
  cursor: crosshair;
}

.sub-handle:hover {
  background: #9b59b6;
}

.status-indicator {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-indicator.thinking {
  background: #f39c12;
}

.pulse {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: inherit;
  animation: pulse 2s ease-out infinite;
}

@keyframes pulse {
  0% {
    transform: scale(1);
    opacity: 1;
  }
  100% {
    transform: scale(3);
    opacity: 0;
  }
}
</style>