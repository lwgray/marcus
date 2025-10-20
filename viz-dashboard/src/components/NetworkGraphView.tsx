import { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { useVisualizationStore } from '../store/visualizationStore';
import { Task, TaskStatus } from '../data/mockDataGenerator';
import { getTaskStateAtTime } from '../utils/timelineUtils';
import './NetworkGraphView.css';

interface GraphNode extends d3.SimulationNodeDatum {
  id: string;
  task: Task;
  status: TaskStatus;
  progress: number;
  isActive: boolean;
}

interface GraphLink extends d3.SimulationLinkDatum<GraphNode> {
  source: string | GraphNode;
  target: string | GraphNode;
}

const NetworkGraphView = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  const simulationRef = useRef<d3.Simulation<GraphNode, GraphLink> | null>(null);
  const nodesRef = useRef<GraphNode[]>([]);

  const tasks = useVisualizationStore((state) => state.getVisibleTasks());
  const currentTime = useVisualizationStore((state) => state.currentTime);
  const selectTask = useVisualizationStore((state) => state.selectTask);
  const selectedTaskId = useVisualizationStore((state) => state.selectedTaskId);

  // Build graph structure once when tasks change
  useEffect(() => {
    if (!svgRef.current) return;

    // Clear previous
    d3.select(svgRef.current).selectAll('*').remove();

    const width = svgRef.current.clientWidth;
    const height = svgRef.current.clientHeight;

    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height);

    // Create container for zoom
    const g = svg.append('g');

    // Prepare static data
    const startTime = new Date(useVisualizationStore.getState().data.metadata.start_time).getTime();
    const currentAbsTime = startTime + currentTime;

    const nodes: GraphNode[] = tasks.map(task => {
      const state = getTaskStateAtTime(task, currentAbsTime);
      return {
        id: task.id,
        task,
        status: state.status,
        progress: state.progress,
        isActive: state.isActive,
      };
    });

    nodesRef.current = nodes;

    const links: GraphLink[] = [];
    tasks.forEach(task => {
      task.dependencies.forEach(depId => {
        if (nodes.find(n => n.id === depId)) {
          links.push({
            source: depId,
            target: task.id,
          });
        }
      });
    });

    // Color scale
    const statusColor = (status: TaskStatus, isActive: boolean) => {
      if (isActive) return '#3b82f6'; // Blue for active
      switch (status) {
        case TaskStatus.TODO: return '#64748b'; // Gray
        case TaskStatus.IN_PROGRESS: return '#3b82f6'; // Blue
        case TaskStatus.DONE: return '#10b981'; // Green
        case TaskStatus.BLOCKED: return '#ef4444'; // Red
        default: return '#64748b';
      }
    };

    // Calculate hierarchical layout based on dependencies
    // This prevents line overlaps by organizing tasks in layers
    const calculateDepth = (nodeId: string, depthMap: Map<string, number>): number => {
      if (depthMap.has(nodeId)) {
        return depthMap.get(nodeId)!;
      }

      const node = nodes.find(n => n.id === nodeId);
      if (!node || node.task.dependencies.length === 0) {
        depthMap.set(nodeId, 0);
        return 0;
      }

      const maxDepDep = Math.max(
        ...node.task.dependencies.map(depId => calculateDepth(depId, depthMap))
      );
      const depth = maxDepDep + 1;
      depthMap.set(nodeId, depth);
      return depth;
    };

    const depthMap = new Map<string, number>();
    nodes.forEach(node => calculateDepth(node.id, depthMap));

    // Group nodes by depth (layer)
    const layers = new Map<number, GraphNode[]>();
    nodes.forEach(node => {
      const depth = depthMap.get(node.id)!;
      if (!layers.has(depth)) {
        layers.set(depth, []);
      }
      layers.get(depth)!.push(node);
    });

    // Position nodes in hierarchical layout
    const maxDepth = Math.max(...Array.from(depthMap.values()));
    const verticalSpacing = (height - 100) / (maxDepth || 1);
    const padding = 50;

    layers.forEach((layerNodes, depth) => {
      const horizontalSpacing = (width - padding * 2) / (layerNodes.length + 1);
      layerNodes.forEach((node, index) => {
        node.x = padding + horizontalSpacing * (index + 1);
        node.y = padding + depth * verticalSpacing;
        node.fx = node.x; // Fix position
        node.fy = node.y;
      });
    });

    // Create node lookup map for link resolution
    const nodeMap = new Map<string, GraphNode>();
    nodes.forEach(n => nodeMap.set(n.id, n));

    // Resolve link references from IDs to actual node objects
    links.forEach(link => {
      if (typeof link.source === 'string') {
        link.source = nodeMap.get(link.source)!;
      }
      if (typeof link.target === 'string') {
        link.target = nodeMap.get(link.target)!;
      }
    });

    // No need for force simulation - we have explicit positions
    const simulation = d3.forceSimulation(nodes);
    simulationRef.current = simulation;

    // Draw links
    const link = g.append('g')
      .selectAll('line')
      .data(links)
      .enter().append('line')
      .attr('stroke', '#475569')
      .attr('stroke-width', 2)
      .attr('stroke-opacity', 0.6)
      .attr('marker-end', 'url(#arrow)');

    // Add arrow marker
    svg.append('defs').append('marker')
      .attr('id', 'arrow')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 25)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', '#475569');

    // Draw nodes
    const node = g.append('g')
      .selectAll('g')
      .data(nodes)
      .enter().append('g')
      .attr('cursor', 'pointer')
      .attr('class', d => `node-${d.id}`);

    // Node circles
    node.append('circle')
      .attr('class', 'node-circle')
      .attr('r', 20)
      .attr('fill', d => statusColor(d.status, d.isActive))
      .attr('stroke', d => d.id === selectedTaskId ? '#f59e0b' : '#1e293b')
      .attr('stroke-width', d => d.id === selectedTaskId ? 4 : 2)
      .on('click', (_, d) => {
        selectTask(d.id);
      });

    // Node labels
    node.append('text')
      .attr('class', 'node-label')
      .text(d => d.task.name.length > 20 ? d.task.name.substring(0, 20) + '...' : d.task.name)
      .attr('x', 0)
      .attr('y', 35)
      .attr('text-anchor', 'middle')
      .attr('fill', '#e2e8f0')
      .attr('font-size', '11px')
      .attr('font-weight', '500')
      .style('pointer-events', 'none');

    // Progress text
    node.append('text')
      .attr('class', 'node-progress')
      .text(d => `${d.progress}%`)
      .attr('x', 0)
      .attr('y', 5)
      .attr('text-anchor', 'middle')
      .attr('fill', 'white')
      .attr('font-size', '10px')
      .attr('font-weight', '700')
      .style('pointer-events', 'none');

    // Positions are already set explicitly in hierarchical layout
    // No simulation needed - just position the elements
    simulation.stop();

    // Position nodes and links based on hierarchical layout
    link
      .attr('x1', d => (d.source as GraphNode).x!)
      .attr('y1', d => (d.source as GraphNode).y!)
      .attr('x2', d => (d.target as GraphNode).x!)
      .attr('y2', d => (d.target as GraphNode).y!);

    node.attr('transform', d => `translate(${d.x},${d.y})`);

    // Zoom behavior
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.5, 3])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
      });

    svg.call(zoom);

    return () => {
      simulation.stop();
    };
  }, [tasks]); // Only re-run when tasks change (not selection!)

  // Update visual properties when time or selection changes
  useEffect(() => {
    if (!svgRef.current || nodesRef.current.length === 0) return;

    const startTime = new Date(useVisualizationStore.getState().data.metadata.start_time).getTime();
    const currentAbsTime = startTime + currentTime;

    const svg = d3.select(svgRef.current);

    // Update each node's visual state
    nodesRef.current.forEach(node => {
      const state = getTaskStateAtTime(node.task, currentAbsTime);
      node.status = state.status;
      node.progress = state.progress;
      node.isActive = state.isActive;
    });

    const statusColor = (status: TaskStatus, isActive: boolean) => {
      if (isActive) return '#3b82f6';
      switch (status) {
        case TaskStatus.TODO: return '#64748b';
        case TaskStatus.IN_PROGRESS: return '#3b82f6';
        case TaskStatus.DONE: return '#10b981';
        case TaskStatus.BLOCKED: return '#ef4444';
        default: return '#64748b';
      }
    };

    // Update circle colors
    svg.selectAll('.node-circle')
      .data(nodesRef.current)
      .attr('fill', d => statusColor(d.status, d.isActive))
      .attr('stroke', d => d.id === selectedTaskId ? '#f59e0b' : '#1e293b')
      .attr('stroke-width', d => d.id === selectedTaskId ? 4 : 2)
      .attr('class', d => `node-circle ${d.isActive ? 'pulsing-node' : ''}`);

    // Update progress text
    svg.selectAll('.node-progress')
      .data(nodesRef.current)
      .text(d => `${d.progress}%`);

  }, [currentTime, selectedTaskId]); // Re-run when time or selection changes

  return (
    <div className="network-graph-view">
      <svg ref={svgRef} className="network-svg" />
      <div className="legend">
        <div className="legend-item">
          <div className="legend-color" style={{ backgroundColor: '#64748b' }}></div>
          <span>Backlog</span>
        </div>
        <div className="legend-item">
          <div className="legend-color" style={{ backgroundColor: '#3b82f6' }}></div>
          <span>In Progress</span>
        </div>
        <div className="legend-item">
          <div className="legend-color" style={{ backgroundColor: '#10b981' }}></div>
          <span>Done</span>
        </div>
        <div className="legend-item">
          <div className="legend-color" style={{ backgroundColor: '#ef4444' }}></div>
          <span>Blocked</span>
        </div>
      </div>
    </div>
  );
};

export default NetworkGraphView;
