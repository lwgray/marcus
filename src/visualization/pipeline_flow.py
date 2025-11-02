"""Minimal stubs for pipeline flow management."""

from datetime import datetime, timezone
from typing import Any, Dict, List

from .shared_pipeline_events import PipelineStage

# Explicitly export PipelineStage to avoid mypy attr-defined errors
__all__ = ["PipelineFlow", "PipelineStage"]


class PipelineFlow:
    """Minimal stub for pipeline flow tracking.

    Parameters
    ----------
    flow_id : str
        Unique identifier for the flow.
    flow_type : str, optional
        Type of the flow, by default "general".

    Attributes
    ----------
    flow_id : str
        Unique identifier for the flow.
    flow_type : str
        Type of the flow.
    stages : List[PipelineStage]
        List of pipeline stages in the flow.
    status : str
        Current status of the flow.
    created_at : str
        ISO format timestamp of when the flow was created.
    metadata : Dict[str, Any]
        Additional metadata for the flow.
    """

    def __init__(self, flow_id: str, flow_type: str = "general"):
        self.flow_id = flow_id
        self.flow_type = flow_type
        self.stages: List[PipelineStage] = []
        self.status = "created"
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.metadata: Dict[str, Any] = {}

    def add_stage(self, stage: PipelineStage) -> None:
        """Add a stage to the flow.

        Parameters
        ----------
        stage : PipelineStage
            The pipeline stage to add.
        """
        self.stages.append(stage)

    def start(self) -> None:
        """Start the flow."""
        self.status = "running"

    def complete(self) -> None:
        """Complete the flow."""
        self.status = "completed"

    def fail(self, error: str) -> None:
        """Fail the flow.

        Parameters
        ----------
        error : str
            The error message describing the failure.
        """
        self.status = "failed"
        self.metadata["error"] = error

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns
        -------
        Dict[str, Any]
            Dictionary representation of the pipeline flow.
        """
        return {
            "flow_id": self.flow_id,
            "flow_type": self.flow_type,
            "status": self.status,
            "created_at": self.created_at,
            "stages": [stage.to_dict() for stage in self.stages],
            "metadata": self.metadata,
        }
