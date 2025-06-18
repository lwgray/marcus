<template>
  <div class="decision-node">
    <Handle type="target" :position="Position.Top" />
    
    <div class="decision-icon">
      <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
        <path d="M10 0L12.5 7.5L20 10L12.5 12.5L10 20L7.5 12.5L0 10L7.5 7.5L10 0Z"/>
      </svg>
    </div>
    
    <div class="decision-content">
      <div class="decision-text">{{ data.label }}</div>
      <div class="confidence-bar">
        <div class="confidence-fill" :style="{ width: `${(data.confidence || 0) * 100}%` }"></div>
      </div>
      <div class="confidence-text">{{ Math.round((data.confidence || 0) * 100) }}% confidence</div>
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
.decision-node {
  background: #2a2a2a;
  border: 1px solid #444;
  border-radius: 12px;
  padding: 12px;
  min-width: 200px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
}

.decision-icon {
  width: 32px;
  height: 32px;
  background: #f39c12;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 8px;
  color: white;
}

.decision-content {
  text-align: center;
}

.decision-text {
  font-size: 12px;
  color: #fff;
  margin-bottom: 8px;
  line-height: 1.3;
}

.confidence-bar {
  height: 3px;
  background: #333;
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 4px;
}

.confidence-fill {
  height: 100%;
  background: #f39c12;
  transition: width 0.3s ease;
}

.confidence-text {
  font-size: 10px;
  color: #888;
}
</style>