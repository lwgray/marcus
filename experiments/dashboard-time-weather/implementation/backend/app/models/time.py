"""Pydantic models for the Time Display System API.

Defines request/response schemas for timezone listing and current time endpoints.
"""

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
    datetime_str : str
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

    datetime_str: str
    timezone: str
    utc_offset: str
    unix_timestamp: float
    formatted: FormattedTime


class TimeErrorResponse(BaseModel):
    """Standard error response for time endpoints.

    Attributes
    ----------
    error : str
        Error code (e.g., "invalid_timezone").
    message : str
        Human-readable error description.
    """

    error: str
    message: str
