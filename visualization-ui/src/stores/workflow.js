import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { MarkerType } from '@vue-flow/core'

/**
 * Workflow store for managing the Marcus workflow visualization
 * 
 * This Pinia store manages the state of the workflow visualization including
 * nodes (Marcus, workers, Kanban board, knowledge base), edges (connections),
 * execution state, and various operations like adding/updating nodes, 
 * animating data flow, and managing the visual workflow canvas.
 * 
 * @returns {Object} Workflow store state, computed properties, and actions
 * 
 * @example
 * ```javascript
 * // In a Vue component
 * import { useWorkflowStore } from '@/stores/workflow'
 * 
 * export default {
 *   setup() {
 *     const workflowStore = useWorkflowStore()
 *     
 *     // Add a new worker node
 *     const newWorker = workflowStore.addNode({
 *       type: 'worker',
 *       label: 'Backend Developer',
 *       position: { x: 200, y: 400 },
 *       data: { role: 'Backend Developer', skills: ['Node.js'] }
 *     })
 *     
 *     // Animate data flow
 *     workflowStore.animateDataFlow('pm-agent', newWorker.id, {
 *       type: 'task_assignment',
 *       message: 'New task assigned'
 *     })
 *     
 *     return {
 *       nodes: workflowStore.nodes,
 *       edges: workflowStore.edges
 *     }
 *   }
 * }
 * ```
 */
export const useWorkflowStore = defineStore('workflow', () => {
  // State
  
  /**
   * Reactive array of workflow nodes (Marcus, workers, services)
   * @type {import('vue').Ref<Array<Object>>}
   */
  const nodes = ref([])
  
  /**
   * Reactive array of workflow edges (connections between nodes)
   * @type {import('vue').Ref<Array<Object>>}
   */
  const edges = ref([])
  
  /**
   * Currently selected node for detailed view
   * @type {import('vue').Ref<Object|null>}
   */
  const selectedNode = ref(null)
  
  /**
   * Execution state tracking for workflow animations and status
   * @type {import('vue').Ref<Object>}
   * @property {boolean} isRunning - Whether workflow execution is active
   * @property {boolean} isPaused - Whether execution is paused
   * @property {string|null} currentStep - Current execution step identifier
   * @property {Array<Object>} activeConnections - Currently animated connections
   */
  const executionState = ref({
    isRunning: false,
    isPaused: false,
    currentStep: null,
    activeConnections: []
  })

  /**
   * Initializes the workflow with default nodes and connections
   * 
   * Sets up the base workflow structure with Marcus, Kanban Board,
   * and Knowledge Base nodes, along with their initial connections.
   * This provides the foundation for the workflow visualization.
   * 
   * @example
   * ```javascript
   * // Called automatically when store is created, but can be used to reset
   * initializeNodes()
   * ```
   */
  const initializeNodes = () => {
    nodes.value = [
      {
        id: 'pm-agent',
        type: 'pm-agent',
        position: { x: 400, y: 200 },
        data: { 
          label: 'Marcus',
          status: 'idle',
          metrics: {
            decisionsToday: 0,
            avgConfidence: 0,
            activeWorkers: 0
          }
        }
      },
      {
        id: 'kanban-board',
        type: 'kanban',
        position: { x: 700, y: 100 },
        data: { 
          label: 'Kanban Board',
          status: 'connected',
          metrics: {
            totalTasks: 0,
            inProgress: 0,
            completed: 0
          }
        }
      },
      {
        id: 'knowledge-base',
        type: 'knowledge',
        position: { x: 700, y: 300 },
        data: { 
          label: 'Knowledge Base',
          status: 'synced',
          metrics: {
            totalNodes: 0,
            relationships: 0
          }
        }
      }
    ]
    
    // Initialize edges (connections)
    edges.value = [
      {
        id: 'pm-kanban',
        source: 'pm-agent',
        target: 'kanban-board',
        type: 'smoothstep',
        animated: false,
        style: { stroke: '#555', strokeWidth: 2 }
      },
      {
        id: 'pm-knowledge',
        source: 'pm-agent',
        target: 'knowledge-base',
        type: 'smoothstep',
        animated: false,
        style: { stroke: '#555', strokeWidth: 2 }
      }
    ]
  }

  // Actions
  
  /**
   * Adds a new node to the workflow
   * 
   * Creates a new node with auto-generated ID, default position, and
   * initializing status. The node is added to the nodes array and
   * can represent workers, services, or other workflow components.
   * 
   * @param {Object} node - Node configuration object
   * @param {string} node.type - Type of node (worker, service, etc.)
   * @param {string} node.label - Display label for the node
   * @param {Object} [node.position] - Node position {x, y}, defaults to {100, 100}
   * @param {Object} [node.data] - Additional node data
   * 
   * @returns {Object} The created node object with generated ID
   * 
   * @example
   * ```javascript
   * // Add a worker node
   * const worker = addNode({
   *   type: 'worker',
   *   label: 'Frontend Developer',
   *   position: { x: 300, y: 400 },
   *   data: {
   *     role: 'Frontend Developer',
   *     skills: ['React', 'Vue.js', 'CSS'],
   *     status: 'available'
   *   }
   * })
   * 
   * // Add a service node
   * const service = addNode({
   *   type: 'service',
   *   label: 'Database',
   *   data: { connectionStatus: 'connected' }
   * })
   * ```
   */
  const addNode = (node) => {
    const newNode = {
      id: `${node.type}-${Date.now()}`,
      type: node.type,
      position: node.position || { x: 100, y: 100 },
      data: {
        label: node.label,
        status: 'initializing',
        ...node.data
      }
    }
    nodes.value.push(newNode)
    return newNode
  }

  /**
   * Updates an existing node's properties
   * 
   * Merges the provided updates with the existing node data,
   * preserving existing properties while updating specified ones.
   * Particularly useful for updating node status, progress, or metadata.
   * 
   * @param {string} nodeId - ID of the node to update
   * @param {Object} updates - Updates to apply to the node
   * @param {Object} [updates.data] - Data updates (merged with existing data)
   * @param {Object} [updates.position] - Position updates
   * @param {string} [updates.label] - Label update
   * 
   * @example
   * ```javascript
   * // Update worker status and progress
   * updateNode('worker-123', {
   *   data: {
   *     status: 'working',
   *     progress: 50,
   *     currentTask: 'Implementing authentication'
   *   }
   * })
   * 
   * // Update node position
   * updateNode('pm-agent', {
   *   position: { x: 500, y: 300 }
   * })
   * 
   * // Update multiple properties
   * updateNode('kanban-board', {
   *   label: 'Kanban Board (Updated)',
   *   data: {
   *     status: 'syncing',
   *     lastSync: new Date().toISOString()
   *   }
   * })
   * ```
   */
  const updateNode = (nodeId, updates) => {
    const nodeIndex = nodes.value.findIndex(n => n.id === nodeId)
    if (nodeIndex !== -1) {
      nodes.value[nodeIndex] = {
        ...nodes.value[nodeIndex],
        ...updates,
        data: {
          ...nodes.value[nodeIndex].data,
          ...(updates.data || {})
        }
      }
    }
  }

  const removeNode = (nodeId) => {
    nodes.value = nodes.value.filter(n => n.id !== nodeId)
    edges.value = edges.value.filter(e => e.source !== nodeId && e.target !== nodeId)
  }

  const addEdge = (connection) => {
    const newEdge = {
      id: `${connection.source}-${connection.target}-${Date.now()}`,
      source: connection.source,
      target: connection.target,
      type: 'smoothstep',
      animated: false,
      markerEnd: MarkerType.ArrowClosed,
      style: {
        stroke: '#666',
        strokeWidth: 2
      },
      data: {
        messageCount: 0,
        lastMessage: null
      }
    }
    edges.value.push(newEdge)
    return newEdge
  }

  const updateEdge = (edgeId, updates) => {
    const edgeIndex = edges.value.findIndex(e => e.id === edgeId)
    if (edgeIndex !== -1) {
      edges.value[edgeIndex] = {
        ...edges.value[edgeIndex],
        ...updates
      }
    }
  }

  /**
   * Animates data flow between two nodes
   * 
   * Creates a visual animation effect on the edge connecting two nodes
   * to represent data flow, communication, or task assignment. The edge
   * is temporarily highlighted with color coding based on the data type
   * and automatically returns to normal styling after a delay.
   * 
   * @param {string} sourceId - ID of the source node
   * @param {string} targetId - ID of the target node  
   * @param {Object} data - Data being transmitted
   * @param {string} data.type - Type of data flow (request, response, decision, error, update)
   * @param {string} [data.message] - Message content
   * @param {Object} [data.metadata] - Additional metadata
   * 
   * @example
   * ```javascript
   * // Animate task assignment from Marcus to worker
   * animateDataFlow('pm-agent', 'worker-123', {
   *   type: 'request',
   *   message: 'New task assigned: Implement user login',
   *   metadata: { taskId: 'task-456', priority: 'high' }
   * })
   * 
   * // Animate progress update from worker to Marcus
   * animateDataFlow('worker-123', 'pm-agent', {
   *   type: 'update',
   *   message: 'Task 75% complete',
   *   metadata: { progress: 75, estimatedCompletion: '2h' }
   * })
   * 
   * // Animate error reporting
   * animateDataFlow('worker-456', 'pm-agent', {
   *   type: 'error',
   *   message: 'Database connection failed',
   *   metadata: { errorCode: 'DB_CONN_ERROR' }
   * })
   * ```
   */
  const animateDataFlow = (sourceId, targetId, data) => {
    const edge = edges.value.find(e => 
      e.source === sourceId && e.target === targetId
    )
    
    if (edge) {
      // Update edge to show animation
      updateEdge(edge.id, {
        animated: true,
        style: {
          ...edge.style,
          stroke: getDataFlowColor(data.type),
          strokeWidth: 3
        },
        data: {
          ...edge.data,
          messageCount: edge.data.messageCount + 1,
          lastMessage: data
        }
      })

      // Add to active connections
      executionState.value.activeConnections.push({
        edgeId: edge.id,
        timestamp: Date.now(),
        data
      })

      // Remove animation after delay
      setTimeout(() => {
        updateEdge(edge.id, {
          animated: false,
          style: {
            ...edge.style,
            strokeWidth: 2
          }
        })
        
        // Remove from active connections
        executionState.value.activeConnections = executionState.value.activeConnections
          .filter(conn => conn.edgeId !== edge.id)
      }, 2000)
    }
  }

  /**
   * Determines the color for data flow animations based on event type
   * 
   * Maps different types of data flow events to appropriate colors
   * for visual distinction in the workflow animation system.
   * 
   * @param {string} type - Type of data flow event
   * @returns {string} Hex color code for the event type
   * 
   * @example
   * ```javascript
   * // Get color for different event types
   * const requestColor = getDataFlowColor('request')    // '#3498db' (blue)
   * const responseColor = getDataFlowColor('response')  // '#2ecc71' (green) 
   * const errorColor = getDataFlowColor('error')        // '#e74c3c' (red)
   * const decisionColor = getDataFlowColor('decision')  // '#f39c12' (orange)
   * const updateColor = getDataFlowColor('update')      // '#9b59b6' (purple)
   * const defaultColor = getDataFlowColor('unknown')    // '#666' (gray)
   * ```
   */
  const getDataFlowColor = (type) => {
    const colors = {
      request: '#3498db',
      response: '#2ecc71',
      decision: '#f39c12',
      error: '#e74c3c',
      update: '#9b59b6'
    }
    return colors[type] || '#666'
  }

  const setSelectedNode = (node) => {
    selectedNode.value = node
  }

  const clearCanvas = () => {
    nodes.value = []
    edges.value = []
    selectedNode.value = null
    executionState.value = {
      isRunning: false,
      isPaused: false,
      currentStep: null,
      activeConnections: []
    }
    // Re-initialize with base nodes
    initializeNodes()
  }

  const startExecution = () => {
    executionState.value.isRunning = true
    executionState.value.isPaused = false
  }

  const pauseExecution = () => {
    executionState.value.isPaused = true
  }

  const stopExecution = () => {
    executionState.value.isRunning = false
    executionState.value.isPaused = false
    executionState.value.currentStep = null
    executionState.value.activeConnections = []
  }

  // Computed Properties
  
  /**
   * Computed array of active nodes in the workflow
   * 
   * Filters nodes to show only those with 'active' or 'working' status,
   * useful for displaying current activity indicators and metrics.
   * 
   * @returns {import('vue').ComputedRef<Array<Object>>} Array of active nodes
   * 
   * @example
   * ```javascript
   * // Use in a component to show active workers
   * const activeWorkers = activeNodes.value
   * console.log(`${activeWorkers.length} workers currently active`)
   * 
   * // In a template for status display
   * <div>Active Workers: {{ activeNodes.length }}</div>
   * ```
   */
  const activeNodes = computed(() => 
    nodes.value.filter(n => n.data.status === 'active' || n.data.status === 'working')
  )

  /**
   * Computed array of worker nodes specifically
   * 
   * Filters nodes to show only worker-type nodes, excluding services
   * and system components. Useful for worker-specific operations and displays.
   * 
   * @returns {import('vue').ComputedRef<Array<Object>>} Array of worker nodes
   * 
   * @example
   * ```javascript
   * // Get all worker nodes for assignment logic
   * const availableWorkers = workerNodes.value.filter(w => 
   *   w.data.status === 'available'
   * )
   * 
   * // Display worker count in UI
   * <div>Total Workers: {{ workerNodes.length }}</div>
   * 
   * // Iterate through workers in template
   * <div v-for="worker in workerNodes" :key="worker.id">
   *   {{ worker.data.role }}: {{ worker.data.status }}
   * </div>
   * ```
   */
  const workerNodes = computed(() => 
    nodes.value.filter(n => n.type === 'worker')
  )

  // Initialize on store creation
  console.log('Initializing workflow store...')
  initializeNodes()
  console.log('Initial nodes:', nodes.value)

  return {
    // State
    nodes,
    edges,
    selectedNode,
    executionState,
    
    // Computed
    activeNodes,
    workerNodes,
    
    // Actions
    addNode,
    updateNode,
    removeNode,
    addEdge,
    updateEdge,
    animateDataFlow,
    setSelectedNode,
    clearCanvas,
    startExecution,
    pauseExecution,
    stopExecution
  }
})