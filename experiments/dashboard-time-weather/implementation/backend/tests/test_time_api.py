"""Unit tests for the Time Display System API.

Tests timezone listing, current time retrieval, and error handling.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture  # type: ignore[misc]
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    from backend.app.main import app

    return TestClient(app)


class TestGetTimezones:
    """Test suite for GET /api/time/zones endpoint."""

    def test_returns_timezone_list(self, client: TestClient) -> None:
        """Test that endpoint returns a list of timezones."""
        response = client.get("/api/time/zones")
        assert response.status_code == 200
        data = response.json()
        assert "timezones" in data
        assert "count" in data
        assert isinstance(data["timezones"], list)
        assert data["count"] > 0

    def test_timezone_has_required_fields(self, client: TestClient) -> None:
        """Test each timezone has name, utc_offset, region, display_name."""
        response = client.get("/api/time/zones")
        data = response.json()
        tz = data["timezones"][0]
        assert "name" in tz
        assert "utc_offset" in tz
        assert "region" in tz
        assert "display_name" in tz

    def test_count_matches_list_length(self, client: TestClient) -> None:
        """Test that count field matches the number of timezones."""
        response = client.get("/api/time/zones")
        data = response.json()
        assert data["count"] == len(data["timezones"])

    def test_includes_common_timezones(self, client: TestClient) -> None:
        """Test that common timezones like UTC are included."""
        response = client.get("/api/time/zones")
        data = response.json()
        tz_names = [tz["name"] for tz in data["timezones"]]
        assert "UTC" in tz_names
        assert "America/New_York" in tz_names
        assert "Europe/London" in tz_names

    def test_timezones_have_region_grouping(self, client: TestClient) -> None:
        """Test that timezones are grouped by region."""
        response = client.get("/api/time/zones")
        data = response.json()
        regions = {tz["region"] for tz in data["timezones"]}
        assert "Americas" in regions
        assert "Europe" in regions


class TestGetCurrentTime:
    """Test suite for GET /api/time/now endpoint."""

    def test_returns_current_time_utc_default(self, client: TestClient) -> None:
        """Test that endpoint returns current time in UTC by default."""
        response = client.get("/api/time/now")
        assert response.status_code == 200
        data = response.json()
        assert data["timezone"] == "UTC"

    def test_returns_required_fields(self, client: TestClient) -> None:
        """Test that response has all required fields."""
        response = client.get("/api/time/now")
        data = response.json()
        assert "datetime_str" in data
        assert "timezone" in data
        assert "utc_offset" in data
        assert "unix_timestamp" in data
        assert "formatted" in data

    def test_formatted_time_fields(self, client: TestClient) -> None:
        """Test that formatted time has all display fields."""
        response = client.get("/api/time/now")
        data = response.json()
        formatted = data["formatted"]
        assert "time_24h" in formatted
        assert "time_12h" in formatted
        assert "date" in formatted
        assert "day_of_week" in formatted

    def test_accepts_timezone_parameter(self, client: TestClient) -> None:
        """Test that timezone query parameter changes the response."""
        response = client.get(
            "/api/time/now",
            params={"timezone": "America/New_York"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["timezone"] == "America/New_York"

    def test_invalid_timezone_returns_400(self, client: TestClient) -> None:
        """Test that invalid timezone returns 400 error."""
        response = client.get(
            "/api/time/now",
            params={"timezone": "Invalid/Zone"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "invalid_timezone"

    def test_unix_timestamp_is_numeric(self, client: TestClient) -> None:
        """Test that unix_timestamp is a valid number."""
        response = client.get("/api/time/now")
        data = response.json()
        assert isinstance(data["unix_timestamp"], (int, float))
        assert data["unix_timestamp"] > 0

    def test_utc_offset_format(self, client: TestClient) -> None:
        """Test that utc_offset is in +/-HH:MM format."""
        response = client.get("/api/time/now", params={"timezone": "UTC"})
        data = response.json()
        assert data["utc_offset"] == "+00:00"

    def test_time_24h_format(self, client: TestClient) -> None:
        """Test that time_24h is in HH:MM:SS format."""
        response = client.get("/api/time/now")
        data = response.json()
        time_str = data["formatted"]["time_24h"]
        parts = time_str.split(":")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)
