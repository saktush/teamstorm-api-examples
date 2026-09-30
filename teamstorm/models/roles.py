from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import Field

from .base import TsBaseModel
from .common import UserModel


class Permission(StrEnum):
    """
    Swagger: Permission -- the fixed vocabulary of grantable permissions used
    in `RoleModel.permissions` / `CreateRoleRequestBody.permissions` /
    `PatchRoleRequestBody.permissions`. Covers workspace-, workitem- and
    document-scoped actions (e.g. `WorkitemCreate`, `DocumentBlock`,
    `WorkspaceAccessEdit`); this is the authoritative wire vocabulary, not a
    client-side approximation of it.
    """

    WorkspaceContentRead = "WorkspaceContentRead"
    WorkspaceEdit = "WorkspaceEdit"
    WorkspaceQueryManagement = "WorkspaceQueryManagement"
    WorkspaceAccessEdit = "WorkspaceAccessEdit"
    WorkspaceIntegrationsEdit = "WorkspaceIntegrationsEdit"
    WorkspaceDelete = "WorkspaceDelete"
    WorkspaceWorkitemTypesEdit = "WorkspaceWorkitemTypesEdit"
    WorkspaceAttributesEdit = "WorkspaceAttributesEdit"
    WorkspaceWorkflowsEdit = "WorkspaceWorkflowsEdit"
    WorkspaceAutomationRulesEdit = "WorkspaceAutomationRulesEdit"
    WorkspaceFolderCreate = "WorkspaceFolderCreate"
    WorkspaceFolderEdit = "WorkspaceFolderEdit"
    WorkspaceFolderDelete = "WorkspaceFolderDelete"
    WorkspaceViewCreate = "WorkspaceViewCreate"
    WorkspaceViewEdit = "WorkspaceViewEdit"
    WorkspaceViewDelete = "WorkspaceViewDelete"
    WorkspaceTicketsSettings = "WorkspaceTicketsSettings"
    WorkspaceTreeMove = "WorkspaceTreeMove"
    WorkitemCreate = "WorkitemCreate"
    WorkitemAssignEdit = "WorkitemAssignEdit"
    WorkitemStatusEdit = "WorkitemStatusEdit"
    WorkitemStatusEditForce = "WorkitemStatusEditForce"
    WorkitemAttributesEdit = "WorkitemAttributesEdit"
    WorkitemAttachmentsCreate = "WorkitemAttachmentsCreate"
    WorkitemAttachmentsDelete = "WorkitemAttachmentsDelete"
    WorkitemCommentsCreate = "WorkitemCommentsCreate"
    WorkitemCommentsEdit = "WorkitemCommentsEdit"
    WorkitemCommentsDelete = "WorkitemCommentsDelete"
    WorkitemCommentsForceDelete = "WorkitemCommentsForceDelete"
    WorkitemRelationsCreate = "WorkitemRelationsCreate"
    WorkitemRelationsDelete = "WorkitemRelationsDelete"
    WorkitemDelete = "WorkitemDelete"
    WorkitemMove = "WorkitemMove"
    WorkitemTimeTrackCreateEditDelete = "WorkitemTimeTrackCreateEditDelete"
    WorkitemTimeTrackEditDeleteForce = "WorkitemTimeTrackEditDeleteForce"
    WorkspaceTimeTrackReport = "WorkspaceTimeTrackReport"
    WorkspaceExport = "WorkspaceExport"
    ExtensionsEdit = "ExtensionsEdit"
    WorkitemSharing = "WorkitemSharing"
    WikiInlineCommentResolve = "WikiInlineCommentResolve"
    WikiInlineCommentResolveForce = "WikiInlineCommentResolveForce"
    WorkspaceWebhook = "WorkspaceWebhook"
    DocumentCreate = "DocumentCreate"
    DocumentEdit = "DocumentEdit"
    DocumentStatusEdit = "DocumentStatusEdit"
    DocumentVersionsRead = "DocumentVersionsRead"
    DocumentVersionsRestore = "DocumentVersionsRestore"
    DocumentVersionsDelete = "DocumentVersionsDelete"
    DocumentAttachmentsCreate = "DocumentAttachmentsCreate"
    DocumentAttachmentsDelete = "DocumentAttachmentsDelete"
    DocumentCommentsCreate = "DocumentCommentsCreate"
    DocumentCommentsEdit = "DocumentCommentsEdit"
    DocumentCommentsForceEdit = "DocumentCommentsForceEdit"
    DocumentCommentsDelete = "DocumentCommentsDelete"
    DocumentCommentsForceDelete = "DocumentCommentsForceDelete"
    DocumentRelationsCreate = "DocumentRelationsCreate"
    DocumentRelationsDelete = "DocumentRelationsDelete"
    DocumentMove = "DocumentMove"
    DocumentDelete = "DocumentDelete"
    DocumentForceDelete = "DocumentForceDelete"
    DocumentSharing = "DocumentSharing"
    DocumentExport = "DocumentExport"
    DocumentBlock = "DocumentBlock"
    WorkspaceDocumentsRead = "WorkspaceDocumentsRead"
    WorkspaceTimeMetrics = "WorkspaceTimeMetrics"


class SimpleRoleModel(TsBaseModel):
    """
    A role's id/name only, without its permission list -- the shape returned
    when listing the roles assigned *to* a user or group, as opposed to
    fetching a role's own full definition (see `RoleModel`).

    Swagger: SimpleRoleModel
    required: id, name
    """

    id: UUID
    name: str


class SimpleRoleModelList(TsBaseModel):
    """
    Response envelope for GET /workspaces/{workspace}/users/{user}/roles and
    GET /workspaces/{workspace}/groups/{group}/roles.

    Swagger: SimpleRoleModelList
    """

    roles: list[SimpleRoleModel]


class RoleModel(TsBaseModel):
    """
    A workspace role: a named, authored set of `Permission`s that can be
    granted to users/groups.

    Swagger: RoleModel
    required: author, id, isSystem, name, permissions
    """

    id: UUID
    name: str
    author: UserModel
    is_system: bool = Field(alias="isSystem")
    permissions: list[Permission]


class RolesModelList(TsBaseModel):
    """
    Paginated response envelope for GET /workspaces/{workspace}/roles.

    Swagger: RolesModelList
    required: items
    """

    from_token: str | None = Field(default=None, alias="fromToken")
    max_items_count: int | None = Field(default=None, alias="maxItemsCount")
    next_token: str | None = Field(default=None, alias="nextToken")
    items: list[RoleModel]


class CreateRoleRequestBody(TsBaseModel):
    """
    Request body for POST /workspaces/{workspace}/roles.

    Swagger: CreateRoleRequestBody
    required: name, permissions
    """

    name: str
    permissions: list[Permission]


class PatchRoleRequestBody(TsBaseModel):
    """
    Request body for PATCH /workspaces/{workspace}/roles/{role}.

    Swagger: PatchRoleRequestBody
    required: (none -- every field optional, partial-merge PATCH)
    """

    name: str | None = None
    permissions: list[Permission] | None = None
