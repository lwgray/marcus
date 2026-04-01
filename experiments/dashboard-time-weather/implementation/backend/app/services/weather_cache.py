"""In-memory weather data cache with TTL."""

from datetime import datetime, timedelta, timezone

from app.models.weather import CacheEntry, WeatherData


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
        """Build a normalized cache key.

        Parameters
        ----------
        city : str
            City name.
        units : str
            Temperature units.

        Returns
        -------
        str
            Normalized cache key.
        """
        return f"weather:{city.lower().strip()}:{units}"

    def get(self, city: str, units: str) -> CacheEntry | None:
        """Retrieve a cache entry.

        Parameters
        ----------
        city : str
            City name.
        units : str
            Temperature units.

        Returns
        -------
        CacheEntry | None
            The cached entry, or None if not found.
            Caller should check ``is_expired`` to decide
            whether to refresh.
        """
        key = self._make_key(city, units)
        return self._cache.get(key)

    def set(self, city: str, units: str, data: WeatherData) -> None:
        """Store weather data in the cache.

        Parameters
        ----------
        city : str
            City name.
        units : str
            Temperature units.
        data : WeatherData
            Weather data to cache.
        """
        key = self._make_key(city, units)
        now = datetime.now(timezone.utc)
        self._cache[key] = CacheEntry(
            data=data,
            cached_at=now,
            expires_at=now + self._ttl,
        )
