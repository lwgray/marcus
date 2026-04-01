"""Custom exceptions for the Weather Information Service."""


class WeatherServiceError(Exception):
    """Base exception for weather service errors.

    Attributes
    ----------
    code : str
        Machine-readable error code.
    message : str
        Human-readable error message.
    status_code : int
        HTTP status code to return.
    """

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 500,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class CityNotFoundError(WeatherServiceError):
    """Raised when the requested city is not found."""

    def __init__(self, city: str) -> None:
        super().__init__(
            code="CITY_NOT_FOUND",
            message=f"Could not find weather data for '{city}'",
            status_code=404,
        )


class InvalidApiKeyError(WeatherServiceError):
    """Raised when the API key is invalid."""

    def __init__(self) -> None:
        super().__init__(
            code="INVALID_API_KEY",
            message="Weather API key is invalid or expired",
            status_code=401,
        )


class RateLimitedError(WeatherServiceError):
    """Raised when the external API rate limit is exceeded."""

    def __init__(self) -> None:
        super().__init__(
            code="RATE_LIMITED",
            message="Weather API rate limit exceeded. Please try again later.",
            status_code=429,
        )


class ExternalServiceError(WeatherServiceError):
    """Raised when the external weather API is unavailable."""

    def __init__(self, detail: str = "") -> None:
        msg = "Weather service is temporarily unavailable"
        if detail:
            msg = f"{msg}: {detail}"
        super().__init__(
            code="SERVICE_UNAVAILABLE",
            message=msg,
            status_code=503,
        )
