<template>
  <div class="worker-node">
    <Handle type="source" :position="Position.Right" :style="{ top: '50%' }" />
    <Handle type="target" :position="Position.Left" :style="{ top: '50%' }" />
    
    <!-- Main Node Content -->
    <div class="node-header">
      <div class="node-icon">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
        </svg>
      </div>
      <div class="node-info">
        <h3 class="node-title">{{ data.label || 'Claude Worker' }}</h3>
        <p class="node-subtitle">{{ data.role || 'AI Agent' }}</p>
      </div>
      <div v-if="data.hasGitHubContext" class="github-context-badge" title="Has implementation context">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
          <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
        </svg>
      </div>
      <div class="status-badge" :class="statusClass">
        {{ data.status || 'available' }}
      </div>
    </div>
    
    <!-- Progress Bar -->
    <div v-if="data.currentTask && data.progress !== undefined" class="progress-section">
      <div class="progress-info">
        <span class="task-name">{{ data.taskName || 'Working...' }}</span>
        <span class="progress-text">{{ data.progress }}%</span>
      </div>
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: `${data.progress}%` }"></div>
      </div>
      <div v-if="data.implementation" class="implementation-hint">
        {{ truncateImplementation(data.implementation) }}
      </div>
    </div>
    
    <!-- Skills -->
    <div v-if="data.skills && data.skills.length" class="skills-section">
      <div class="skill-chip" v-for="skill in data.skills.slice(0, 4)" :key="skill">
        {{ skill }}
      </div>
      <div v-if="data.skills.length > 4" class="skill-chip more">
        +{{ data.skills.length - 4 }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'

const props = defineProps({
  data: {
    type: Object,
    required: true
  }
})

const statusClass = computed(() => {
  const status = props.data.status || 'available'
  return {
    'available': status === 'available',
    'working': status === 'working',
    'blocked': status === 'blocked',
    'initializing': status === 'initializing'
  }
})

const truncateImplementation = (text) => {
  if (!text) return ''
  const maxLength = 60
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}
</script>

<style scoped>
.worker-node {
  min-width: 260px;
  background: #2a2a2a;
  border: 1px solid #444;
  border-radius: 12px;
  position: relative;
  overflow: hidden;
}

.node-header {
  display: flex;
  align-items: center;
  padding: 16px;
  gap: 12px;
  position: relative;
}

.node-icon {
  width: 40px;
  height: 40px;
  background: #3498db;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
}

.node-info {
  flex: 1;
  min-width: 0;
}

.node-title {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.node-subtitle {
  font-size: 11px;
  color: #999;
  margin: 2px 0 0 0;
}

.status-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
  text-transform: uppercase;
}

.status-badge.available {
  background: #27ae60;
  color: white;
}

.status-badge.working {
  background: #3498db;
  color: white;
}

.status-badge.blocked {
  background: #e74c3c;
  color: white;
}

.status-badge.initializing {
  background: #f39c12;
  color: white;
}

.progress-section {
  padding: 0 16px 12px;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.task-name {
  font-size: 11px;
  color: #bbb;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.progress-text {
  font-size: 11px;
  color: #3498db;
  font-weight: 600;
  margin-left: 8px;
}

.progress-bar {
  height: 4px;
  background: #333;
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #3498db;
  transition: width 0.3s ease;
  border-radius: 2px;
}

.skills-section {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 0 16px 12px;
  border-top: 1px solid #333;
  margin-top: 8px;
  padding-top: 12px;
}

.skill-chip {
  font-size: 10px;
  padding: 3px 8px;
  background: #333;
  color: #aaa;
  border-radius: 12px;
  border: 1px solid #444;
}

.skill-chip.more {
  background: transparent;
  color: #666;
  border-style: dashed;
}

.github-context-badge {
  position: absolute;
  top: 36px;
  right: 8px;
  width: 24px;
  height: 24px;
  background: #1a1a1a;
  border: 1px solid #333;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #7a7a7a;
  cursor: help;
}

.github-context-badge:hover {
  background: #333;
  color: #fff;
  border-color: #555;
}

.implementation-hint {
  font-size: 10px;
  color: #888;
  margin-top: 4px;
  font-style: italic;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>