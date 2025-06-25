import { defineStore } from 'pinia'
import { ref } from 'vue'
import { io } from 'socket.io-client'
import { useWorkflowStore } from './workflow'
import { useEventStore } from './events'

/**
 * WebSocket store for real-time communication with Marcus server
 * 
 * Manages Socket.IO connection to the Marcus visualization server,
 * handles incoming events, and coordinates updates to the workflow
 * and event stores. Provides real-time visualization of Marcus
 * activities including worker registration, task assignments,
 * progress updates, and decision-making processes.
 * 
 * @returns {Object} WebSocket store state and actions
 * 
 * @example
 * ```javascript
 * // In a Vue component
 * import { useWebSocketStore } from '@/stores/websocket'
 * 
 * export default {
 *   setup() {
 *     const wsStore = useWebSocketStore()
 *     
 *     // Connect to server on component mount
 *     onMounted(() => {
 *       wsStore.connect()
 *     })
 *     
 *     // Clean up on unmount
 *     onUnmounted(() => {
 *       wsStore.disconnect()
 *     })
 *     
 *     return {
 *       isConnected: wsStore.isConnected,
 *       connectionError: wsStore.connectionError
 *     }
 *   }
 * }
 * ```
 */
export const useWebSocketStore = defineStore('websocket', () => {
  // State
  
  /**
   * Socket.IO client instance
   * @type {import('vue').Ref<import('socket.io-client').Socket|null>}
   */
  const socket = ref(null)
  
  /**
   * Connection status indicator
   * @type {import('vue').Ref<boolean>}
   */
  const isConnected = ref(false)
  
  /**
   * Last connection error message
   * @type {import('vue').Ref<string|null>}
   */
  const connectionError = ref(null)
  
  /**
   * Establishes WebSocket connection to the Marcus server
   * 
   * Creates a new Socket.IO connection with automatic reconnection settings
   * and sets up all event handlers for the various Marcus events.
   * 
   * @example
   * ```javascript
   * // Connect when app starts
   * const wsStore = useWebSocketStore()
   * wsStore.connect()
   * 
   * // Check connection status
   * if (wsStore.isConnected.value) {
   *   console.log('Connected to Marcus server')
   * }
   * ```
   */
  const connect = () => {
    socket.value = io('http://localhost:8080', {
      transports: ['websocket'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000
    })

    setupEventHandlers()
  }

  /**
   * Sets up all Socket.IO event handlers for Marcus communication
   * 
   * Registers handlers for connection events, conversation events, worker
   * registration, task assignments, progress updates, decisions, and system
   * metrics. Each handler updates the appropriate stores and triggers
   * visualization updates.
   * 
   * @example
   * ```javascript
   * // Called automatically by connect(), but can be used independently
   * setupEventHandlers()
   * ```
   */
  const setupEventHandlers = () => {
    const workflowStore = useWorkflowStore()
    const eventStore = useEventStore()

    socket.value.on('connect', () => {
      isConnected.value = true
      connectionError.value = null
      console.log('Connected to Marcus server')
      
      // Subscribe to events
      socket.value.emit('subscribe_conversations', {})
    })

    socket.value.on('disconnect', () => {
      isConnected.value = false
    })

    socket.value.on('connect_error', (error) => {
      connectionError.value = error.message
    })

    // Handle conversation events
    socket.value.on('conversation_event', (event) => {
      handleConversationEvent(event)
      eventStore.addEvent(event)
    })

    // Handle specific event types
    socket.value.on('worker_registration', (data) => {
      handleWorkerRegistration(data)
    })

    socket.value.on('task_assignment', (data) => {
      handleTaskAssignment(data)
    })

    socket.value.on('progress_update', (data) => {
      handleProgressUpdate(data)
    })

    socket.value.on('decision_event', (data) => {
      handleDecisionEvent(data)
    })

    socket.value.on('system_metrics', (data) => {
      handleSystemMetrics(data)
    })
  }

  // Event Handlers
  
  /**
   * Handles conversation events between Marcus and workers
   * 
   * Processes conversation events to update workflow visualization,
   * create worker nodes if they don't exist, and animate data flow
   * between nodes. Automatically determines worker roles based on
   * worker IDs and creates appropriate visual connections.
   * 
   * @param {Object} event - Conversation event data
   * @param {string} event.source - Source worker/agent ID
   * @param {string} event.target - Target worker/agent ID
   * @param {string} event.event_type - Type of conversation event
   * @param {string} event.message - Event message content
   * @param {Object} [event.metadata] - Additional event metadata
   * 
   * @example
   * ```javascript
   * // Example conversation event
   * const event = {
   *   source: 'backend-worker-123',
   *   target: 'pm-agent',
   *   event_type: 'task_update',
   *   message: 'Task 50% complete',
   *   metadata: { progress: 0.5, taskId: 'task-456' }
   * }
   * handleConversationEvent(event)
   * ```
   */
  const handleConversationEvent = (event) => {
    const workflowStore = useWorkflowStore()
    
    // Animate data flow between nodes
    if (event.source && event.target) {
      // Check if nodes exist, create worker nodes if needed
      if ((event.source.includes('backend') || event.source.includes('frontend') || event.source.includes('test') || event.source.startsWith('claude_')) && !workflowStore.nodes.find(n => n.id === event.source)) {
        // Determine worker role from ID
        let role = 'Developer'
        if (event.source.includes('backend')) role = 'Backend Developer'
        else if (event.source.includes('frontend')) role = 'Frontend Developer'
        else if (event.source.includes('test')) role = 'QA Engineer'
        
        const workerNode = workflowStore.addNode({
          type: 'worker',
          label: event.source,
          position: { 
            x: 100 + (workflowStore.workerNodes.length * 200), 
            y: 400 
          },
          data: {
            workerId: event.source,
            role: role,
            status: 'active',
            currentTask: null,
            hasGitHubContext: false
          }
        })
        
        // Connect to Marcus
        workflowStore.addEdge({
          source: workerNode.id,
          target: 'pm-agent'
        })
      }
      
      // Animate the data flow
      workflowStore.animateDataFlow(event.source, event.target, {
        type: event.event_type,
        message: event.message,
        metadata: event.metadata
      })
    }
  }

  /**
   * Handles worker registration events
   * 
   * Updates existing worker nodes with registration data including
   * name, role, skills, and status. If the worker node exists,
   * its data is updated to reflect the registered state.
   * 
   * @param {Object} data - Worker registration data
   * @param {string} data.workerId - Unique worker identifier
   * @param {string} data.name - Worker display name
   * @param {string} data.role - Worker role (e.g., 'Backend Developer')
   * @param {Array<string>} data.skills - Array of worker skills
   * 
   * @example
   * ```javascript
   * // Example worker registration data
   * const registrationData = {
   *   workerId: 'claude-backend-001',
   *   name: 'Claude Backend Developer',
   *   role: 'Backend Developer',
   *   skills: ['Node.js', 'Express', 'MongoDB', 'REST APIs']
   * }
   * handleWorkerRegistration(registrationData)
   * ```
   */
  const handleWorkerRegistration = (data) => {
    const workflowStore = useWorkflowStore()
    
    // Create or update worker node
    const existingNode = workflowStore.nodes.find(n => n.id === data.workerId)
    if (existingNode) {
      workflowStore.updateNode(data.workerId, {
        data: {
          ...existingNode.data,
          name: data.name,
          role: data.role,
          skills: data.skills,
          status: 'registered'
        }
      })
    }
  }

  /**
   * Handles task assignment events from Marcus to workers
   * 
   * Updates worker nodes with current task information and creates
   * visual animation showing task flow from Marcus to the assigned worker.
   * 
   * @param {Object} data - Task assignment data
   * @param {string} data.workerId - ID of worker receiving the task
   * @param {string} data.taskId - Unique task identifier
   * @param {string} data.taskName - Human-readable task name
   * 
   * @example
   * ```javascript
   * // Example task assignment data
   * const taskData = {
   *   workerId: 'claude-frontend-001',
   *   taskId: 'task-789',
   *   taskName: 'Implement user authentication UI'
   * }
   * handleTaskAssignment(taskData)
   * ```
   */
  const handleTaskAssignment = (data) => {
    const workflowStore = useWorkflowStore()
    
    // Update worker node with task
    workflowStore.updateNode(data.workerId, {
      data: {
        currentTask: data.taskId,
        taskName: data.taskName,
        status: 'working'
      }
    })
    
    // Create task flow visualization
    workflowStore.animateDataFlow('pm-agent', data.workerId, {
      type: 'task_assignment',
      taskId: data.taskId,
      taskName: data.taskName
    })
  }

  /**
   * Handles progress update events from workers
   * 
   * Updates worker node data with current progress percentage and
   * last update message to show real-time task progress in the visualization.
   * 
   * @param {Object} data - Progress update data
   * @param {string} data.workerId - ID of worker reporting progress
   * @param {number} data.progress - Progress percentage (0-100)
   * @param {string} data.message - Progress update message
   * 
   * @example
   * ```javascript
   * // Example progress update
   * const progressData = {
   *   workerId: 'claude-backend-001',
   *   progress: 75,
   *   message: 'API endpoints implemented, starting tests'
   * }
   * handleProgressUpdate(progressData)
   * ```
   */
  const handleProgressUpdate = (data) => {
    const workflowStore = useWorkflowStore()
    
    // Update worker progress
    const node = workflowStore.nodes.find(n => n.id === data.workerId)
    if (node) {
      workflowStore.updateNode(data.workerId, {
        data: {
          ...node.data,
          progress: data.progress,
          lastUpdate: data.message
        }
      })
    }
  }

  const handleDecisionEvent = (data) => {
    const workflowStore = useWorkflowStore()
    
    // Create decision node
    const decisionNode = workflowStore.addNode({
      type: 'decision',
      label: data.decision.substring(0, 30) + '...',
      position: { x: 400, y: 350 + (Math.random() * 100) },
      data: {
        decision: data.decision,
        rationale: data.rationale,
        confidence: data.confidence_score,
        timestamp: data.timestamp
      }
    })
    
    // Connect to Marcus
    workflowStore.addEdge({
      source: 'pm-agent',
      target: decisionNode.id
    })
    
    // Auto-remove decision nodes after some time to avoid clutter
    setTimeout(() => {
      workflowStore.removeNode(decisionNode.id)
    }, 30000)
  }

  const handleSystemMetrics = (data) => {
    const workflowStore = useWorkflowStore()
    
    // Update Marcus metrics
    workflowStore.updateNode('pm-agent', {
      data: {
        metrics: {
          decisionsToday: data.decisions_today || 0,
          avgConfidence: data.avg_confidence || 0,
          activeWorkers: data.active_workers || 0
        }
      }
    })
    
    // Update Kanban metrics
    workflowStore.updateNode('kanban-board', {
      data: {
        metrics: {
          totalTasks: data.total_tasks || 0,
          inProgress: data.tasks_in_progress || 0,
          completed: data.tasks_completed || 0
        }
      }
    })
  }

  // Outbound Event Methods
  
  /**
   * Requests decision tree data from the Marcus server
   * 
   * Sends a request to the server to retrieve detailed decision tree
   * information for a specific decision ID. Used for drilling down
   * into Marcus's decision-making process.
   * 
   * @param {string} decisionId - Unique identifier for the decision
   * 
   * @example
   * ```javascript
   * // Request decision tree when user clicks on a decision node
   * const onDecisionClick = (decisionId) => {
   *   requestDecisionTree(decisionId)
   * }
   * ```
   */
  const requestDecisionTree = (decisionId) => {
    if (socket.value && isConnected.value) {
      socket.value.emit('request_decision_tree', { decision_id: decisionId })
    }
  }

  /**
   * Requests knowledge graph data from the Marcus server
   * 
   * Sends a request to retrieve knowledge graph data with optional
   * filters for visualization. The knowledge graph shows relationships
   * between tasks, workers, and decisions in the Marcus system.
   * 
   * @param {Object} [filters={}] - Optional filters for the knowledge graph
   * @param {Array<string>} [filters.nodeTypes] - Types of nodes to include
   * @param {string} [filters.timeRange] - Time range for the data
   * @param {Array<string>} [filters.workerIds] - Specific workers to include
   * 
   * @example
   * ```javascript
   * // Request full knowledge graph
   * requestKnowledgeGraph()
   * 
   * // Request filtered knowledge graph
   * requestKnowledgeGraph({
   *   nodeTypes: ['workers', 'tasks'],
   *   timeRange: 'last_24h',
   *   workerIds: ['claude-backend-001', 'claude-frontend-001']
   * })
   * ```
   */
  const requestKnowledgeGraph = (filters = {}) => {
    if (socket.value && isConnected.value) {
      socket.value.emit('request_knowledge_graph', filters)
    }
  }

  /**
   * Disconnects from the Marcus server
   * 
   * Safely closes the Socket.IO connection and resets the connection state.
   * Should be called when the component unmounts or the app shuts down.
   * 
   * @example
   * ```javascript
   * // Disconnect when component unmounts
   * onUnmounted(() => {
   *   disconnect()
   * })
   * 
   * // Disconnect manually
   * const handleDisconnect = () => {
   *   disconnect()
   * }
   * ```
   */
  const disconnect = () => {
    if (socket.value) {
      socket.value.disconnect()
      socket.value = null
      isConnected.value = false
    }
  }

  return {
    // State
    isConnected,
    connectionError,
    
    // Actions
    connect,
    disconnect,
    requestDecisionTree,
    requestKnowledgeGraph
  }
})