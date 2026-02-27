"""Typed exceptions for the Cloudinary People Search SDK.

HTTP status codes are mapped to specific exception classes so callers
can catch only the errors they care about.
"""

from __future__ import annotations

from typing import Optional


class CloudinaryPeopleError(Exception):
    """Base exception for all Cloudinary People Search SDK errors.

    Attributes:
        message: Human-readable description of the error.
        status_code: HTTP status code returned by the API, if applicable.
        raw_response: The raw response body as a string, if available.
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        raw_response: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.raw_response = raw_response

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"status_code={self.status_code!r})"
        )


class AuthenticationError(CloudinaryPeopleError):
    """Raised when the API returns HTTP 401.

    Typically caused by an invalid API key or API secret.
    """


class FeatureNotEnabledError(CloudinaryPeopleError):
    """Raised when the API returns HTTP 403.

    People Search must be enabled for the product environment before
    these endpoints can be used.
    """


class PersonNotFoundError(CloudinaryPeopleError):
    """Raised when the API returns HTTP 404.

    The requested ``person_id`` does not exist in the product environment.
    """


class APIValidationError(CloudinaryPeopleError):
    """Raised when the API returns HTTP 400.

    Indicates a bad request, such as an invalid parameter value or a
    missing required field. Named ``APIValidationError`` to avoid confusion
    with ``pydantic.ValidationError``, which is raised for local model
    validation failures.
    """


class ServerError(CloudinaryPeopleError):
    """Raised when the API returns HTTP 5xx.

    Indicates an unexpected error on Cloudinary's side.
    """


class NetworkError(CloudinaryPeopleError):
    """Raised when a network-level failure occurs before a response is received.

    Examples: DNS resolution failure, connection refused, read/write timeout.
    The original ``requests`` exception is available as ``__cause__``.
    """


def raise_for_status(status_code: int, message: str, raw_response: str) -> None:
    """Map an HTTP error status code to the appropriate SDK exception and raise it.

    Args:
        status_code: The HTTP status code from the API response.
        message: Error message extracted from the response body.
        raw_response: The raw response body string (for debugging).

    Raises:
        APIValidationError: For 400 responses.
        AuthenticationError: For 401 responses.
        FeatureNotEnabledError: For 403 responses.
        PersonNotFoundError: For 404 responses.
        ServerError: For 5xx responses.
        CloudinaryPeopleError: For any other non-2xx status.
    """
    if status_code == 400:
        raise APIValidationError(message, status_code=status_code, raw_response=raw_response)
    if status_code == 401:
        raise AuthenticationError(message, status_code=status_code, raw_response=raw_response)
    if status_code == 403:
        raise FeatureNotEnabledError(message, status_code=status_code, raw_response=raw_response)
    if status_code == 404:
        raise PersonNotFoundError(message, status_code=status_code, raw_response=raw_response)
    if status_code >= 500:
        raise ServerError(message, status_code=status_code, raw_response=raw_response)
    raise CloudinaryPeopleError(message, status_code=status_code, raw_response=raw_response)
