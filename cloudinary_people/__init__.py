"""Cloudinary People Search SDK.

A lightweight Python SDK for the Cloudinary People Search API, providing
typed access to list, retrieve, and update recognized people in a Cloudinary
product environment.

Quick start::

    from cloudinary_people import CloudinaryPeopleClient, PersonStatus

    client = CloudinaryPeopleClient(
        cloud_name="my-cloud",
        api_key="123456789012345",
        api_secret="abcdefghijklmnopqrstuvwxyz",
    )

    # List all recognized people
    response = client.list_people(max_results=10)
    for person in response.people:
        print(person.id, person.name, person.status)

    # Get a specific person
    person = client.get_person("f10f893da5a1586dca6764b22514aa0d25e6b867")

    # Update a person
    result = client.update_person(
        person_id=person.id,
        name="Jane Doe",
        status=PersonStatus.ACTIVE,
    )
"""

from .client import CloudinaryPeopleClient
from .exceptions import (
    APIValidationError,
    AuthenticationError,
    CloudinaryPeopleError,
    FeatureNotEnabledError,
    NetworkError,
    PersonNotFoundError,
    ServerError,
)
from .models import (
    BoundingBox,
    ListPeopleResponse,
    NameStatus,
    PersonDetails,
    PersonStatus,
    SortBy,
    SortDirection,
    Thumbnail,
    UpdatePersonRequest,
    UpdatePersonResponse,
)

__all__ = [
    # Client
    "CloudinaryPeopleClient",
    # Models
    "PersonStatus",
    "NameStatus",
    "SortBy",
    "SortDirection",
    "BoundingBox",
    "Thumbnail",
    "PersonDetails",
    "ListPeopleResponse",
    "UpdatePersonRequest",
    "UpdatePersonResponse",
    # Exceptions
    "CloudinaryPeopleError",
    "APIValidationError",
    "AuthenticationError",
    "FeatureNotEnabledError",
    "NetworkError",
    "PersonNotFoundError",
    "ServerError",
]

__version__ = "0.1.0"
