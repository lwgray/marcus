"""
Unit tests for KnowledgeGraphBuilder
"""
import pytest
import json
import tempfile
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from src.visualization.knowledge_graph import (
    KnowledgeGraphBuilder,
    KnowledgeNode,
    KnowledgeEdge
)
from tests.unit.visualization.factories import (
    create_mock_worker_status,
    create_mock_task,
    create_knowledge_graph_data
)


class TestKnowledgeGraphBuilder:
    """Test cases for KnowledgeGraphBuilder"""
    
    @pytest.fixture
    def builder(self):
        """Create a KnowledgeGraphBuilder instance"""
        return KnowledgeGraphBuilder()
    
    def test_initialization(self, builder):
        """Test builder initialization"""
        assert builder.graph is not None
        assert len(builder.nodes) == 0
        assert len(builder.node_types) == 5  # worker, task, skill, project, decision
        assert len(builder.graph.nodes()) == 0
        assert len(builder.graph.edges()) == 0
    
    def test_add_worker(self, builder):
        """Test adding a worker node"""
        worker_id = builder.add_worker(
            worker_id="worker-123",
            name="John Doe",
            skills=["python", "javascript", "docker"]
        )
        
        assert worker_id == "worker-123"
        assert worker_id in builder.nodes
        assert builder.nodes[worker_id].node_type == "worker"
        assert builder.nodes[worker_id].label == "John Doe"
        
        # Check skills were added
        assert "skill_python" in builder.nodes
        assert "skill_javascript" in builder.nodes
        assert "skill_docker" in builder.nodes
        
        # Check edges
        edges = list(builder.graph.edges(worker_id, data=True))
        assert len(edges) == 3  # One for each skill
        for _, target, data in edges:
            assert data["edge_type"] == "has_skill"
    
    def test_add_task(self, builder):
        """Test adding a task node"""
        task_id = builder.add_task(
            task_id="task-456",
            name="Implement feature X",
            properties={
                "priority": "high",
                "estimated_hours": 16,
                "required_skills": ["python", "api"],
                "dependencies": []
            }
        )
        
        assert task_id == "task-456"
        assert task_id in builder.nodes
        assert builder.nodes[task_id].node_type == "task"
        assert builder.nodes[task_id].properties["priority"] == "high"
        assert builder.nodes[task_id].properties["estimated_hours"] == 16
    
    def test_add_task_with_dependencies(self, builder):
        """Test adding a task with dependencies"""
        # Add first task
        task1_id = builder.add_task("task-1", "Task 1", {})
        
        # Add second task that depends on first
        task2_id = builder.add_task(
            "task-2", 
            "Task 2",
            {"dependencies": ["task-1"]}
        )
        
        # Check dependency edge exists
        assert builder.graph.has_edge(task2_id, task1_id)
        edge_data = builder.graph.get_edge_data(task2_id, task1_id)
        assert any(d["edge_type"] == "depends_on" for d in edge_data.values())
    
    def test_assign_task(self, builder):
        """Test assigning a task to a worker"""
        # Add worker and task
        worker_id = builder.add_worker("worker-1", "Worker 1", ["python"])
        task_id = builder.add_task("task-1", "Task 1", {})
        
        # Assign task
        builder.assign_task(task_id, worker_id, confidence=0.85)
        
        # Check assignment edge
        assert builder.graph.has_edge(worker_id, task_id)
        edge_data = builder.graph.get_edge_data(worker_id, task_id)
        assert any(d["edge_type"] == "assigned_to" for d in edge_data.values())
        
        # Check task properties updated
        assert builder.nodes[task_id].properties["assigned_to"] == worker_id
        assert builder.nodes[task_id].properties["status"] == "in_progress"
    
    def test_update_task_status(self, builder):
        """Test updating task status"""
        task_id = builder.add_task("task-1", "Task 1", {})
        
        builder.update_task_status(task_id, "completed")
        
        assert builder.nodes[task_id].properties["status"] == "completed"
        assert builder.nodes[task_id].updated_at > builder.nodes[task_id].created_at
    
    def test_get_worker_tasks(self, builder):
        """Test getting tasks assigned to a worker"""
        worker_id = builder.add_worker("worker-1", "Worker 1", ["python"])
        
        # Add and assign multiple tasks
        task_ids = []
        for i in range(3):
            task_id = builder.add_task(f"task-{i}", f"Task {i}", {})
            builder.assign_task(task_id, worker_id)
            task_ids.append(task_id)
        
        # Get worker tasks
        tasks = builder.get_worker_tasks(worker_id)
        
        assert len(tasks) == 3
        assert all(task_id in tasks for task_id in task_ids)
    
    def test_get_task_candidates(self, builder):
        """Test finding suitable workers for a task"""
        # Add workers with different skills
        builder.add_worker("worker-1", "Worker 1", ["python", "api"])
        builder.add_worker("worker-2", "Worker 2", ["javascript", "react"])
        builder.add_worker("worker-3", "Worker 3", ["python", "docker"])
        
        # Add task requiring python
        task_id = builder.add_task(
            "task-1",
            "Python API Task",
            {"required_skills": ["python"]}
        )
        
        candidates = builder.get_task_candidates(task_id)
        
        # Should return workers with python skill
        assert len(candidates) == 2
        assert "worker-1" in candidates
        assert "worker-3" in candidates
        assert "worker-2" not in candidates
    
    @patch('src.visualization.knowledge_graph.Network')
    def test_visualize_graph(self, mock_network, builder):
        """Test graph visualization"""
        # Add some nodes
        builder.add_worker("worker-1", "Worker 1", ["python"])
        builder.add_task("task-1", "Task 1", {})
        
        # Mock network instance
        mock_net_instance = MagicMock()
        mock_network.return_value = mock_net_instance
        
        # Visualize
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as tmp:
            output = builder.visualize_graph(output_file=tmp.name)
        
        # Check network was created and saved
        mock_network.assert_called_once()
        mock_net_instance.from_nx.assert_called_once()
        mock_net_instance.save_graph.assert_called_once_with(tmp.name)
        
        assert output == tmp.name
    
    def test_export_graph_json(self, builder):
        """Test exporting graph as JSON"""
        # Add some nodes
        builder.add_worker("worker-1", "Worker 1", ["python"])
        builder.add_task("task-1", "Task 1", {})
        builder.assign_task("task-1", "worker-1")
        
        # Export
        json_data = builder.export_graph_json()
        data = json.loads(json_data)
        
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) >= 2  # At least worker and task
        assert len(data["edges"]) >= 1  # At least assignment edge
    
    def test_find_shortest_path(self, builder):
        """Test finding shortest path between nodes"""
        # Create a simple graph
        builder.add_worker("worker-1", "Worker 1", ["python"])
        builder.add_task("task-1", "Task 1", {})
        builder.add_task("task-2", "Task 2", {"dependencies": ["task-1"]})
        builder.assign_task("task-1", "worker-1")
        
        # Find path from worker to task-2
        path = builder.find_shortest_path("worker-1", "task-2")
        
        assert path is not None
        assert len(path) > 0
        assert path[0] == "worker-1"
        assert path[-1] == "task-2"
    
    def test_get_node_centrality(self, builder):
        """Test calculating node centrality"""
        # Create a connected graph
        worker_id = builder.add_worker("worker-1", "Worker 1", ["python", "api"])
        task1_id = builder.add_task("task-1", "Task 1", {"required_skills": ["python"]})
        task2_id = builder.add_task("task-2", "Task 2", {"required_skills": ["api"]})
        builder.assign_task(task1_id, worker_id)
        builder.assign_task(task2_id, worker_id)
        
        centrality = builder.get_node_centrality()
        
        assert worker_id in centrality
        assert centrality[worker_id] > 0  # Worker should have high centrality
    
    def test_get_connected_components(self, builder):
        """Test finding connected components"""
        # Create two separate subgraphs
        builder.add_worker("worker-1", "Worker 1", ["python"])
        builder.add_task("task-1", "Task 1", {})
        builder.assign_task("task-1", "worker-1")
        
        builder.add_worker("worker-2", "Worker 2", ["javascript"])
        builder.add_task("task-2", "Task 2", {})
        builder.assign_task("task-2", "worker-2")
        
        # Skills nodes might connect them, so let's check
        components = builder.get_connected_components()
        
        assert len(components) >= 1
        # All nodes should be in some component
        all_nodes = set()
        for component in components:
            all_nodes.update(component)
        assert "worker-1" in all_nodes
        assert "task-1" in all_nodes
    
    def test_prune_graph(self, builder):
        """Test pruning old completed tasks"""
        # Add tasks with different statuses
        task1_id = builder.add_task("task-1", "Old Task", {"status": "completed"})
        task2_id = builder.add_task("task-2", "Current Task", {"status": "in_progress"})
        
        # Manually set task-1 as old
        builder.nodes[task1_id].created_at = datetime(2020, 1, 1)
        builder.nodes[task1_id].properties["status"] = "completed"
        
        initial_count = len(builder.nodes)
        
        # Prune old tasks (older than 30 days by default)
        removed = builder.prune_old_nodes(days=30)
        
        assert removed > 0
        assert task1_id not in builder.nodes
        assert task2_id in builder.nodes
        assert len(builder.nodes) < initial_count