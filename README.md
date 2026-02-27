# cloudinary-people

A typed Python SDK for the [Cloudinary People Search API](https://cloudinary.github.io/api-schemas/index.html?schema=api&viewer=stoplight#/operations/listPeople).

> **Prerequisite:** People Search must be enabled for your Cloudinary product environment before these endpoints can be used.

---

## Installation

```bash
pip install cloudinary-people
```

Or directly from source:

```bash
git clone https://github.com/akshayranganath/cld-people-search.git
cd cld-people-search
pip install -e ".[dev]"
```

---

## Quick Start

**Option 1 — credentials from environment variable (recommended)**

```bash
export CLOUDINARY_URL=cloudinary://api_key:api_secret@cloud_name
```

```python
from cloudinary_people import CloudinaryPeopleClient

client = CloudinaryPeopleClient()   # reads CLOUDINARY_URL automatically

response = client.list_people(max_results=10)
for person in response.people:
    print(person.id, person.name, person.status)
```

**Option 2 — explicit credentials**

```python
client = CloudinaryPeopleClient(
    cloud_name="my-cloud",
    api_key="123456789012345",
    api_secret="abcdefghijklmnopqrstuvwxyz",
)
```

Explicit values always take precedence over `CLOUDINARY_URL`. You can also mix them — any credential not passed explicitly is read from the environment variable.

---

## API Reference

### `CloudinaryPeopleClient(cloud_name=None, api_key=None, api_secret=None, ...)`

Creates a new client instance.

Credentials can be supplied explicitly or omitted; in that case they are read
from the `CLOUDINARY_URL` environment variable
(`cloudinary://api_key:api_secret@cloud_name`).  Explicit values always win.

| Parameter    | Type   | Required | Description                                          |
|-------------|--------|----------|------------------------------------------------------|
| `cloud_name` | `str`  | No*      | Your Cloudinary cloud name                           |
| `api_key`    | `str`  | No*      | API key (used as Basic Auth username)                |
| `api_secret` | `str`  | No*      | API secret (used as Basic Auth password)             |
| `timeout`    | `float`| No       | Request timeout in seconds (default `30.0`)          |

\* Required unless `CLOUDINARY_URL` is set in the environment.

---

### `list_people(...) → ListPeopleResponse`

Returns a paginated list of all recognized people in the product environment.

```python
from cloudinary_people import NameStatus, PersonStatus, SortBy, SortDirection

response = client.list_people(
    max_results=20,          # 1–100, default 50
    next_cursor="...",       # for pagination
    name_status=NameStatus.NAMED,
    name_prefix="Jane",
    status=PersonStatus.ACTIVE,
    sort_by=SortBy.CREATED_AT,
    direction=SortDirection.DESC,
)

for person in response.people:
    print(person.id, person.name)

# Fetch next page
if response.next_cursor:
    next_page = client.list_people(next_cursor=response.next_cursor)
```

**Parameters**

| Parameter     | Type            | Description                                                        |
|--------------|-----------------|--------------------------------------------------------------------|
| `max_results` | `int`           | Max people to return (1–100, default 50)                           |
| `next_cursor` | `str`           | Pagination cursor from the previous response                       |
| `name_status` | `NameStatus`    | `all` (default) \| `named` \| `unnamed`                           |
| `name_prefix` | `str`           | Return only people whose name starts with this prefix              |
| `status`      | `PersonStatus`  | `active` \| `hidden`                                               |
| `sort_by`     | `SortBy`        | `name` (default) \| `created_at` \| `updated_at`                 |
| `direction`   | `SortDirection` | `asc` \| `desc`                                                    |

---

### `get_person(person_id) → PersonDetails`

Returns full details of a single recognized person.

```python
person = client.get_person("f10f893da5a1586dca6764b22514aa0d25e6b867baffc4fb43a2318a25d8e5b2")
print(person.name, person.status, person.thumbnail.url)
```

---

### `update_person(person_id, name=None, status=None, thumbnail_asset_id=None) → UpdatePersonResponse`

Updates a person's name, status, or thumbnail. At least one field must be provided.

```python
from cloudinary_people import PersonStatus

result = client.update_person(
    person_id="f10f893da5a1586dca6764b22514aa0d25e6b867baffc4fb43a2318a25d8e5b2",
    name="Jane Doe",
    status=PersonStatus.ACTIVE,
)
print(result.id, result.name, result.status)
```

---

## Models

| Model                  | Fields                                                               |
|-----------------------|----------------------------------------------------------------------|
| `PersonDetails`        | `id`, `name`, `status`, `thumbnail`, `created_at`, `updated_at`    |
| `Thumbnail`            | `asset_id`, `bounding_box`, `url`, `resource_type`, `type`, `public_id`, `version` |
| `ListPeopleResponse`   | `people: list[PersonDetails]`, `next_cursor: str \| None`           |
| `UpdatePersonResponse` | `person_id`, `name`, `status`                                        |

### Enums

| Enum            | Values                            |
|----------------|-----------------------------------|
| `PersonStatus`  | `active`, `hidden`                |
| `NameStatus`    | `all`, `named`, `unnamed`         |
| `SortBy`        | `name`, `created_at`, `updated_at` |
| `SortDirection` | `asc`, `desc`                     |

---

## Exceptions

All exceptions extend `CloudinaryPeopleError` and expose `.message` and `.status_code`.

| Exception               | HTTP Status | Cause                                          |
|------------------------|-------------|------------------------------------------------|
| `AuthenticationError`   | 401         | Invalid API key or secret                      |
| `FeatureNotEnabledError`| 403         | People Search not enabled for the environment  |
| `PersonNotFoundError`   | 404         | No person found for the given `person_id`      |
| `APIValidationError`    | 400         | Invalid parameter value or missing field       |
| `ServerError`           | 5xx         | Unexpected server-side error                   |

```python
from cloudinary_people import PersonNotFoundError, AuthenticationError

try:
    person = client.get_person("nonexistent-id")
except PersonNotFoundError as e:
    print(f"Not found: {e.message}")
except AuthenticationError as e:
    print(f"Auth failed ({e.status_code}): {e.message}")
```

---

## Running Tests

```bash
pip install -e ".[dev]"
pytest
```

---

## Verbose Logging

All requests and responses are logged via the `cloudinary_people` logger at `DEBUG` level. Enable it using Python's standard `logging` module:

```python
import logging

logging.getLogger("cloudinary_people").setLevel(logging.DEBUG)
logging.basicConfig(level=logging.DEBUG)

client = CloudinaryPeopleClient(
    cloud_name="my-cloud",
    api_key="...",
    api_secret="...",
)
```

---

## License

MIT
