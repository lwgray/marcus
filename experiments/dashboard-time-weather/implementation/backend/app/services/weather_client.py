"""HTTP client for the OpenWeatherMap API."""

from datetime import datetime, timezone
from typing import Any

import httpx
from app.config import OWM_BASE_URL, OWM_GEO_PATH, OWM_WEATHER_PATH
from app.exceptions import (
    CityNotFoundError,
    ExternalServiceError,
    InvalidApiKeyError,
    RateLimitedError,
)
from app.models.weather import CityResult, WeatherData


def transform_owm_response(raw: dict[str, Any]) -> WeatherData:
    """Transform an OpenWeatherMap API response to WeatherData.

    Parameters
    ----------
    raw : dict
        Raw JSON response from the OWM current weather endpoint.

    Returns
    -------
    WeatherData
        Structured weather data.

    Raises
    ------
    KeyError
        If required fields are missing from the response.
    """
    weather = raw["weather"][0]
    icon_code = weather["icon"]

    return WeatherData(
        city=raw["name"],
        country=raw["sys"]["country"],
        temperature=raw["main"]["temp"],
        feels_like=raw["main"]["feels_like"],
        temp_min=raw["main"]["temp_min"],
        temp_max=raw["main"]["temp_max"],
        humidity=raw["main"]["humidity"],
        pressure=raw["main"]["pressure"],
        wind_speed=raw["wind"]["speed"],
        wind_direction=raw["wind"].get("deg", 0),
        condition=weather["description"],
        condition_code=weather["id"],
        icon=icon_code,
        icon_url=(f"https://openweathermap.org/img/wn/{icon_code}@2x.png"),
        visibility=raw.get("visibility", 0),
        timestamp=datetime.fromtimestamp(raw["dt"], tz=timezone.utc),
        sunrise=datetime.fromtimestamp(raw["sys"]["sunrise"], tz=timezone.utc),
        sunset=datetime.fromtimestamp(raw["sys"]["sunset"], tz=timezone.utc),
    )


class WeatherAPIClient:
    """HTTP client for OpenWeatherMap API.

    Parameters
    ----------
    api_key : str
        OpenWeatherMap API key.
    base_url : str
        Base URL for the OWM API.
    timeout : float
        HTTP request timeout in seconds.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = OWM_BASE_URL,
        timeout: float = 10.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._client = httpx.AsyncClient(timeout=timeout)

    async def fetch_weather(self, city: str, units: str = "imperial") -> WeatherData:
        """Fetch current weather data for a city.

        Parameters
        ----------
        city : str
            City name.
        units : str
            Temperature units ("imperial" or "metric").

        Returns
        -------
        WeatherData
            Parsed weather data.

        Raises
        ------
        CityNotFoundError
            If the city is not found (404).
        InvalidApiKeyError
            If the API key is invalid (401).
        RateLimitedError
            If rate limited (429).
        ExternalServiceError
            For other API or network errors.
        """
        try:
            response = await self._client.get(
                f"{self._base_url}{OWM_WEATHER_PATH}",
                params={
                    "q": city,
                    "units": units,
                    "appid": self._api_key,
                },
            )
        except Exception as exc:
            raise ExternalServiceError(str(exc)) from exc

        status = response.status_code

        if status == 200:
            return transform_owm_response(response.json())
        elif status == 404:
            raise CityNotFoundError(city)
        elif status == 401:
            raise InvalidApiKeyError()
        elif status == 429:
            raise RateLimitedError()
        else:
            raise ExternalServiceError(
                f"HTTP {status}: " f"{response.json().get('message', 'Unknown error')}"
            )

    async def search_cities(self, query: str, limit: int = 5) -> list[CityResult]:
        """Search for cities by name.

        Parameters
        ----------
        query : str
            Partial city name to search for.
        limit : int
            Maximum number of results.

        Returns
        -------
        list[CityResult]
            Matching cities.

        Raises
        ------
        ExternalServiceError
            For API or network errors.
        """
        try:
            response = await self._client.get(
                f"{self._base_url}{OWM_GEO_PATH}",
                params={
                    "q": query,
                    "limit": limit,
                    "appid": self._api_key,
                },
            )
            response.raise_for_status()
        except Exception as exc:
            raise ExternalServiceError(str(exc)) from exc

        results = response.json()
        return [
            CityResult(
                name=item["name"],
                country=item["country"],
                state=item.get("state"),
            )
            for item in results
        ]

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()
