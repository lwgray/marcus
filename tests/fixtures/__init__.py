"""
Domain-organized test fixtures for Marcus.

This package provides real implementations for testing Marcus components
without relying on mocks. Fixtures are organized by domain:

- fixtures_core: Core Marcus objects (tasks, agents, context)
- fixtures_ai: AI and enrichment related objects  
- fixtures_integration: Integration and external service objects

Usage:
    from tests.fixtures.fixtures_core import sample_task
    from tests.fixtures.fixtures_ai import sample_semantic_analysis
    from tests.fixtures.fixtures_integration import real_kanban_client
"""