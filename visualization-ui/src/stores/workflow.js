import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { MarkerType } from '@vue-flow/core'

export const useWorkflowStore = defineStore('workflow', () => {
  // State
  const nodes = ref([])
  const edges = ref([])
  const selectedNode = ref(null)
  const executionState = ref({
    isRunning: false,
    isPaused: false,
    currentStep: null,
    activeConnections: []
  })

  // Initial nodes setup
  const initializeNodes = () => {
    nodes.value = [
      {
        id: 'pm-agent',
        type: 'pm-agent',
        position: { x: 400, y: 200 },
        data: { 
          label: 'PM Agent',
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

  // Computed
  const activeNodes = computed(() => 
    nodes.value.filter(n => n.data.status === 'active' || n.data.status === 'working')
  )

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