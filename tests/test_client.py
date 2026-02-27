"""Unit tests for CloudinaryPeopleClient.

Uses the `responses` library to mock HTTP calls so no real network
traffic is made during the test suite.
"""

from __future__ import annotations

import pytest
import pydantic
import requests.exceptions
import responses as rsps_lib

from cloudinary_people import (
    APIValidationError,
    AuthenticationError,
    CloudinaryPeopleClient,
    FeatureNotEnabledError,
    ListPeopleResponse,
    NameStatus,
    NetworkError,
    PersonDetails,
    PersonNotFoundError,
    PersonStatus,
    SortBy,
    SortDirection,
    UpdatePersonResponse,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

CLOUD_NAME = "test-cloud"
API_KEY = "test-key"
API_SECRET = "test-secret"
BASE_URL = f"https://api.cloudinary.com/v1_1/{CLOUD_NAME}/people"

PERSON_ID = "f10f893da5a1586dca6764b22514aa0d25e6b867baffc4fb43a2318a25d8e5b2"

PERSON_PAYLOAD = {
    "id": PERSON_ID,
    "name": "Jane Doe",
    "status": "active",
    "thumbnail": {
        "asset_id": "abc123",
        "bounding_box": [10, 20, 100, 150],
        "url": "https://res.cloudinary.com/test-cloud/image/upload/v1/sample.jpg",
        "resource_type": "image",
        "type": "upload",
        "public_id": "sample",
        "version": 1234567890,
    },
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-20T14:45:00Z",
}


@pytest.fixture
def client() -> CloudinaryPeopleClient:
    return CloudinaryPeopleClient(
        cloud_name=CLOUD_NAME,
        api_key=API_KEY,
        api_secret=API_SECRET,
    )


# ---------------------------------------------------------------------------
# Constructor validation
# ---------------------------------------------------------------------------


def test_constructor_rejects_empty_cloud_name():
    with pytest.raises(ValueError, match="cloud_name"):
        CloudinaryPeopleClient(cloud_name="", api_key="k", api_secret="s")


def test_constructor_rejects_empty_api_key():
    with pytest.raises(ValueError, match="api_key"):
        CloudinaryPeopleClient(cloud_name="c", api_key="", api_secret="s")


def test_constructor_rejects_empty_api_secret():
    with pytest.raises(ValueError, match="api_secret"):
        CloudinaryPeopleClient(cloud_name="c", api_key="k", api_secret="")


# ---------------------------------------------------------------------------
# CLOUDINARY_URL environment variable
# ---------------------------------------------------------------------------


def test_constructor_reads_cloudinary_url(monkeypatch):
    monkeypatch.setenv("CLOUDINARY_URL", "cloudinary://mykey:mysecret@mycloud")
    client = CloudinaryPeopleClient()
    assert client._base_people_url.endswith("/mycloud/people")
    assert client._session.auth == ("mykey", "mysecret")


def test_constructor_explicit_creds_take_precedence(monkeypatch):
    monkeypatch.setenv("CLOUDINARY_URL", "cloudinary://envkey:envsecret@envcloud")
    client = CloudinaryPeopleClient(
        cloud_name="explicit-cloud",
        api_key="explicit-key",
        api_secret="explicit-secret",
    )
    assert client._base_people_url.endswith("/explicit-cloud/people")
    assert client._session.auth == ("explicit-key", "explicit-secret")


def test_constructor_partial_override_uses_env_for_missing(monkeypatch):
    monkeypatch.setenv("CLOUDINARY_URL", "cloudinary://envkey:envsecret@envcloud")
    client = CloudinaryPeopleClient(cloud_name="override-cloud")
    assert client._base_people_url.endswith("/override-cloud/people")
    assert client._session.auth == ("envkey", "envsecret")


def test_constructor_raises_when_no_credentials_and_no_env(monkeypatch):
    monkeypatch.delenv("CLOUDINARY_URL", raising=False)
    with pytest.raises(ValueError, match="CLOUDINARY_URL"):
        CloudinaryPeopleClient()


def test_constructor_raises_on_malformed_cloudinary_url(monkeypatch):
    monkeypatch.setenv("CLOUDINARY_URL", "https://mykey:mysecret@mycloud")
    with pytest.raises(ValueError, match="cloudinary://"):
        CloudinaryPeopleClient()


def test_constructor_raises_on_incomplete_cloudinary_url(monkeypatch):
    monkeypatch.setenv("CLOUDINARY_URL", "cloudinary://mycloud")
    with pytest.raises(ValueError, match="cloudinary://api_key:api_secret@cloud_name"):
        CloudinaryPeopleClient()


def test_constructor_raises_on_cloudinary_url_missing_cloud_name(monkeypatch):
    monkeypatch.setenv("CLOUDINARY_URL", "cloudinary://mykey:mysecret@")
    with pytest.raises(ValueError, match="cloudinary://api_key:api_secret@cloud_name"):
        CloudinaryPeopleClient()


def test_constructor_partial_override_api_key_only(monkeypatch):
    monkeypatch.setenv("CLOUDINARY_URL", "cloudinary://envkey:envsecret@envcloud")
    client = CloudinaryPeopleClient(api_key="override-key")
    assert client._base_people_url.endswith("/envcloud/people")
    assert client._session.auth == ("override-key", "envsecret")


def test_constructor_partial_override_api_secret_only(monkeypatch):
    monkeypatch.setenv("CLOUDINARY_URL", "cloudinary://envkey:envsecret@envcloud")
    client = CloudinaryPeopleClient(api_secret="override-secret")
    assert client._base_people_url.endswith("/envcloud/people")
    assert client._session.auth == ("envkey", "override-secret")


@rsps_lib.activate
def test_list_people_uses_credentials_from_env(monkeypatch):
    """Full round-trip: client built from CLOUDINARY_URL makes an authenticated request."""
    monkeypatch.setenv("CLOUDINARY_URL", "cloudinary://envkey:envsecret@envcloud")
    env_base_url = "https://api.cloudinary.com/v1_1/envcloud/people"
    rsps_lib.add(
        rsps_lib.GET,
        env_base_url,
        json={"people": [PERSON_PAYLOAD], "next_cursor": None},
        status=200,
    )

    client = CloudinaryPeopleClient()
    response = client.list_people()

    assert len(response.people) == 1
    assert response.people[0].name == "Jane Doe"
    assert len(rsps_lib.calls) == 1
    sent_request = rsps_lib.calls[0].request
    import base64
    expected_token = base64.b64encode(b"envkey:envsecret").decode()
    assert sent_request.headers["Authorization"] == f"Basic {expected_token}"


# ---------------------------------------------------------------------------
# list_people
# ---------------------------------------------------------------------------


@rsps_lib.activate
def test_list_people_default(client: CloudinaryPeopleClient):
    rsps_lib.add(
        rsps_lib.GET,
        BASE_URL,
        json={"people": [PERSON_PAYLOAD], "next_cursor": None},
        status=200,
    )

    result = client.list_people()

    assert isinstance(result, ListPeopleResponse)
    assert len(result.people) == 1
    assert result.people[0].name == "Jane Doe"
    assert result.people[0].status == PersonStatus.ACTIVE
    assert result.next_cursor is None


@rsps_lib.activate
def test_list_people_with_all_params(client: CloudinaryPeopleClient):
    rsps_lib.add(
        rsps_lib.GET,
        BASE_URL,
        json={"people": [], "next_cursor": "cursor-token"},
        status=200,
    )

    result = client.list_people(
        max_results=20,
        next_cursor="prev-cursor",
        name_status=NameStatus.NAMED,
        name_prefix="Jane",
        status=PersonStatus.ACTIVE,
        sort_by=SortBy.CREATED_AT,
        direction=SortDirection.DESC,
    )

    assert result.next_cursor == "cursor-token"
    req = rsps_lib.calls[0].request
    assert "max_results=20" in req.url
    assert "name_status=named" in req.url
    assert "name_prefix=Jane" in req.url
    assert "status=active" in req.url
    assert "sort_by=created_at" in req.url
    assert "direction=desc" in req.url


@rsps_lib.activate
def test_list_people_returns_empty_list(client: CloudinaryPeopleClient):
    rsps_lib.add(rsps_lib.GET, BASE_URL, json={"people": []}, status=200)
    result = client.list_people()
    assert result.people == []


# ---------------------------------------------------------------------------
# get_person
# ---------------------------------------------------------------------------


@rsps_lib.activate
def test_get_person_success(client: CloudinaryPeopleClient):
    rsps_lib.add(
        rsps_lib.GET,
        f"{BASE_URL}/{PERSON_ID}",
        json={"person": PERSON_PAYLOAD},
        status=200,
    )

    person = client.get_person(PERSON_ID)

    assert isinstance(person, PersonDetails)
    assert person.id == PERSON_ID
    assert person.name == "Jane Doe"
    assert person.thumbnail is not None
    bb = person.thumbnail.bounding_box
    assert bb is not None
    assert bb.x == 10
    assert bb.y == 20
    assert bb.width == 100
    assert bb.height == 150


def test_get_person_empty_id_raises(client: CloudinaryPeopleClient):
    with pytest.raises(ValueError, match="person_id"):
        client.get_person("")


@rsps_lib.activate
def test_get_person_not_found(client: CloudinaryPeopleClient):
    rsps_lib.add(
        rsps_lib.GET,
        f"{BASE_URL}/{PERSON_ID}",
        json={"error": {"message": f"Can't find Person with id {PERSON_ID}"}},
        status=404,
    )

    with pytest.raises(PersonNotFoundError) as exc_info:
        client.get_person(PERSON_ID)

    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# update_person
# ---------------------------------------------------------------------------


@rsps_lib.activate
def test_update_person_name(client: CloudinaryPeopleClient):
    rsps_lib.add(
        rsps_lib.PUT,
        f"{BASE_URL}/{PERSON_ID}",
        json={"person_id": PERSON_ID, "name": "Jane Doe", "status": "active"},
        status=200,
    )

    result = client.update_person(person_id=PERSON_ID, name="Jane Doe")

    assert isinstance(result, UpdatePersonResponse)
    assert result.id == PERSON_ID
    assert result.name == "Jane Doe"
    assert result.status == PersonStatus.ACTIVE


@rsps_lib.activate
def test_update_person_status(client: CloudinaryPeopleClient):
    rsps_lib.add(
        rsps_lib.PUT,
        f"{BASE_URL}/{PERSON_ID}",
        json={"person_id": PERSON_ID, "name": None, "status": "hidden"},
        status=200,
    )

    result = client.update_person(person_id=PERSON_ID, status=PersonStatus.HIDDEN)
    assert result.status == PersonStatus.HIDDEN


@rsps_lib.activate
def test_update_person_thumbnail(client: CloudinaryPeopleClient):
    asset_id = "2262b0b5eb88f1fd7724e29b0e57d730"
    rsps_lib.add(
        rsps_lib.PUT,
        f"{BASE_URL}/{PERSON_ID}",
        json={"person_id": PERSON_ID, "name": "Jane Doe", "status": "active"},
        status=200,
    )

    result = client.update_person(person_id=PERSON_ID, thumbnail_asset_id=asset_id)
    assert result.id == PERSON_ID

    req_body = rsps_lib.calls[0].request.body
    body_str = req_body.decode() if isinstance(req_body, bytes) else req_body
    assert asset_id in body_str


def test_update_person_no_fields_raises(client: CloudinaryPeopleClient):
    with pytest.raises(pydantic.ValidationError):
        client.update_person(person_id=PERSON_ID)


def test_update_person_empty_id_raises(client: CloudinaryPeopleClient):
    with pytest.raises(ValueError, match="person_id"):
        client.update_person(person_id="", name="Test")


# ---------------------------------------------------------------------------
# Error mapping
# ---------------------------------------------------------------------------


@rsps_lib.activate
def test_authentication_error(client: CloudinaryPeopleClient):
    rsps_lib.add(
        rsps_lib.GET,
        BASE_URL,
        json={"error": {"message": "Invalid credentials"}},
        status=401,
    )
    with pytest.raises(AuthenticationError) as exc_info:
        client.list_people()
    assert exc_info.value.status_code == 401


@rsps_lib.activate
def test_feature_not_enabled_error(client: CloudinaryPeopleClient):
    rsps_lib.add(
        rsps_lib.GET,
        BASE_URL,
        json={"error": {"message": "People Search is not enabled for this customer"}},
        status=403,
    )
    with pytest.raises(FeatureNotEnabledError) as exc_info:
        client.list_people()
    assert exc_info.value.status_code == 403


@rsps_lib.activate
def test_api_validation_error(client: CloudinaryPeopleClient):
    rsps_lib.add(
        rsps_lib.GET,
        BASE_URL,
        json={"error": {"message": "Invalid sort_by value"}},
        status=400,
    )
    with pytest.raises(APIValidationError) as exc_info:
        client.list_people()
    assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# Network-level failure
# ---------------------------------------------------------------------------


@rsps_lib.activate
def test_network_error_on_connection_failure(client: CloudinaryPeopleClient):
    rsps_lib.add(
        rsps_lib.GET,
        BASE_URL,
        body=requests.exceptions.ConnectionError("simulated network failure"),
    )
    with pytest.raises(NetworkError):
        client.list_people()


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


@rsps_lib.activate
def test_context_manager_usage():
    rsps_lib.add(
        rsps_lib.GET,
        BASE_URL,
        json={"people": []},
        status=200,
    )
    with CloudinaryPeopleClient(
        cloud_name=CLOUD_NAME, api_key=API_KEY, api_secret=API_SECRET
    ) as c:
        result = c.list_people()
    assert result.people == []


# ---------------------------------------------------------------------------
# Custom base_url and timeout
# ---------------------------------------------------------------------------


def test_custom_base_url_is_used():
    custom_url = "https://staging.example.com/v1_1"
    c = CloudinaryPeopleClient(
        cloud_name=CLOUD_NAME, api_key=API_KEY, api_secret=API_SECRET, base_url=custom_url
    )
    assert c._base_people_url == f"{custom_url}/{CLOUD_NAME}/people"


def test_custom_timeout_is_stored():
    c = CloudinaryPeopleClient(
        cloud_name=CLOUD_NAME, api_key=API_KEY, api_secret=API_SECRET, timeout=5.0
    )
    assert c._timeout == 5.0
