<template>
  <div class="kanban-node">
    <Handle type="source" :position="Position.Left" :style="{ top: '50%' }" />
    <Handle type="target" :position="Position.Right" :style="{ top: '50%' }" />
    
    <!-- Main Node Content -->
    <div class="node-header">
      <div class="node-icon">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
          <path d="M4 6h16v2H4zm0 5h16v2H4zm0 5h16v2H4z"/>
        </svg>
      </div>
      <div class="node-info">
        <h3 class="node-title">Kanban Board</h3>
        <p class="node-subtitle">Planka</p>
      </div>
    </div>
    
    <!-- Metrics Grid -->
    <div class="metrics-grid">
      <div class="metric-item">
        <div class="metric-value">{{ data.metrics?.totalTasks || 0 }}</div>
        <div class="metric-label">Total</div>
      </div>
      <div class="metric-item">
        <div class="metric-value in-progress">{{ data.metrics?.inProgress || 0 }}</div>
        <div class="metric-label">Active</div>
      </div>
      <div class="metric-item">
        <div class="metric-value completed">{{ data.metrics?.completed || 0 }}</div>
        <div class="metric-label">Done</div>
      </div>
    </div>
    
    <!-- Connection Status -->
    <div class="connection-status" :class="{ connected: data.status === 'connected' }">
      <div class="status-dot"></div>
      {{ data.status || 'connected' }}
    </div>
  </div>
</template>

<script setup>
import { Handle, Position } from '@vue-flow/core'

const props = defineProps({
  data: {
    type: Object,
    required: true
  }
})
</script>

<style scoped>
.kanban-node {
  min-width: 240px;
  background: #2a2a2a;
  border: 1px solid #444;
  border-radius: 12px;
  position: relative;
}

.node-header {
  display: flex;
  align-items: center;
  padding: 16px;
  gap: 12px;
  border-bottom: 1px solid #333;
}

.node-icon {
  width: 40px;
  height: 40px;
  background: #2ecc71;
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
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  margin: 0;
}

.node-subtitle {
  font-size: 11px;
  color: #999;
  margin: 2px 0 0 0;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  padding: 16px 8px;
  gap: 8px;
}

.metric-item {
  text-align: center;
  padding: 8px 4px;
}

.metric-value {
  font-size: 20px;
  font-weight: 700;
  color: #fff;
  margin-bottom: 4px;
}

.metric-value.in-progress {
  color: #3498db;
}

.metric-value.completed {
  color: #2ecc71;
}

.metric-label {
  font-size: 10px;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.connection-status {
  position: absolute;
  top: 8px;
  right: 8px;
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  color: #666;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #666;
}

.connection-status.connected .status-dot {
  background: #2ecc71;
  box-shadow: 0 0 4px #2ecc71;
}
</style>