"""Pydantic models for the Weather Information Service."""

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class WeatherData(BaseModel):
    """Core weather data model returned by the API.

    Attributes
    ----------
    city : str
        City name.
    country : str
        ISO 3166 country code.
    temperature : float
        Current temperature in requested units.
    feels_like : float
        Perceived temperature.
    temp_min : float
        Minimum temperature currently observed in the area.
    temp_max : float
        Maximum temperature currently observed in the area.
    humidity : int
        Humidity percentage (0-100).
    pressure : int
        Atmospheric pressure in hPa.
    wind_speed : float
        Wind speed (mph for imperial, m/s for metric).
    wind_direction : int
        Wind direction in degrees (0-360).
    condition : str
        Human-readable weather description.
    condition_code : int
        OpenWeatherMap condition code for icon mapping.
    icon : str
        Icon code (e.g., "01d", "10n").
    icon_url : str
        Full URL to the weather icon image.
    visibility : int
        Visibility in meters.
    timestamp : datetime
        When the weather data was observed (UTC).
    sunrise : datetime
        Sunrise time (UTC).
    sunset : datetime
        Sunset time (UTC).
    """

    city: str
    country: str
    temperature: float
    feels_like: float
    temp_min: float
    temp_max: float
    humidity: int = Field(ge=0, le=100)
    pressure: int
    wind_speed: float = Field(ge=0)
    wind_direction: int = Field(ge=0, le=360)
    condition: str
    condition_code: int
    icon: str
    icon_url: str
    visibility: int = Field(ge=0)
    timestamp: datetime
    sunrise: datetime
    sunset: datetime


class WeatherResponse(BaseModel):
    """Wrapper for successful weather API responses.

    Attributes
    ----------
    success : bool
        Always True for successful responses.
    data : WeatherData
        The weather data payload.
    stale : bool
        True if data is from an expired cache entry.
    cached_at : datetime
        When this data was cached.
    """

    success: bool = True
    data: WeatherData
    stale: bool = False
    cached_at: datetime


class ErrorDetail(BaseModel):
    """Error detail within an error response.

    Attributes
    ----------
    code : str
        Machine-readable error code.
    message : str
        Human-readable error description.
    """

    code: str
    message: str


class ErrorResponse(BaseModel):
    """Wrapper for error API responses.

    Attributes
    ----------
    success : bool
        Always False for error responses.
    error : ErrorDetail
        Error details.
    """

    success: bool = False
    error: ErrorDetail


class CityResult(BaseModel):
    """A single city search result.

    Attributes
    ----------
    name : str
        City name.
    country : str
        ISO 3166 country code.
    state : str | None
        State/province name if available.
    """

    name: str
    country: str
    state: str | None = None


class CitySearchResponse(BaseModel):
    """Response for city search endpoint.

    Attributes
    ----------
    success : bool
        Always True for successful responses.
    cities : list[CityResult]
        List of matching cities.
    """

    success: bool = True
    cities: list[CityResult]


class CacheEntry(BaseModel):
    """Internal model for cached weather data.

    Attributes
    ----------
    data : WeatherData
        The cached weather data.
    cached_at : datetime
        When the data was cached.
    expires_at : datetime
        When the cache entry expires.
    """

    data: WeatherData
    cached_at: datetime
    expires_at: datetime

    @property
    def is_expired(self) -> bool:
        """Check if this cache entry has expired.

        Returns
        -------
        bool
            True if the entry is past its expiration time.
        """
        return datetime.now(timezone.utc) > self.expires_at
