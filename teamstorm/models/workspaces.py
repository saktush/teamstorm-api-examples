from __future__ import annotations

from uuid import UUID

from pydantic import Field

from .base import TsBaseModel
from .common import UserModel


class CreateWorkspaceRequestBody(TsBaseModel):
    """
    Request body for POST /workspaces.

    Swagger: CreateWorkspaceRequestBody
    required: key, name
    """

    key: str
    name: str
    description: str | None = None


class PatchWorkspaceRequestBody(TsBaseModel):
    """
    Request body for PATCH /workspaces/{workspace}.

    Swagger: PatchWorkspaceRequestBody
    required: (none -- every field optional, partial-merge PATCH)
    """

    name: str | None = None
    description: str | None = None


class WorkspaceModel(TsBaseModel):
    """
    Swagger: WorkspaceModel [1]
    required: id, key, name
    """

    id: UUID
    key: str
    name: str
    description: str | None = None
    author: UserModel | None = None


class WorkspaceModelList(TsBaseModel):
    """
    Swagger: WorkspaceModelList
    required: items

    Not currently used by WorkspacesAPI.list() (which unwraps the envelope via
    client.get_all() + TypeAdapter(List[WorkspaceModel]) instead, per the
    repo's dominant list() convention) -- kept as a strict, correctly-aliased
    model of the /workspaces envelope shape for any future caller that needs
    the raw paginated response object.
    """

    from_token: str | None = Field(default=None, alias="fromToken")
    max_items_count: int | None = Field(default=None, alias="maxItemsCount")
    next_token: str | None = Field(default=None, alias="nextToken")
    items: list[WorkspaceModel]
