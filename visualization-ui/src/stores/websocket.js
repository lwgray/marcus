import { defineStore } from 'pinia'
import { ref } from 'vue'
import { io } from 'socket.io-client'
import { useWorkflowStore } from './workflow'
import { useEventStore } from './events'

export const useWebSocketStore = defineStore('websocket', () => {
  // State
  const socket = ref(null)
  const isConnected = ref(false)
  const connectionError = ref(null)
  
  // Connect to server
  const connect = () => {
    socket.value = io('http://localhost:8080', {
      transports: ['websocket'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000
    })

    setupEventHandlers()
  }

  // Setup event handlers
  const setupEventHandlers = () => {
    const workflowStore = useWorkflowStore()
    const eventStore = useEventStore()

    socket.value.on('connect', () => {
      isConnected.value = true
      connectionError.value = null
      console.log('Connected to PM Agent server')
      
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

  // Event handlers
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
        
        // Connect to PM Agent
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
    
    // Connect to PM Agent
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
    
    // Update PM Agent metrics
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

  // Send events
  const requestDecisionTree = (decisionId) => {
    if (socket.value && isConnected.value) {
      socket.value.emit('request_decision_tree', { decision_id: decisionId })
    }
  }

  const requestKnowledgeGraph = (filters = {}) => {
    if (socket.value && isConnected.value) {
      socket.value.emit('request_knowledge_graph', filters)
    }
  }

  // Disconnect
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