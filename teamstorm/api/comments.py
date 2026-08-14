# teamstorm/api/comments.py
from __future__ import annotations

from uuid import UUID

from teamstorm.api._base import BaseAPI
from teamstorm.models.comments import (
    CommentModel,
    CommentModelList,
    CommentVisibilitySettingsModel,
    CreateCommentRequestBody,
    UpdateCommentRequestBody,
    UpdateCommentVisibilitySettingsRequestBody,
)
from teamstorm.models.common import UUIDStr


class WorkitemCommentsAPI(BaseAPI):
    """
    Threaded comments on workitems, including per-comment visibility settings.

    6 ops (WorkitemComments tag): list/create/update/delete on the comment
    itself, plus get/update on the comment's visibility sub-resource.
    """

    def list(self, workspace_key: str, *, workitem_id: UUIDStr) -> list[CommentModel]:
        """
        List every comment on a workitem.

        workspace_key: workspace key.
        workitem_id: workitem UUID (path segment).
        Returns: every CommentModel on the workitem.
        GET /workspaces/{workspace}/workitems/{workitem}/comments.
        NOTE: this endpoint does not paginate (no fromToken/maxItemsCount query
        params, no nextToken in the response) -- uses a plain get(), not get_all().
        """
        data = self.client.get(f"/workspaces/{workspace_key}/workitems/{workitem_id}/comments")
        return CommentModelList.model_validate(data).items

    def create(
        self,
        workspace_key: str,
        *,
        workitem_id: UUIDStr,
        body: CreateCommentRequestBody,
    ) -> CommentModel:
        """
        Add a new comment to a workitem.

        workspace_key: workspace key.
        workitem_id: workitem UUID (path segment).
        body: comment text.
        Returns: the created CommentModel.
        POST /workspaces/{workspace}/workitems/{workitem}/comments.
        """
        payload = body.model_dump(mode="json", exclude_none=True)
        data = self.client.post(f"/workspaces/{workspace_key}/workitems/{workitem_id}/comments", payload)
        return CommentModel.model_validate(data)

    def update(
        self,
        workspace_key: str,
        *,
        workitem_id: UUIDStr,
        comment_id: UUID,
        body: UpdateCommentRequestBody,
    ) -> CommentModel:
        """
        Replace a workitem comment's text.

        workspace_key: workspace key.
        workitem_id: workitem UUID (path segment).
        comment_id: comment UUID (path segment).
        body: new comment text (full replace, not a partial patch).
        Returns: the updated CommentModel.
        PUT /workspaces/{workspace}/workitems/{workitem}/comments/{commentId}.
        NOTE: this is a PUT (full replace), so the body is serialized with
        exclude_none=True, not exclude_unset -- unlike PATCH endpoints elsewhere.
        """
        payload = body.model_dump(mode="json", exclude_none=True)
        data = self.client.put(
            f"/workspaces/{workspace_key}/workitems/{workitem_id}/comments/{comment_id}",
            payload,
        )
        return CommentModel.model_validate(data)

    def delete(self, workspace_key: str, *, workitem_id: UUIDStr, comment_id: UUID) -> None:
        """
        Delete a comment from a workitem.

        workspace_key: workspace key.
        workitem_id: workitem UUID (path segment).
        comment_id: comment UUID (path segment).
        Returns: None.
        DELETE /workspaces/{workspace}/workitems/{workitem}/comments/{commentId}.
        """
        self.client.delete(f"/workspaces/{workspace_key}/workitems/{workitem_id}/comments/{comment_id}")
        return None

    def get_visibility(
        self,
        workspace_key: str,
        *,
        workitem_id: UUIDStr,
        comment_id: UUID,
    ) -> CommentVisibilitySettingsModel:
        """
        Get a comment's visibility settings.

        workspace_key: workspace key.
        workitem_id: workitem UUID (path segment).
        comment_id: comment UUID (path segment).
        Returns: the CommentVisibilitySettingsModel (visibility type + access list).
        GET /workspaces/{workspace}/workitems/{workitem}/comments/{commentId}/visibility.
        """
        data = self.client.get(f"/workspaces/{workspace_key}/workitems/{workitem_id}/comments/{comment_id}/visibility")
        return CommentVisibilitySettingsModel.model_validate(data)

    def update_visibility(
        self,
        workspace_key: str,
        *,
        workitem_id: UUIDStr,
        comment_id: UUID,
        body: UpdateCommentVisibilitySettingsRequestBody,
    ) -> CommentVisibilitySettingsModel:
        """
        Replace a comment's visibility settings.

        workspace_key: workspace key.
        workitem_id: workitem UUID (path segment).
        comment_id: comment UUID (path segment).
        body: new visibility type + access list (full replace).
        Returns: the updated CommentVisibilitySettingsModel.
        PUT /workspaces/{workspace}/workitems/{workitem}/comments/{commentId}/visibility.
        """
        payload = body.model_dump(mode="json", exclude_none=True)
        data = self.client.put(
            f"/workspaces/{workspace_key}/workitems/{workitem_id}/comments/{comment_id}/visibility",
            payload,
        )
        return CommentVisibilitySettingsModel.model_validate(data)


class DocumentCommentsAPI(BaseAPI):
    """
    Threaded comments on documents.

    3 ops (DocumentComments tag): list/create/delete only -- unlike
    WorkitemCommentsAPI, there is no update endpoint and no visibility
    sub-resource for document comments. Documents themselves are addressed
    purely by id here; the Documents resource is out of scope for this module.
    """

    def list(self, workspace_key: str, *, document_id: UUIDStr) -> list[CommentModel]:
        """
        List every comment on a document.

        workspace_key: workspace key.
        document_id: document UUID (path segment).
        Returns: every CommentModel on the document.
        GET /workspaces/{workspace}/documents/{document}/comments.
        NOTE: this endpoint does not paginate -- uses a plain get(), not get_all().
        """
        data = self.client.get(f"/workspaces/{workspace_key}/documents/{document_id}/comments")
        return CommentModelList.model_validate(data).items

    def create(
        self,
        workspace_key: str,
        *,
        document_id: UUIDStr,
        body: CreateCommentRequestBody,
    ) -> CommentModel:
        """
        Add a new comment to a document.

        workspace_key: workspace key.
        document_id: document UUID (path segment).
        body: comment text.
        Returns: the created CommentModel.
        POST /workspaces/{workspace}/documents/{document}/comments.
        """
        payload = body.model_dump(mode="json", exclude_none=True)
        data = self.client.post(f"/workspaces/{workspace_key}/documents/{document_id}/comments", payload)
        return CommentModel.model_validate(data)

    def delete(self, workspace_key: str, *, document_id: UUIDStr, comment_id: UUID) -> None:
        """
        Delete a comment from a document.

        workspace_key: workspace key.
        document_id: document UUID (path segment).
        comment_id: comment UUID (path segment).
        Returns: None.
        DELETE /workspaces/{workspace}/documents/{document}/comments/{commentId}.
        """
        self.client.delete(f"/workspaces/{workspace_key}/documents/{document_id}/comments/{comment_id}")
        return None
