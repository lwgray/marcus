# Weather Information Service - Integration Specification

## Overview

This document defines how components communicate, how external APIs are integrated,
and the data transformation pipeline from OpenWeatherMap to the frontend widget.

## 1. Frontend ↔ Backend Communication

### Polling Strategy

The frontend `useWeather` hook polls the backend at a fixed interval:

```
Interval: 300,000 ms (5 minutes)
Method:   HTTP GET
Endpoint: /api/weather?city={city}&units={units}
Trigger:  On mount + every 5 minutes + on city change
```

**Why polling over WebSockets?**
- Weather data changes slowly (every few minutes at most)
- Polling is simpler to implement, debug, and scale
- No persistent connection overhead
- 5-minute interval matches our cache TTL

### Request Flow

```
1. useWeather hook fires (on mount, interval tick, or city change)
2. GET /api/weather?city=New+York&units=imperial
3. Headers: { Content-Type: application/json }
4. On success: update state with WeatherData
5. On error:
   - 404: show "City not found" message
   - 429: back off, retry after Retry-After header
   - 503: show last known data with "offline" indicator
   - Network error: show last known data with "offline" indicator
```

### Frontend Error Recovery

```typescript
// Pseudocode for useWeather hook
const useWeather = (city: string, units: string = "imperial") => {
  const [data, setData] = useState<WeatherData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [stale, setStale] = useState(false);

  const fetchWeather = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/weather?city=${encodeURIComponent(city)}&units=${units}`);
      const json = await res.json();
      if (json.success) {
        setData(json.data);
        setStale(json.stale);
        setError(null);
      } else {
        setError(json.error.message);
        // Keep previous data visible
      }
    } catch {
      setError("Unable to connect to weather service");
      // Keep previous data visible with stale indicator
      setStale(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWeather();
    const interval = setInterval(fetchWeather, 300_000);
    return () => clearInterval(interval);
  }, [city, units]);

  return { data, error, loading, stale };
};
```

## 2. Backend ↔ OpenWeatherMap Integration

### External API Configuration

```python
# Environment variables required
OPENWEATHERMAP_API_KEY: str  # Required, no default
WEATHER_CACHE_TTL: int = 300  # Optional, default 5 minutes
DEFAULT_CITY: str = "New York"  # Optional, default city
```

### API Endpoints Used

#### Current Weather Data
```
GET https://api.openweathermap.org/data/2.5/weather
  ?q={city}
  &units={imperial|metric}
  &appid={API_KEY}
```

#### Geocoding (for city search)
```
GET http://api.openweathermap.org/geo/1.0/direct
  ?q={query}
  &limit=5
  &appid={API_KEY}
```

### Data Transformation Pipeline

```python
async def transform_owm_response(raw: dict, units: str) -> WeatherData:
    """Transform OpenWeatherMap API response to our WeatherData model.

    Parameters
    ----------
    raw : dict
        Raw JSON response from OpenWeatherMap current weather API.
    units : str
        Temperature units ("imperial" or "metric").

    Returns
    -------
    WeatherData
        Transformed weather data model.
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
        icon_url=f"https://openweathermap.org/img/wn/{icon_code}@2x.png",
        visibility=raw.get("visibility", 0),
        timestamp=datetime.utcfromtimestamp(raw["dt"]),
        sunrise=datetime.utcfromtimestamp(raw["sys"]["sunrise"]),
        sunset=datetime.utcfromtimestamp(raw["sys"]["sunset"]),
    )
```

### Error Handling for External API

```python
# HTTP status code mapping
OWM_STATUS_MAPPING = {
    401: ("INVALID_API_KEY", "Weather API key is invalid or expired"),
    404: ("CITY_NOT_FOUND", "Could not find weather data for the specified city"),
    429: ("RATE_LIMITED", "Weather API rate limit exceeded"),
    500: ("SERVICE_ERROR", "Weather API internal error"),
    502: ("SERVICE_UNAVAILABLE", "Weather API is temporarily unavailable"),
    503: ("SERVICE_UNAVAILABLE", "Weather API is temporarily unavailable"),
}
```

### Rate Limiting Strategy

OpenWeatherMap free tier allows 60 calls/minute:

- Backend cache (5-min TTL) dramatically reduces API calls
- With 2 widgets polling every 5 min, worst case: ~24 calls/hour per city
- Well within free tier limits even with multiple cities
- If rate limited, serve stale cache and set Retry-After header

## 3. Backend Caching Layer

### Cache Implementation

```python
from datetime import datetime, timedelta


class WeatherCache:
    """In-memory weather data cache with TTL.

    Parameters
    ----------
    ttl_seconds : int
        Cache entry time-to-live in seconds.
    """

    def __init__(self, ttl_seconds: int = 300) -> None:
        self._cache: dict[str, CacheEntry] = {}
        self._ttl = timedelta(seconds=ttl_seconds)

    def _make_key(self, city: str, units: str) -> str:
        return f"weather:{city.lower().strip()}:{units}"

    def get(self, city: str, units: str) -> CacheEntry | None:
        key = self._make_key(city, units)
        entry = self._cache.get(key)
        if entry is None:
            return None
        return entry  # Caller checks is_expired

    def set(self, city: str, units: str, data: WeatherData) -> None:
        key = self._make_key(city, units)
        now = datetime.utcnow()
        self._cache[key] = CacheEntry(
            data=data,
            cached_at=now,
            expires_at=now + self._ttl,
        )
```

### Cache Flow Decision Tree

```
Request arrives for city={city}, units={units}
  │
  ├─ Cache entry exists?
  │   ├─ YES, not expired → Return cached data (stale=false)
  │   ├─ YES, expired → Try external API
  │   │   ├─ API success → Update cache, return fresh data
  │   │   └─ API failure → Return expired cache (stale=true)
  │   └─ NO → Try external API
  │       ├─ API success → Cache and return fresh data
  │       └─ API failure → Return 503 error
```

## 4. File Structure

```
implementation/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app setup, CORS config
│   │   ├── config.py            # Environment variable loading
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── weather.py       # Pydantic models (WeatherData, etc.)
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   └── weather.py       # /api/weather endpoints
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── weather_service.py   # Business logic orchestration
│   │   │   ├── weather_cache.py     # In-memory caching
│   │   │   └── weather_client.py    # OpenWeatherMap HTTP client
│   │   └── exceptions.py       # Custom exception classes
│   ├── tests/
│   │   ├── unit/
│   │   │   ├── test_weather_models.py
│   │   │   ├── test_weather_cache.py
│   │   │   └── test_weather_service.py
│   │   └── integration/
│   │       └── test_weather_api.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   └── weather/
│   │   │       ├── WeatherWidget.tsx
│   │   │       ├── CitySelector.tsx
│   │   │       ├── TemperatureDisplay.tsx
│   │   │       ├── WeatherIcon.tsx
│   │   │       ├── ConditionDescription.tsx
│   │   │       └── MetadataBar.tsx
│   │   ├── hooks/
│   │   │   └── useWeather.ts
│   │   ├── types/
│   │   │   └── weather.ts       # TypeScript interfaces
│   │   └── api/
│   │       └── weatherApi.ts    # API client functions
│   ├── package.json
│   └── tsconfig.json
└── docs/
    ├── architecture/
    │   └── weather-service-architecture.md
    ├── api/
    │   └── weather-api-contract.yaml
    ├── specifications/
    │   └── weather-data-models.md
    └── design/
        └── weather-integration-spec.md
```

## 5. Configuration & Environment

### Required Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENWEATHERMAP_API_KEY` | Yes | — | API key from openweathermap.org |
| `WEATHER_CACHE_TTL` | No | `300` | Cache TTL in seconds |
| `DEFAULT_CITY` | No | `"New York"` | Default city on first load |
| `CORS_ORIGINS` | No | `["http://localhost:3000"]` | Allowed CORS origins |
| `API_HOST` | No | `"0.0.0.0"` | Backend host |
| `API_PORT` | No | `8000` | Backend port |

### .env.example

```env
OPENWEATHERMAP_API_KEY=your_api_key_here
WEATHER_CACHE_TTL=300
DEFAULT_CITY=New York
CORS_ORIGINS=["http://localhost:3000"]
```
