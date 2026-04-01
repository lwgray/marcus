"""Weather service orchestrating cache and API client."""

from datetime import datetime, timezone

from app.exceptions import ExternalServiceError
from app.models.weather import CityResult, WeatherResponse
from app.services.weather_cache import WeatherCache
from app.services.weather_client import WeatherAPIClient


class WeatherService:
    """Orchestrates weather data retrieval with caching.

    Parameters
    ----------
    client : WeatherAPIClient
        The API client for fetching weather data.
    cache_ttl : int
        Cache time-to-live in seconds.
    """

    def __init__(
        self,
        client: WeatherAPIClient,
        cache_ttl: int = 300,
    ) -> None:
        self._client = client
        self._cache = WeatherCache(ttl_seconds=cache_ttl)

    async def get_current_weather(
        self,
        city: str,
        units: str = "imperial",
    ) -> WeatherResponse:
        """Get current weather, using cache when available.

        Parameters
        ----------
        city : str
            City name.
        units : str
            Temperature units ("imperial" or "metric").

        Returns
        -------
        WeatherResponse
            Weather data with cache metadata.

        Raises
        ------
        ExternalServiceError
            If the API fails and no cached data is available.
        CityNotFoundError
            If the city is not found.
        """
        # Check cache first
        entry = self._cache.get(city, units)
        if entry is not None and not entry.is_expired:
            return WeatherResponse(
                data=entry.data,
                stale=False,
                cached_at=entry.cached_at,
            )

        # Cache miss or expired: fetch from API
        try:
            data = await self._client.fetch_weather(city, units)
            self._cache.set(city, units, data)
            return WeatherResponse(
                data=data,
                stale=False,
                cached_at=datetime.now(timezone.utc),
            )
        except ExternalServiceError:
            # Serve stale cache if available
            if entry is not None:
                return WeatherResponse(
                    data=entry.data,
                    stale=True,
                    cached_at=entry.cached_at,
                )
            raise

    async def search_cities(self, query: str) -> list[CityResult]:
        """Search for cities by name.

        Parameters
        ----------
        query : str
            Partial city name.

        Returns
        -------
        list[CityResult]
            Matching cities.
        """
        return await self._client.search_cities(query)
