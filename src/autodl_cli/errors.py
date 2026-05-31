from __future__ import annotations


class AutoDLError(Exception):
    """Base exception for autodl-cli failures."""


class AutoDLConfigError(AutoDLError):
    """Configuration is missing or invalid."""


class AutoDLHTTPError(AutoDLError):
    """The AutoDL API returned a non-successful HTTP response."""

    def __init__(self, message: str, *, status_code: int, body: str = "") -> None:
        self.status_code = status_code
        self.body = body
        super().__init__(message)


class AutoDLAPIError(AutoDLError):
    """The AutoDL API returned code != Success."""

    def __init__(self, message: str, *, code: str | None = None) -> None:
        self.code = code
        super().__init__(message)


class AutoDLAuthError(AutoDLAPIError):
    """Authentication failed."""


class AutoDLCapacityError(AutoDLAPIError):
    """No matching compute resource is currently available."""
