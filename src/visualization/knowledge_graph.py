"""
Knowledge graph builder for Marcus system

Builds and maintains a graph of:
- Workers and their skills
- Tasks and dependencies
- Project structure
- Decision outcomes
"""

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx
import plotly.graph_objects as go
from pyvis.network import Network


@dataclass
class KnowledgeNode:
    """Node in the knowledge graph"""

    id: str
    node_type: str  # 'worker', 'task', 'skill', 'project', 'decision'
    label: str
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class KnowledgeEdge:
    """Edge in the knowledge graph"""

    source: str
    target: str
    edge_type: str  # 'has_skill', 'assigned_to', 'depends_on', 'resulted_in'
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


class KnowledgeGraphBuilder:
    """
    Builds and maintains a knowledge graph of the Marcus system
    """

    def __init__(self) -> None:
        self.graph = nx.MultiDiGraph()
        self.nodes: Dict[str, KnowledgeNode] = {}
        self.node_types = {
            "worker": {"color": "#3498db", "size": 25, "shape": "dot"},
            "task": {"color": "#e74c3c", "size": 20, "shape": "square"},
            "skill": {"color": "#2ecc71", "size": 15, "shape": "triangle"},
            "project": {"color": "#9b59b6", "size": 30, "shape": "star"},
            "decision": {"color": "#f39c12", "size": 18, "shape": "diamond"},
        }

    def add_worker(
        self, worker_id: str, name: str, role: str, skills: List[str]
    ) -> str:
        """Add a worker node to the graph"""
        node = KnowledgeNode(
            id=worker_id,
            node_type="worker",
            label=name,
            properties={
                "role": role,
                "skills": skills,
                "status": "available",
                "tasks_completed": 0,
                "performance_score": 1.0,
            },
        )

        self._add_node(node)

        # Add skill nodes and edges
        for skill in skills:
            skill_id = f"skill_{skill}"
            if skill_id not in self.nodes:
                skill_node = KnowledgeNode(
                    id=skill_id,
                    node_type="skill",
                    label=skill,
                    properties={"workers": []},
                )
                self._add_node(skill_node)

            # Add has_skill edge
            self._add_edge(
                KnowledgeEdge(
                    source=worker_id,
                    target=skill_id,
                    edge_type="has_skill",
                    properties={"proficiency": 1.0},
                )
            )

            # Update skill node with worker
            if "workers" not in self.nodes[skill_id].properties:
                self.nodes[skill_id].properties["workers"] = []
            self.nodes[skill_id].properties["workers"].append(worker_id)

        return worker_id

    def add_task(self, task_id: str, name: str, properties: Dict[str, Any]) -> str:
        """Add a task node to the graph"""
        node = KnowledgeNode(
            id=task_id,
            node_type="task",
            label=name,
            properties={
                "status": "backlog",
                "priority": properties.get("priority", "medium"),
                "estimated_hours": properties.get("estimated_hours", 8),
                "required_skills": properties.get("required_skills", []),
                **properties,
            },
        )

        self._add_node(node)

        # Add dependencies
        for dep_id in properties.get("dependencies", []):
            if dep_id in self.nodes:
                self._add_edge(
                    KnowledgeEdge(
                        source=task_id,
                        target=dep_id,
                        edge_type="depends_on",
                        properties={},
                    )
                )

        return task_id

    def assign_task(
        self, task_id: str, worker_id: str, assignment_score: float
    ) -> None:
        """Create assignment relationship between worker and task"""
        if task_id in self.nodes and worker_id in self.nodes:
            # Add edge from worker to task (as expected by tests)
            self._add_edge(
                KnowledgeEdge(
                    source=worker_id,
                    target=task_id,
                    edge_type="assigned_to",
                    properties={
                        "assignment_score": assignment_score,
                        "assigned_at": datetime.now().isoformat(),
                    },
                )
            )

            # Update task properties
            self.nodes[task_id].properties["assigned_to"] = worker_id
            self.nodes[task_id].properties["status"] = "in_progress"
            self.nodes[task_id].updated_at = datetime.now()
            self.nodes[worker_id].properties["status"] = "working"
            self.nodes[worker_id].properties["current_task"] = task_id

    def complete_task(self, task_id: str, worker_id: str, actual_hours: float) -> None:
        """Mark task as completed and update graph"""
        if task_id in self.nodes:
            task_node = self.nodes[task_id]
            task_node.properties["status"] = "completed"
            task_node.properties["completed_by"] = worker_id
            task_node.properties["actual_hours"] = actual_hours
            task_node.properties["completed_at"] = datetime.now().isoformat()

            # Update worker stats
            if worker_id in self.nodes:
                worker_node = self.nodes[worker_id]
                worker_node.properties["status"] = "available"
                worker_node.properties["current_task"] = None
                worker_node.properties["tasks_completed"] += 1

                # Calculate performance based on estimate vs actual
                estimated = task_node.properties.get("estimated_hours", 8)
                performance_ratio = (
                    estimated / actual_hours if actual_hours > 0 else 1.0
                )
                # Update rolling average performance score
                current_score = worker_node.properties.get("performance_score", 1.0)
                completed = worker_node.properties["tasks_completed"]
                new_score = (
                    (current_score * (completed - 1)) + performance_ratio
                ) / completed
                worker_node.properties["performance_score"] = new_score

    def add_decision(
        self,
        decision_id: str,
        decision_text: str,
        related_entities: List[str],
        outcome: Optional[str] = None,
    ) -> str:
        """Add a decision node to the graph"""
        node = KnowledgeNode(
            id=decision_id,
            node_type="decision",
            label=(
                decision_text[:50] + "..." if len(decision_text) > 50 else decision_text
            ),
            properties={
                "full_text": decision_text,
                "outcome": outcome,
                "related_entities": related_entities,
            },
        )

        self._add_node(node)

        # Link to related entities
        for entity_id in related_entities:
            if entity_id in self.nodes:
                self._add_edge(
                    KnowledgeEdge(
                        source=decision_id,
                        target=entity_id,
                        edge_type="related_to",
                        properties={},
                    )
                )

        return decision_id

    def _add_node(self, node: KnowledgeNode) -> None:
        """Add node to graph"""
        self.nodes[node.id] = node
        node_style = self.node_types.get(node.node_type, {})
        self.graph.add_node(
            node.id,
            label=node.label,
            node_type=node.node_type,
            **node_style,
            **node.properties,
        )

    def _add_edge(self, edge: KnowledgeEdge) -> None:
        """Add edge to graph"""
        self.graph.add_edge(
            edge.source, edge.target, edge_type=edge.edge_type, **edge.properties
        )

    def get_worker_recommendations(self, task_id: str) -> List[Tuple[str, float]]:
        """Get recommended workers for a task based on skills and availability"""
        if task_id not in self.nodes:
            return []

        task = self.nodes[task_id]
        required_skills = task.properties.get("required_skills", [])

        recommendations = []

        for worker_id, worker in self.nodes.items():
            if worker.node_type != "worker":
                continue

            # Skip if worker is busy
            if worker.properties.get("status") != "available":
                continue

            # Calculate skill match score
            worker_skills = set(worker.properties.get("skills", []))
            required_skills_set = set(required_skills)

            if not required_skills_set:
                # If no specific skills required, all available workers are candidates
                score = worker.properties.get("performance_score", 1.0)
            else:
                # Calculate skill overlap
                overlap = len(worker_skills.intersection(required_skills_set))
                skill_match = (
                    overlap / len(required_skills_set) if required_skills_set else 0
                )

                # Factor in performance score
                performance = worker.properties.get("performance_score", 1.0)

                # Combined score (70% skills, 30% performance)
                score = (0.7 * skill_match) + (0.3 * performance)

            if score > 0:
                recommendations.append((worker_id, score))

        # Sort by score descending
        recommendations.sort(key=lambda x: x[1], reverse=True)
        return recommendations

    def find_skill_gaps(self) -> Dict[str, List[str]]:
        """Find skills that are in demand but have few workers"""
        skill_demand: Dict[str, int] = defaultdict(int)
        skill_supply = defaultdict(int)

        # Count skill supply (from workers)
        for node_id, node in self.nodes.items():
            if node.node_type == "skill":
                skill_supply[node.label] = len(node.properties.get("workers", []))

        # Count skill demand (from tasks)
        for node_id, node in self.nodes.items():
            if (
                node.node_type == "task"
                and node.properties.get("status") != "completed"
            ):
                for skill in node.properties.get("required_skills", []):
                    skill_demand[skill] += 1

        # Find gaps
        gaps: Dict[str, List[str]] = {
            "high_demand_low_supply": [],
            "no_supply": [],
            "balanced": [],
            "oversupplied": [],
        }

        for skill, demand in skill_demand.items():
            supply = skill_supply.get(skill, 0)

            if supply == 0:
                gaps["no_supply"].append(skill)
            elif demand > supply * 2:  # High demand relative to supply
                gaps["high_demand_low_supply"].append(skill)
            elif supply > demand * 2:  # Oversupplied
                gaps["oversupplied"].append(skill)
            else:
                gaps["balanced"].append(skill)

        return gaps

    def update_task_status(self, task_id: str, status: str) -> None:
        """Update the status of a task"""
        if task_id in self.nodes:
            self.nodes[task_id].properties["status"] = status
            self.nodes[task_id].updated_at = datetime.now()
            self.graph.nodes[task_id]["status"] = status

            # If task is completed, free up the assigned worker
            if status == "completed":
                worker_id = self.nodes[task_id].properties.get("assigned_to")
                if worker_id and worker_id in self.nodes:
                    self.nodes[worker_id].properties["status"] = "available"
                    self.nodes[worker_id].properties["current_task"] = None

    def get_worker_tasks(self, worker_id: str) -> List[str]:
        """Get all tasks assigned to a worker"""
        tasks = []
        for edge in self.graph.edges(worker_id, data=True):
            if edge[2].get("edge_type") == "assigned_to":
                tasks.append(edge[1])
        return tasks

    def get_task_candidates(self, task_id: str) -> List[str]:
        """Get suitable worker candidates for a task"""
        if task_id not in self.nodes:
            return []

        task = self.nodes[task_id]
        required_skills = task.properties.get("required_skills", [])

        candidates = []
        for node_id, node in self.nodes.items():
            if node.node_type == "worker":
                # Check if worker is available
                if node.properties.get("status") == "available":
                    worker_skills = set(node.properties.get("skills", []))
                    required_skills_set = set(required_skills)
                    # Return workers with any matching skills (partial match)
                    if worker_skills.intersection(required_skills_set):
                        candidates.append(node_id)

        return candidates

    def find_shortest_path(self, source: str, target: str) -> Optional[List[str]]:
        """Find shortest path between two nodes"""
        try:
            import networkx as nx

            # Convert to undirected for path finding
            undirected = self.graph.to_undirected()
            return nx.shortest_path(undirected, source, target)  # type: ignore[no-any-return]
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def get_node_centrality(self) -> Dict[str, float]:
        """Calculate node centrality scores"""
        import networkx as nx

        return nx.degree_centrality(self.graph)  # type: ignore[no-any-return]

    def get_connected_components(self) -> List[Set[str]]:
        """Get connected components in the graph"""
        import networkx as nx

        # Convert to undirected for component analysis
        undirected = self.graph.to_undirected()
        return list(nx.connected_components(undirected))

    def prune_old_nodes(self, days: int = 30) -> int:
        """Remove old completed tasks from the graph"""
        cutoff_date = datetime.now() - timedelta(days=days)
        nodes_to_remove = []

        for node_id, node in self.nodes.items():
            if (
                node.node_type == "task"
                and node.properties.get("status") == "completed"
                and node.created_at < cutoff_date
            ):
                nodes_to_remove.append(node_id)

        for node_id in nodes_to_remove:
            self.graph.remove_node(node_id)
            del self.nodes[node_id]

        return len(nodes_to_remove)

    def export_graph_json(self) -> str:
        """Export graph as JSON"""
        import networkx as nx

        graph_data = nx.node_link_data(self.graph, edges="edges")

        # Add node details
        for node in graph_data["nodes"]:
            node_id = node["id"]
            if node_id in self.nodes:
                node["details"] = {
                    "type": self.nodes[node_id].node_type,
                    "label": self.nodes[node_id].label,
                    "properties": self.nodes[node_id].properties,
                }

        return json.dumps(graph_data, indent=2)

    def visualize_graph(self, output_file: str = "graph.html") -> str:
        """Generate graph visualization using pyvis"""
        # Create network from networkx graph
        net = Network(height="750px", width="100%", directed=True)
        net.from_nx(self.graph)

        # Save the visualization
        net.save_graph(output_file)

        return output_file

    def get_task_dependencies_tree(self, task_id: str) -> Dict[str, Any]:
        """Get dependency tree for a task"""
        if task_id not in self.nodes:
            return {}

        def build_tree(node_id: str, visited: Set[str]) -> Dict[str, Any]:
            if node_id in visited:
                return {"id": node_id, "label": "Circular dependency", "children": []}

            visited.add(node_id)

            node = self.nodes.get(node_id)
            if not node:
                return {"id": node_id, "label": "Unknown", "children": []}

            tree = {
                "id": node_id,
                "label": node.label,
                "status": node.properties.get("status", "unknown"),
                "children": [],
            }

            # Get dependencies
            for edge in self.graph.edges(node_id, data=True):
                if edge[2].get("edge_type") == "depends_on":
                    child_tree = build_tree(edge[1], visited.copy())
                    tree["children"].append(child_tree)

            return tree

        return build_tree(task_id, set())

    def generate_interactive_graph(
        self,
        output_file: str = "knowledge_graph.html",
        filter_types: Optional[List[str]] = None,
    ) -> None:
        """Generate interactive HTML visualization of the knowledge graph"""
        # Create filtered subgraph if needed
        if filter_types:
            nodes_to_include = [
                n
                for n, d in self.graph.nodes(data=True)
                if d.get("node_type") in filter_types
            ]
            subgraph = self.graph.subgraph(nodes_to_include)
        else:
            subgraph = self.graph

        # Create Pyvis network
        net = Network(height="750px", width="100%", directed=True)

        # Add nodes with custom styling
        for node_id, node_data in subgraph.nodes(data=True):
            node_type = node_data.get("node_type", "default")
            style = self.node_types.get(node_type, {})

            net.add_node(
                node_id,
                label=node_data.get("label", node_id),
                color=style.get("color", "#888888"),
                size=style.get("size", 20),
                shape=style.get("shape", "dot"),
                title=self._create_node_tooltip(node_id, node_data),
            )

        # Add edges with labels
        for source, target, edge_data in subgraph.edges(data=True):
            edge_type = edge_data.get("edge_type", "")
            edge_label = edge_type.replace("_", " ").title()

            net.add_edge(source, target, label=edge_label, color="#888888", arrows="to")

        # Set physics options
        net.set_options(
            """
        var options = {
          "physics": {
            "forceAtlas2Based": {
              "gravitationalConstant": -50,
              "centralGravity": 0.01,
              "springLength": 100,
              "springConstant": 0.08
            },
            "solver": "forceAtlas2Based"
          }
        }
        """
        )

        net.save_graph(output_file)

    def export_graph_data(self, format: str = "json") -> str:
        """Export graph data in specified format"""
        if format == "json":
            return self.export_graph_json()
        else:
            # For now, only JSON is supported
            return self.export_graph_json()

    def _create_node_tooltip(self, node_id: str, node_data: Dict[str, Any]) -> str:
        """Create detailed tooltip for node"""
        node = self.nodes.get(node_id)
        if not node:
            return node_id

        lines = [f"<b>{node.label}</b>", f"Type: {node.node_type}"]

        # Add type-specific information
        if node.node_type == "worker":
            lines.extend(
                [
                    f"Role: {node.properties.get('role', 'Unknown')}",
                    f"Skills: {', '.join(node.properties.get('skills', []))}",
                    f"Status: {node.properties.get('status', 'Unknown')}",
                    f"Tasks Completed: {node.properties.get('tasks_completed', 0)}",
                    f"Performance: {node.properties.get('performance_score', 0):.2f}",
                ]
            )
        elif node.node_type == "task":
            lines.extend(
                [
                    f"Status: {node.properties.get('status', 'Unknown')}",
                    f"Priority: {node.properties.get('priority', 'Unknown')}",
                    f"Estimated Hours: {node.properties.get('estimated_hours', 'Unknown')}",
                    f"Required Skills: {', '.join(node.properties.get('required_skills', []))}",
                ]
            )
        elif node.node_type == "skill":
            worker_count = len(node.properties.get("workers", []))
            lines.append(f"Workers with skill: {worker_count}")

        return "<br>".join(lines)

    def export_graph_data_extended(self, format: str = "json") -> str:
        """Export graph data for external analysis"""
        export_data: Dict[str, Any] = {
            "nodes": [],
            "edges": [],
            "statistics": self.get_graph_statistics(),
        }

        # Export nodes
        for node_id, node in self.nodes.items():
            export_data["nodes"].append(
                {
                    "id": node_id,
                    "type": node.node_type,
                    "label": node.label,
                    "properties": node.properties,
                    "created_at": node.created_at.isoformat(),
                    "updated_at": node.updated_at.isoformat(),
                }
            )

        # Export edges
        for source, target, edge_data in self.graph.edges(data=True):
            export_data["edges"].append(
                {
                    "source": source,
                    "target": target,
                    "type": edge_data.get("edge_type", "unknown"),
                    "properties": {
                        k: v for k, v in edge_data.items() if k != "edge_type"
                    },
                }
            )

        if format == "json":
            return json.dumps(export_data, indent=2)
        else:
            return json.dumps(export_data)

    def get_graph_statistics(self) -> Dict[str, Any]:
        """Get statistics about the knowledge graph"""
        stats = {
            "total_nodes": len(self.nodes),
            "total_edges": self.graph.number_of_edges(),
            "nodes_by_type": defaultdict(int),
            "edges_by_type": defaultdict(int),
            "avg_worker_skills": 0,
            "avg_task_dependencies": 0,
            "skill_coverage": {},
        }

        # Count nodes by type
        for node in self.nodes.values():
            stats["nodes_by_type"][node.node_type] += 1

        # Count edges by type
        for _, _, edge_data in self.graph.edges(data=True):
            edge_type = edge_data.get("edge_type", "unknown")
            stats["edges_by_type"][edge_type] += 1

        # Calculate averages
        worker_skills = []
        task_deps = []

        for node in self.nodes.values():
            if node.node_type == "worker":
                worker_skills.append(len(node.properties.get("skills", [])))
            elif node.node_type == "task":
                deps = len(
                    [
                        e
                        for e in self.graph.edges(node.id)
                        if self.graph.edges[e].get("edge_type") == "depends_on"
                    ]
                )
                task_deps.append(deps)

        if worker_skills:
            stats["avg_worker_skills"] = sum(worker_skills) / len(worker_skills)
        if task_deps:
            stats["avg_task_dependencies"] = sum(task_deps) / len(task_deps)

        # Skill coverage
        stats["skill_coverage"] = self.find_skill_gaps()

        return stats
