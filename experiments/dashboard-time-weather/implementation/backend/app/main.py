"""FastAPI application for the Dashboard Time & Weather backend.

Provides API endpoints for time display and weather widgets.
"""

from backend.app.models import (
    CurrentTimeResponse,
    TimeErrorResponse,
    TimezoneListResponse,
)
from backend.app.services.time_service import (
    get_current_time,
    get_timezone_list,
)
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Dashboard Time & Weather API",
    version="0.1.0",
    description="Backend API for dashboard time and weather widgets",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(  # type: ignore[misc]
    "/api/time/zones",
    response_model=TimezoneListResponse,
)
def list_timezones() -> TimezoneListResponse:
    """List all available timezones with metadata.

    Returns
    -------
    TimezoneListResponse
        List of IANA timezones grouped by region.

    Examples
    --------
    Response::

        {
            "timezones": [
                {
                    "name": "America/New_York",
                    "utc_offset": "-05:00",
                    "region": "Americas",
                    "display_name": "New York"
                }
            ],
            "count": 1
        }
    """
    return get_timezone_list()


@app.get(  # type: ignore[misc]
    "/api/time/now",
    response_model=CurrentTimeResponse,
    responses={400: {"model": TimeErrorResponse}},
)
def current_time(
    timezone: str = Query(default="UTC", description="IANA timezone ID"),
) -> CurrentTimeResponse | JSONResponse:
    """Get current time in the specified timezone.

    Parameters
    ----------
    timezone : str
        IANA timezone identifier (e.g., "America/New_York").
        Defaults to "UTC".

    Returns
    -------
    CurrentTimeResponse | JSONResponse
        Current time data or 400 error for invalid timezone.

    Examples
    --------
    Success response::

        {
            "datetime_str": "2026-03-31T15:30:45-05:00",
            "timezone": "America/New_York",
            "utc_offset": "-05:00",
            "unix_timestamp": 1775010645.123,
            "formatted": {
                "time_24h": "15:30:45",
                "time_12h": "03:30:45 PM",
                "date": "March 31, 2026",
                "day_of_week": "Tuesday"
            }
        }

    Error response (400)::

        {
            "error": "invalid_timezone",
            "message": "Unknown timezone: 'Bad/Zone'."
        }
    """
    try:
        return get_current_time(timezone)
    except ValueError:
        return JSONResponse(
            status_code=400,
            content=TimeErrorResponse(
                error="invalid_timezone",
                message=(
                    f"Unknown timezone: '{timezone}'. "
                    "Use GET /api/time/zones for valid options."
                ),
            ).model_dump(),
        )
