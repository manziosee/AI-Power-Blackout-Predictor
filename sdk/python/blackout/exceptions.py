class BlackoutAPIError(Exception):
    """Raised when the API returns a non-2xx response."""
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail}")


class BlackoutAuthError(BlackoutAPIError):
    """Raised on 401 / 403 responses."""


class BlackoutNotFoundError(BlackoutAPIError):
    """Raised on 404 responses."""


class BlackoutRateLimitError(BlackoutAPIError):
    """Raised on 429 responses."""
    def __init__(self, retry_after: int | None = None) -> None:
        self.retry_after = retry_after
        super().__init__(429, f"Rate limit exceeded. Retry after {retry_after}s.")
