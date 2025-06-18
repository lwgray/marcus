import { ref, computed } from 'vue'
import { useVueFlow } from '@vue-flow/core'
import { useWorkflowStore } from '@/stores/workflow'

export function useCanvasOperations() {
  const workflowStore = useWorkflowStore()
  const { 
    getNodes, 
    getEdges, 
    project, 
    onConnect, 
    addNodes, 
    removeNodes,
    updateNode,
    fitView
  } = useVueFlow()

  // Handle drop events for adding nodes
  const onDrop = (event) => {
    event.preventDefault()

    const type = event.dataTransfer?.getData('application/vueflow')
    
    if (!type) return

    const nodeData = JSON.parse(type)
    const position = project({ 
      x: event.clientX, 
      y: event.clientY 
    })

    const newNode = {
      id: `${nodeData.type}-${Date.now()}`,
      type: nodeData.type,
      position,
      data: { 
        label: nodeData.label,
        ...nodeData.data 
      }
    }

    addNodes([newNode])
  }

  const onDragOver = (event) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'move'
  }

  // Auto-layout nodes
  const autoLayout = () => {
    const nodes = getNodes.value
    const edges = getEdges.value
    
    // Simple force-directed layout
    const centerX = 400
    const centerY = 300
    const radius = 200
    
    nodes.forEach((node, index) => {
      const angle = (index / nodes.length) * 2 * Math.PI
      node.position = {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle)
      }
    })
    
    fitView()
  }

  // Create connection between nodes
  const createConnection = (sourceId, targetId) => {
    onConnect({
      source: sourceId,
      target: targetId,
      sourceHandle: null,
      targetHandle: null
    })
  }

  // Highlight path between nodes
  const highlightPath = (sourceId, targetId) => {
    const edges = getEdges.value
    
    edges.forEach(edge => {
      if (edge.source === sourceId && edge.target === targetId) {
        edge.animated = true
        edge.style = {
          ...edge.style,
          stroke: '#3498db',
          strokeWidth: 3
        }
      }
    })
  }

  // Clear all highlights
  const clearHighlights = () => {
    const edges = getEdges.value
    
    edges.forEach(edge => {
      edge.animated = false
      edge.style = {
        ...edge.style,
        stroke: '#666',
        strokeWidth: 2
      }
    })
  }

  return {
    onDrop,
    onDragOver,
    autoLayout,
    createConnection,
    highlightPath,
    clearHighlights
  }
}