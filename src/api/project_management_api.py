"""
Project Management API endpoints

Handles project creation, feature management, and workflow orchestration using Marcus MCP.
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List

from flask import Blueprint, jsonify, request

from src.marcus_mcp.client import SimpleMarcusClient
from src.visualization.pipeline_manager import PipelineFlowManager
from src.workflow.project_workflow import ProjectWorkflowManager

# Create blueprint
project_api = Blueprint("project_api", __name__, url_prefix="/api/projects")

# In-memory storage for simplicity (should use proper DB in production)
projects_store = {}
features_store = {}
project_flows = {}

# Initialize components
flow_manager = PipelineFlowManager()
marcus_client = None
workflow_manager = None


def initialize_project_components():
    """Initialize Marcus client and related components."""
    global marcus_client, workflow_manager

    if not marcus_client:
        try:
            # Initialize Marcus MCP client
            marcus_client = SimpleMarcusClient()

            # Initialize workflow manager
            workflow_manager = ProjectWorkflowManager(marcus_client, flow_manager)

            print("✅ Project components initialized successfully")

        except Exception as e:
            print(f"❌ Failed to initialize project components: {e}")
            raise


@project_api.route("/create", methods=["POST"])
def create_project():
    """Create a new project using Marcus MCP with PRD analysis."""
    try:
        data = request.json

        # Validate input - now we just need description and optional name
        if not data.get("description"):
            return (
                jsonify({"success": False, "error": "Project description is required"}),
                400,
            )

        # Initialize Marcus client if needed
        initialize_project_components()

        # Create project through Marcus MCP - it will handle PRD analysis
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Prepare Marcus create_project parameters
            marcus_params = {
                "description": data["description"],
                "project_name": data.get("name", "Untitled Project"),
                "options": data.get("options", {}),
            }

            print(
                f"📝 Creating project '{marcus_params['project_name']}' with description length: {len(marcus_params['description'])} chars"
            )

            # Call Marcus to create project with PRD analysis
            marcus_result = loop.run_until_complete(
                asyncio.wait_for(
                    marcus_client.call_tool("create_project", marcus_params),
                    timeout=90.0,  # 90 second timeout for complex PRD analysis
                )
            )
        except asyncio.TimeoutError:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Project creation timed out after 90 seconds. The AI is taking longer than expected to analyze your project description. Please try with a shorter description or break it into smaller parts.",
                    }
                ),
                504,
            )
        except Exception as e:
            print(f"Error creating project: {e}")
            return (
                jsonify(
                    {"success": False, "error": f"Failed to create project: {str(e)}"}
                ),
                500,
            )
        finally:
            loop.close()

        if not marcus_result or "error" in marcus_result:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": marcus_result.get(
                            "error", "Failed to create project in Marcus"
                        ),
                    }
                ),
                500,
            )

        # Create local project record
        project_id = str(uuid.uuid4())
        project = {
            "id": project_id,
            "name": data.get("name", "Untitled Project"),
            "description": data["description"],
            "type": data.get("type", "web_app"),
            "status": "planning",
            "created_at": datetime.now().isoformat(),
            "flow_id": None,
            "marcus_board_id": marcus_result.get("board_id"),
            "prd_analysis": marcus_result.get("analysis"),
            "task_count": marcus_result.get("task_count", 0),
            "estimated_hours": marcus_result.get("estimated_hours", 0),
            "progress": 0,
        }

        # Store project
        projects_store[project_id] = project

        # Create a flow for this project
        flow_id = flow_manager.create_flow(
            project_name=project["name"],
            project_type=project["type"],
            description=project["description"],
        )
        project["flow_id"] = flow_id

        # Emit project creation event
        flow_manager.add_event(
            flow_id,
            {
                "type": "project_created",
                "project_id": project_id,
                "name": project["name"],
                "task_count": project["task_count"],
                "estimated_hours": project["estimated_hours"],
                "timestamp": datetime.now().isoformat(),
            },
        )

        return jsonify(
            {
                "success": True,
                "project": project,
                "prd_analysis": marcus_result.get("analysis", {}),
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@project_api.route("/features/add", methods=["POST"])
def add_feature():
    """Add a feature to a project."""
    try:
        data = request.json
        project_id = data.get("project_id")

        if not project_id or project_id not in projects_store:
            return jsonify({"success": False, "error": "Invalid project ID"}), 400

        # Create feature
        feature_id = str(uuid.uuid4())
        feature = {
            "id": feature_id,
            "project_id": project_id,
            "title": data["title"],
            "description": data["description"],
            "priority": data.get("priority", "medium"),
            "acceptance_criteria": data.get("acceptance_criteria", []),
            "created_at": datetime.now().isoformat(),
            "status": "pending",
        }

        # Store feature
        if project_id not in features_store:
            features_store[project_id] = []
        features_store[project_id].append(feature)

        # Update project
        project = projects_store[project_id]
        project["feature_count"] = len(features_store[project_id])

        # Add event to flow
        if project["flow_id"]:
            flow_manager.add_event(
                project["flow_id"],
                {
                    "type": "feature_added",
                    "feature_id": feature_id,
                    "title": feature["title"],
                    "priority": feature["priority"],
                    "timestamp": datetime.now().isoformat(),
                },
            )

        return jsonify({"success": True, "feature": feature})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@project_api.route("/features/<feature_id>", methods=["DELETE"])
def remove_feature(feature_id):
    """Remove a feature from a project."""
    try:
        # Find and remove feature
        removed = False
        for project_id, features in features_store.items():
            for i, feature in enumerate(features):
                if feature["id"] == feature_id:
                    features.pop(i)
                    removed = True

                    # Update project
                    project = projects_store[project_id]
                    project["feature_count"] = len(features)

                    # Add event to flow
                    if project["flow_id"]:
                        flow_manager.add_event(
                            project["flow_id"],
                            {
                                "type": "feature_removed",
                                "feature_id": feature_id,
                                "timestamp": datetime.now().isoformat(),
                            },
                        )

                    break
            if removed:
                break

        return jsonify({"success": removed})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@project_api.route("/workflow/start", methods=["POST"])
def start_workflow():
    """Start the workflow for a project using Marcus MCP."""
    try:
        data = request.json
        project_id = data.get("project_id")
        options = data.get("options", {})

        if not project_id or project_id not in projects_store:
            return jsonify({"success": False, "error": "Invalid project ID"}), 400

        project = projects_store[project_id]

        # Initialize components if needed
        initialize_project_components()

        # If project was already created in Marcus, we can start workflow directly
        if not project.get("marcus_board_id"):
            # Project wasn't created through Marcus yet, create it now
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            marcus_params = {
                "description": project["description"],
                "project_name": project["name"],
                "options": {},
            }

            try:
                marcus_result = loop.run_until_complete(
                    asyncio.wait_for(
                        marcus_client.call_tool("create_project", marcus_params),
                        timeout=90.0,  # 90 second timeout
                    )
                )
            except asyncio.TimeoutError:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Project creation timed out after 90 seconds during workflow start.",
                        }
                    ),
                    504,
                )
            except Exception as e:
                print(f"Error creating project in workflow: {e}")
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"Failed to create project: {str(e)}",
                        }
                    ),
                    500,
                )

            if marcus_result and "board_id" in marcus_result:
                project["marcus_board_id"] = marcus_result["board_id"]
                project["task_count"] = marcus_result.get("task_count", 0)

        # Update project status
        project["status"] = "running"

        # Start workflow orchestration
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            workflow_result = loop.run_until_complete(
                asyncio.wait_for(
                    workflow_manager.start_project_workflow(
                        project_id=project_id,
                        flow_id=project["flow_id"],
                        options=options,
                    ),
                    timeout=30.0,  # 30 second timeout for workflow start
                )
            )
        except asyncio.TimeoutError:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Workflow start timed out after 30 seconds. The system might be busy.",
                    }
                ),
                504,
            )
        except Exception as e:
            print(f"Error starting workflow: {e}")
            return (
                jsonify(
                    {"success": False, "error": f"Failed to start workflow: {str(e)}"}
                ),
                500,
            )

        project["workflow_id"] = workflow_result["workflow_id"]

        # Add workflow start event
        if project["flow_id"]:
            flow_manager.add_event(
                project["flow_id"],
                {
                    "type": "workflow_started",
                    "options": options,
                    "task_count": project.get("task_count", 0),
                    "workflow_id": workflow_result["workflow_id"],
                    "timestamp": datetime.now().isoformat(),
                },
            )

        return jsonify(
            {
                "success": True,
                "flow_id": project["flow_id"],
                "workflow_id": workflow_result["workflow_id"],
                "task_count": project.get("task_count", 0),
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@project_api.route("/workflow/pause", methods=["POST"])
def pause_workflow():
    """Pause the workflow for a project."""
    try:
        data = request.json
        project_id = data.get("project_id")

        if not project_id or project_id not in projects_store:
            return jsonify({"success": False, "error": "Invalid project ID"}), 400

        project = projects_store[project_id]

        # Pause workflow if it exists
        if "workflow_id" in project and workflow_manager:
            workflow_manager.pause_workflow(project["workflow_id"])

        project["status"] = "paused"

        # Add pause event
        if project["flow_id"]:
            flow_manager.add_event(
                project["flow_id"],
                {"type": "workflow_paused", "timestamp": datetime.now().isoformat()},
            )

        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@project_api.route("/workflow/stop", methods=["POST"])
def stop_workflow():
    """Stop the workflow for a project."""
    try:
        data = request.json
        project_id = data.get("project_id")

        if not project_id or project_id not in projects_store:
            return jsonify({"success": False, "error": "Invalid project ID"}), 400

        project = projects_store[project_id]

        # Stop workflow if it exists
        if "workflow_id" in project and workflow_manager:
            workflow_manager.stop_workflow(project["workflow_id"])

        project["status"] = "stopped"

        # Add stop event
        if project["flow_id"]:
            flow_manager.add_event(
                project["flow_id"],
                {"type": "workflow_stopped", "timestamp": datetime.now().isoformat()},
            )

        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@project_api.route("/samples", methods=["GET"])
def get_sample_projects():
    """Get pre-defined sample projects for quick testing."""
    samples = [
        {
            "id": "sample-1",
            "name": "E-commerce Platform",
            "description": """Build a modern e-commerce platform with the following features:
- User authentication and profiles
- Product catalog with search and filtering
- Shopping cart and checkout process
- Payment integration (Stripe)
- Order management and tracking
- Admin dashboard for inventory management
- Responsive design for mobile and desktop
Tech stack: React frontend, Node.js/Express backend, PostgreSQL database, Redis for caching""",
        },
        {
            "id": "sample-2",
            "name": "Task Management System",
            "description": """Create a collaborative task management application similar to Trello with:
- User registration and team management
- Board creation with lists and cards
- Drag-and-drop functionality
- Real-time updates using WebSockets
- File attachments and comments
- Due dates and notifications
- Activity feed and history
- REST API for third-party integrations
Tech stack: Vue.js frontend, Python/FastAPI backend, MongoDB database""",
        },
        {
            "id": "sample-3",
            "name": "Real-time Chat Application",
            "description": """Develop a Slack-like real-time chat application featuring:
- User authentication with OAuth support
- Direct messages and group channels
- Real-time messaging with WebSockets
- File and image sharing
- Message search and history
- User presence indicators
- Emoji reactions and threading
- Voice and video calling capabilities
Tech stack: React Native for mobile, React for web, Node.js backend, Socket.io, PostgreSQL""",
        },
        {
            "id": "sample-4",
            "name": "AI-Powered Blog Platform",
            "description": """Build an AI-enhanced blogging platform with:
- AI-powered content suggestions and auto-completion
- SEO optimization recommendations
- Multi-author support with role-based permissions
- Rich text editor with markdown support
- Automatic image optimization
- Comment system with spam detection
- Analytics dashboard
- RSS feed generation
Tech stack: Next.js, Prisma ORM, PostgreSQL, OpenAI API integration""",
        },
        {
            "id": "sample-5",
            "name": "Fitness Tracking Mobile App",
            "description": """Create a comprehensive fitness tracking application with:
- User profiles with fitness goals
- Workout planning and tracking
- Exercise library with videos
- Progress charts and analytics
- Nutrition tracking with barcode scanning
- Social features for sharing achievements
- Integration with wearable devices
- Offline mode support
Tech stack: Flutter for mobile, Firebase backend, Cloud Firestore database""",
        },
    ]

    return jsonify({"success": True, "samples": samples})


@project_api.route("/list", methods=["GET"])
def list_projects():
    """List all projects."""
    try:
        projects_list = list(projects_store.values())

        # Sort by created date, newest first
        projects_list.sort(key=lambda p: p["created_at"], reverse=True)

        return jsonify({"success": True, "projects": projects_list})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@project_api.route("/<project_id>", methods=["GET"])
def get_project(project_id):
    """Get project details."""
    try:
        if project_id not in projects_store:
            return jsonify({"success": False, "error": "Project not found"}), 404

        project = projects_store[project_id]
        features = features_store.get(project_id, [])

        return jsonify({"success": True, "project": project, "features": features})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@project_api.route("/<project_id>/flow", methods=["GET"])
def get_project_flow(project_id):
    """Get the flow ID for a project."""
    try:
        if project_id not in projects_store:
            return jsonify({"success": False, "error": "Project not found"}), 404

        project = projects_store[project_id]

        return jsonify({"success": True, "flow_id": project.get("flow_id")})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
