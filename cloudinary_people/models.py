"""Pydantic models for the Cloudinary People Search API."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PersonStatus(str, Enum):
    """Status of a recognized person in Cloudinary."""

    ACTIVE = "active"
    HIDDEN = "hidden"


class NameStatus(str, Enum):
    """Filter for whether a person has been named."""

    ALL = "all"
    NAMED = "named"
    UNNAMED = "unnamed"


class SortBy(str, Enum):
    """Fields available for sorting list results."""

    NAME = "name"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"


class SortDirection(str, Enum):
    """Sort direction for list results."""

    ASC = "asc"
    DESC = "desc"


class BoundingBox(BaseModel):
    """Bounding box of a detected face within an asset.

    All coordinates are in pixels relative to the top-left corner of the image.
    """

    x: int = Field(description="Horizontal offset of the top-left corner of the bounding box.")
    y: int = Field(description="Vertical offset of the top-left corner of the bounding box.")
    width: int = Field(description="Width of the bounding box.")
    height: int = Field(description="Height of the bounding box.")

    @classmethod
    def from_list(cls, values: list[int]) -> "BoundingBox":
        """Construct from a 4-element ``[x, y, width, height]`` list."""
        if len(values) != 4:
            raise ValueError(f"bounding_box must have exactly 4 elements, got {len(values)}")
        return cls(x=values[0], y=values[1], width=values[2], height=values[3])

    @model_validator(mode="before")
    @classmethod
    def coerce_list(cls, data: object) -> object:
        """Accept a raw ``[x, y, width, height]`` list from the API."""
        if isinstance(data, list):
            if len(data) != 4:
                raise ValueError(f"bounding_box must have exactly 4 elements, got {len(data)}")
            return {"x": data[0], "y": data[1], "width": data[2], "height": data[3]}
        return data


class Thumbnail(BaseModel):
    """Thumbnail image associated with a recognized person."""

    asset_id: Optional[str] = Field(
        None,
        description="External ID of the asset used for the thumbnail.",
    )
    bounding_box: Optional[BoundingBox] = Field(
        None,
        description="Bounding box (x, y, width, height) of the face in the asset.",
    )
    url: Optional[str] = Field(
        None,
        description="Secure delivery URL of the thumbnail asset.",
    )
    resource_type: Optional[str] = Field(
        None,
        description="Resource type of the asset (e.g. 'image').",
    )
    type: Optional[str] = Field(
        None,
        description="Upload type of the asset (e.g. 'upload').",
    )
    public_id: Optional[str] = Field(
        None,
        description="Public ID of the asset.",
    )
    version: Optional[int] = Field(
        None,
        description="Version number of the asset.",
    )


class PersonDetails(BaseModel):
    """Full details of a recognized person."""

    id: str = Field(description="Unique identifier of the person.")
    name: Optional[str] = Field(
        None,
        description="Display name of the person, or null if not yet named.",
    )
    status: Optional[PersonStatus] = Field(
        None,
        description="Current status of the person.",
    )
    thumbnail: Optional[Thumbnail] = Field(
        None,
        description="Thumbnail image for the person.",
    )
    created_at: Optional[datetime] = Field(
        None,
        description="Timestamp when the person was first detected.",
    )
    updated_at: Optional[datetime] = Field(
        None,
        description="Timestamp when the person record was last updated.",
    )


class ListPeopleResponse(BaseModel):
    """Response from the List People endpoint."""

    people: list[PersonDetails] = Field(
        default_factory=list,
        description="List of recognized person objects.",
    )
    next_cursor: Optional[str] = Field(
        None,
        description="Cursor to pass as `next_cursor` to retrieve the next page.",
    )


class GetPersonResponse(BaseModel):
    """Internal envelope for the Get Person endpoint response."""

    person: PersonDetails = Field(description="Details of the requested person.")


class UpdatePersonRequest(BaseModel):
    """Request body for updating a recognized person.

    At least one of ``name``, ``status``, or ``thumbnail_asset_id`` must be provided.
    """

    name: Optional[str] = Field(
        None,
        max_length=255,
        description="New display name for the person (max 255 characters).",
    )
    status: Optional[PersonStatus] = Field(
        None,
        description="New status for the person.",
    )
    thumbnail_asset_id: Optional[str] = Field(
        None,
        description="External ID of an asset whose face should become the thumbnail.",
    )

    @model_validator(mode="after")
    def at_least_one_field(self) -> "UpdatePersonRequest":
        """Ensure at least one updatable field is set."""
        if self.name is None and self.status is None and self.thumbnail_asset_id is None:
            raise ValueError(
                "At least one of 'name', 'status', or 'thumbnail_asset_id' must be provided."
            )
        return self

    def to_api_dict(self) -> dict:
        """Serialize only the fields that were explicitly set, ready for the API body."""
        return self.model_dump(exclude_none=True)


class UpdatePersonResponse(BaseModel):
    """Response from the Update Person endpoint.

    The ``id`` field maps from the API's ``person_id`` key so it is consistent
    with :class:`PersonDetails`.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(
        alias="person_id",
        description="Unique identifier of the updated person.",
    )
    name: Optional[str] = Field(
        None,
        description="Updated display name of the person.",
    )
    status: Optional[PersonStatus] = Field(
        None,
        description="Updated status of the person.",
    )
