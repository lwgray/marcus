<template>
  <div class="knowledge-node">
    <Handle type="source" :position="Position.Top" :style="{ left: '50%' }" />
    <Handle type="target" :position="Position.Bottom" :style="{ left: '50%' }" />
    
    <!-- Main Node Content -->
    <div class="node-header">
      <div class="node-icon">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
        </svg>
      </div>
      <div class="node-info">
        <h3 class="node-title">Knowledge Base</h3>
        <p class="node-subtitle">Graph Database</p>
      </div>
    </div>
    
    <!-- Metrics -->
    <div class="metrics-row">
      <div class="metric">
        <div class="metric-value">{{ data.metrics?.totalNodes || 0 }}</div>
        <div class="metric-label">Nodes</div>
      </div>
      <div class="metric">
        <div class="metric-value">{{ data.metrics?.relationships || 0 }}</div>
        <div class="metric-label">Relations</div>
      </div>
    </div>
    
    <!-- Status -->
    <div class="sync-status" :class="{ synced: data.status === 'synced' }">
      <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
        <path d="M10.8 5.4H9.6C9.3 3.5 7.8 2 6 2 3.8 2 2 3.8 2 6s1.8 4 4 4c1.1 0 2.1-.5 2.8-1.2l.9.9C8.7 10.5 7.4 11 6 11c-2.8 0-5-2.2-5-5s2.2-5 5-5c2.3 0 4.2 1.5 4.8 3.6H12L9.6 7 7.2 4.6 10.8 5.4z"/>
      </svg>
      {{ data.status || 'synced' }}
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
.knowledge-node {
  min-width: 220px;
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
  background: #e74c3c;
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

.metrics-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  padding: 12px 16px;
  gap: 16px;
}

.metric {
  text-align: center;
}

.metric-value {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  margin-bottom: 2px;
}

.metric-label {
  font-size: 10px;
  color: #666;
  text-transform: uppercase;
}

.sync-status {
  position: absolute;
  top: 8px;
  right: 8px;
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  color: #666;
}

.sync-status.synced {
  color: #2ecc71;
}

.sync-status svg {
  animation: rotate 2s linear infinite;
}

.sync-status.synced svg {
  animation: none;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>