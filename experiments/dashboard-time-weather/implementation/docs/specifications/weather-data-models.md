# Weather Information Service - Data Models

## Backend Models (Python/Pydantic)

### WeatherData - Core weather response model

```python
from datetime import datetime
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
        Human-readable weather description (e.g., "clear sky").
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
```

### WeatherResponse - API response wrapper

```python
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
```

### ErrorResponse - API error wrapper

```python
class ErrorDetail(BaseModel):
    """Error detail within an error response.

    Attributes
    ----------
    code : str
        Machine-readable error code (e.g., "CITY_NOT_FOUND").
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
```

### CityResult - City search result

```python
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
```

### CacheEntry - Internal cache model

```python
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
        """Check if this cache entry has expired."""
        return datetime.utcnow() > self.expires_at
```

## Frontend Models (TypeScript)

### WeatherData interface

```typescript
interface WeatherData {
  city: string;
  country: string;
  temperature: number;
  feels_like: number;
  temp_min: number;
  temp_max: number;
  humidity: number;
  pressure: number;
  wind_speed: number;
  wind_direction: number;
  condition: string;
  condition_code: number;
  icon: string;
  icon_url: string;
  visibility: number;
  timestamp: string; // ISO 8601
  sunrise: string;   // ISO 8601
  sunset: string;    // ISO 8601
}

interface WeatherResponse {
  success: true;
  data: WeatherData;
  stale: boolean;
  cached_at: string; // ISO 8601
}

interface ErrorResponse {
  success: false;
  error: {
    code: string;
    message: string;
  };
}

interface CityResult {
  name: string;
  country: string;
  state?: string;
}

interface CitySearchResponse {
  success: true;
  cities: CityResult[];
}

// Union type for API responses
type ApiResponse<T> = T | ErrorResponse;
```

## OpenWeatherMap API Response Mapping

The backend transforms OpenWeatherMap's response into our `WeatherData` model:

| OpenWeatherMap Field | Our Field | Transformation |
|---------------------|-----------|----------------|
| `name` | `city` | Direct copy |
| `sys.country` | `country` | Direct copy |
| `main.temp` | `temperature` | Direct copy (units handled by API param) |
| `main.feels_like` | `feels_like` | Direct copy |
| `main.temp_min` | `temp_min` | Direct copy |
| `main.temp_max` | `temp_max` | Direct copy |
| `main.humidity` | `humidity` | Direct copy |
| `main.pressure` | `pressure` | Direct copy |
| `wind.speed` | `wind_speed` | Direct copy |
| `wind.deg` | `wind_direction` | Direct copy |
| `weather[0].description` | `condition` | Direct copy |
| `weather[0].id` | `condition_code` | Direct copy |
| `weather[0].icon` | `icon` | Direct copy |
| `weather[0].icon` | `icon_url` | Prefix with `https://openweathermap.org/img/wn/{icon}@2x.png` |
| `visibility` | `visibility` | Direct copy |
| `dt` | `timestamp` | Unix → ISO 8601 datetime |
| `sys.sunrise` | `sunrise` | Unix → ISO 8601 datetime |
| `sys.sunset` | `sunset` | Unix → ISO 8601 datetime |

## Caching Strategy

- **Cache key**: `weather:{city_lowercase}:{units}` (e.g., `weather:new york:imperial`)
- **TTL**: 300 seconds (5 minutes)
- **Storage**: In-memory dict (sufficient for single-server deployment)
- **Stale serving**: If external API fails, serve expired cache with `stale: true`
- **Cache invalidation**: Automatic via TTL; no manual invalidation needed
