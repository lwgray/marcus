import { ref, computed } from 'vue'
import { useVueFlow } from '@vue-flow/core'
import { useWorkflowStore } from '@/stores/workflow'

/**
 * Canvas operations composable for Vue Flow workflow visualization
 * 
 * Provides functionality for managing node and edge operations on the workflow canvas,
 * including drag-and-drop operations, auto-layout, connections, and visual highlighting.
 * 
 * @returns {Object} Canvas operation functions and utilities
 * 
 * @example
 * ```javascript
 * // In a Vue component
 * import { useCanvasOperations } from '@/composables/useCanvasOperations'
 * 
 * export default {
 *   setup() {
 *     const {
 *       onDrop,
 *       onDragOver,
 *       autoLayout,
 *       createConnection,
 *       highlightPath,
 *       clearHighlights
 *     } = useCanvasOperations()
 *     
 *     return {
 *       onDrop,
 *       onDragOver,
 *       autoLayout,
 *       createConnection,
 *       highlightPath,
 *       clearHighlights
 *     }
 *   }
 * }
 * ```
 */
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

  /**
   * Handles drop events for adding new nodes to the canvas
   * 
   * Processes drag-and-drop operations by extracting node data from the transfer object,
   * calculating the drop position relative to the canvas, and creating a new node
   * with unique ID and proper positioning.
   * 
   * @param {DragEvent} event - The drop event containing the dragged node data
   * @param {DataTransfer} event.dataTransfer - Contains the node data in 'application/vueflow' format
   * @param {number} event.clientX - X coordinate of the drop position
   * @param {number} event.clientY - Y coordinate of the drop position
   * 
   * @example
   * ```javascript
   * // In a template
   * <div @drop="onDrop" @dragover="onDragOver">
   *   <!-- Canvas content -->
   * </div>
   * 
   * // The dragged data should be in format:
   * const nodeData = {
   *   type: 'worker',
   *   label: 'Backend Developer',
   *   data: { role: 'backend', skills: ['Node.js', 'Express'] }
   * }
   * ```
   */
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

  /**
   * Handles drag over events to enable dropping
   * 
   * Prevents the default browser behavior and sets the visual feedback
   * for the drag operation to indicate that dropping is allowed.
   * 
   * @param {DragEvent} event - The dragover event
   * @param {DataTransfer} event.dataTransfer - Data transfer object to set drop effect
   * 
   * @example
   * ```javascript
   * // In a template
   * <div @dragover="onDragOver">
   *   <!-- Canvas content -->
   * </div>
   * ```
   */
  const onDragOver = (event) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'move'
  }

  /**
   * Automatically arranges nodes in a circular layout
   * 
   * Implements a simple force-directed layout algorithm that positions all nodes
   * in a circular pattern around a center point. Useful for organizing cluttered
   * workflows or providing a standard starting layout.
   * 
   * @example
   * ```javascript
   * // Trigger auto-layout after adding multiple nodes
   * autoLayout()
   * 
   * // Use in a button click handler
   * const handleAutoLayout = () => {
   *   autoLayout()
   * }
   * ```
   */
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

  /**
   * Creates a connection between two nodes
   * 
   * Establishes a directed edge connection from a source node to a target node.
   * This is useful for programmatically creating connections in the workflow
   * without user interaction.
   * 
   * @param {string} sourceId - The ID of the source node
   * @param {string} targetId - The ID of the target node
   * 
   * @example
   * ```javascript
   * // Connect a worker to the PM agent
   * createConnection('worker-123', 'pm-agent')
   * 
   * // Connect PM agent to Kanban board
   * createConnection('pm-agent', 'kanban-board')
   * ```
   */
  const createConnection = (sourceId, targetId) => {
    onConnect({
      source: sourceId,
      target: targetId,
      sourceHandle: null,
      targetHandle: null
    })
  }

  /**
   * Highlights the path between two nodes with visual animation
   * 
   * Applies visual styling to the edge connecting two nodes to indicate
   * active data flow or communication. The edge becomes animated with
   * a blue color and increased stroke width.
   * 
   * @param {string} sourceId - The ID of the source node
   * @param {string} targetId - The ID of the target node
   * 
   * @example
   * ```javascript
   * // Highlight communication from worker to PM agent
   * highlightPath('worker-123', 'pm-agent')
   * 
   * // Highlight task assignment flow
   * highlightPath('pm-agent', 'worker-456')
   * ```
   */
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

  /**
   * Clears all visual highlights from edges
   * 
   * Resets all edges to their default styling by removing animation
   * and restoring original stroke color and width. Used to clean up
   * the visual state after highlighting operations.
   * 
   * @example
   * ```javascript
   * // Clear all highlights after a delay
   * setTimeout(() => {
   *   clearHighlights()
   * }, 3000)
   * 
   * // Clear highlights when switching views
   * const onViewChange = () => {
   *   clearHighlights()
   * }
   * ```
   */
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