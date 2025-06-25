"""
Integration tests for Marcus.

This package contains integration tests that verify the interaction between
multiple Marcus components and external services like the MCP kanban server.

Notes
-----
Integration tests may require external services to be running (e.g., Planka,
MCP servers) and are typically slower than unit tests. Use the @pytest.mark.integration
marker for these tests.
"""