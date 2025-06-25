<!--
  HealthAnalysisPanel Component
  
  Purpose: Displays AI-powered project health analysis and recommendations.
  Provides comprehensive insights into project status, risks, and optimization opportunities.
  
  Features:
  - Overall project health status with visual indicators
  - Timeline predictions with confidence scores
  - Risk factor identification and mitigation strategies
  - Actionable recommendations prioritized by impact
  - Resource optimization suggestions
  - Historical health trends and patterns
  - Real-time updates via WebSocket connection
  
  Health Analysis Categories:
  - Green: Project on track with minimal risks
  - Yellow: Some concerns requiring attention
  - Red: Critical issues needing immediate action
  
  Data Sources:
  - Project metrics and KPIs
  - Task completion rates and velocity
  - Team status and availability
  - Historical performance data
-->
<template>
  <div class="health-analysis-panel">
    <!-- Panel header with refresh controls -->
    <div class="panel-header">
      <h3>Project Health Analysis</h3>
      <button 
        @click="refreshAnalysis" 
        :disabled="loading"
        class="refresh-btn"
      >
        <span v-if="loading">Analyzing...</span>
        <span v-else>Refresh Analysis</span>
      </button>
    </div>

    <!-- Error state display -->
    <div v-if="error" class="error-message">
      {{ error }}
    </div>

    <!-- No data state with initialization option -->
    <div v-else-if="!healthData" class="no-data">
      <p>No health analysis available</p>
      <button @click="runAnalysis" class="primary-btn">
        Run Initial Analysis
      </button>
    </div>

    <!-- Main health analysis content -->
    <div v-else class="health-content">
      <!-- Overall Health Status indicator -->
      <div class="health-status" :class="`health-${healthData.overall_health}`">
        <div class="status-indicator">
          <span class="status-icon">{{ getHealthIcon(healthData.overall_health) }}</span>
          <span class="status-text">{{ healthData.overall_health.toUpperCase() }}</span>
        </div>
        <div class="last-updated">
          Updated: {{ formatTime(healthData.timestamp) }}
        </div>
      </div>

      <!-- Timeline Prediction section -->
      <div class="timeline-section">
        <h4>Timeline Prediction</h4>
        <div class="timeline-status">
          <span :class="{ 'on-track': healthData.timeline_prediction.on_track }">
            {{ healthData.timeline_prediction.on_track ? '✓ On Track' : '⚠ Off Track' }}
          </span>
          <span class="confidence">
            Confidence: {{ (healthData.timeline_prediction.confidence * 100).toFixed(0) }}%
          </span>
        </div>
        <p class="completion-estimate">
          {{ healthData.timeline_prediction.estimated_completion }}
        </p>
        <!-- Critical path risks -->
        <div v-if="healthData.timeline_prediction.critical_path_risks?.length" class="critical-risks">
          <strong>Critical Path Risks:</strong>
          <ul>
            <li v-for="risk in healthData.timeline_prediction.critical_path_risks" :key="risk">
              {{ risk }}
            </li>
          </ul>
        </div>
      </div>

      <!-- Risk Factors section -->
      <div v-if="healthData.risk_factors?.length" class="risk-factors">
        <h4>Risk Factors ({{ healthData.risk_factors.length }})</h4>
        <div 
          v-for="(risk, index) in healthData.risk_factors" 
          :key="index"
          class="risk-item"
          :class="`risk-${risk.severity}`"
        >
          <div class="risk-header">
            <span class="risk-type">{{ risk.type }}</span>
            <span class="risk-severity">{{ risk.severity }}</span>
          </div>
          <p class="risk-description">{{ risk.description }}</p>
          <p class="risk-mitigation">
            <strong>Mitigation:</strong> {{ risk.mitigation }}
          </p>
        </div>
      </div>

      <!-- Recommendations section -->
      <div v-if="healthData.recommendations?.length" class="recommendations">
        <h4>Recommendations</h4>
        <div 
          v-for="(rec, index) in healthData.recommendations" 
          :key="index"
          class="recommendation-item"
          :class="`priority-${rec.priority}`"
        >
          <div class="rec-header">
            <span class="priority-badge">{{ rec.priority }}</span>
          </div>
          <p class="rec-action">{{ rec.action }}</p>
          <p class="rec-impact">
            <em>Expected Impact: {{ rec.expected_impact }}</em>
          </p>
        </div>
      </div>

      <!-- Resource Optimization section -->
      <div v-if="healthData.resource_optimization?.length" class="resource-optimization">
        <h4>Resource Optimization</h4>
        <div 
          v-for="(opt, index) in healthData.resource_optimization" 
          :key="index"
          class="optimization-item"
        >
          <p class="opt-suggestion">{{ opt.suggestion }}</p>
          <p class="opt-impact">
            <strong>Impact:</strong> {{ opt.impact }}
          </p>
        </div>
      </div>

      <!-- Trends analysis (if available) -->
      <div v-if="healthData.trends" class="trends">
        <h4>Trends</h4>
        <div class="trend-items">
          <div class="trend-item">
            <span class="trend-label">Health:</span>
            <span :class="`trend-${healthData.trends.health_direction}`">
              {{ getTrendIcon(healthData.trends.health_direction) }}
              {{ healthData.trends.health_direction }}
            </span>
          </div>
          <div class="trend-item">
            <span class="trend-label">Confidence:</span>
            <span :class="{ positive: healthData.trends.confidence_change > 0 }">
              {{ healthData.trends.confidence_change > 0 ? '+' : '' }}
              {{ (healthData.trends.confidence_change * 100).toFixed(1) }}%
            </span>
          </div>
          <div class="trend-item">
            <span class="trend-label">Risks:</span>
            <span :class="`trend-${healthData.trends.risk_change}`">
              {{ healthData.trends.risk_change }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Health History visualization -->
    <div v-if="showHistory" class="health-history">
      <h4>Health History (24h)</h4>
      <div class="history-chart">
        <!-- Simple icon-based timeline visualization -->
        <div class="history-summary">
          <div v-for="(item, index) in healthHistory" :key="index" class="history-item">
            <span class="history-time">{{ formatTime(item.timestamp, true) }}</span>
            <span :class="`health-${item.overall_health}`">
              {{ getHealthIcon(item.overall_health) }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
/**
 * HealthAnalysisPanel - AI-powered project health monitoring and analysis
 * 
 * This component provides comprehensive project health insights including:
 * - Overall health status and trends
 * - Timeline predictions with confidence scores
 * - Risk identification and mitigation strategies
 * - Actionable recommendations prioritized by impact
 * - Resource optimization opportunities
 * - Historical health data visualization
 * 
 * The analysis is powered by AI and considers multiple project factors:
 * - Task completion velocity and patterns
 * - Team availability and performance
 * - Risk factors and blockers
 * - Resource utilization efficiency
 */

import { ref, onMounted, onUnmounted } from 'vue'
import { useWebSocketStore } from '@/stores/websocket'

export default {
  name: 'HealthAnalysisPanel',
  setup() {
    // Store reference for WebSocket communication
    const wsStore = useWebSocketStore()
    
    // Reactive state for health analysis data
    const healthData = ref(null)
    const healthHistory = ref([])
    const loading = ref(false)
    const error = ref(null)
    const showHistory = ref(false)
    let healthUpdateHandler = null

    /**
     * Maps health status to appropriate emoji icons
     * Provides quick visual identification of project health
     * 
     * @param {string} health - Health status (green, yellow, red, unknown)
     * @returns {string} Corresponding emoji icon
     */
    const getHealthIcon = (health) => {
      const icons = {
        green: '✅',
        yellow: '⚠️',
        red: '🚨',
        unknown: '❓'
      }
      return icons[health] || '❓'
    }

    /**
     * Maps trend direction to directional arrow icons
     * Shows whether metrics are improving, stable, or declining
     * 
     * @param {string} direction - Trend direction (improving, stable, declining)
     * @returns {string} Corresponding directional icon
     */
    const getTrendIcon = (direction) => {
      const icons = {
        improving: '↗️',
        stable: '→',
        declining: '↘️'
      }
      return icons[direction] || '→'
    }

    /**
     * Formats timestamp for display in the UI
     * Supports both short and long format options
     * 
     * @param {number|string} timestamp - Unix timestamp or ISO date string
     * @param {boolean} short - Whether to use short format (HH:MM vs full date)
     * @returns {string} Formatted time string
     */
    const formatTime = (timestamp, short = false) => {
      if (!timestamp) return 'N/A'
      const date = new Date(timestamp)
      if (short) {
        return date.toLocaleTimeString('en-US', { 
          hour: '2-digit', 
          minute: '2-digit' 
        })
      }
      return date.toLocaleString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit',
        month: 'short',
        day: 'numeric'
      })
    }

    /**
     * Fetches current health analysis data from the API
     * Handles both successful responses and 404 not found cases
     */
    const fetchCurrentHealth = async () => {
      try {
        const response = await fetch('/api/health/current')
        if (response.ok) {
          const data = await response.json()
          healthData.value = data
        } else if (response.status === 404) {
          healthData.value = null
        } else {
          throw new Error('Failed to fetch health data')
        }
      } catch (err) {
        error.value = err.message
      }
    }

    /**
     * Fetches historical health data for trend visualization
     * Retrieves last 24 hours of health analysis results
     */
    const fetchHealthHistory = async () => {
      try {
        const response = await fetch('/api/health/history?hours=24')
        if (response.ok) {
          const data = await response.json()
          healthHistory.value = data.history
          showHistory.value = data.history.length > 0
        }
      } catch (err) {
        console.error('Failed to fetch health history:', err)
      }
    }

    /**
     * Triggers a new health analysis with current project data
     * Gathers project state and sends to AI analysis engine
     */
    const runAnalysis = async () => {
      loading.value = true
      error.value = null
      
      try {
        // In production, this would gather actual project state
        const mockData = {
          project_state: {
            board_id: 'BOARD-001',
            project_name: 'Marcus Development',
            total_tasks: 50,
            completed_tasks: 20,
            in_progress_tasks: 15,
            blocked_tasks: 3,
            progress_percent: 40.0,
            team_velocity: 3.5,
            risk_level: 'MEDIUM'
          },
          recent_activities: [
            { type: 'task_completed', count: 5, timeframe: 'last_week' },
            { type: 'task_blocked', count: 2, timeframe: 'last_week' }
          ],
          team_status: []
        }
        
        const response = await fetch('/api/health/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(mockData)
        })
        
        if (response.ok) {
          const data = await response.json()
          healthData.value = data
          error.value = null
        } else {
          throw new Error('Analysis failed')
        }
      } catch (err) {
        error.value = err.message
      } finally {
        loading.value = false
      }
    }

    /**
     * Refreshes both current analysis and historical data
     * Called when user clicks the refresh button
     */
    const refreshAnalysis = async () => {
      await runAnalysis()
      await fetchHealthHistory()
    }

    /**
     * Handles real-time health updates from WebSocket
     * Updates current data and maintains rolling history
     * 
     * @param {Object} data - New health analysis data
     */
    const handleHealthUpdate = (data) => {
      healthData.value = data
      // Add to history
      healthHistory.value.push(data)
      // Keep only last 50 items
      if (healthHistory.value.length > 50) {
        healthHistory.value = healthHistory.value.slice(-50)
      }
    }

    onMounted(async () => {
      // Subscribe to health updates via WebSocket
      if (wsStore.socket) {
        wsStore.socket.emit('subscribe_health_updates', {})
        healthUpdateHandler = handleHealthUpdate
        wsStore.socket.on('health_update', healthUpdateHandler)
      }
      
      // Fetch initial data
      await fetchCurrentHealth()
      await fetchHealthHistory()
    })

    onUnmounted(() => {
      // Cleanup WebSocket subscription
      if (wsStore.socket && healthUpdateHandler) {
        wsStore.socket.off('health_update', healthUpdateHandler)
      }
    })

    return {
      healthData,
      healthHistory,
      loading,
      error,
      showHistory,
      getHealthIcon,
      getTrendIcon,
      formatTime,
      runAnalysis,
      refreshAnalysis
    }
  }
}
</script>

<style scoped>
.health-analysis-panel {
  background: var(--bg-secondary);
  border-radius: 8px;
  padding: 16px;
  height: 100%;
  overflow-y: auto;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.panel-header h3 {
  margin: 0;
  color: var(--text-primary);
}

.refresh-btn {
  padding: 6px 12px;
  background: var(--accent-color);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.refresh-btn:hover:not(:disabled) {
  background: var(--accent-hover);
}

.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error-message {
  background: #ff4444;
  color: white;
  padding: 12px;
  border-radius: 4px;
  margin-bottom: 16px;
}

.no-data {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-secondary);
}

.primary-btn {
  padding: 10px 20px;
  background: var(--accent-color);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
  margin-top: 16px;
}

.primary-btn:hover {
  background: var(--accent-hover);
}

/* Health Status */
.health-status {
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.health-status.health-green {
  background: rgba(76, 175, 80, 0.1);
  border: 1px solid #4CAF50;
}

.health-status.health-yellow {
  background: rgba(255, 193, 7, 0.1);
  border: 1px solid #FFC107;
}

.health-status.health-red {
  background: rgba(244, 67, 54, 0.1);
  border: 1px solid #F44336;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-icon {
  font-size: 24px;
}

.status-text {
  font-weight: bold;
  font-size: 18px;
}

.last-updated {
  color: var(--text-secondary);
  font-size: 12px;
}

/* Timeline Section */
.timeline-section {
  margin-bottom: 20px;
}

.timeline-section h4 {
  margin: 0 0 12px 0;
  color: var(--text-primary);
}

.timeline-status {
  display: flex;
  gap: 16px;
  margin-bottom: 8px;
}

.timeline-status .on-track {
  color: #4CAF50;
  font-weight: bold;
}

.confidence {
  color: var(--text-secondary);
}

.completion-estimate {
  margin: 8px 0;
  color: var(--text-primary);
}

.critical-risks {
  margin-top: 12px;
  padding: 12px;
  background: rgba(255, 193, 7, 0.1);
  border-radius: 4px;
}

.critical-risks ul {
  margin: 8px 0 0 0;
  padding-left: 20px;
}

/* Risk Factors */
.risk-factors h4 {
  margin: 0 0 12px 0;
  color: var(--text-primary);
}

.risk-item {
  margin-bottom: 12px;
  padding: 12px;
  border-radius: 4px;
  border: 1px solid;
}

.risk-item.risk-low {
  background: rgba(76, 175, 80, 0.05);
  border-color: #4CAF50;
}

.risk-item.risk-medium {
  background: rgba(255, 193, 7, 0.05);
  border-color: #FFC107;
}

.risk-item.risk-high {
  background: rgba(244, 67, 54, 0.05);
  border-color: #F44336;
}

.risk-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.risk-type {
  font-weight: bold;
  text-transform: capitalize;
}

.risk-severity {
  font-size: 12px;
  text-transform: uppercase;
  padding: 2px 8px;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.1);
}

.risk-description {
  margin: 8px 0;
  color: var(--text-primary);
}

.risk-mitigation {
  margin: 8px 0 0 0;
  font-size: 14px;
  color: var(--text-secondary);
}

/* Recommendations */
.recommendations h4 {
  margin: 20px 0 12px 0;
  color: var(--text-primary);
}

.recommendation-item {
  margin-bottom: 12px;
  padding: 12px;
  border-radius: 4px;
  background: var(--bg-primary);
}

.priority-badge {
  font-size: 12px;
  text-transform: uppercase;
  padding: 2px 8px;
  border-radius: 12px;
  font-weight: bold;
}

.recommendation-item.priority-high .priority-badge {
  background: #F44336;
  color: white;
}

.recommendation-item.priority-medium .priority-badge {
  background: #FFC107;
  color: #333;
}

.recommendation-item.priority-low .priority-badge {
  background: #4CAF50;
  color: white;
}

.rec-action {
  margin: 8px 0;
  font-weight: 500;
}

.rec-impact {
  margin: 8px 0 0 0;
  font-size: 14px;
  color: var(--text-secondary);
}

/* Resource Optimization */
.resource-optimization h4 {
  margin: 20px 0 12px 0;
  color: var(--text-primary);
}

.optimization-item {
  margin-bottom: 12px;
  padding: 12px;
  background: rgba(33, 150, 243, 0.05);
  border: 1px solid #2196F3;
  border-radius: 4px;
}

.opt-suggestion {
  margin: 0 0 8px 0;
  color: var(--text-primary);
}

.opt-impact {
  margin: 0;
  font-size: 14px;
  color: var(--text-secondary);
}

/* Trends */
.trends {
  margin-top: 20px;
  padding: 12px;
  background: var(--bg-primary);
  border-radius: 4px;
}

.trends h4 {
  margin: 0 0 12px 0;
  color: var(--text-primary);
}

.trend-items {
  display: flex;
  gap: 20px;
}

.trend-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.trend-label {
  color: var(--text-secondary);
  font-size: 14px;
}

.trend-improving {
  color: #4CAF50;
}

.trend-stable {
  color: var(--text-secondary);
}

.trend-declining {
  color: #F44336;
}

.trend-decreasing {
  color: #4CAF50;
}

.trend-increasing {
  color: #F44336;
}

.positive {
  color: #4CAF50;
}

/* Health History */
.health-history {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid var(--border-color);
}

.health-history h4 {
  margin: 0 0 12px 0;
  color: var(--text-primary);
}

.history-chart {
  background: var(--bg-primary);
  padding: 12px;
  border-radius: 4px;
}

.history-summary {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.history-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 4px;
}

.history-time {
  font-size: 10px;
  color: var(--text-secondary);
}

/* Dark theme variables */
:root {
  --bg-primary: #1e1e1e;
  --bg-secondary: #252525;
  --text-primary: #e0e0e0;
  --text-secondary: #a0a0a0;
  --border-color: #333;
  --accent-color: #2196F3;
  --accent-hover: #1976D2;
}
</style>