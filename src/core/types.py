"""Shared data types for Marcus.

This module contains common dataclasses and types used across multiple modules.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ProjectOutcome:
    """Outcome of a project execution.

    Attributes
    ----------
    successful : bool
        Whether the project completed successfully
    completion_time_days : float
        Time taken to complete in days
    quality_score : float
        Quality score of the deliverable
    cost : float
        Total cost of the project
    failure_reasons : Optional[List[str]], optional
        Reasons for failure if unsuccessful
    """

    successful: bool
    completion_time_days: float
    quality_score: float
    cost: float
    failure_reasons: Optional[List[str]] = None
