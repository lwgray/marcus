"""Unit tests for WeatherService and WeatherAPIClient."""

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.exceptions import (
    CityNotFoundError,
    ExternalServiceError,
    InvalidApiKeyError,
    RateLimitedError,
)
from app.models.weather import WeatherData
from app.services.weather_client import (
    WeatherAPIClient,
    transform_owm_response,
)
from app.services.weather_service import WeatherService


@pytest.fixture  # type: ignore[misc]
def owm_response() -> dict[str, Any]:
    """Create a sample OpenWeatherMap API response.

    Returns
    -------
    dict[str, Any]
        A mock OWM current weather response.
    """
    return {
        "name": "New York",
        "sys": {
            "country": "US",
            "sunrise": 1743411900,
            "sunset": 1743456900,
        },
        "main": {
            "temp": 72.5,
            "feels_like": 70.1,
            "temp_min": 68.0,
            "temp_max": 75.0,
            "humidity": 55,
            "pressure": 1013,
        },
        "wind": {
            "speed": 8.5,
            "deg": 220,
        },
        "weather": [
            {
                "id": 800,
                "description": "clear sky",
                "icon": "01d",
            }
        ],
        "visibility": 10000,
        "dt": 1743453000,
    }


class TestTransformOwmResponse:
    """Test suite for transform_owm_response."""

    def test_transforms_valid_response(self, owm_response: dict[str, Any]) -> None:
        """Test successful transformation of OWM response."""
        result = transform_owm_response(owm_response)
        assert isinstance(result, WeatherData)
        assert result.city == "New York"
        assert result.country == "US"
        assert result.temperature == 72.5
        assert result.humidity == 55
        assert result.condition == "clear sky"
        assert result.condition_code == 800
        assert result.icon == "01d"
        assert "01d@2x.png" in result.icon_url

    def test_missing_wind_deg_defaults_to_zero(
        self, owm_response: dict[str, Any]
    ) -> None:
        """Test that missing wind.deg defaults to 0."""
        del owm_response["wind"]["deg"]
        result = transform_owm_response(owm_response)
        assert result.wind_direction == 0

    def test_missing_visibility_defaults_to_zero(
        self, owm_response: dict[str, Any]
    ) -> None:
        """Test that missing visibility defaults to 0."""
        del owm_response["visibility"]
        result = transform_owm_response(owm_response)
        assert result.visibility == 0

    def test_transforms_timestamps_from_unix(
        self, owm_response: dict[str, Any]
    ) -> None:
        """Test that unix timestamps are converted to datetime."""
        result = transform_owm_response(owm_response)
        assert isinstance(result.timestamp, datetime)
        assert isinstance(result.sunrise, datetime)
        assert isinstance(result.sunset, datetime)

    def test_malformed_response_raises_key_error(self) -> None:
        """Test that malformed data raises KeyError."""
        with pytest.raises(KeyError):
            transform_owm_response({"name": "Test"})


class TestWeatherAPIClient:
    """Test suite for WeatherAPIClient."""

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_fetch_weather_success(self, owm_response: dict[str, Any]) -> None:
        """Test successful weather fetch from API."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = owm_response
        mock_response.raise_for_status = MagicMock()

        client = WeatherAPIClient(api_key="test_key")
        with patch.object(
            client._client,
            "get",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await client.fetch_weather("New York", "imperial")
            assert isinstance(result, WeatherData)
            assert result.city == "New York"

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_fetch_weather_404_raises_city_not_found(
        self,
    ) -> None:
        """Test that 404 response raises CityNotFoundError."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"message": "city not found"}

        client = WeatherAPIClient(api_key="test_key")
        with patch.object(
            client._client,
            "get",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            with pytest.raises(CityNotFoundError):
                await client.fetch_weather("Faketown", "imperial")

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_fetch_weather_401_raises_invalid_api_key(
        self,
    ) -> None:
        """Test that 401 response raises InvalidApiKeyError."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"message": "Invalid API key"}

        client = WeatherAPIClient(api_key="bad_key")
        with patch.object(
            client._client,
            "get",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            with pytest.raises(InvalidApiKeyError):
                await client.fetch_weather("New York", "imperial")

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_fetch_weather_429_raises_rate_limited(
        self,
    ) -> None:
        """Test that 429 response raises RateLimitedError."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"message": "rate limit exceeded"}

        client = WeatherAPIClient(api_key="test_key")
        with patch.object(
            client._client,
            "get",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            with pytest.raises(RateLimitedError):
                await client.fetch_weather("New York", "imperial")

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_fetch_weather_500_raises_external_service_error(
        self,
    ) -> None:
        """Test that 5xx response raises ExternalServiceError."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"message": "internal error"}

        client = WeatherAPIClient(api_key="test_key")
        with patch.object(
            client._client,
            "get",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            with pytest.raises(ExternalServiceError):
                await client.fetch_weather("New York", "imperial")

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_fetch_weather_network_error(self) -> None:
        """Test that network errors raise ExternalServiceError."""
        client = WeatherAPIClient(api_key="test_key")
        with patch.object(
            client._client,
            "get",
            new_callable=AsyncMock,
            side_effect=Exception("Connection refused"),
        ):
            with pytest.raises(ExternalServiceError):
                await client.fetch_weather("New York", "imperial")

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_search_cities_success(self) -> None:
        """Test successful city search."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "name": "New York",
                "country": "US",
                "state": "New York",
            },
            {
                "name": "New Delhi",
                "country": "IN",
            },
        ]
        mock_response.raise_for_status = MagicMock()

        client = WeatherAPIClient(api_key="test_key")
        with patch.object(
            client._client,
            "get",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            results = await client.search_cities("New")
            assert len(results) == 2
            assert results[0].name == "New York"
            assert results[1].state is None


class TestWeatherService:
    """Test suite for WeatherService."""

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_get_weather_cache_miss(self, owm_response: dict[str, Any]) -> None:
        """Test getting weather with cache miss fetches from API."""
        mock_client = AsyncMock()
        mock_weather = WeatherData(
            city="New York",
            country="US",
            temperature=72.5,
            feels_like=70.1,
            temp_min=68.0,
            temp_max=75.0,
            humidity=55,
            pressure=1013,
            wind_speed=8.5,
            wind_direction=220,
            condition="clear sky",
            condition_code=800,
            icon="01d",
            icon_url="https://openweathermap.org/img/wn/01d@2x.png",
            visibility=10000,
            timestamp=datetime(2026, 3, 31, 20, 30, 0),
            sunrise=datetime(2026, 3, 31, 10, 45, 0),
            sunset=datetime(2026, 3, 31, 23, 15, 0),
        )
        mock_client.fetch_weather = AsyncMock(return_value=mock_weather)

        service = WeatherService(client=mock_client)
        response = await service.get_current_weather("New York", "imperial")

        assert response.success is True
        assert response.stale is False
        assert response.data.city == "New York"
        mock_client.fetch_weather.assert_called_once_with("New York", "imperial")

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_get_weather_cache_hit(self) -> None:
        """Test getting weather with cache hit skips API call."""
        mock_client = AsyncMock()
        mock_weather = WeatherData(
            city="New York",
            country="US",
            temperature=72.5,
            feels_like=70.1,
            temp_min=68.0,
            temp_max=75.0,
            humidity=55,
            pressure=1013,
            wind_speed=8.5,
            wind_direction=220,
            condition="clear sky",
            condition_code=800,
            icon="01d",
            icon_url="https://openweathermap.org/img/wn/01d@2x.png",
            visibility=10000,
            timestamp=datetime(2026, 3, 31, 20, 30, 0),
            sunrise=datetime(2026, 3, 31, 10, 45, 0),
            sunset=datetime(2026, 3, 31, 23, 15, 0),
        )
        mock_client.fetch_weather = AsyncMock(return_value=mock_weather)

        service = WeatherService(client=mock_client)
        # First call populates cache
        await service.get_current_weather("New York", "imperial")
        # Second call should use cache
        response = await service.get_current_weather("New York", "imperial")

        assert response.success is True
        assert response.stale is False
        # Should only have been called once (cache hit on second)
        mock_client.fetch_weather.assert_called_once()

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_get_weather_api_failure_serves_stale(
        self,
    ) -> None:
        """Test that API failure serves stale cache data."""
        mock_client = AsyncMock()
        mock_weather = WeatherData(
            city="New York",
            country="US",
            temperature=72.5,
            feels_like=70.1,
            temp_min=68.0,
            temp_max=75.0,
            humidity=55,
            pressure=1013,
            wind_speed=8.5,
            wind_direction=220,
            condition="clear sky",
            condition_code=800,
            icon="01d",
            icon_url="https://openweathermap.org/img/wn/01d@2x.png",
            visibility=10000,
            timestamp=datetime(2026, 3, 31, 20, 30, 0),
            sunrise=datetime(2026, 3, 31, 10, 45, 0),
            sunset=datetime(2026, 3, 31, 23, 15, 0),
        )

        # First call succeeds, populates cache
        mock_client.fetch_weather = AsyncMock(return_value=mock_weather)
        service = WeatherService(client=mock_client, cache_ttl=0)
        await service.get_current_weather("New York", "imperial")

        # Second call fails - should serve stale
        mock_client.fetch_weather = AsyncMock(
            side_effect=ExternalServiceError("API down")
        )
        response = await service.get_current_weather("New York", "imperial")

        assert response.success is True
        assert response.stale is True
        assert response.data.city == "New York"

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_get_weather_no_cache_api_failure_raises(
        self,
    ) -> None:
        """Test that API failure with no cache raises error."""
        mock_client = AsyncMock()
        mock_client.fetch_weather = AsyncMock(
            side_effect=ExternalServiceError("API down")
        )

        service = WeatherService(client=mock_client)
        with pytest.raises(ExternalServiceError):
            await service.get_current_weather("New York", "imperial")
