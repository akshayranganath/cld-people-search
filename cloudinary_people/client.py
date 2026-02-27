"""Main client for the Cloudinary People Search API."""

from __future__ import annotations

import logging
import os
import warnings
from urllib.parse import quote, urlparse
from typing import Optional

import requests
import requests.exceptions

from .exceptions import NetworkError, raise_for_status
from .models import (
    GetPersonResponse,
    ListPeopleResponse,
    NameStatus,
    PersonDetails,
    PersonStatus,
    SortBy,
    SortDirection,
    UpdatePersonRequest,
    UpdatePersonResponse,
)

logger = logging.getLogger("cloudinary_people")

_DEFAULT_BASE_URL = "https://api.cloudinary.com/v1_1"


def _parse_cloudinary_url(url: str) -> tuple[str, str, str]:
    """Parse a ``CLOUDINARY_URL`` string into ``(cloud_name, api_key, api_secret)``.

    Expected format: ``cloudinary://api_key:api_secret@cloud_name``

    Raises:
        ValueError: If the URL is malformed or missing required components.
    """
    parsed = urlparse(url)
    if parsed.scheme != "cloudinary":
        raise ValueError(
            "CLOUDINARY_URL must start with 'cloudinary://' "
            f"(got scheme '{parsed.scheme}')."
        )
    cloud_name = parsed.hostname
    api_key = parsed.username
    api_secret = parsed.password
    if not cloud_name or not api_key or not api_secret:
        raise ValueError(
            "CLOUDINARY_URL must be in the format "
            "'cloudinary://api_key:api_secret@cloud_name'."
        )
    return cloud_name, api_key, api_secret


class CloudinaryPeopleClient:
    """Client for the Cloudinary People Search API.

    Provides typed methods to list, retrieve, and update recognized people
    in a Cloudinary product environment. The People Search feature must be
    enabled for the target environment before these endpoints can be used.

    The client manages a :class:`requests.Session` internally for connection
    pooling. Use it as a context manager to ensure the session is closed
    cleanly::

        with CloudinaryPeopleClient(...) as client:
            people = client.list_people()

    Credentials can be supplied explicitly or omitted to let the client read
    them from the ``CLOUDINARY_URL`` environment variable
    (``cloudinary://api_key:api_secret@cloud_name``). Explicitly-supplied
    values always take precedence over the environment variable.

    Args:
        cloud_name: Your Cloudinary cloud name.  If ``None``, read from
            ``CLOUDINARY_URL``.
        api_key: Your Cloudinary API key (used as the HTTP Basic Auth username).
            If ``None``, read from ``CLOUDINARY_URL``.
        api_secret: Your Cloudinary API secret (used as the HTTP Basic Auth
            password).  If ``None``, read from ``CLOUDINARY_URL``.
        base_url: Override the API base URL (useful for testing or staging
            environments).  Defaults to ``https://api.cloudinary.com/v1_1``.
        timeout: Seconds to wait for a response before raising
            :class:`NetworkError`.  Defaults to ``30.0``.

    Example — explicit credentials::

        from cloudinary_people import CloudinaryPeopleClient

        client = CloudinaryPeopleClient(
            cloud_name="my-cloud",
            api_key="123456789012345",
            api_secret="abcdefghijklmnopqrstuvwxyz",
        )

    Example — credentials from ``CLOUDINARY_URL``::

        # export CLOUDINARY_URL=cloudinary://api_key:api_secret@cloud_name
        client = CloudinaryPeopleClient()

        people = client.list_people(max_results=10)
        for person in people.people:
            print(person.id, person.name)
    """

    def __init__(
        self,
        cloud_name: Optional[str] = None,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = 30.0,
    ) -> None:
        if cloud_name is None or api_key is None or api_secret is None:
            env_url = os.environ.get("CLOUDINARY_URL")
            if not env_url:
                raise ValueError(
                    "Credentials are required. Pass cloud_name, api_key, and "
                    "api_secret explicitly, or set the CLOUDINARY_URL "
                    "environment variable."
                )
            env_cloud, env_key, env_secret = _parse_cloudinary_url(env_url)
            cloud_name = cloud_name or env_cloud
            api_key = api_key or env_key
            api_secret = api_secret or env_secret

        if not cloud_name:
            raise ValueError("cloud_name must not be empty.")
        if not api_key:
            raise ValueError("api_key must not be empty.")
        if not api_secret:
            raise ValueError("api_secret must not be empty.")

        if not base_url.startswith("https://"):
            warnings.warn(
                "base_url does not use HTTPS; credentials may be transmitted in plain text.",
                stacklevel=2,
            )

        self._base_people_url = f"{base_url}/{cloud_name}/people"
        self._timeout = timeout

        self._session = requests.Session()
        self._session.auth = (api_key, api_secret)

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "CloudinaryPeopleClient":
        return self

    def __exit__(self, *args: object) -> None:
        self._session.close()

    def close(self) -> None:
        """Close the underlying HTTP session and release connections."""
        self._session.close()

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def list_people(
        self,
        max_results: Optional[int] = None,
        next_cursor: Optional[str] = None,
        name_status: Optional[NameStatus] = None,
        name_prefix: Optional[str] = None,
        status: Optional[PersonStatus] = None,
        sort_by: Optional[SortBy] = None,
        direction: Optional[SortDirection] = None,
    ) -> ListPeopleResponse:
        """Return a paginated list of recognized people.

        Args:
            max_results: Maximum number of people to return (1–100, default 50).
            next_cursor: Cursor from a previous response to fetch the next page.
            name_status: Filter by naming state — ``all`` (default), ``named``,
                or ``unnamed``.
            name_prefix: Return only people whose names start with this prefix
                (case-insensitive).
            status: Filter by person status (``active`` or ``hidden``).
            sort_by: Field to sort by — ``name`` (default), ``created_at``,
                or ``updated_at``.
            direction: Sort direction — ``asc`` or ``desc``.

        Returns:
            A :class:`~cloudinary_people.models.ListPeopleResponse` containing
            the list of people and an optional ``next_cursor`` for pagination.

        Raises:
            APIValidationError: If a query parameter value is invalid.
            AuthenticationError: If the API key or secret is incorrect.
            FeatureNotEnabledError: If People Search is not enabled.
            NetworkError: If a connection-level failure occurs.
            CloudinaryPeopleError: For any other unexpected API error.

        Example::

            response = client.list_people(
                max_results=20,
                name_status=NameStatus.NAMED,
                sort_by=SortBy.CREATED_AT,
                direction=SortDirection.DESC,
            )
            for person in response.people:
                print(person.id, person.name)

            # Fetch next page
            if response.next_cursor:
                next_page = client.list_people(next_cursor=response.next_cursor)
        """
        params: dict = {}
        if max_results is not None:
            params["max_results"] = max_results
        if next_cursor is not None:
            params["next_cursor"] = next_cursor
        if name_status is not None:
            params["name_status"] = name_status.value
        if name_prefix is not None:
            params["name_prefix"] = name_prefix
        if status is not None:
            params["status"] = status.value
        if sort_by is not None:
            params["sort_by"] = sort_by.value
        if direction is not None:
            params["direction"] = direction.value

        data = self._request("GET", self._base_people_url, params=params)
        return ListPeopleResponse.model_validate(data)

    def get_person(self, person_id: str) -> PersonDetails:
        """Return details for a single recognized person.

        Args:
            person_id: The unique identifier of the person to retrieve.

        Returns:
            A :class:`~cloudinary_people.models.PersonDetails` object.

        Raises:
            PersonNotFoundError: If no person with ``person_id`` exists.
            AuthenticationError: If the API key or secret is incorrect.
            FeatureNotEnabledError: If People Search is not enabled.
            NetworkError: If a connection-level failure occurs.
            CloudinaryPeopleError: For any other unexpected API error.

        Example::

            person = client.get_person("f10f893da5a1586dca6764b22514aa0d25e6b867")
            print(person.name, person.status)
        """
        if not person_id:
            raise ValueError("person_id must not be empty.")

        url = f"{self._base_people_url}/{quote(person_id, safe='')}"
        data = self._request("GET", url)
        response = GetPersonResponse.model_validate(data)
        return response.person

    def update_person(
        self,
        person_id: str,
        name: Optional[str] = None,
        status: Optional[PersonStatus] = None,
        thumbnail_asset_id: Optional[str] = None,
    ) -> UpdatePersonResponse:
        """Update a recognized person's name, status, or thumbnail.

        At least one of ``name``, ``status``, or ``thumbnail_asset_id``
        must be provided.

        Args:
            person_id: The unique identifier of the person to update.
            name: New display name (max 255 characters). Pass ``None`` to leave
                unchanged.
            status: New status for the person. Pass ``None`` to leave unchanged.
            thumbnail_asset_id: External ID of an asset whose face should become
                the person's thumbnail. The asset must contain a face that matches
                this person. Pass ``None`` to leave unchanged.

        Returns:
            An :class:`~cloudinary_people.models.UpdatePersonResponse` with the
            updated ``id``, ``name``, and ``status``.

        Raises:
            ValueError: If no updatable field is provided or ``person_id`` is empty.
            APIValidationError: If a field value is invalid (e.g. name too long,
                asset has no face, asset face does not match this person).
            PersonNotFoundError: If no person with ``person_id`` exists.
            AuthenticationError: If the API key or secret is incorrect.
            FeatureNotEnabledError: If People Search is not enabled.
            NetworkError: If a connection-level failure occurs.
            CloudinaryPeopleError: For any other unexpected API error.

        Example::

            result = client.update_person(
                person_id="f10f893da5a1586dca6764b22514aa0d25e6b867",
                name="Jane Doe",
                status=PersonStatus.ACTIVE,
            )
            print(result.id, result.name)
        """
        if not person_id:
            raise ValueError("person_id must not be empty.")

        payload = UpdatePersonRequest(
            name=name,
            status=status,
            thumbnail_asset_id=thumbnail_asset_id,
        )
        url = f"{self._base_people_url}/{quote(person_id, safe='')}"
        data = self._request("PUT", url, body=payload.to_api_dict())
        return UpdatePersonResponse.model_validate(data)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        url: str,
        params: Optional[dict] = None,
        body: Optional[dict] = None,
    ) -> dict:
        """Execute an authenticated HTTP request and return the parsed JSON body.

        Args:
            method: HTTP method (``"GET"``, ``"PUT"``, etc.).
            url: Full URL to request.
            params: Optional query string parameters.
            body: Optional JSON request body (for PUT requests).

        Returns:
            Parsed JSON response as a dict.

        Raises:
            NetworkError: If a connection-level failure occurs (timeout, DNS, etc.).
            CloudinaryPeopleError: (or a subclass) if the response status is not 2xx.
        """
        logger.debug("→ %s %s", method, url)
        if params:
            logger.debug("  params: %s", params)
        if body:
            logger.debug("  body:   %s", body)

        try:
            response = self._session.request(
                method,
                url,
                params=params,
                json=body,
                timeout=self._timeout,
            )
        except requests.exceptions.RequestException as exc:
            raise NetworkError(str(exc)) from exc

        logger.debug("← %s %s", response.status_code, response.reason)

        if not response.ok:
            raw = response.text
            try:
                error_msg = response.json().get("error", {}).get("message", raw)
            except Exception:
                error_msg = raw
            raise_for_status(response.status_code, error_msg, raw)

        result: dict = response.json()
        logger.debug("  response: %s", result)
        return result
