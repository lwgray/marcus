"""
FastAPI backend for Marcus Visualization Dashboard.

Provides REST API endpoints to serve Marcus data to the viz-dashboard frontend.
Supports CORS for local development and production deployment.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from viz_backend.data_loader import MarcusDataLoader

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Marcus Visualization API",
    description="Backend API for Marcus multi-agent visualization dashboard",
    version="1.0.0",
)

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",  # Vite default
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize data loader (will auto-detect Marcus root)
data_loader = MarcusDataLoader()


@app.get("/")  # type: ignore[misc]
async def root() -> Dict[str, Any]:
    """
    Root endpoint with API information.

    Returns
    -------
    dict
        API information and status
    """
    return {
        "name": "Marcus Visualization API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "/api/data": "Get all simulation data",
            "/api/tasks": "Get tasks",
            "/api/agents": "Get agents",
            "/api/messages": "Get messages",
            "/api/events": "Get events",
            "/api/metadata": "Get metadata",
            "/health": "Health check",
        },
    }


@app.get("/health")  # type: ignore[misc]
async def health() -> Dict[str, str]:
    """
    Health check endpoint.

    Returns
    -------
    dict
        Health status
    """
    return {"status": "healthy"}


@app.get("/api/data")  # type: ignore[misc]
async def get_all_data(
    project_id: Optional[str] = Query(None, description="Project ID to filter by"),
    view: str = Query("subtasks", description="View mode: 'subtasks' or 'parents'"),
) -> Dict[str, Any]:
    """
    Get all simulation data for the dashboard.

    Parameters
    ----------
    project_id : Optional[str]
        Specific project to load data for
    view : str
        View mode: 'subtasks' (default) or 'parents'

    Returns
    -------
    dict
        Complete simulation data including tasks, agents, messages, events, and metadata
    """
    try:
        logger.info(
            f"Loading all data for project: {project_id or 'all'}, view: {view}"
        )
        data = data_loader.load_all_data(project_id=project_id, view=view)
        return data
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        raise HTTPException(status_code=500, detail=f"Error loading data: {str(e)}")


@app.get("/api/tasks")  # type: ignore[misc]
async def get_tasks(
    project_id: Optional[str] = Query(None, description="Project ID to filter by"),
    view: str = Query("subtasks", description="View mode: 'subtasks' or 'parents'"),
) -> Dict[str, Any]:
    """
    Get tasks from Marcus persistence.

    Parameters
    ----------
    project_id : Optional[str]
        Specific project to load tasks for
    view : str
        View mode: 'subtasks' (default) or 'parents'

    Returns
    -------
    dict
        List of tasks (either subtasks or parent tasks)
    """
    try:
        logger.info(f"Loading tasks for project: {project_id or 'all'}, view: {view}")

        if view == "parents":
            tasks = data_loader.load_parent_tasks_from_persistence(
                project_id=project_id
            )
        else:
            tasks = data_loader.load_tasks_from_persistence(project_id=project_id)

        return {"tasks": tasks, "view": view}
    except Exception as e:
        logger.error(f"Error loading tasks: {e}")
        raise HTTPException(status_code=500, detail=f"Error loading tasks: {str(e)}")


@app.get("/api/agents")  # type: ignore[misc]
async def get_agents(
    project_id: Optional[str] = Query(None, description="Project ID to filter by")
) -> Dict[str, Any]:
    """
    Get agents inferred from tasks and messages.

    Parameters
    ----------
    project_id : Optional[str]
        Specific project to load agents for

    Returns
    -------
    dict
        List of agents with metrics
    """
    try:
        logger.info(f"Loading agents for project: {project_id or 'all'}")
        # Load tasks and messages to infer agents
        tasks = data_loader.load_tasks_from_persistence(project_id=project_id)
        messages = data_loader.load_messages_from_logs()
        agents = data_loader.infer_agents_from_data(tasks, messages)
        return {"agents": agents}
    except Exception as e:
        logger.error(f"Error loading agents: {e}")
        raise HTTPException(status_code=500, detail=f"Error loading agents: {str(e)}")


@app.get("/api/messages")  # type: ignore[misc]
async def get_messages() -> Dict[str, Any]:
    """
    Get conversation messages from Marcus logs.

    Returns
    -------
    dict
        List of messages
    """
    try:
        logger.info("Loading messages from logs")
        messages = data_loader.load_messages_from_logs()
        return {"messages": messages}
    except Exception as e:
        logger.error(f"Error loading messages: {e}")
        raise HTTPException(status_code=500, detail=f"Error loading messages: {str(e)}")


@app.get("/api/events")  # type: ignore[misc]
async def get_events() -> Dict[str, Any]:
    """
    Get agent events from Marcus logs.

    Returns
    -------
    dict
        List of events
    """
    try:
        logger.info("Loading events from logs")
        events = data_loader.load_events_from_logs()
        return {"events": events}
    except Exception as e:
        logger.error(f"Error loading events: {e}")
        raise HTTPException(status_code=500, detail=f"Error loading events: {str(e)}")


@app.get("/api/projects")  # type: ignore[misc]
async def get_projects() -> Dict[str, Any]:
    """
    Get list of all projects.

    Returns
    -------
    dict
        List of projects with metadata and active project ID
    """
    try:
        logger.info("Loading projects list")
        projects = data_loader.get_projects_list()
        active_project_id = data_loader.get_active_project_id()
        return {"projects": projects, "active_project_id": active_project_id}
    except Exception as e:
        logger.error(f"Error loading projects: {e}")
        raise HTTPException(status_code=500, detail=f"Error loading projects: {str(e)}")


@app.get("/api/metadata")  # type: ignore[misc]
async def get_metadata(
    project_id: Optional[str] = Query(None, description="Project ID to filter by")
) -> Dict[str, Any]:
    """
    Get project metadata and metrics.

    Parameters
    ----------
    project_id : Optional[str]
        Specific project to calculate metadata for

    Returns
    -------
    dict
        Metadata including project info and duration
    """
    try:
        logger.info(f"Calculating metadata for project: {project_id or 'all'}")
        # Load all data to calculate metadata
        tasks = data_loader.load_tasks_from_persistence(project_id=project_id)
        messages = data_loader.load_messages_from_logs()
        events = data_loader.load_events_from_logs()
        metadata = data_loader.calculate_metadata(tasks, messages, events)
        return {"metadata": metadata}
    except Exception as e:
        logger.error(f"Error calculating metadata: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error calculating metadata: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=4300, log_level="info")  # nosec B104
