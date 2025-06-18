import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useEventStore = defineStore('events', () => {
  // State
  const events = ref([])
  const maxEvents = 1000
  const filters = ref({
    showWorkerMessages: true,
    showDecisions: true,
    showKanbanUpdates: true,
    showProgressUpdates: true,
    showThinking: true
  })

  // Actions
  const addEvent = (event) => {
    events.value.unshift({
      ...event,
      id: `event-${Date.now()}-${Math.random()}`,
      timestamp: new Date(event.timestamp || Date.now())
    })
    
    // Keep only last maxEvents
    if (events.value.length > maxEvents) {
      events.value = events.value.slice(0, maxEvents)
    }
  }

  const clearEvents = () => {
    events.value = []
  }

  const toggleFilter = (filterName) => {
    filters.value[filterName] = !filters.value[filterName]
  }

  // Computed
  const filteredEvents = computed(() => {
    return events.value.filter(event => {
      const eventType = event.event_type || event.type
      
      if (!filters.value.showWorkerMessages && eventType === 'worker_message') return false
      if (!filters.value.showDecisions && eventType === 'pm_decision') return false
      if (!filters.value.showKanbanUpdates && (eventType === 'kanban_request' || eventType === 'kanban_response')) return false
      if (!filters.value.showProgressUpdates && eventType === 'progress_update') return false
      if (!filters.value.showThinking && eventType === 'pm_thinking') return false
      
      return true
    })
  })

  const recentEvents = computed(() => {
    return filteredEvents.value.slice(0, 50)
  })

  const eventStats = computed(() => {
    const stats = {
      total: events.value.length,
      byType: {},
      lastHour: 0,
      lastMinute: 0
    }
    
    const now = Date.now()
    const oneHourAgo = now - (60 * 60 * 1000)
    const oneMinuteAgo = now - (60 * 1000)
    
    events.value.forEach(event => {
      const eventType = event.event_type || event.type || 'unknown'
      stats.byType[eventType] = (stats.byType[eventType] || 0) + 1
      
      const eventTime = event.timestamp.getTime()
      if (eventTime > oneHourAgo) stats.lastHour++
      if (eventTime > oneMinuteAgo) stats.lastMinute++
    })
    
    return stats
  })

  return {
    // State
    events,
    filters,
    
    // Computed
    filteredEvents,
    recentEvents,
    eventStats,
    
    // Actions
    addEvent,
    clearEvents,
    toggleFilter
  }
})