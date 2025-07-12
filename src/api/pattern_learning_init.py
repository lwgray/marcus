"""
Initialize pattern learning components for API usage
"""

from src.integrations.ai_analysis_engine import AIAnalysisEngine
from src.integrations.github_mcp_interface import GitHubMCPInterface
from src.learning.project_pattern_learner import ProjectPatternLearner
from src.monitoring.project_monitor import ProjectMonitor
from src.quality.board_quality_validator import BoardQualityValidator
from src.quality.project_quality_assessor import ProjectQualityAssessor
from src.recommendations.recommendation_engine import PatternDatabase

# Global instances
_pattern_learner = None
_quality_assessor = None
_project_monitor = None


def init_pattern_learning_components(kanban_client=None, ai_engine=None):
    """
    Initialize pattern learning components for the API

    Parameters
    ----------
    kanban_client : KanbanInterface, optional
        Kanban client for accessing project data
    ai_engine : AIAnalysisEngine, optional
        AI engine for analysis (will create new if not provided)

    Returns
    -------
    tuple
        (pattern_learner, quality_assessor, project_monitor)
    """
    global _pattern_learner, _quality_assessor, _project_monitor

    # Create AI engine if not provided
    if not ai_engine:
        ai_engine = AIAnalysisEngine()

    # Create pattern database
    pattern_db = PatternDatabase()

    # Create pattern learner
    _pattern_learner = ProjectPatternLearner(
        pattern_db=pattern_db,
        ai_engine=ai_engine,
        code_analyzer=None,  # GitHub integration optional
    )

    # Create quality assessor
    github_mcp = None
    try:
        # Try to create GitHub interface if available
        github_mcp = GitHubMCPInterface()
    except Exception:
        # GitHub integration is optional
        pass

    board_validator = BoardQualityValidator()

    _quality_assessor = ProjectQualityAssessor(
        ai_engine=ai_engine, github_mcp=github_mcp, board_validator=board_validator
    )

    # Create project monitor if kanban client provided
    if kanban_client:
        _project_monitor = ProjectMonitor(
            kanban_client=kanban_client,
            pattern_learner=_pattern_learner,
            quality_assessor=_quality_assessor,
        )

    # Initialize the pattern API with components
    from src.api.pattern_learning_api import init_pattern_api

    init_pattern_api(
        _pattern_learner, _quality_assessor, _project_monitor, kanban_client
    )

    return _pattern_learner, _quality_assessor, _project_monitor


def get_pattern_learner():
    """Get the global pattern learner instance"""
    return _pattern_learner


def get_quality_assessor():
    """Get the global quality assessor instance"""
    return _quality_assessor


def get_project_monitor():
    """Get the global project monitor instance"""
    return _project_monitor
