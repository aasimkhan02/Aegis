"""Exceptions raised by assistant adapters."""

from typing import Any


class AdapterError(Exception):
    """Base exception for assistant adapter errors."""

    def __init__(self, message: str, provider: str = "unknown", details: Any = None):
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.details = details

    def __str__(self) -> str:
        return f"[{self.provider}] {self.message}"


class AdapterConnectionError(AdapterError):
    """Raised when connecting to an assistant provider fails or times out."""


class AdapterResponseError(AdapterError):
    """Raised when an assistant provider returns an HTTP error status or malformed response."""

    def __init__(
        self,
        message: str,
        provider: str = "unknown",
        status_code: int | None = None,
        details: Any = None,
    ):
        super().__init__(message, provider=provider, details=details)
        self.status_code = status_code


class AdapterConfigError(AdapterError):
    """Raised when an adapter is misconfigured or lacks mandatory parameters."""

