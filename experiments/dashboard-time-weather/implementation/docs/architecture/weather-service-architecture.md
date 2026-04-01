# Weather Information Service - Architecture Design

## Component Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                      │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │            WeatherWidget Component                │   │
│  │  ┌────────────┐ ┌──────────┐ ┌────────────────┐ │   │
│  │  │ CitySelect │ │ TempDisp │ │ WeatherIcon    │ │   │
│  │  │ (dropdown) │ │ (°F/°C)  │ │ (condition)    │ │   │
│  │  └────────────┘ └──────────┘ └────────────────┘ │   │
│  │  ┌────────────────────┐ ┌──────────────────────┐ │   │
│  │  │ ConditionDesc      │ │ MetadataBar          │ │   │
│  │  │ (sunny, rainy...)  │ │ (humidity, wind,     │ │   │
│  │  │                    │ │  last updated)       │ │   │
│  │  └────────────────────┘ └──────────────────────┘ │   │
│  └──────────────────────────────────────────────────┘   │
│                         │                                │
│              useWeather() hook                           │
│              (polling every 5 min)                       │
└─────────────┬───────────────────────────────────────────┘
              │ HTTP GET /api/weather?city={city}
              ▼
┌─────────────────────────────────────────────────────────┐
│                  BACKEND (FastAPI)                        │
│                                                          │
│  ┌──────────────────┐   ┌─────────────────────────────┐ │
│  │  Weather Router   │──▶│  WeatherService             │ │
│  │  /api/weather     │   │  - get_current_weather()    │ │
│  │  /api/weather/    │   │  - search_cities()          │ │
│  │    cities         │   │  - validate_city()          │ │
│  └──────────────────┘   └────────────┬────────────────┘ │
│                                      │                   │
│                          ┌───────────▼──────────┐       │
│                          │  WeatherCache        │       │
│                          │  (in-memory, 5m TTL) │       │
│                          └───────────┬──────────┘       │
│                                      │ cache miss       │
│                          ┌───────────▼──────────┐       │
│                          │  WeatherAPIClient    │       │
│                          │  (OpenWeatherMap)    │       │
│                          └──────────────────────┘       │
└─────────────────────────────────────────────────────────┘
              │
              │ HTTPS GET api.openweathermap.org
              ▼
┌─────────────────────────────────────────────────────────┐
│           OpenWeatherMap API (External)                   │
│           - Current Weather Data endpoint                 │
│           - Free tier: 60 calls/min                      │
└─────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### Frontend Components

| Component | Responsibility |
|-----------|---------------|
| `WeatherWidget` | Container component; manages city state, renders sub-components |
| `CitySelector` | Dropdown for selecting city; calls /api/weather/cities for suggestions |
| `TemperatureDisplay` | Shows temperature with unit toggle (°F/°C) |
| `WeatherIcon` | Maps weather condition codes to visual icons |
| `ConditionDescription` | Displays human-readable weather description |
| `MetadataBar` | Shows humidity, wind speed, and last-updated timestamp |
| `useWeather` hook | Fetches weather data, manages polling interval, handles errors |

### Backend Components

| Component | Responsibility |
|-----------|---------------|
| `weather_router` | FastAPI router; defines HTTP endpoints, validates query params |
| `WeatherService` | Business logic; orchestrates cache checks and API calls |
| `WeatherCache` | In-memory cache with TTL; reduces external API calls |
| `WeatherAPIClient` | HTTP client for OpenWeatherMap; handles auth, transforms responses |

## Data Flow

1. User selects a city in `CitySelector`
2. `useWeather` hook triggers GET `/api/weather?city={city}`
3. `weather_router` receives request, validates city parameter
4. `WeatherService.get_current_weather(city)` checks `WeatherCache`
5. **Cache HIT**: Return cached data immediately
6. **Cache MISS**: `WeatherAPIClient` calls OpenWeatherMap API
7. Response transformed into `WeatherData` model
8. Result cached with 5-minute TTL
9. JSON response sent to frontend
10. `WeatherWidget` renders updated weather data

## Error Handling Flow

- **External API down**: Return cached data (even if stale) with `stale: true` flag
- **Invalid city**: Return 404 with helpful message
- **Rate limited**: Return 429 with retry-after header
- **Network error**: Frontend shows last known data with "offline" indicator
