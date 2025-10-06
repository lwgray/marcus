"""
Integration test for Marcus MCP interruption recovery.

Tests that the system properly handles interruptions during task requests
and can recover gracefully.
"""

import asyncio
import signal
import subprocess
import time
from pathlib import Path

import pytest

from src.worker.inspector import Inspector


class TestInterruptionRecovery:
    """Test interruption and recovery scenarios."""

    @pytest.mark.asyncio
    async def test_ping_health_check(self):
        """Test that ping with health command returns system status."""
        client = Inspector()

        async with client.connect_to_marcus() as session:
            client.session = session

            # Ping with health check
            result = await session.call_tool("ping", arguments={"echo": "health"})

            assert result.content
            response = eval(result.content[0].text)  # Safe in test context

            assert response["success"] is True
            assert response["status"] == "online"
            assert "health" in response
            assert "tasks_being_assigned" in response["health"]
            assert "active_agents" in response["health"]

    @pytest.mark.asyncio
    async def test_cleanup_stuck_assignments(self):
        """Test that ping cleanup command clears stuck assignments."""
        client = Inspector()

        async with client.connect_to_marcus() as session:
            client.session = session

            # First, register an agent
            await client.register_agent(
                "test-agent-1", "Test Agent", "Developer", ["python"]
            )

            # Try to request a task (might get stuck)
            try:
                await client.request_next_task("test-agent-1")
            except:
                pass  # We're testing recovery, so failures are ok

            # Run cleanup
            result = await session.call_tool("ping", arguments={"echo": "cleanup"})
            response = eval(result.content[0].text)

            assert response["success"] is True
            assert "cleanup" in response
            assert response["cleanup"]["success"] is True

    @pytest.mark.asyncio
    async def test_retry_on_connection_failure(self):
        """Test that client retries operations on connection failure."""
        client = Inspector()

        # Track retry attempts
        attempts = []

        # Mock the session to fail first time, succeed second time
        class MockSession:
            async def call_tool(self, name, arguments):
                attempts.append(name)
                if len(attempts) == 1:
                    raise ConnectionError("Simulated connection failure")

                # Return mock response
                class MockResponse:
                    content = [
                        type(
                            "obj",
                            (object,),
                            {"text": '{"success": true, "task": null}'},
                        )
                    ]

                return MockResponse()

        client.session = MockSession()

        # This should retry and eventually succeed
        result = await client.request_next_task("test-agent")

        assert len(attempts) >= 1  # Should have retried
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_graceful_shutdown_on_sigint(self):
        """Test that Marcus handles SIGINT gracefully."""
        # Start Marcus server as subprocess
        marcus_path = Path(__file__).parent.parent.parent / "marcus_mcp_server.py"
        process = subprocess.Popen(
            ["python", str(marcus_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        # Give it time to start
        await asyncio.sleep(2)

        # Send SIGINT
        process.send_signal(signal.SIGINT)

        # Wait for process to exit
        stdout, stderr = process.communicate(timeout=5)

        # Check that cleanup message appeared
        stderr_text = stderr.decode()
        assert (
            "initiating graceful shutdown" in stderr_text
            or "Cleaning up" in stderr_text
        )

        # Process should have exited cleanly
        assert process.returncode is not None

    @pytest.mark.asyncio
    async def test_state_recovery_after_interruption(self):
        """Test that state is properly recovered after interruption."""
        client = Inspector()

        async with client.connect_to_marcus() as session:
            client.session = session

            # Register agent
            await client.register_agent(
                "recovery-test", "Recovery Test", "Dev", ["test"]
            )

            # Get initial health
            result = await session.call_tool("ping", arguments={"echo": "health"})
            initial_health = eval(result.content[0].text)

            # Simulate some operations
            try:
                await client.request_next_task("recovery-test")
            except:
                pass

            # Force cleanup
            await session.call_tool("ping", arguments={"echo": "cleanup"})

            # Get health after cleanup
            result = await session.call_tool("ping", arguments={"echo": "health"})
            final_health = eval(result.content[0].text)

            # Should have cleaned up stuck assignments
            assert len(final_health["health"]["tasks_being_assigned"]) == 0


if __name__ == "__main__":
    # Run specific test
    import sys

    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        pytest.main([__file__, f"::{test_name}", "-v"])
    else:
        pytest.main([__file__, "-v"])
