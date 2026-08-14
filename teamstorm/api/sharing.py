# teamstorm/api/sharing.py
from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import TypeAdapter

from teamstorm.api._base import BaseAPI
from teamstorm.client import TsClient
from teamstorm.models.common import UUIDStr
from teamstorm.models.sharing import (
    CreateSharedDocumentPermission,
    CreateSharedWorkitemPermission,
    PatchSharedDocumentPermissionBody,
    PatchSharedWorkitemPermissionBody,
    SharedDocumentPermission,
    SharedWorkitemPermission,
)

_WORKITEM_PERMISSION_ADAPTER: TypeAdapter = TypeAdapter(SharedWorkitemPermission)
_WORKITEM_PERMISSION_LIST_ADAPTER: TypeAdapter = TypeAdapter(list[SharedWorkitemPermission])
_DOCUMENT_PERMISSION_ADAPTER: TypeAdapter = TypeAdapter(SharedDocumentPermission)
_DOCUMENT_PERMISSION_LIST_ADAPTER: TypeAdapter = TypeAdapter(list[SharedDocumentPermission])


# ---------------------------------------------------------------------------
# Shared marshalling helpers.
#
# WorkitemSharingAPI and DocumentSharingAPI expose the identical 4-operation
# shape (list/create/patch/delete) against two different resources. Only the
# path prefix and the pydantic models differ; the actual HTTP-verb dispatch,
# request-body serialization and response validation are factored here once
# instead of being duplicated across the two classes.
# ---------------------------------------------------------------------------


def _list_shared_permissions(client: TsClient, path: str, list_adapter: TypeAdapter) -> list[Any]:
    """
    GET the sharing-permission collection at *path* and validate it.

    Bare-array response, no fromToken/maxItemsCount query params on this
    endpoint -- unpaginated, so get_all() is used purely for its safe
    bare-array short-circuit (see teamstorm.client.extract_items_and_token), not
    because the endpoint actually paginates.
    """
    data = client.get_all(path)
    return list_adapter.validate_python(data)


def _create_shared_permission(client: TsClient, path: str, body: Any, single_adapter: TypeAdapter) -> Any:
    """
    POST a new sharing permission to *path*.

    Full-representation create: model_dump(mode="json", exclude_none=True),
    not a partial update.
    """
    payload = body.model_dump(mode="json", exclude_none=True)
    data = client.post(path, payload)
    return single_adapter.validate_python(data)


def _patch_shared_permission(client: TsClient, path: str, body: Any, single_adapter: TypeAdapter) -> Any:
    """
    PATCH an existing sharing permission at *path*.

    Real partial update: model_dump(mode="json", exclude_unset=True,
    exclude_none=False). exclude_unset drops a field the caller never
    assigned (server: leave unchanged); exclude_none=False still sends an
    explicitly-assigned None as JSON null (server: a legal, distinct value)
    instead of silently dropping it -- see
    docs/api-analysis/upstream-semantics.md "PATCH".
    """
    payload = body.model_dump(mode="json", exclude_unset=True, exclude_none=False)
    data = client.patch(path, payload)
    return single_adapter.validate_python(data)


def _delete_shared_permission(client: TsClient, path: str) -> None:
    """DELETE the sharing permission at *path*. Returns None (204 No Content)."""
    client.delete(path)
    return None


class WorkitemSharingAPI(BaseAPI):
    """
    Direct, per-principal sharing permissions on a single workitem.

    A sharing permission is an access grant layered on top of whatever
    workspace-role-based access already applies: it names one user or one
    group and a Read/Edit/Comment access level for that principal on this
    one workitem.

    - create() GRANTS access: the named user, or every current and future
      member of the named group, immediately gains the given access level
      on the workitem -- they may not have been able to see it at all
      before this call.
    - patch() MODIFIES an existing grant's access level in place (e.g.
      Read -> Edit) for the same, unchanged principal. It does not
      reassign the permission to a different user or group.
    - delete() REVOKES the grant: the named principal immediately loses
      this direct access to the workitem (they may still retain access
      separately if their workspace role independently allows it).

    4 ops (WorkitemsSharing tag): list/create on the collection,
    patch/delete on a single permission identified by permissionId.
    """

    def list(self, workspace_key: str, *, workitem_id: UUIDStr) -> list[SharedWorkitemPermission]:
        """
        List every sharing permission granted on a workitem -- i.e. every
        user/group that currently has direct (non-role-based) access to it,
        and at what level.

        workspace_key: workspace key or id.
        workitem_id: workitem UUID (path segment).
        Returns: every SharedWorkitemUserPermissionModel /
        SharedWorkitemGroupPermissionModel granted on the workitem.
        GET /workspaces/{workspace}/workitems/{workitem}/sharing.
        """
        path = f"/workspaces/{workspace_key}/workitems/{workitem_id}/sharing"
        return _list_shared_permissions(self.client, path, _WORKITEM_PERMISSION_LIST_ADAPTER)

    def create(
        self,
        workspace_key: str,
        *,
        workitem_id: UUIDStr,
        body: CreateSharedWorkitemPermission,
    ) -> SharedWorkitemPermission:
        """
        Grant a user or group direct access to a workitem. This changes who
        can see and act on the workitem: the named principal gains access
        they may not have had before.

        workspace_key: workspace key or id.
        workitem_id: workitem UUID (path segment).
        body: CreateSharedWorkitemUserPermissionBody or
        CreateSharedWorkitemGroupPermissionBody -- selects exactly one
        principal (userId or groupId) plus the accessLevel (Read/Edit/
        Comment) to grant.
        Returns: the created SharedWorkitemUserPermissionModel /
        SharedWorkitemGroupPermissionModel (includes the new permissionId).
        POST /workspaces/{workspace}/workitems/{workitem}/sharing.
        """
        path = f"/workspaces/{workspace_key}/workitems/{workitem_id}/sharing"
        return _create_shared_permission(self.client, path, body, _WORKITEM_PERMISSION_ADAPTER)

    def patch(
        self,
        workspace_key: str,
        *,
        workitem_id: UUIDStr,
        permission_id: UUID,
        body: PatchSharedWorkitemPermissionBody,
    ) -> SharedWorkitemPermission:
        """
        Change the access level of an existing workitem sharing permission
        in place. This modifies what the existing principal (unchanged) is
        allowed to do with the workitem -- it does not change who the
        permission applies to.

        workspace_key: workspace key or id.
        workitem_id: workitem UUID (path segment).
        permission_id: the sharing permission's own UUID (path segment, from
        a prior list()/create() response's permissionId) -- not the user's
        or group's id.
        body: PatchSharedWorkitemPermissionBody; a partial update, so only an
        explicitly-set accessLevel is sent.
        Returns: the updated SharedWorkitemUserPermissionModel /
        SharedWorkitemGroupPermissionModel.
        PATCH /workspaces/{workspace}/workitems/{workitem}/sharing/{permissionId}.
        """
        path = f"/workspaces/{workspace_key}/workitems/{workitem_id}/sharing/{permission_id}"
        return _patch_shared_permission(self.client, path, body, _WORKITEM_PERMISSION_ADAPTER)

    def delete(self, workspace_key: str, *, workitem_id: UUIDStr, permission_id: UUID) -> None:
        """
        Revoke a sharing permission on a workitem. This immediately removes
        the named user's or group's direct access grant to the workitem --
        they may still retain access separately via their workspace role.

        workspace_key: workspace key or id.
        workitem_id: workitem UUID (path segment).
        permission_id: the sharing permission's own UUID (path segment).
        Returns: None.
        DELETE /workspaces/{workspace}/workitems/{workitem}/sharing/{permissionId}.
        """
        path = f"/workspaces/{workspace_key}/workitems/{workitem_id}/sharing/{permission_id}"
        return _delete_shared_permission(self.client, path)


class DocumentSharingAPI(BaseAPI):
    """
    Direct, per-principal sharing permissions on a single document.

    Structurally identical to WorkitemSharingAPI (same 4 operations, same
    semantics), scoped to a document instead of a workitem -- see
    docs/api-analysis/upstream-semantics.md "Sharing / Permissions".

    - create() GRANTS access: the named user, or every current and future
      member of the named group, immediately gains the given access level
      on the document.
    - patch() MODIFIES an existing grant's access level in place for the
      same, unchanged principal.
    - delete() REVOKES the grant: the named principal immediately loses
      this direct access to the document (they may still retain access
      separately if their workspace role independently allows it).

    4 ops (DocumentsSharing tag): list/create on the collection,
    patch/delete on a single permission identified by permissionId.
    """

    def list(self, workspace_key: str, *, document_id: UUIDStr) -> list[SharedDocumentPermission]:
        """
        List every sharing permission granted on a document -- i.e. every
        user/group that currently has direct (non-role-based) access to it,
        and at what level.

        workspace_key: workspace key or id.
        document_id: document UUID (path segment).
        Returns: every SharedDocumentUserPermissionModel /
        SharedDocumentGroupPermissionModel granted on the document.
        GET /workspaces/{workspace}/documents/{document}/sharing.
        """
        path = f"/workspaces/{workspace_key}/documents/{document_id}/sharing"
        return _list_shared_permissions(self.client, path, _DOCUMENT_PERMISSION_LIST_ADAPTER)

    def create(
        self,
        workspace_key: str,
        *,
        document_id: UUIDStr,
        body: CreateSharedDocumentPermission,
    ) -> SharedDocumentPermission:
        """
        Grant a user or group direct access to a document. This changes who
        can see and act on the document: the named principal gains access
        they may not have had before.

        workspace_key: workspace key or id.
        document_id: document UUID (path segment).
        body: CreateSharedDocumentUserPermissionBody or
        CreateSharedDocumentGroupPermissionBody -- selects exactly one
        principal (userId or groupId) plus the accessLevel (Read/Edit/
        Comment) to grant.
        Returns: the created SharedDocumentUserPermissionModel /
        SharedDocumentGroupPermissionModel (includes the new permissionId).
        POST /workspaces/{workspace}/documents/{document}/sharing.
        """
        path = f"/workspaces/{workspace_key}/documents/{document_id}/sharing"
        return _create_shared_permission(self.client, path, body, _DOCUMENT_PERMISSION_ADAPTER)

    def patch(
        self,
        workspace_key: str,
        *,
        document_id: UUIDStr,
        permission_id: UUID,
        body: PatchSharedDocumentPermissionBody,
    ) -> SharedDocumentPermission:
        """
        Change the access level of an existing document sharing permission
        in place. This modifies what the existing principal (unchanged) is
        allowed to do with the document -- it does not change who the
        permission applies to.

        workspace_key: workspace key or id.
        document_id: document UUID (path segment).
        permission_id: the sharing permission's own UUID (path segment, from
        a prior list()/create() response's permissionId) -- not the user's
        or group's id.
        body: PatchSharedDocumentPermissionBody; a partial update, so only an
        explicitly-set accessLevel is sent.
        Returns: the updated SharedDocumentUserPermissionModel /
        SharedDocumentGroupPermissionModel.
        PATCH /workspaces/{workspace}/documents/{document}/sharing/{permissionId}.
        """
        path = f"/workspaces/{workspace_key}/documents/{document_id}/sharing/{permission_id}"
        return _patch_shared_permission(self.client, path, body, _DOCUMENT_PERMISSION_ADAPTER)

    def delete(self, workspace_key: str, *, document_id: UUIDStr, permission_id: UUID) -> None:
        """
        Revoke a sharing permission on a document. This immediately removes
        the named user's or group's direct access grant to the document --
        they may still retain access separately via their workspace role.

        workspace_key: workspace key or id.
        document_id: document UUID (path segment).
        permission_id: the sharing permission's own UUID (path segment).
        Returns: None.
        DELETE /workspaces/{workspace}/documents/{document}/sharing/{permissionId}.
        """
        path = f"/workspaces/{workspace_key}/documents/{document_id}/sharing/{permission_id}"
        return _delete_shared_permission(self.client, path)
