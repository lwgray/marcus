<template>
  <div class="filter-panel">
    <h3 class="text-sm font-medium text-gray-400 mb-3">Event Filters</h3>
    
    <div class="space-y-2">
      <label 
        v-for="(value, key) in filters" 
        :key="key"
        class="flex items-center gap-2 cursor-pointer hover:text-gray-300"
      >
        <input
          type="checkbox"
          :checked="value"
          @change="eventStore.toggleFilter(key)"
          class="w-4 h-4 rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-blue-500 focus:ring-offset-0"
        />
        <span class="text-sm">{{ getFilterLabel(key) }}</span>
      </label>
    </div>
    
    <div class="mt-4 pt-4 border-t border-dark-border">
      <h4 class="text-xs font-medium text-gray-500 mb-2">Event Stats</h4>
      <div class="space-y-1 text-xs">
        <div class="flex justify-between">
          <span class="text-gray-500">Total Events:</span>
          <span>{{ eventStats.total }}</span>
        </div>
        <div class="flex justify-between">
          <span class="text-gray-500">Last Minute:</span>
          <span>{{ eventStats.lastMinute }}</span>
        </div>
        <div class="flex justify-between">
          <span class="text-gray-500">Last Hour:</span>
          <span>{{ eventStats.lastHour }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { storeToRefs } from 'pinia'
import { useEventStore } from '@/stores/events'

const eventStore = useEventStore()
const { filters, eventStats } = storeToRefs(eventStore)

const getFilterLabel = (key) => {
  const labels = {
    showWorkerMessages: 'Worker Messages',
    showDecisions: 'PM Decisions',
    showKanbanUpdates: 'Kanban Updates',
    showProgressUpdates: 'Progress Updates',
    showThinking: 'PM Thinking'
  }
  return labels[key] || key
}
</script>