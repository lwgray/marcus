# Time Display System - Data Models

## Backend Models (Python/Pydantic)

### TimezoneInfo
```python
from pydantic import BaseModel


class TimezoneInfo(BaseModel):
    """Represents a single timezone with metadata.

    Attributes
    ----------
    name : str
        IANA timezone identifier (e.g., "America/New_York").
    utc_offset : str
        Current UTC offset in +/-HH:MM format.
    region : str
        Geographic region grouping (Americas, Europe, Asia, etc.).
    display_name : str
        Human-readable display name.
    """

    name: str
    utc_offset: str
    region: str
    display_name: str
```

### TimezoneListResponse
```python
class TimezoneListResponse(BaseModel):
    """Response model for GET /api/time/zones.

    Attributes
    ----------
    timezones : list[TimezoneInfo]
        List of available timezones.
    count : int
        Total number of timezones returned.
    """

    timezones: list[TimezoneInfo]
    count: int
```

### CurrentTimeResponse
```python
class FormattedTime(BaseModel):
    """Formatted time strings for display.

    Attributes
    ----------
    time_24h : str
        Time in 24-hour format (e.g., "15:30:45").
    time_12h : str
        Time in 12-hour format (e.g., "3:30:45 PM").
    date : str
        Full date string (e.g., "March 31, 2026").
    day_of_week : str
        Day of week (e.g., "Tuesday").
    """

    time_24h: str
    time_12h: str
    date: str
    day_of_week: str


class CurrentTimeResponse(BaseModel):
    """Response model for GET /api/time/now.

    Attributes
    ----------
    datetime : str
        ISO 8601 formatted datetime in the requested timezone.
    timezone : str
        IANA timezone identifier used.
    utc_offset : str
        Current UTC offset.
    unix_timestamp : float
        Unix timestamp for client sync.
    formatted : FormattedTime
        Pre-formatted time strings for display.
    """

    datetime: str
    timezone: str
    utc_offset: str
    unix_timestamp: float
    formatted: FormattedTime
```

### ErrorResponse
```python
class ErrorResponse(BaseModel):
    """Standard error response.

    Attributes
    ----------
    error : str
        Error code (e.g., "invalid_timezone").
    message : str
        Human-readable error description.
    """

    error: str
    message: str
```

## Frontend Types (TypeScript)

```typescript
/** IANA timezone metadata */
interface TimezoneInfo {
  name: string;        // e.g., "America/New_York"
  utc_offset: string;  // e.g., "-05:00"
  region: string;      // e.g., "Americas"
  display_name: string; // e.g., "Eastern Time (US & Canada)"
}

/** Response from GET /api/time/zones */
interface TimezoneListResponse {
  timezones: TimezoneInfo[];
  count: number;
}

/** Pre-formatted time strings */
interface FormattedTime {
  time_24h: string;
  time_12h: string;
  date: string;
  day_of_week: string;
}

/** Response from GET /api/time/now */
interface CurrentTimeResponse {
  datetime: string;
  timezone: string;
  utc_offset: string;
  unix_timestamp: number;
  formatted: FormattedTime;
}

/** Clock widget state */
interface ClockState {
  selectedTimezone: string;   // IANA timezone ID
  currentTime: Date;          // JS Date object, re-created every 1s
  timezones: TimezoneInfo[];  // Available timezones from API
  isLoading: boolean;         // True while fetching timezone list
}
```

## Persistence

**No database required.** All data is ephemeral:
- Timezone list: derived from Python `zoneinfo.available_timezones()` at runtime
- Current time: computed on each request from `datetime.now(tz)`
- User's selected timezone: stored in React component state (optionally localStorage for persistence across page reloads)

## Region Mapping

Timezones are grouped into regions based on their IANA prefix:

| Prefix       | Region       |
|-------------|-------------|
| America/    | Americas     |
| Europe/     | Europe       |
| Asia/       | Asia         |
| Africa/     | Africa       |
| Pacific/    | Pacific      |
| Australia/  | Australia    |
| Indian/     | Indian Ocean |
| Atlantic/   | Atlantic     |
| Arctic/     | Arctic       |
| Antarctica/ | Antarctica   |
| UTC, GMT    | Universal    |
