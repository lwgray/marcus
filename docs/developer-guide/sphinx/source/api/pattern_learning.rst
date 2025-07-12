Pattern Learning API
====================

The Pattern Learning system provides automatic pattern extraction from completed projects
to improve future recommendations and risk assessment.

ProjectPatternLearner
---------------------

.. automodule:: src.learning.project_pattern_learner
   :members:
   :undoc-members:
   :show-inheritance:

ProjectQualityAssessor
----------------------

.. automodule:: src.quality.project_quality_assessor
   :members:
   :undoc-members:
   :show-inheritance:

Pattern Learning MCP Tools
--------------------------

.. automodule:: src.marcus_mcp.tools.pattern_learning
   :members:
   :undoc-members:
   :show-inheritance:

Data Models
-----------

ProjectPattern
~~~~~~~~~~~~~~

.. autoclass:: src.learning.project_pattern_learner.ProjectPattern
   :members:
   :undoc-members:
   :show-inheritance:

ProjectQualityAssessment
~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: src.quality.project_quality_assessor.ProjectQualityAssessment
   :members:
   :undoc-members:
   :show-inheritance:

CodeQualityMetrics
~~~~~~~~~~~~~~~~~~

.. autoclass:: src.quality.project_quality_assessor.CodeQualityMetrics
   :members:
   :undoc-members:
   :show-inheritance:

ProcessQualityMetrics
~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: src.quality.project_quality_assessor.ProcessQualityMetrics
   :members:
   :undoc-members:
   :show-inheritance:

TeamPerformanceMetrics
~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: src.learning.project_pattern_learner.TeamPerformanceMetrics
   :members:
   :undoc-members:
   :show-inheritance:

Usage Examples
--------------

Basic Pattern Learning
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from src.learning.project_pattern_learner import ProjectPatternLearner
   from src.recommendations.recommendation_engine import ProjectOutcome

   # Initialize learner
   learner = ProjectPatternLearner()

   # Learn from completed project
   pattern = await learner.learn_from_project(
       project_state=final_state,
       tasks=all_tasks,
       team_members=team,
       outcome=ProjectOutcome(
           successful=True,
           completion_time_days=45,
           quality_score=0.85,
           cost=50000
       )
   )

Quality Assessment
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from src.quality.project_quality_assessor import ProjectQualityAssessor

   # Initialize assessor
   assessor = ProjectQualityAssessor()

   # Assess project quality
   assessment = await assessor.assess_project_quality(
       project_state=state,
       tasks=tasks,
       team_members=team,
       github_config={
           "github_owner": "org",
           "github_repo": "repo",
           "project_start_date": "2024-01-01"
       }
   )

   print(f"Overall Quality: {assessment.overall_score:.0%}")

Finding Similar Projects
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Find similar successful projects
   similar_projects = learner.find_similar_projects(
       target_pattern=current_pattern,
       min_similarity=0.7
   )

   for pattern, similarity in similar_projects[:5]:
       print(f"{pattern.project_name}: {similarity:.0%} similar")

MCP Tool Usage
~~~~~~~~~~~~~~

.. code-block:: python

   # Using MCP tools from Claude Desktop
   response = await mcp_client.call_tool(
       "get_pattern_recommendations",
       {
           "project_context": {
               "total_tasks": 40,
               "team_size": 3,
               "velocity": 7.5
           }
       }
   )

See Also
--------

* :doc:`../../../pattern-learning-system` - Comprehensive pattern learning documentation
* :doc:`../../../api/pattern_learner` - Detailed ProjectPatternLearner API
* :doc:`../../../api/quality_assessor` - Detailed ProjectQualityAssessor API
* :doc:`../../../api/pattern_mcp_tools` - Pattern Learning MCP Tools API
