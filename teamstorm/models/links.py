from __future__ import annotations

from uuid import UUID

from pydantic import Field

from teamstorm.models.workitems import WorkitemModel

from .base import TsBaseModel


class LinkTypeModel(TsBaseModel):
    """
    A workitem link type (relation kind), e.g. "Relates to" / "Blocks".

    Swagger: LinkTypeModel
    required: id, name
    NOTE: link types are read-only, per-workspace, system/pre-seeded data
    (docs/api-analysis/upstream-semantics.md, "Links" section) -- they are
    not a fixed client-side enum. Always fetch the configured values via
    LinksAPI.list_types() rather than hardcoding ids/keys/names.
    """

    id: UUID
    name: str
    key: str | None = None


class LinkTypeModelList(TsBaseModel):
    """
    Response envelope for GET /workspaces/{workspace}/link-types.

    Swagger: LinkTypeModelList
    required: items
    """

    items: list[LinkTypeModel]


class WorkitemLinkModel(TsBaseModel):
    """
    A link from one workitem to another, together with its relation type.

    Swagger: WorkitemLinkModel
    required: id, type, linkedWorkitem
    """

    id: UUID
    type: LinkTypeModel
    linked_workitem: WorkitemModel = Field(alias="linkedWorkitem")


class CreateWorkitemLinkRequestBody(TsBaseModel):
    """
    Request body for POST /workspaces/{workspace}/workitems/{workitem}/links.

    Swagger: CreateWorkitemLinkRequestBody
    required: type, linkedWorkitem, linkedWorkspace
    NOTE: `type` is a plain string per swagger (no enum values enumerated).
    Per docs/api-analysis/upstream-semantics.md ("Links" section), it accepts
    either the link type's GUID or its exact name, resolved against the
    *source* workspace's own link-type configuration (see LinksAPI.list_types()).
    Link types are per-tenant, user-visible data, not a closed enum -- do not
    hardcode a fixed set of values here.
    `linkedWorkitem` is the target workitem's key or GUID.
    `linkedWorkspace` is the key/GUID of the workspace that owns the *target*
    workitem -- as of the 2026-07-31 spec it is required, so `linkedWorkitem`
    is NOT resolved tenant-wide on its own; the server needs to be told which
    workspace to look it up in.
    """

    type: str
    linked_workitem: str = Field(alias="linkedWorkitem")
    linked_workspace: str = Field(alias="linkedWorkspace")
