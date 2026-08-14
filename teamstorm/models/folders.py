# teamstorm/models/folders.py
from __future__ import annotations

from uuid import UUID

from pydantic import Field

from .base import TsBaseModel


class FolderModel(TsBaseModel):
    """
    Swagger: FolderModel [1]
    required: id, name, parentId
    """

    id: UUID
    name: str
    description: str | None = None
    parent_id: UUID = Field(alias="parentId")


class CreateFolderRequestBody(TsBaseModel):
    """
    Swagger: CreateFolderRequestBody
    required: name
    NOTE: Swagger marks parentId as nullable, but this model deliberately requires it.
    Omitting parentId makes the server substitute Guid.Empty, which breaks downstream
    services (see docs/api-analysis/upstream-semantics.md). Being stricter than the spec
    on an outbound body is intentional; do not widen this to Optional.
    """

    name: str
    parent_id: UUID = Field(alias="parentId")
    description: str | None = None


class PatchFolderRequestBody(TsBaseModel):
    """
    Swagger: PatchFolderRequestBody
    required: (none — every field optional, partial-merge PATCH)

    The API layer serializes this with exclude_unset=True (and exclude_none=False
    to override TsBaseModel's own default): a field never assigned here is
    omitted from the request entirely (server: leave unchanged), while a field
    explicitly assigned None is sent as JSON null (server: clear this field).
    See docs/api-analysis/upstream-semantics.md §7.
    """

    name: str | None = None
    description: str | None = None
    parent_id: UUID | None = Field(default=None, alias="parentId")
