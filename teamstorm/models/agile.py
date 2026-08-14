from __future__ import annotations

from uuid import UUID
from pydantic import Field
from .base import TsBaseModel

EstimatesType = str


class CreateAgileRequestBody(TsBaseModel):
    """
    Request body for POST /workspaces/{workspace}/agile -- turns a folder
    into an agile (Scrum/Kanban) board with the given estimation scheme.

    Swagger: CreateAgileRequestBody
    required: folderId, estimatesType
    """

    folder_id: UUID = Field(alias="folderId")
    estimates_type: EstimatesType = Field(alias="estimatesType")


class AgileModel(TsBaseModel):
    """
    An agile board: the agile configuration attached to a folder, returned by
    AgileAPI.get/list/create.

    Swagger: AgileModel
    required: estimatesType, folderId, id, name
    """

    id: UUID
    name: str
    folder_id: UUID = Field(alias="folderId")
    estimates_type: EstimatesType = Field(alias="estimatesType")
