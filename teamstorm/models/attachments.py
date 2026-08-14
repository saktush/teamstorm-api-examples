# teamstorm/models/attachments.py
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from .base import TsBaseModel
from .common import UserModel
from .enums import AntivirusScanVerdict


class AttachmentModel(TsBaseModel):
    """
    Swagger: AttachmentModel
    required: attachmentId, workspaceId, createdBy, fileId, name, size, type,
    version, createdAt, antivirusVerdict

    One version of one file attachment on a workitem or document. `version`
    is the running version number for this `attachmentId`. On the public
    API, `fileId` always equals `str(attachmentId)` and `version` is always
    1 -- see WorkitemAttachmentsAPI's module docstring
    (teamstorm/api/attachments.py) and docs/api-analysis/upstream-semantics.md
    "Attachment upload/download flow" for why the public route cannot
    itself produce version 2+.
    """

    attachment_id: UUID = Field(alias="attachmentId")
    workspace_id: UUID = Field(alias="workspaceId")
    created_by: UserModel = Field(alias="createdBy")
    file_id: str = Field(alias="fileId")
    name: str
    version: int
    type: str
    size: int
    created_at: datetime = Field(alias="createdAt")
    antivirus_verdict: AntivirusScanVerdict = Field(alias="antivirusVerdict")


class AttachmentModelList(TsBaseModel):
    """
    Swagger: AttachmentModelList
    required: items

    Bare-array envelope -- no fromToken/maxItemsCount/nextToken fields exist
    on this schema, so both the list() and list_versions() endpoints that
    return it are unpaginated.
    """

    items: list[AttachmentModel]
