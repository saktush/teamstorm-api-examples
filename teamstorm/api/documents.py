# teamstorm/api/documents.py
from __future__ import annotations

import builtins
from typing import Any

from pydantic import TypeAdapter

from teamstorm.api._base import BaseAPI
from teamstorm.models.common import UUIDStr
from teamstorm.models.documents import (
    CreateDocumentRequestBody,
    CreateDocumentWorkitemLinkRequestBody,
    DeleteDocumentWorkitemLinkRequestBody,
    DocumentModel,
    DocumentsStatusModelList,
    DocumentStatusModel,
    DocumentVersionModel,
    PatchDocumentRequestBody,
)
from teamstorm.models.workitems import WorkitemModel


class DocumentsAPI(BaseAPI):
    """
    Documents core CRUD: list/get/create/patch/delete plus block/unblock.

    7 ops (Documents tag). Document comments already live in
    DocumentCommentsAPI (teamstorm/api/comments.py, added in an earlier task);
    document<->workitem links live in DocumentWorkitemLinksAPI below;
    sharing and attachments are separate resources, out of scope here.
    """

    def list(
        self,
        workspace_key: str,
        *,
        from_token: str | None = None,
        max_items_count: int | None = None,
    ) -> list[DocumentModel]:
        """
        List every document in a workspace.

        workspace_key: workspace key or id.
        from_token: pagination cursor from a previous page's nextToken.
        max_items_count: page size (server default 50, max 1000).
        Returns: every DocumentModel across all pages.
        GET /workspaces/{workspace}/documents.
        NOTE: this endpoint IS paginated (fromToken/maxItemsCount query
        params, nextToken in the response envelope) -- uses get_all(), not a
        bare get().
        """
        params: dict[str, Any] = {}
        if from_token is not None:
            params["fromToken"] = from_token
        if max_items_count is not None:
            params["maxItemsCount"] = max_items_count

        data = self.client.get_all(f"/workspaces/{workspace_key}/documents", params=params or None)
        return TypeAdapter(list[DocumentModel]).validate_python(data)

    def get(self, workspace_key: str, *, document_id: UUIDStr) -> DocumentModel:
        """
        Fetch a single document by id.

        workspace_key: workspace key or id.
        document_id: document UUID (path segment).
        Returns: the matching DocumentModel.
        GET /workspaces/{workspace}/documents/{document}.
        """
        data = self.client.get(f"/workspaces/{workspace_key}/documents/{document_id}")
        return DocumentModel.model_validate(data)

    def create(self, workspace_key: str, body: CreateDocumentRequestBody) -> DocumentModel:
        """
        Create a new document.

        workspace_key: workspace key or id.
        body: see CreateDocumentRequestBody docstring for two verified server
        gotchas: body.parent_id is required (omitting it server-side breaks
        tree placement rather than defaulting to a safe root -- pass the
        workspace's own GUID to place the document at the workspace root),
        and body.content gets auto-wrapped in <p> tags by the server before
        storage.
        Returns: the created DocumentModel.
        POST /workspaces/{workspace}/documents.
        """
        payload = body.model_dump(mode="json", exclude_none=True)
        data = self.client.post(f"/workspaces/{workspace_key}/documents", payload)
        return DocumentModel.model_validate(data)

    def patch(
        self,
        workspace_key: str,
        *,
        document_id: UUIDStr,
        body: PatchDocumentRequestBody,
    ) -> DocumentModel:
        """
        Partially update a document's status -- the only field
        PatchDocumentRequestBody exposes (see its docstring: there is no way
        to change name/content after creation via the public API).

        workspace_key: workspace key or id.
        document_id: document UUID (path segment).
        body: partial document fields to update (status only).
        Returns: the updated DocumentModel.
        PATCH /workspaces/{workspace}/documents/{document}.
        NOTE: serialized with exclude_unset=True, exclude_none=False (not the
        POST/PUT default exclude_none=True): a field never assigned on body is
        omitted from the request (server: leave unchanged), while a field
        explicitly set to None is sent as JSON null (server: clear it).
        """
        payload = body.model_dump(mode="json", exclude_unset=True, exclude_none=False)
        data = self.client.patch(f"/workspaces/{workspace_key}/documents/{document_id}", payload)
        return DocumentModel.model_validate(data)

    def delete(self, workspace_key: str, *, document_id: UUIDStr) -> None:
        """
        Delete a document.

        workspace_key: workspace key or id.
        document_id: document UUID (path segment).
        Returns: None.
        DELETE /workspaces/{workspace}/documents/{document}.
        """
        self.client.delete(f"/workspaces/{workspace_key}/documents/{document_id}")
        return None

    def block(self, workspace_key: str, *, document_id: UUIDStr) -> DocumentModel:
        """
        Block a document, preventing further edits.

        workspace_key: workspace key or id.
        document_id: document UUID (path segment).
        Returns: the updated DocumentModel (isBlocked=True).
        POST /workspaces/{workspace}/documents/{document}/block.
        NOTE: body-less POST -- no request payload is sent.
        """
        data = self.client.post(f"/workspaces/{workspace_key}/documents/{document_id}/block")
        return DocumentModel.model_validate(data)

    def unblock(self, workspace_key: str, *, document_id: UUIDStr) -> DocumentModel:
        """
        Unblock a previously blocked document.

        workspace_key: workspace key or id.
        document_id: document UUID (path segment).
        Returns: the updated DocumentModel (isBlocked=False).
        POST /workspaces/{workspace}/documents/{document}/unblock.
        NOTE: body-less POST -- no request payload is sent.
        """
        data = self.client.post(f"/workspaces/{workspace_key}/documents/{document_id}/unblock")
        return DocumentModel.model_validate(data)


class DocumentVersionsAPI(BaseAPI):
    """
    Read-only version history for a document: list versions, fetch a document
    snapshot at a given version, and delete a historical version.

    3 ops (DocumentVersions tag).
    """

    def list(
        self,
        workspace_key: str,
        *,
        document_id: UUIDStr,
        from_token: str | None = None,
        max_items_count: int | None = None,
    ) -> list[DocumentVersionModel]:
        """
        List every version of a document.

        workspace_key: workspace key or id.
        document_id: document UUID (path segment).
        from_token: pagination cursor from a previous page's nextToken.
        max_items_count: page size (server default 50, max 1000).
        Returns: every DocumentVersionModel across all pages.
        GET /workspaces/{workspace}/documents/{document}/versions.
        NOTE: this endpoint IS paginated (fromToken/maxItemsCount query
        params, nextToken in the response envelope) -- uses get_all().
        """
        params: dict[str, Any] = {}
        if from_token is not None:
            params["fromToken"] = from_token
        if max_items_count is not None:
            params["maxItemsCount"] = max_items_count

        data = self.client.get_all(
            f"/workspaces/{workspace_key}/documents/{document_id}/versions",
            params=params or None,
        )
        return TypeAdapter(list[DocumentVersionModel]).validate_python(data)

    def get(self, workspace_key: str, *, document_id: UUIDStr, version: int) -> DocumentModel:
        """
        Fetch a document as it existed at a specific version number.

        workspace_key: workspace key or id.
        document_id: document UUID (path segment).
        version: the version number (documentVersion path segment, int32).
        Returns: DocumentModel -- the full document snapshot at that version
        (the response schema is DocumentModel, not DocumentVersionModel).
        GET /workspaces/{workspace}/documents/{document}/versions/{documentVersion}.
        """
        data = self.client.get(f"/workspaces/{workspace_key}/documents/{document_id}/versions/{version}")
        return DocumentModel.model_validate(data)

    def delete(self, workspace_key: str, *, document_id: UUIDStr, version: int) -> None:
        """
        Delete a specific historical version of a document.

        workspace_key: workspace key or id.
        document_id: document UUID (path segment).
        version: the version number (documentVersion path segment, int32).
        Returns: None.
        DELETE /workspaces/{workspace}/documents/{document}/versions/{documentVersion}.
        """
        self.client.delete(f"/workspaces/{workspace_key}/documents/{document_id}/versions/{version}")
        return None


class DocumentStatusesAPI(BaseAPI):
    """
    Workspace-configurable named statuses documents can be tagged with (e.g.
    "Draft", "Approved") -- read-only via the public API: no create/patch/
    delete endpoint exists for document statuses.

    2 ops (DocumentsStatuses tag).
    """

    def list(self, workspace_key: str) -> list[DocumentStatusModel]:
        """
        List every document status defined in a workspace.

        workspace_key: workspace key or id.
        Returns: every DocumentStatusModel in the workspace.
        GET /workspaces/{workspace}/documents-statuses.
        NOTE: this endpoint does NOT paginate (no fromToken/maxItemsCount
        query params; DocumentsStatusModelList has no nextToken field) --
        uses a plain get() and unwraps "items", not get_all().
        """
        data = self.client.get(f"/workspaces/{workspace_key}/documents-statuses")
        return DocumentsStatusModelList.model_validate(data).items

    def get(self, workspace_key: str, *, status_key: str) -> DocumentStatusModel:
        """
        Fetch a single document status by id or name.

        workspace_key: workspace key or id.
        status_key: document status UUID or name (path segment).
        Returns: the matching DocumentStatusModel.
        GET /workspaces/{workspace}/documents-statuses/{status}.
        """
        data = self.client.get(f"/workspaces/{workspace_key}/documents-statuses/{status_key}")
        return DocumentStatusModel.model_validate(data)


class DocumentWorkitemLinksAPI(BaseAPI):
    """
    Untyped links between a document and one or more workitems -- the bridge
    between DocumentsAPI (this module) and LinksAPI (teamstorm/api/links.py, which
    covers workitem-to-workitem links only).

    4 ops (DocumentLinks tag). The surface is asymmetric: list()/create()/
    delete() are document-scoped, nested under
    /documents/{document}/workitem-links. The reverse lookup -- "what
    documents does this workitem link to" -- is workitem-scoped
    (/workitems/{workitem}/document-links) and is exposed here as
    list_by_workitem(), so both directions of the relationship live in one
    class even though 3 of the 4 routes hang off the document.

    Unlike WorkitemLinkModel (teamstorm/models/links.py), these links carry no
    `type`/relation kind: per docs/api-analysis/upstream-semantics.md
    ("Links" section), document<->workitem links are untyped.
    """

    def list(self, workspace_key: str, *, document_id: UUIDStr) -> list[WorkitemModel]:
        """
        List every workitem linked to a document.

        workspace_key: workspace key or id.
        document_id: document UUID (path segment).
        Returns: every WorkitemModel linked to the document (bare array in
        the response -- not paginated, no fromToken/maxItemsCount on this
        endpoint).
        GET /workspaces/{workspace}/documents/{document}/workitem-links.
        """
        data = self.client.get_all(f"/workspaces/{workspace_key}/documents/{document_id}/workitem-links")
        return TypeAdapter(list[WorkitemModel]).validate_python(data)

    def create(
        self,
        workspace_key: str,
        *,
        document_id: UUIDStr,
        body: CreateDocumentWorkitemLinkRequestBody,
    ) -> None:
        """
        Link a workitem to a document.

        workspace_key: workspace key or id.
        document_id: document UUID (path segment).
        body: the target workitem's key/GUID plus the workspace it lives in
        (workitemWorkspace) -- unlike workitem-to-workitem links, this
        endpoint does not resolve the workitem tenant-wide.
        Returns: None (server responds 204 No Content).
        POST /workspaces/{workspace}/documents/{document}/workitem-links.
        """
        payload = body.model_dump(mode="json", exclude_none=True)
        self.client.post(f"/workspaces/{workspace_key}/documents/{document_id}/workitem-links", payload)
        return None

    def delete(
        self,
        workspace_key: str,
        *,
        document_id: UUIDStr,
        body: DeleteDocumentWorkitemLinkRequestBody,
    ) -> None:
        """
        Remove the link between a document and one workitem.

        workspace_key: workspace key or id.
        document_id: document UUID (path segment).
        body: identifies which linked workitem to unlink (workitem key/GUID
        plus workitemWorkspace). NOTE: this is the only DELETE operation in
        the whole spec that carries a request body instead of a path id or
        query params -- the route is the bare collection path with no
        linkId, so this body is what selects the one link removed; it does
        not delete every workitem-link on the document.
        Returns: None (server responds 204 No Content).
        DELETE /workspaces/{workspace}/documents/{document}/workitem-links.
        """
        payload = body.model_dump(mode="json", exclude_none=True)
        self.client.delete(
            f"/workspaces/{workspace_key}/documents/{document_id}/workitem-links",
            body=payload,
        )
        return None

    def list_by_workitem(self, workspace_key: str, *, workitem_id: UUIDStr) -> builtins.list[DocumentModel]:
        """
        List every document linked to a workitem (the reverse direction).

        workspace_key: workspace key or id.
        workitem_id: workitem UUID (path segment).
        Returns: every DocumentModel linked to the workitem (bare array, not
        paginated).
        GET /workspaces/{workspace}/workitems/{workitem}/document-links.
        NOTE: despite being workitem-scoped, this route ships under the
        DocumentLinks controller/tag per swagger and
        docs/api-analysis/upstream-semantics.md ("Routing quirk") -- kept
        here rather than in LinksAPI so both directions of the document<->
        workitem relationship live in one class.
        """
        data = self.client.get_all(f"/workspaces/{workspace_key}/workitems/{workitem_id}/document-links")
        return TypeAdapter(list[DocumentModel]).validate_python(data)
