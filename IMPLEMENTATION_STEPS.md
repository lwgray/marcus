# Marcus + Seneca Implementation Step-by-Step Guide

This guide helps individual developers and small teams set up their own Marcus instance. Follow these steps to get your personal AI development team running.

## 📋 Pre-Implementation Checklist

Before starting, ensure you have:
- [ ] Git repositories for Marcus and Seneca
- [ ] Node.js 18+ and Python 3.11+ installed
- [ ] Docker and Docker Compose installed (optional but recommended)
- [ ] SQLite (comes with Python - no setup needed!)
- [ ] A Planka board or GitHub project for task tracking

---

## Phase 1: Foundation (Days 1-3)

### Step 1: Set Up Development Environment
```bash
# 1.1 Create development branches
cd /path/to/marcus
git checkout -b develop
git push -u origin develop

cd /path/to/seneca
git checkout -b develop
git push -u origin develop

# 1.2 Set up branch protection on GitHub
# Go to Settings → Branches → Add rule
# - Branch name pattern: main
# - Require PR reviews: 1
# - Require status checks
# - Require branches up to date

# 1.3 Create feature branch for MVP
git checkout -b feature/mvp-analytics
```

### Step 2: Configure CI/CD Pipeline
```bash
# 2.1 Create GitHub Actions workflow for Marcus
mkdir -p .github/workflows
```

Create `.github/workflows/ci.yml`:
```yaml
name: CI/CD Pipeline
on:
  pull_request:
    branches: [develop, main]
  push:
    branches: [develop, main]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install black ruff pytest pytest-cov

      - name: Lint with black and ruff
        run: |
          black --check src/
          ruff check src/

      - name: Run tests with coverage
        run: |
          pytest tests/ --cov=src --cov-report=xml
          coverage report --fail-under=80

      - name: Type check with mypy
        run: mypy src/ --strict
```

### Step 3: Set Up Testing Framework
```bash
# 3.1 Create test structure for Marcus
mkdir -p tests/{unit,integration,fixtures}

# 3.2 Create pytest configuration
```

Create `pytest.ini`:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (requires services)
    slow: Slow tests (>1s)
```

### Step 4: Create Simple Local Setup
```bash
# 4.1 For individual developers - just run locally!
# No Docker required for getting started
```

Option A: Direct local execution:
```bash
# Terminal 1: Start Marcus
cd marcus
python -m marcus_mcp.server

# Terminal 2: Start Seneca
cd seneca
python app.py
```

Option B: Simple Docker setup (if preferred):
```yaml
# docker-compose.yml - Minimal setup for individuals
version: '3.8'
services:
  marcus:
    build: ./marcus
    ports:
      - "4300:4300"
    volumes:
      - ./data:/data  # Your projects stored here
      - ./marcus:/app
    environment:
      - DATABASE_PATH=/data/marcus.db  # SQLite file

  seneca:
    build: ./seneca
    ports:
      - "5000:5000"
    environment:
      - MARCUS_URL=http://marcus:4300
    depends_on:
      - marcus
    volumes:
      - ./seneca:/app
```

### Step 5: Implement Tool Verification Tests
```python
# 5.1 Create tool availability test
# tests/integration/test_tool_availability.py

import pytest
import asyncio
from marcus_mcp.client import MarcusClient

class TestMVPTools:
    """Verify all 18 MVP tools are available and working"""

    MVP_TOOLS = [
        # System Health (3)
        "ping", "get_system_metrics", "check_board_health",
        # Project Core (4)
        "get_project_status", "list_projects", "switch_project", "get_current_project",
        # Agent Identity (3)
        "register_agent", "get_agent_status", "list_registered_agents",
        # Work Flow (4)
        "request_next_task", "report_task_progress", "get_task_metrics", "check_task_dependencies",
        # Future Sight (2)
        "predict_completion_time", "predict_blockage_probability",
        # Quick Start (2)
        "create_project", "authenticate"
    ]

    @pytest.mark.integration
    async def test_all_mvp_tools_available(self):
        """Test that all 18 MVP tools are available"""
        client = MarcusClient("http://localhost:4300")
        tools = await client.list_tools()
        tool_names = {tool.name for tool in tools}

        missing = set(self.MVP_TOOLS) - tool_names
        assert not missing, f"Missing MVP tools: {missing}"

    @pytest.mark.integration
    async def test_tool_execution(self):
        """Test each tool executes without error"""
        client = MarcusClient("http://localhost:4300")

        # Test system health tools
        health = await client.call_tool("ping", {"echo": "health"})
        assert health["status"] == "healthy"

        metrics = await client.call_tool("get_system_metrics", {"time_window": "1h"})
        assert "active_agents" in metrics

        board = await client.call_tool("check_board_health")
        assert "health_score" in board
```

---

## Phase 2: MVP Analytics Implementation (Days 4-7)

### Step 6: Set Up Seneca Analytics Foundation
```bash
# 6.1 Install required packages for Seneca
cd seneca
pip install flask flask-cors flask-socketio httpx
# Note: No Redis needed for single-user setup!
npm install react recharts socket.io-client
```

### Step 7: Create Analytics API Structure
```python
# 7.1 Create analytics blueprint
# src/api/analytics_dashboard_api.py

from flask import Blueprint, jsonify
from src.mcp_client import MarcusClient
import asyncio
from datetime import datetime, timedelta

analytics_bp = Blueprint('analytics_dashboard', __name__)
# For local development
marcus_client = MarcusClient("http://localhost:4300")
# For Docker: use "http://marcus:4300"

@analytics_bp.route('/api/analytics/health-score')
async def get_health_score():
    """MVP Analytics #1: Project Health Score"""
    try:
        # Get data from multiple tools
        system_health = await marcus_client.call_tool("ping", {"echo": "health"})
        project_status = await marcus_client.call_tool("get_project_status")
        board_health = await marcus_client.call_tool("check_board_health")

        # Calculate composite score
        health_score = calculate_health_score(
            system=system_health,
            project=project_status,
            board=board_health
        )

        return jsonify({
            "score": health_score["score"],
            "factors": health_score["factors"],
            "recommendations": health_score["actions"],
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def calculate_health_score(system, project, board):
    """Calculate composite health score with factors"""
    # Weight different factors
    weights = {
        "system_performance": 0.2,
        "task_completion": 0.3,
        "blocked_ratio": 0.3,
        "team_utilization": 0.2
    }

    factors = {
        "system_performance": system.get("performance_score", 0),
        "task_completion": project.get("completion_percentage", 0),
        "blocked_ratio": 100 - (board.get("blocked_task_ratio", 0) * 100),
        "team_utilization": board.get("utilization_score", 0)
    }

    # Calculate weighted score
    score = sum(factors[key] * weights[key] for key in factors)

    # Generate recommendations based on lowest factors
    recommendations = generate_health_recommendations(factors)

    return {
        "score": round(score),
        "factors": factors,
        "actions": recommendations
    }
```

### Step 8: Implement Core Visualizations
```jsx
// 8.1 Create Health Gauge Component
// src/components/analytics/HealthGauge.jsx

import React, { useEffect, useState } from 'react';
import { RadialBarChart, RadialBar, ResponsiveContainer } from 'recharts';

const HealthGauge = ({ apiEndpoint = '/api/analytics/health-score' }) => {
  const [healthData, setHealthData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const response = await fetch(apiEndpoint);
        const data = await response.json();
        setHealthData(data);
      } catch (error) {
        console.error('Failed to fetch health score:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchHealth();
    const interval = setInterval(fetchHealth, 30000); // Update every 30s

    return () => clearInterval(interval);
  }, [apiEndpoint]);

  if (loading) return <div>Loading health status...</div>;
  if (!healthData) return <div>Unable to load health data</div>;

  const { score, factors, recommendations } = healthData;
  const color = score >= 80 ? '#22c55e' : score >= 60 ? '#f59e0b' : '#ef4444';

  const gaugeData = [{
    name: 'Health',
    value: score,
    fill: color
  }];

  return (
    <div className="health-gauge-container">
      <h2>Project Health</h2>
      <ResponsiveContainer width="100%" height={200}>
        <RadialBarChart
          cx="50%"
          cy="50%"
          innerRadius="60%"
          outerRadius="90%"
          data={gaugeData}
          startAngle={180}
          endAngle={0}
        >
          <RadialBar dataKey="value" cornerRadius={10} fill={color} />
        </RadialBarChart>
      </ResponsiveContainer>

      <div className="health-score">{score}</div>

      <div className="health-factors">
        {Object.entries(factors).map(([key, value]) => (
          <div key={key} className="factor">
            <span>{key.replace(/_/g, ' ')}</span>
            <span>{Math.round(value)}%</span>
          </div>
        ))}
      </div>

      {recommendations.length > 0 && (
        <div className="recommendations">
          <h3>Recommended Actions</h3>
          {recommendations.map((action, idx) => (
            <button key={idx} onClick={() => executeAction(action)}>
              {action.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
```

### Step 9: Implement Task Velocity Chart
```jsx
// 9.1 Create Velocity Chart Component
// src/components/analytics/VelocityChart.jsx

import React, { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const VelocityChart = () => {
  const [velocityData, setVelocityData] = useState([]);

  useEffect(() => {
    const fetchVelocity = async () => {
      const response = await fetch('/api/analytics/task-velocity');
      const data = await response.json();
      setVelocityData(data.metrics);
    };

    fetchVelocity();
    const interval = setInterval(fetchVelocity, 300000); // Update every 5 min

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="velocity-chart">
      <h2>Task Velocity Trend</h2>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={velocityData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Line
            type="monotone"
            dataKey="completed"
            stroke="#22c55e"
            name="Completed Tasks"
          />
          <Line
            type="monotone"
            dataKey="velocity"
            stroke="#3b82f6"
            name="Velocity Trend"
            strokeDasharray="5 5"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};
```

### Step 10: Create Timeline Prediction
```python
# 10.1 Add prediction endpoint
# src/api/analytics_dashboard_api.py

@analytics_bp.route('/api/analytics/completion-prediction')
async def get_completion_prediction():
    """MVP Analytics #3: Timeline Prediction with Confidence"""
    try:
        current_project = await marcus_client.call_tool("get_current_project")

        prediction = await marcus_client.call_tool("predict_completion_time", {
            "project_id": current_project["id"],
            "include_confidence": True
        })

        # Format for visualization
        return jsonify({
            "predicted_date": prediction["predicted_date"],
            "confidence_intervals": prediction["confidence_intervals"],
            "factors": prediction["factors"],
            "current_velocity": prediction.get("current_velocity"),
            "remaining_tasks": prediction.get("remaining_tasks")
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

### Step 11: Build Team Utilization Heatmap
```jsx
// 11.1 Create Utilization Heatmap
// src/components/analytics/UtilizationHeatmap.jsx

import React, { useEffect, useState } from 'react';
import * as d3 from 'd3';

const UtilizationHeatmap = () => {
  const [utilizationData, setUtilizationData] = useState(null);

  useEffect(() => {
    const fetchUtilization = async () => {
      // Get all agents
      const agentsRes = await fetch('/api/analytics/team-utilization');
      const data = await agentsRes.json();
      setUtilizationData(data);
    };

    fetchUtilization();
    const ws = new WebSocket('ws://localhost:8080/utilization');

    ws.onmessage = (event) => {
      const update = JSON.parse(event.data);
      setUtilizationData(prev => ({
        ...prev,
        matrix: {
          ...prev.matrix,
          [update.agent_id]: update.utilization
        }
      }));
    };

    return () => ws.close();
  }, []);

  // D3 heatmap rendering
  useEffect(() => {
    if (!utilizationData) return;

    const margin = { top: 50, right: 50, bottom: 50, left: 100 };
    const width = 600 - margin.left - margin.right;
    const height = 400 - margin.top - margin.bottom;

    // Clear previous
    d3.select('#utilization-heatmap').selectAll('*').remove();

    const svg = d3.select('#utilization-heatmap')
      .append('svg')
      .attr('width', width + margin.left + margin.right)
      .attr('height', height + margin.top + margin.bottom)
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Color scale
    const colorScale = d3.scaleLinear()
      .domain([0, 50, 80, 100])
      .range(['#f3f4f6', '#22c55e', '#f59e0b', '#ef4444']);

    // Render heatmap cells
    const agents = Object.keys(utilizationData.matrix);
    const dates = Object.keys(utilizationData.matrix[agents[0]] || {});

    const xScale = d3.scaleBand().domain(dates).range([0, width]).padding(0.05);
    const yScale = d3.scaleBand().domain(agents).range([0, height]).padding(0.05);

    // Add cells
    svg.selectAll()
      .data(agents.flatMap(agent =>
        dates.map(date => ({
          agent,
          date,
          value: utilizationData.matrix[agent][date]
        }))
      ))
      .enter()
      .append('rect')
      .attr('x', d => xScale(d.date))
      .attr('y', d => yScale(d.agent))
      .attr('width', xScale.bandwidth())
      .attr('height', yScale.bandwidth())
      .attr('fill', d => colorScale(d.value))
      .on('click', (event, d) => {
        showAgentTasksForDate(d.agent, d.date);
      });

  }, [utilizationData]);

  return (
    <div className="utilization-heatmap">
      <h2>Team Utilization</h2>
      <div id="utilization-heatmap"></div>
      <div className="legend">
        <span style={{ background: '#f3f4f6' }}>Idle</span>
        <span style={{ background: '#22c55e' }}>Optimal</span>
        <span style={{ background: '#f59e0b' }}>High</span>
        <span style={{ background: '#ef4444' }}>Overloaded</span>
      </div>
    </div>
  );
};
```

### Step 12: Create Smart Task Queue
```python
# 12.1 Task assignment endpoint
# src/api/analytics_dashboard_api.py

@analytics_bp.route('/api/analytics/task-assignments')
async def get_smart_assignments():
    """MVP Analytics #5: Smart Task Assignment Queue"""
    try:
        # Get all registered agents
        agents = await marcus_client.call_tool("list_registered_agents")

        # Get optimal task for each agent
        assignments = []
        for agent in agents:
            try:
                # Request next task for this agent
                next_task = await marcus_client.call_tool("request_next_task", {
                    "agent_id": agent["id"]
                })

                if next_task:
                    # Get dependencies
                    deps = await marcus_client.call_tool("check_task_dependencies", {
                        "task_id": next_task["id"]
                    })

                    assignments.append({
                        "agent": agent,
                        "task": next_task,
                        "score": next_task.get("assignment_score", 0),
                        "dependencies": deps,
                        "ready": len(deps.get("blocking", [])) == 0
                    })
            except Exception as e:
                print(f"Error getting task for agent {agent['id']}: {e}")

        # Sort by score
        assignments.sort(key=lambda x: x["score"], reverse=True)

        return jsonify({
            "assignments": assignments,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

---

## Phase 3: Integration & Testing (Week 7-8)

### Step 13: Create Integration Tests
```python
# 13.1 End-to-end test
# tests/integration/test_mvp_flow.py

import pytest
import asyncio
from datetime import datetime
import httpx

class TestMVPUserJourney:
    """Test the complete MVP user journey"""

    @pytest.mark.integration
    async def test_5_minute_onboarding(self):
        """Test that users can get value in 5 minutes"""
        start_time = datetime.now()

        # Step 1: Create project
        async with httpx.AsyncClient() as client:
            # Create project from description
            project_response = await client.post(
                "http://localhost:4300/mcp",
                json={
                    "method": "tools/call",
                    "params": {
                        "name": "create_project",
                        "arguments": {
                            "description": "Simple todo app with React frontend",
                            "project_name": "test-todo-app"
                        }
                    }
                }
            )
            assert project_response.status_code == 200

            # Step 2: Check dashboard loads
            dashboard_response = await client.get(
                "http://localhost:5000/api/analytics/health-score"
            )
            assert dashboard_response.status_code == 200
            health_data = dashboard_response.json()
            assert "score" in health_data

            # Step 3: Verify predictions available
            prediction_response = await client.get(
                "http://localhost:5000/api/analytics/completion-prediction"
            )
            assert prediction_response.status_code == 200
            prediction = prediction_response.json()
            assert "predicted_date" in prediction

            # Verify it took less than 5 minutes
            elapsed = (datetime.now() - start_time).total_seconds()
            assert elapsed < 300, f"Onboarding took {elapsed}s, should be < 300s"

    @pytest.mark.integration
    async def test_team_workflow(self):
        """Test daily team workflow with 3 developers"""
        # Register 3 agents
        agents = []
        for i in range(3):
            agent = await register_test_agent(f"dev-{i}", ["python", "react"])
            agents.append(agent)

        # Each requests work
        for agent in agents:
            task = await request_task(agent["id"])
            assert task is not None

            # Report progress
            await report_progress(agent["id"], task["id"], 50)

        # Verify dashboard shows activity
        utilization = await get_team_utilization()
        assert len(utilization["agents"]) == 3
        assert all(a["utilization"] > 0 for a in utilization["agents"])
```

### Step 14: Performance Testing
```python
# 14.1 Performance benchmarks
# tests/performance/test_response_times.py

import pytest
import asyncio
import time
from statistics import mean, stdev

class TestPerformance:
    """Ensure < 2s response time for 95% of requests"""

    @pytest.mark.performance
    async def test_dashboard_load_time(self):
        """Test all dashboard endpoints respond < 2s"""
        endpoints = [
            "/api/analytics/health-score",
            "/api/analytics/task-velocity",
            "/api/analytics/completion-prediction",
            "/api/analytics/team-utilization",
            "/api/analytics/task-assignments"
        ]

        response_times = []

        async with httpx.AsyncClient() as client:
            for endpoint in endpoints:
                for _ in range(20):  # 20 requests per endpoint
                    start = time.time()
                    response = await client.get(f"http://localhost:5000{endpoint}")
                    elapsed = time.time() - start
                    response_times.append(elapsed)
                    assert response.status_code == 200

        # Calculate 95th percentile
        sorted_times = sorted(response_times)
        p95_index = int(len(sorted_times) * 0.95)
        p95_time = sorted_times[p95_index]

        assert p95_time < 2.0, f"95th percentile response time {p95_time}s > 2s"
        print(f"Performance: mean={mean(response_times):.3f}s, p95={p95_time:.3f}s")
```

### Step 15: Create Demo Environment
```bash
# 15.1 Build demo data generator
# scripts/generate_demo_data.py

import asyncio
from marcus_mcp.client import MarcusClient

async def generate_demo_project():
    """Generate a realistic demo project"""
    client = MarcusClient("http://localhost:4300")

    # Create project
    project = await client.call_tool("create_project", {
        "description": """
        E-commerce platform with:
        - Product catalog with search and filters
        - Shopping cart and checkout
        - User authentication and profiles
        - Order tracking and history
        - Admin dashboard for inventory
        """,
        "project_name": "demo-ecommerce",
        "options": {
            "team_size": 5,
            "complexity": "medium",
            "tech_stack": ["react", "python", "postgresql"]
        }
    })

    # Register demo agents
    agents = [
        {"id": "alice", "name": "Alice", "skills": ["react", "ui/ux"]},
        {"id": "bob", "name": "Bob", "skills": ["python", "api"]},
        {"id": "carol", "name": "Carol", "skills": ["database", "python"]},
        {"id": "dave", "name": "Dave", "skills": ["testing", "devops"]},
        {"id": "eve", "name": "Eve", "skills": ["react", "testing"]}
    ]

    for agent in agents:
        await client.call_tool("register_agent", agent)

    # Simulate some progress
    for i in range(10):
        # Each agent requests and works on tasks
        for agent in agents:
            task = await client.call_tool("request_next_task", {
                "agent_id": agent["id"]
            })

            if task:
                # Simulate work
                await asyncio.sleep(1)

                # Report progress
                progress = (i + 1) * 10
                await client.call_tool("report_task_progress", {
                    "agent_id": agent["id"],
                    "task_id": task["id"],
                    "status": "in_progress" if progress < 100 else "completed",
                    "progress": progress
                })

    print("Demo project created and populated!")

if __name__ == "__main__":
    asyncio.run(generate_demo_project())
```

---

## Phase 4: Documentation & Polish (Week 9-10)

### Step 16: Create User Documentation
```markdown
# 16.1 Create quickstart guide
# docs/quickstart/5-minute-quickstart.md

# Marcus 5-Minute Quickstart

Get your first AI-powered project running in 5 minutes.

## Prerequisites
- Docker and Docker Compose installed
- 4GB RAM available
- Port 5000 (Seneca) and 4300 (Marcus) free

## Step 1: Clone and Start (1 minute)

```bash
# Clone the repositories
git clone https://github.com/your-org/marcus.git
git clone https://github.com/your-org/seneca.git

# Start with Docker Compose
cd marcus
docker-compose -f docker-compose.quickstart.yml up -d
```

## Step 2: Create Your First Project (2 minutes)

Open http://localhost:5000 in your browser.

1. Click "Create Project"
2. Describe your project in plain English:
   ```
   Build a task tracking app with:
   - User authentication
   - Create, edit, delete tasks
   - Mark tasks as complete
   - Filter by status
   ```
3. Click "Generate Project"

Marcus will:
- Break down your description into tasks
- Create optimal work phases
- Set up dependencies
- Estimate timelines

## Step 3: See the Magic (2 minutes)

### Dashboard Overview
- **Health Gauge**: Shows your project status (should be green!)
- **Timeline**: When your project will complete
- **Team**: AI agents ready to work

### Watch Agents Work
1. Click "Start Work" to activate agents
2. Watch the velocity chart update in real-time
3. See tasks move through the pipeline
4. Monitor progress on the timeline

## What Just Happened?

You've just:
✅ Created a complete project plan from natural language
✅ Activated AI agents to work autonomously
✅ Got predictions on completion time
✅ Started tracking progress in real-time

## Next Steps

- [Add your own agents](../guides/byoa-guide.md)
- [Understand the philosophy](../concepts/philosophy.md)
- [Explore advanced features](../guides/advanced-features.md)

Welcome to the future of software development! 🚀
```

### Step 17: Create API Documentation
```python
# 17.1 Generate API docs
# scripts/generate_api_docs.py

import inspect
from marcus_mcp.tools import TOOL_REGISTRY

def generate_tool_documentation():
    """Generate markdown documentation for all tools"""
    docs = ["# Marcus Tools API Reference\n\n"]

    # Group tools by category
    categories = {
        "System Health": ["ping", "get_system_metrics", "check_board_health"],
        "Project Management": ["get_project_status", "list_projects", "switch_project", "get_current_project"],
        "Agent Management": ["register_agent", "get_agent_status", "list_registered_agents"],
        "Task Management": ["request_next_task", "report_task_progress", "get_task_metrics", "check_task_dependencies"],
        "Predictions": ["predict_completion_time", "predict_blockage_probability"],
        "Project Creation": ["create_project", "authenticate"]
    }

    for category, tool_names in categories.items():
        docs.append(f"## {category}\n\n")

        for tool_name in tool_names:
            if tool_name in TOOL_REGISTRY:
                tool = TOOL_REGISTRY[tool_name]

                docs.append(f"### `{tool_name}`\n\n")
                docs.append(f"{tool.__doc__}\n\n")

                # Get parameters
                sig = inspect.signature(tool)
                if sig.parameters:
                    docs.append("**Parameters:**\n")
                    for param_name, param in sig.parameters.items():
                        if param_name not in ['self', 'state', 'arguments']:
                            param_type = param.annotation if param.annotation != param.empty else "Any"
                            docs.append(f"- `{param_name}` ({param_type}): Description\n")
                    docs.append("\n")

                # Add example
                docs.append("**Example:**\n```python\n")
                docs.append(f'result = await marcus.call_tool("{tool_name}", {{\n')
                docs.append('    # parameters here\n')
                docs.append('})\n```\n\n')

                docs.append("---\n\n")

    # Write to file
    with open("docs/api-reference.md", "w") as f:
        f.write("".join(docs))

if __name__ == "__main__":
    generate_tool_documentation()
```

### Step 18: Create Video Demo Script
```markdown
# 18.1 Demo video script
# docs/demo/video-script.md

# Marcus Demo Video Script (5 minutes)

## Opening (0:00-0:30)
"What if you could describe a project in plain English and have AI agents build it for you?"

[Show marcus-ai.dev landing page]

"Marcus makes this possible. Let me show you how in just 5 minutes."

## Project Creation (0:30-1:30)
"Let's build a real project. I'll type what I want:"

[Type]: "Build a team collaboration tool with real-time chat, file sharing,
task assignments, and video calls"

[Click Create Project]

"Watch as Marcus breaks this down into phases, tasks, and dependencies..."

[Show task breakdown appearing]

"It's created 47 tasks across Design, Implementation, and Testing phases."

## Dashboard Overview (1:30-2:30)
"Now let's see our project dashboard."

[Navigate to dashboard]

"The health score shows 92 - our project is in great shape."

"The timeline predicts completion in 3 weeks with 80% confidence."

"Our AI team is ready - 5 specialized agents with different skills."

## Agents at Work (2:30-3:30)
"Let's start the agents working."

[Click Start Work]

"Watch the velocity chart - tasks are already being completed."

"The utilization heatmap shows our agents are optimally loaded."

"And the smart task queue ensures everyone gets the right work."

## Real Value (3:30-4:30)
"But here's the real magic - let me show what happens when something goes wrong."

[Inject a blocker]

"The health score immediately drops to yellow."

"Marcus predicts a 2-day delay and suggests reassigning tasks."

[Click recommendation]

"One click and we've prevented the delay. The timeline is green again."

## Closing (4:30-5:00)
"In 5 minutes, we've:
- Created a complex project from plain English
- Got AI agents working autonomously
- Predicted completion with confidence
- Prevented a delay before it happened

This is Marcus - where chaos creates order and every project teaches the system to be smarter.

Try it yourself at marcus-ai.dev"

[Show website URL and GitHub stars]
```

---

## Phase 5: Beta Testing (Week 11-12)

### Step 19: Set Up Beta Program
```python
# 19.1 Beta user onboarding
# scripts/beta_onboarding.py

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_beta_welcome(user_email, beta_key):
    """Send beta welcome email with instructions"""

    message = MIMEMultipart("alternative")
    message["Subject"] = "Welcome to Marcus Beta!"
    message["From"] = "beta@marcus-ai.dev"
    message["To"] = user_email

    text = f"""
    Welcome to the Marcus Beta Program!

    Your beta key: {beta_key}

    Getting Started:
    1. Visit https://beta.marcus-ai.dev
    2. Enter your beta key
    3. Follow the 5-minute quickstart

    What We Need From You:
    - Try creating a real project
    - Report any issues on GitHub
    - Join our Discord for support
    - Share your experience

    Thank you for helping us build the future of development!

    The Marcus Team
    """

    html = f"""
    <html>
      <body>
        <h2>Welcome to the Marcus Beta Program!</h2>
        <p>Your beta key: <code>{beta_key}</code></p>

        <h3>Getting Started:</h3>
        <ol>
          <li>Visit <a href="https://beta.marcus-ai.dev">beta.marcus-ai.dev</a></li>
          <li>Enter your beta key</li>
          <li>Follow the 5-minute quickstart</li>
        </ol>

        <h3>What We Need From You:</h3>
        <ul>
          <li>Try creating a real project</li>
          <li>Report issues on <a href="https://github.com/marcus-ai/marcus/issues">GitHub</a></li>
          <li>Join our <a href="https://discord.gg/marcus">Discord</a></li>
          <li>Share your experience</li>
        </ul>

        <p>Thank you for helping us build the future!</p>
      </body>
    </html>
    """

    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")

    message.attach(part1)
    message.attach(part2)

    # Send email (configure SMTP settings)
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login("beta@marcus-ai.dev", "password")
        server.send_message(message)
```

### Step 20: Implement Analytics Tracking
```javascript
// 20.1 Usage analytics
// src/analytics/tracker.js

class AnalyticsTracker {
  constructor(endpoint = '/api/analytics/events') {
    this.endpoint = endpoint;
    this.sessionId = this.generateSessionId();
    this.queue = [];

    // Batch send every 10 seconds
    setInterval(() => this.flush(), 10000);
  }

  track(event, properties = {}) {
    this.queue.push({
      event,
      properties,
      timestamp: new Date().toISOString(),
      sessionId: this.sessionId,
      userId: this.getUserId()
    });

    // Flush if queue is large
    if (this.queue.length > 50) {
      this.flush();
    }
  }

  async flush() {
    if (this.queue.length === 0) return;

    const events = [...this.queue];
    this.queue = [];

    try {
      await fetch(this.endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ events })
      });
    } catch (error) {
      // Re-queue on failure
      this.queue = events.concat(this.queue);
    }
  }

  // Track specific user actions
  trackProjectCreated(projectId, description) {
    this.track('project_created', { projectId, description });
  }

  trackDashboardView(view) {
    this.track('dashboard_viewed', { view });
  }

  trackPredictionAccuracy(predicted, actual) {
    this.track('prediction_accuracy', { predicted, actual });
  }
}

// Usage
const analytics = new AnalyticsTracker();

// Track user actions
analytics.trackProjectCreated('123', 'Todo app with auth');
analytics.trackDashboardView('health_gauge');
```

---

## Phase 6: Launch Preparation (Week 13-14)

### Step 21: Create Marketing Website
```html
<!-- 21.1 Landing page -->
<!-- website/index.html -->

<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Marcus - AI-Powered Development Teams</title>
  <meta name="description" content="Turn project descriptions into working software with AI agents. Make development so simple a stoic could do it.">
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <header>
    <nav>
      <div class="logo">Marcus</div>
      <ul>
        <li><a href="#features">Features</a></li>
        <li><a href="#how-it-works">How It Works</a></li>
        <li><a href="#pricing">Pricing</a></li>
        <li><a href="https://docs.marcus-ai.dev">Docs</a></li>
        <li><a href="https://github.com/marcus-ai/marcus" class="github">GitHub</a></li>
      </ul>
    </nav>
  </header>

  <section class="hero">
    <h1>Build Software with AI Teams</h1>
    <p>Describe what you want. Watch AI agents build it. Ship faster than ever.</p>

    <div class="demo-box">
      <input type="text" placeholder="Build a team chat app with video calls..." />
      <button onclick="startDemo()">See It Built →</button>
    </div>

    <div class="stats">
      <div class="stat">
        <span class="number">73%</span>
        <span class="label">Faster Delivery</span>
      </div>
      <div class="stat">
        <span class="number">91%</span>
        <span class="label">Prediction Accuracy</span>
      </div>
      <div class="stat">
        <span class="number">5 min</span>
        <span class="label">To First Value</span>
      </div>
    </div>
  </section>

  <section id="features">
    <h2>Why Teams Love Marcus</h2>

    <div class="feature-grid">
      <div class="feature">
        <div class="icon">🧠</div>
        <h3>Natural Language Projects</h3>
        <p>Just describe what you want. Marcus creates tasks, dependencies, and timelines automatically.</p>
      </div>

      <div class="feature">
        <div class="icon">🤖</div>
        <h3>Autonomous AI Agents</h3>
        <p>Specialized agents work together, each focusing on their strengths. No micromanagement needed.</p>
      </div>

      <div class="feature">
        <div class="icon">📊</div>
        <h3>Real-Time Intelligence</h3>
        <p>See everything happening. Predict problems. Make decisions with confidence.</p>
      </div>

      <div class="feature">
        <div class="icon">🎯</div>
        <h3>Stoic Philosophy</h3>
        <p>Control what you can, accept what you cannot. Let chaos create beautiful solutions.</p>
      </div>
    </div>
  </section>

  <section id="how-it-works">
    <h2>How It Works</h2>

    <div class="steps">
      <div class="step">
        <span class="step-number">1</span>
        <h3>Describe Your Project</h3>
        <p>Write what you want in plain English. Be as detailed or simple as you like.</p>
      </div>

      <div class="step">
        <span class="step-number">2</span>
        <h3>Marcus Plans Everything</h3>
        <p>AI breaks down your description into phases, tasks, and dependencies.</p>
      </div>

      <div class="step">
        <span class="step-number">3</span>
        <h3>Agents Start Building</h3>
        <p>Specialized AI agents pull tasks and work autonomously. Watch progress in real-time.</p>
      </div>

      <div class="step">
        <span class="step-number">4</span>
        <h3>Ship with Confidence</h3>
        <p>Get accurate predictions, early warnings, and intelligent recommendations.</p>
      </div>
    </div>
  </section>

  <section class="cta">
    <h2>Ready to Build Smarter?</h2>
    <p>Join thousands of teams shipping faster with Marcus.</p>
    <a href="https://app.marcus-ai.dev/signup" class="button">Start Free Trial</a>
    <p class="note">Open source • No credit card required • 5-minute setup</p>
  </section>

  <script>
    function startDemo() {
      window.location.href = 'https://demo.marcus-ai.dev';
    }
  </script>
</body>
</html>
```

### Step 22: Prepare Launch Checklist
```markdown
# 22.1 Launch checklist
# LAUNCH_CHECKLIST.md

# Marcus Public Launch Checklist

## Technical Readiness
- [ ] All 18 MVP tools tested and working
- [ ] Analytics dashboard complete and responsive
- [ ] Performance: <2s response time verified
- [ ] Security audit completed
- [ ] Load testing passed (100 concurrent users)
- [ ] Backup and recovery tested
- [ ] Monitoring and alerts configured

## Documentation
- [ ] Quickstart guide (<5 minutes)
- [ ] API reference complete
- [ ] Video tutorials recorded
- [ ] Architecture documentation
- [ ] Contributing guidelines
- [ ] Code of conduct

## Infrastructure
- [ ] Production servers provisioned
- [ ] SSL certificates installed
- [ ] CDN configured
- [ ] Database backups automated
- [ ] Error tracking (Sentry) set up
- [ ] Analytics (Plausible) configured
- [ ] Status page created

## Marketing
- [ ] Website live at marcus-ai.dev
- [ ] Demo environment ready
- [ ] ProductHunt assets prepared
- [ ] Blog post drafted
- [ ] Social media accounts created
- [ ] Press kit ready
- [ ] Email templates configured

## Community
- [ ] GitHub repository public
- [ ] Issue templates created
- [ ] Discord server set up
- [ ] First 10 beta users confirmed
- [ ] Community guidelines posted
- [ ] Moderators assigned

## Legal
- [ ] License confirmed (MIT)
- [ ] Terms of service
- [ ] Privacy policy
- [ ] Contributor agreement
- [ ] Trademark registration

## Launch Day
- [ ] Team availability confirmed
- [ ] Support rotation scheduled
- [ ] Monitoring dashboard open
- [ ] Rollback plan ready
- [ ] Communication channels tested
- [ ] Celebration planned! 🎉
```

---

## Post-Launch: Continuous Improvement

### Step 23: Set Up Feedback Loop
```python
# 23.1 Feedback collection system
# src/feedback/collector.py

from datetime import datetime
import json

class FeedbackCollector:
    """Collect and analyze user feedback"""

    def __init__(self):
        self.feedback_db = FeedbackDatabase()
        self.analytics = AnalyticsEngine()

    async def collect_feedback(self, user_id, feedback_type, content):
        """Store user feedback"""
        feedback = {
            "id": generate_id(),
            "user_id": user_id,
            "type": feedback_type,  # bug, feature, praise, complaint
            "content": content,
            "timestamp": datetime.utcnow(),
            "status": "new"
        }

        await self.feedback_db.store(feedback)

        # Auto-categorize
        category = await self.analytics.categorize(content)

        # Create GitHub issue if bug
        if feedback_type == "bug":
            await self.create_github_issue(feedback, category)

        # Alert team if critical
        if await self.is_critical(feedback):
            await self.alert_team(feedback)

        return feedback["id"]

    async def analyze_patterns(self):
        """Find patterns in feedback"""
        recent_feedback = await self.feedback_db.get_recent(days=7)

        patterns = {
            "common_issues": self.find_common_themes(recent_feedback),
            "feature_requests": self.rank_feature_requests(recent_feedback),
            "satisfaction_trend": self.calculate_satisfaction(recent_feedback),
            "response_times": self.measure_response_times(recent_feedback)
        }

        return patterns
```

### Step 24: Implement A/B Testing
```javascript
// 24.1 A/B testing framework
// src/experiments/ab-testing.js

class ABTest {
  constructor(experimentName, variants) {
    this.name = experimentName;
    this.variants = variants;
    this.assignments = new Map();
  }

  getVariant(userId) {
    // Check if already assigned
    if (this.assignments.has(userId)) {
      return this.assignments.get(userId);
    }

    // Assign variant based on user ID hash
    const hash = this.hashUserId(userId);
    const variantIndex = hash % this.variants.length;
    const variant = this.variants[variantIndex];

    this.assignments.set(userId, variant);
    this.trackAssignment(userId, variant);

    return variant;
  }

  trackConversion(userId, value = 1) {
    const variant = this.assignments.get(userId);
    if (variant) {
      analytics.track('ab_test_conversion', {
        experiment: this.name,
        variant: variant,
        value: value,
        userId: userId
      });
    }
  }
}

// Example: Test different onboarding flows
const onboardingTest = new ABTest('onboarding_flow', [
  'guided_tour',
  'video_tutorial',
  'interactive_demo'
]);

// In your component
const OnboardingFlow = ({ userId }) => {
  const variant = onboardingTest.getVariant(userId);

  switch(variant) {
    case 'guided_tour':
      return <GuidedTour onComplete={() => onboardingTest.trackConversion(userId)} />;
    case 'video_tutorial':
      return <VideoTutorial onComplete={() => onboardingTest.trackConversion(userId)} />;
    case 'interactive_demo':
      return <InteractiveDemo onComplete={() => onboardingTest.trackConversion(userId)} />;
  }
};
```

### Step 25: Scale and Iterate
```yaml
# 25.1 Scaling plan
# infrastructure/scaling.yml

# Kubernetes deployment for scale
apiVersion: apps/v1
kind: Deployment
metadata:
  name: marcus-deployment
spec:
  replicas: 3  # Start with 3, scale based on load
  selector:
    matchLabels:
      app: marcus
  template:
    metadata:
      labels:
        app: marcus
    spec:
      containers:
      - name: marcus
        image: marcus-ai/marcus:latest
        ports:
        - containerPort: 4300
        env:
        - name: REDIS_URL
          value: "redis://redis-cluster:6379"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: marcus-secrets
              key: database-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 4300
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 4300
          initialDelaySeconds: 5
          periodSeconds: 5

---
# Horizontal Pod Autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: marcus-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: marcus-deployment
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

---

## Success Celebration Plan 🎉

### When You Hit 1,000 Users:
1. Team video call celebration
2. Blog post: "What We Learned from 1,000 Users"
3. Special badge for early adopters
4. Double down on what's working

### When You Hit 10,000 Users:
1. Marcus Conference (virtual)
2. Pattern Library Launch
3. Enterprise Edition Planning
4. Hire Community Manager

### When You Hit 100,000 Users:
1. You've changed how software is built
2. Write the book
3. Open research lab
4. Marcus Foundation for open source AI

Remember: Every step forward is progress. Ship early, iterate often, and let the community guide you.

> "The impediment to action advances action. What stands in the way becomes the way." - Marcus Aurelius

Now go build the future! 🚀
