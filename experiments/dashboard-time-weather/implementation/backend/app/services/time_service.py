"""Time service providing timezone data and current time.

Uses Python's zoneinfo stdlib for IANA timezone support.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, available_timezones

from backend.app.models import (
    CurrentTimeResponse,
    FormattedTime,
    TimezoneInfo,
    TimezoneListResponse,
)

# Region mapping based on IANA timezone prefix
_REGION_MAP: dict[str, str] = {
    "America": "Americas",
    "US": "Americas",
    "Canada": "Americas",
    "Europe": "Europe",
    "Asia": "Asia",
    "Africa": "Africa",
    "Pacific": "Pacific",
    "Australia": "Australia",
    "Indian": "Indian Ocean",
    "Atlantic": "Atlantic",
    "Arctic": "Arctic",
    "Antarctica": "Antarctica",
}


def _get_region(tz_name: str) -> str:
    """Extract geographic region from an IANA timezone name.

    Parameters
    ----------
    tz_name : str
        IANA timezone identifier.

    Returns
    -------
    str
        Geographic region grouping.
    """
    prefix = tz_name.split("/")[0] if "/" in tz_name else tz_name
    return _REGION_MAP.get(prefix, "Other")


def _get_display_name(tz_name: str) -> str:
    """Create a human-readable display name from IANA timezone.

    Parameters
    ----------
    tz_name : str
        IANA timezone identifier.

    Returns
    -------
    str
        Human-readable display name.
    """
    if "/" in tz_name:
        parts = tz_name.split("/")
        city = parts[-1].replace("_", " ")
        return city
    return tz_name


def _format_utc_offset(dt: datetime) -> str:
    """Format the UTC offset of a datetime as +/-HH:MM.

    Parameters
    ----------
    dt : datetime
        Timezone-aware datetime.

    Returns
    -------
    str
        UTC offset string in +/-HH:MM format.
    """
    utc_offset = dt.utcoffset()
    if utc_offset is None:
        return "+00:00"
    total_seconds = int(utc_offset.total_seconds())
    sign = "+" if total_seconds >= 0 else "-"
    total_seconds = abs(total_seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"{sign}{hours:02d}:{minutes:02d}"


def get_timezone_list() -> TimezoneListResponse:
    """Get list of available timezones with metadata.

    Returns
    -------
    TimezoneListResponse
        List of available timezones grouped by region.
    """
    now_utc = datetime.now(tz=timezone.utc)
    timezones: list[TimezoneInfo] = []

    # Include common timezones (curated list for usability)
    common_zones = sorted(available_timezones())

    for tz_name in common_zones:
        # Skip obscure zones
        if tz_name.startswith("Etc/") or tz_name.startswith("SystemV/"):
            continue

        try:
            tz = ZoneInfo(tz_name)
            dt = now_utc.astimezone(tz)
            utc_offset_str = _format_utc_offset(dt)
            region = _get_region(tz_name)
            display_name = _get_display_name(tz_name)

            timezones.append(
                TimezoneInfo(
                    name=tz_name,
                    utc_offset=utc_offset_str,
                    region=region,
                    display_name=display_name,
                )
            )
        except (KeyError, ValueError):
            continue

    return TimezoneListResponse(
        timezones=timezones,
        count=len(timezones),
    )


def get_current_time(tz_name: str = "UTC") -> CurrentTimeResponse:
    """Get current time in the specified timezone.

    Parameters
    ----------
    tz_name : str
        IANA timezone identifier. Defaults to "UTC".

    Returns
    -------
    CurrentTimeResponse
        Current time with formatted display strings.

    Raises
    ------
    ValueError
        If the timezone identifier is invalid.
    """
    try:
        tz = ZoneInfo(tz_name)
    except (KeyError, ValueError) as exc:
        raise ValueError(
            f"Unknown timezone: '{tz_name}'. "
            "Use GET /api/time/zones for valid options."
        ) from exc

    now = datetime.now(tz=timezone.utc).astimezone(tz)
    utc_offset_str = _format_utc_offset(now)

    formatted = FormattedTime(
        time_24h=now.strftime("%H:%M:%S"),
        time_12h=now.strftime("%I:%M:%S %p"),
        date=now.strftime("%B %d, %Y"),
        day_of_week=now.strftime("%A"),
    )

    return CurrentTimeResponse(
        datetime_str=now.isoformat(),
        timezone=tz_name,
        utc_offset=utc_offset_str,
        unix_timestamp=now.timestamp(),
        formatted=formatted,
    )
