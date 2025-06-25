<!--
  EventLog Component
  
  Purpose: Displays a real-time log of system events from the Marcus workflow.
  Shows communication between workers, Marcus decisions, and system activities.
  
  Features:
  - Real-time event stream with timestamps
  - Color-coded event types for easy identification
  - Source and target formatting for readability
  - Clear button to reset the log
  - Auto-scrolling with overflow handling
  - Hover effects for better interaction
  
  Event Types:
  - Worker messages and communication
  - Marcus decisions and thinking states
  - Kanban board requests and responses
  - Task assignments and progress updates
  - Blocker reports and system notifications
-->
<template>
  <div class="event-log flex flex-col h-full">
    <!-- Header with title and clear button -->
    <div class="flex items-center justify-between p-3 border-b border-dark-border">
      <h3 class="text-sm font-medium">Event Log</h3>
      <button
        @click="eventStore.clearEvents"
        class="text-xs text-gray-500 hover:text-gray-300 transition-colors"
      >
        Clear
      </button>
    </div>
    
    <!-- Scrollable event list -->
    <div class="flex-1 overflow-y-auto p-3 space-y-1">
      <div
        v-for="event in recentEvents"
        :key="event.id"
        class="event-entry text-xs p-2 rounded border-l-2 bg-dark-surface/50"
        :class="getEventClass(event)"
      >
        <div class="flex items-start gap-2">
          <!-- Timestamp -->
          <span class="text-gray-600 flex-shrink-0">{{ formatTime(event.timestamp) }}</span>
          <div class="flex-1">
            <!-- Source → Target relationship -->
            <span class="font-medium">{{ getEventSource(event) }}</span>
            <span class="mx-1 text-gray-600">→</span>
            <span class="font-medium">{{ getEventTarget(event) }}</span>
            <!-- Event message content -->
            <div class="text-gray-400 mt-0.5">{{ event.message }}</div>
          </div>
        </div>
      </div>
      
      <!-- Empty state message -->
      <div v-if="recentEvents.length === 0" class="text-center text-gray-600 py-8">
        No events yet
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * EventLog - Real-time display of Marcus system events
 * 
 * Provides a chronological view of all system activities including:
 * - Inter-agent communication
 * - Marcus decision-making processes
 * - Task assignments and progress updates
 * - System state changes and notifications
 * 
 * Events are color-coded by type and formatted for readability.
 */

import { storeToRefs } from 'pinia'
import { useEventStore } from '@/stores/events'

// Event store instance for accessing system events
const eventStore = useEventStore()

// Reactive reference to recent events from the store
const { recentEvents } = storeToRefs(eventStore)

/**
 * Formats timestamp for display in HH:MM:SS format
 * Uses 24-hour format for precision and consistency
 * 
 * @param {number|string} timestamp - Unix timestamp or ISO date string
 * @returns {string} Formatted time string (HH:MM:SS)
 */
const formatTime = (timestamp) => {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('en-US', { 
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

/**
 * Formats event source for display
 * Converts internal identifiers to human-readable labels
 * 
 * @param {Object} event - Event object
 * @param {string} event.source - Source identifier (e.g., 'worker_123', 'pm_agent')
 * @returns {string} Formatted source name
 */
const getEventSource = (event) => {
  if (event.source?.startsWith('worker_')) {
    return event.source.replace('worker_', 'Worker ')
  }
  return event.source?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) || 'Unknown'
}

/**
 * Formats event target for display
 * Converts internal identifiers to human-readable labels
 * 
 * @param {Object} event - Event object
 * @param {string} event.target - Target identifier (e.g., 'worker_456', 'kanban_board')
 * @returns {string} Formatted target name
 */
const getEventTarget = (event) => {
  if (event.target?.startsWith('worker_')) {
    return event.target.replace('worker_', 'Worker ')
  }
  return event.target?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) || 'Unknown'
}

/**
 * Determines CSS class for event styling based on event type
 * Each event type gets a different colored border for visual categorization
 * 
 * @param {Object} event - Event object
 * @param {string} event.event_type - Primary event type field
 * @param {string} event.type - Fallback type field
 * @returns {string} CSS class name for border color
 */
const getEventClass = (event) => {
  const type = event.event_type || event.type
  const classes = {
    'worker_message': 'border-worker-primary',
    'pm_decision': 'border-decision-primary',
    'pm_thinking': 'border-pm-primary',
    'kanban_request': 'border-kanban-primary',
    'kanban_response': 'border-kanban-secondary',
    'task_assignment': 'border-blue-500',
    'progress_update': 'border-green-500',
    'blocker_report': 'border-red-500'
  }
  return classes[type] || 'border-gray-600'
}
</script>

<style scoped>
.event-log {
  max-height: 100%;
}

.event-entry {
  transition: all 0.2s ease;
}

.event-entry:hover {
  background-color: rgba(255, 255, 255, 0.05);
}
</style>