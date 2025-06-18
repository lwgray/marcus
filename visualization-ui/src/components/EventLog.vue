<template>
  <div class="event-log flex flex-col h-full">
    <div class="flex items-center justify-between p-3 border-b border-dark-border">
      <h3 class="text-sm font-medium">Event Log</h3>
      <button
        @click="eventStore.clearEvents"
        class="text-xs text-gray-500 hover:text-gray-300 transition-colors"
      >
        Clear
      </button>
    </div>
    
    <div class="flex-1 overflow-y-auto p-3 space-y-1">
      <div
        v-for="event in recentEvents"
        :key="event.id"
        class="event-entry text-xs p-2 rounded border-l-2 bg-dark-surface/50"
        :class="getEventClass(event)"
      >
        <div class="flex items-start gap-2">
          <span class="text-gray-600 flex-shrink-0">{{ formatTime(event.timestamp) }}</span>
          <div class="flex-1">
            <span class="font-medium">{{ getEventSource(event) }}</span>
            <span class="mx-1 text-gray-600">→</span>
            <span class="font-medium">{{ getEventTarget(event) }}</span>
            <div class="text-gray-400 mt-0.5">{{ event.message }}</div>
          </div>
        </div>
      </div>
      
      <div v-if="recentEvents.length === 0" class="text-center text-gray-600 py-8">
        No events yet
      </div>
    </div>
  </div>
</template>

<script setup>
import { storeToRefs } from 'pinia'
import { useEventStore } from '@/stores/events'

const eventStore = useEventStore()
const { recentEvents } = storeToRefs(eventStore)

const formatTime = (timestamp) => {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('en-US', { 
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const getEventSource = (event) => {
  if (event.source?.startsWith('worker_')) {
    return event.source.replace('worker_', 'Worker ')
  }
  return event.source?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) || 'Unknown'
}

const getEventTarget = (event) => {
  if (event.target?.startsWith('worker_')) {
    return event.target.replace('worker_', 'Worker ')
  }
  return event.target?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) || 'Unknown'
}

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