import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

/**
 * Events store for managing real-time event data in the Marcus visualization
 * 
 * This Pinia store handles the collection, filtering, and display of various event types
 * from the Marcus system including worker messages, decisions, Kanban updates,
 * progress updates, and thinking processes. It provides reactive state management
 * for the event stream visualization.
 * 
 * @returns {Object} Event store state, computed properties, and actions
 * 
 * @example
 * ```javascript
 * // In a Vue component
 * import { useEventStore } from '@/stores/events'
 * 
 * export default {
 *   setup() {
 *     const eventStore = useEventStore()
 *     
 *     // Add a new event
 *     eventStore.addEvent({
 *       event_type: 'worker_message',
 *       message: 'Task completed successfully',
 *       timestamp: Date.now()
 *     })
 *     
 *     // Get filtered events
 *     const events = eventStore.filteredEvents
 *     
 *     return { events }
 *   }
 * }
 * ```
 */
export const useEventStore = defineStore('events', () => {
  // State
  
  /**
   * Reactive array containing all events from the Marcus system
   * @type {import('vue').Ref<Array<Object>>}
   */
  const events = ref([])
  
  /**
   * Maximum number of events to keep in memory to prevent memory overflow
   * @type {number}
   */
  const maxEvents = 1000
  
  /**
   * Filter settings for controlling which event types are displayed
   * @type {import('vue').Ref<Object>}
   * @property {boolean} showWorkerMessages - Show worker communication events
   * @property {boolean} showDecisions - Show Marcus decision events
   * @property {boolean} showKanbanUpdates - Show Kanban board update events
   * @property {boolean} showProgressUpdates - Show task progress events
   * @property {boolean} showThinking - Show Marcus thinking process events
   */
  const filters = ref({
    showWorkerMessages: true,
    showDecisions: true,
    showKanbanUpdates: true,
    showProgressUpdates: true,
    showThinking: true
  })

  // Actions
  
  /**
   * Adds a new event to the events collection
   * 
   * Prepends the event to the beginning of the events array with auto-generated
   * ID and timestamp if not provided. Maintains the maximum event limit by
   * removing oldest events when the limit is exceeded.
   * 
   * @param {Object} event - The event object to add
   * @param {string} [event.event_type] - Type of event (worker_message, pm_decision, etc.)
   * @param {string} [event.message] - Event message content
   * @param {number|Date} [event.timestamp] - Event timestamp, defaults to current time
   * @param {Object} [event.metadata] - Additional event metadata
   * 
   * @example
   * ```javascript
   * // Add a worker message event
   * addEvent({
   *   event_type: 'worker_message',
   *   message: 'Starting task execution',
   *   metadata: { workerId: 'worker-123', taskId: 'task-456' }
   * })
   * 
   * // Add a PM decision event
   * addEvent({
   *   event_type: 'pm_decision',
   *   message: 'Assigned task to most suitable worker',
   *   timestamp: Date.now(),
   *   metadata: { confidence: 0.85, reasoning: 'Worker has relevant skills' }
   * })
   * ```
   */
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

  /**
   * Clears all events from the collection
   * 
   * Removes all events from the events array, effectively resetting
   * the event history. Useful for cleaning up the display or starting fresh.
   * 
   * @example
   * ```javascript
   * // Clear all events when resetting the view
   * const handleReset = () => {
   *   clearEvents()
   * }
   * ```
   */
  const clearEvents = () => {
    events.value = []
  }

  /**
   * Toggles the visibility of a specific event type filter
   * 
   * Flips the boolean state of the specified filter, controlling whether
   * events of that type are displayed in the filtered view.
   * 
   * @param {string} filterName - The name of the filter to toggle
   *   Valid values: 'showWorkerMessages', 'showDecisions', 'showKanbanUpdates',
   *   'showProgressUpdates', 'showThinking'
   * 
   * @example
   * ```javascript
   * // Toggle worker messages visibility
   * toggleFilter('showWorkerMessages')
   * 
   * // Toggle PM decisions visibility
   * toggleFilter('showDecisions')
   * 
   * // In a template with checkboxes
   * <input type="checkbox" 
   *        :checked="filters.showWorkerMessages" 
   *        @change="toggleFilter('showWorkerMessages')" />
   * ```
   */
  const toggleFilter = (filterName) => {
    filters.value[filterName] = !filters.value[filterName]
  }

  // Computed Properties
  
  /**
   * Events filtered based on current filter settings
   * 
   * Returns a reactive computed array of events that match the current
   * filter criteria. Events are filtered based on their event_type or type
   * property against the corresponding filter settings.
   * 
   * @returns {import('vue').ComputedRef<Array<Object>>} Filtered array of events
   * 
   * @example
   * ```javascript
   * // Use in a component to display filtered events
   * const events = filteredEvents.value
   * 
   * // Reactive - automatically updates when filters change
   * watch(filteredEvents, (newEvents) => {
   *   console.log(`Displaying ${newEvents.length} events`)
   * })
   * ```
   */
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

  /**
   * Most recent filtered events for display optimization
   * 
   * Returns only the first 50 events from the filtered events array
   * to optimize rendering performance in the UI while still showing
   * the most relevant recent activity.
   * 
   * @returns {import('vue').ComputedRef<Array<Object>>} Array of up to 50 recent events
   * 
   * @example
   * ```javascript
   * // Use for displaying a limited event feed
   * const events = recentEvents.value
   * 
   * // In a template
   * <div v-for="event in recentEvents" :key="event.id">
   *   {{ event.message }}
   * </div>
   * ```
   */
  const recentEvents = computed(() => {
    return filteredEvents.value.slice(0, 50)
  })

  /**
   * Computed statistics about the events collection
   * 
   * Provides real-time analytics about the events including total count,
   * breakdown by event type, and time-based activity metrics for the
   * last hour and minute.
   * 
   * @returns {import('vue').ComputedRef<Object>} Statistics object
   * @returns {number} returns.total - Total number of events
   * @returns {Object} returns.byType - Count of events by type
   * @returns {number} returns.lastHour - Events in the last hour
   * @returns {number} returns.lastMinute - Events in the last minute
   * 
   * @example
   * ```javascript
   * // Use for displaying event analytics
   * const stats = eventStats.value
   * console.log(`Total events: ${stats.total}`)
   * console.log(`Worker messages: ${stats.byType.worker_message || 0}`)
   * console.log(`Activity last hour: ${stats.lastHour}`)
   * 
   * // In a template for dashboard metrics
   * <div>
   *   <p>Total: {{ eventStats.total }}</p>
   *   <p>Last Hour: {{ eventStats.lastHour }}</p>
   *   <p>Last Minute: {{ eventStats.lastMinute }}</p>
   * </div>
   * ```
   */
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