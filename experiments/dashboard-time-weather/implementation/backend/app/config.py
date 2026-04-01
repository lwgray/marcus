"""Configuration for the Weather Information Service."""

import os


def get_api_key() -> str:
    """Get the OpenWeatherMap API key from environment.

    Returns
    -------
    str
        The API key.

    Raises
    ------
    ValueError
        If the API key is not set.
    """
    key = os.environ.get("OPENWEATHERMAP_API_KEY", "")
    if not key:
        raise ValueError("OPENWEATHERMAP_API_KEY environment variable is required")
    return key


WEATHER_CACHE_TTL: int = int(os.environ.get("WEATHER_CACHE_TTL", "300"))
DEFAULT_CITY: str = os.environ.get("DEFAULT_CITY", "New York")
OWM_BASE_URL: str = "https://api.openweathermap.org"
OWM_WEATHER_PATH: str = "/data/2.5/weather"
OWM_GEO_PATH: str = "/geo/1.0/direct"
