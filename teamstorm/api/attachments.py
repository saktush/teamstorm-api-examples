# teamstorm/api/attachments.py
"""
File attachments on workitems and documents.

18 ops total, split 9/9 across WorkitemAttachmentsAPI (WorkitemAttachments
tag) and DocumentAttachmentsAPI (DocumentAttachments tag): list, get one,
download, list versions, get one version, upload, delete all, delete one,
delete one version. Both classes share their entire implementation via
_AttachmentsAPIBase below -- the two resources are structurally identical,
differing only in the `workitems`/`documents` parent path segment.

CRITICAL LIMITATION -- re-uploading to an existing attachmentId always
fails (verified against server source, see
docs/api-analysis/upstream-semantics.md "Attachment upload/download flow"):

There is no create-then-upload handshake on this API. `attachmentId` is
client-generated -- the caller mints a UUID and puts it directly in the
upload URL; there is no server round-trip to obtain one first. The public
upload route then forces the storage-layer `fileId` to equal
`str(attachmentId)`, and the upload handler rejects any file whose
`(objectId, fileId)` pair already exists with 400 Bad Request
("File.Conflict"). Because `fileId == attachmentId` is forced on this
route, that condition is met by definition the second time anyone uploads
to the same `attachmentId` -- so **it is never possible to add a new
version to an existing attachment through this API**, even though
list_versions()/get_version()/delete_version() all exist and work
correctly for whichever versions the server already holds (e.g. created
through a non-public internal path). Do not build a retry/version-bump/
"replace" helper on top of upload() expecting it to eventually succeed or
to produce version 2+ -- it cannot, by server design, not by transient
failure.
"""

from __future__ import annotations

import builtins
from typing import BinaryIO
from uuid import UUID, uuid4

from teamstorm.api._base import BaseAPI
from teamstorm.models.attachments import AttachmentModel, AttachmentModelList
from teamstorm.models.common import UUIDStr


class _AttachmentsAPIBase(BaseAPI):
    """
    Shared HTTP/marshalling logic for WorkitemAttachmentsAPI and
    DocumentAttachmentsAPI.

    Not part of the public API wrapper surface -- instantiate WorkitemAttachmentsAPI
    or DocumentAttachmentsAPI instead. A concrete subclass supplies only the
    parent path segment (`_parent_segment = "workitems"` or `"documents"`);
    every path, HTTP verb, and response-validation call is identical between
    the two resources and lives here once instead of being copy-pasted nine
    times per class.
    """

    _parent_segment: str = ""

    def _attachments_path(self, workspace_key: str, parent_id: UUIDStr) -> str:
        return f"/workspaces/{workspace_key}/{self._parent_segment}/{parent_id}/attachments"

    def _list(self, workspace_key: str, parent_id: UUIDStr) -> list[AttachmentModel]:
        data = self.client.get(self._attachments_path(workspace_key, parent_id))
        return AttachmentModelList.model_validate(data).items

    def _get(self, workspace_key: str, parent_id: UUIDStr, attachment_id: UUID) -> AttachmentModel:
        data = self.client.get(f"{self._attachments_path(workspace_key, parent_id)}/{attachment_id}")
        return AttachmentModel.model_validate(data)

    def _download(self, workspace_key: str, parent_id: UUIDStr, attachment_id: UUID) -> bytes:
        path = f"{self._attachments_path(workspace_key, parent_id)}/{attachment_id}/download"
        return self.client.get_bytes(path)

    def _list_versions(self, workspace_key: str, parent_id: UUIDStr) -> list[AttachmentModel]:
        data = self.client.get(f"{self._attachments_path(workspace_key, parent_id)}/versions")
        return AttachmentModelList.model_validate(data).items

    def _get_version(
        self,
        workspace_key: str,
        parent_id: UUIDStr,
        attachment_id: UUID,
        version: int,
    ) -> AttachmentModel:
        path = f"{self._attachments_path(workspace_key, parent_id)}/{attachment_id}/versions/{version}"
        data = self.client.get(path)
        return AttachmentModel.model_validate(data)

    def _upload(
        self,
        workspace_key: str,
        parent_id: UUIDStr,
        *,
        file_name: str,
        content: bytes | BinaryIO,
        content_type: str | None = None,
        attachment_id: UUID | None = None,
    ) -> UUID:
        resolved_id = attachment_id if attachment_id is not None else uuid4()
        path = f"{self._attachments_path(workspace_key, parent_id)}/{resolved_id}/upload"
        self.client.post_multipart(
            path,
            file_name=file_name,
            content=content,
            content_type=content_type,
            field_name="file",
        )
        return resolved_id

    def _delete_all(self, workspace_key: str, parent_id: UUIDStr) -> None:
        self.client.delete(self._attachments_path(workspace_key, parent_id))
        return None

    def _delete(self, workspace_key: str, parent_id: UUIDStr, attachment_id: UUID) -> None:
        self.client.delete(f"{self._attachments_path(workspace_key, parent_id)}/{attachment_id}")
        return None

    def _delete_version(
        self,
        workspace_key: str,
        parent_id: UUIDStr,
        attachment_id: UUID,
        version: int,
    ) -> None:
        path = f"{self._attachments_path(workspace_key, parent_id)}/{attachment_id}/versions/{version}"
        self.client.delete(path)
        return None


class WorkitemAttachmentsAPI(_AttachmentsAPIBase):
    """
    File attachments on a single workitem, including all stored versions.

    9 ops (WorkitemAttachments tag): list, get, download, list_versions,
    get_version, upload, delete_all, delete, delete_version.

    CRITICAL LIMITATION -- see this module's top-level docstring
    (teamstorm/api/attachments.py) and
    docs/api-analysis/upstream-semantics.md "Attachment upload/download
    flow": re-uploading to an attachment_id that already has a file on the
    server ALWAYS fails with 400 Bad Request. upload() cannot be used to add
    a new version to an existing attachment.
    """

    _parent_segment = "workitems"

    def list(self, workspace_key: str, *, workitem_id: UUIDStr) -> list[AttachmentModel]:
        """
        List every attachment on a workitem (latest version of each).

        workspace_key: workspace key or id.
        workitem_id: workitem UUID (path segment).
        Returns: every AttachmentModel currently attached to the workitem.
        GET /workspaces/{workspace}/workitems/{workitem}/attachments.
        NOTE: bare-array response, no pagination fields -- uses a plain
        get(), not get_all().
        """
        return self._list(workspace_key, workitem_id)

    def get(self, workspace_key: str, *, workitem_id: UUIDStr, attachment_id: UUID) -> AttachmentModel:
        """
        Get one attachment's metadata (its latest version).

        workspace_key: workspace key or id.
        workitem_id: workitem UUID (path segment).
        attachment_id: attachment UUID (path segment).
        Returns: the AttachmentModel.
        GET /workspaces/{workspace}/workitems/{workitem}/attachments/{attachmentId}.
        """
        return self._get(workspace_key, workitem_id, attachment_id)

    def download(self, workspace_key: str, *, workitem_id: UUIDStr, attachment_id: UUID) -> bytes:
        """
        Download an attachment's raw file content.

        workspace_key: workspace key or id.
        workitem_id: workitem UUID (path segment).
        attachment_id: attachment UUID (path segment).
        Returns: the raw file bytes -- no JSON envelope; the server sends
        Content-Type: application/octet-stream.
        GET /workspaces/{workspace}/workitems/{workitem}/attachments/{attachmentId}/download.
        NOTE: a file the antivirus scanner flagged surfaces here as
        423 Locked (ApiError), not as a successful response.
        """
        return self._download(workspace_key, workitem_id, attachment_id)

    def list_versions(self, workspace_key: str, *, workitem_id: UUIDStr) -> builtins.list[AttachmentModel]:
        """
        List every attachment on a workitem across all of their versions.

        workspace_key: workspace key or id.
        workitem_id: workitem UUID (path segment).
        Returns: one AttachmentModel per stored version of every attachment
        on the workitem.
        GET /workspaces/{workspace}/workitems/{workitem}/attachments/versions.
        """
        return self._list_versions(workspace_key, workitem_id)

    def get_version(
        self,
        workspace_key: str,
        *,
        workitem_id: UUIDStr,
        attachment_id: UUID,
        version: int,
    ) -> AttachmentModel:
        """
        Get one specific stored version of one attachment.

        workspace_key: workspace key or id.
        workitem_id: workitem UUID (path segment).
        attachment_id: attachment UUID (path segment).
        version: the attachment version number (path segment).
        Returns: the AttachmentModel for that version.
        GET /workspaces/{workspace}/workitems/{workitem}/attachments/{attachmentId}/versions/{attachmentVersion}.
        """
        return self._get_version(workspace_key, workitem_id, attachment_id, version)

    def upload(
        self,
        workspace_key: str,
        *,
        workitem_id: UUIDStr,
        file_name: str,
        content: bytes | BinaryIO,
        content_type: str | None = None,
        attachment_id: UUID | None = None,
    ) -> UUID:
        """
        Upload a new file attachment to a workitem.

        There is no create-then-upload handshake: attachmentId is chosen by
        the client, not returned by the server. When attachment_id is not
        supplied, a fresh uuid4() is generated here and returned, since the
        server responds 204 No Content with no body -- this return value is
        the only way to learn the new attachment's id afterwards.

        CANNOT be used to add a new version to an EXISTING attachment_id.
        The public upload route forces the storage-layer fileId to equal
        attachment_id, and the server rejects an upload whose (object,
        fileId) pair already exists with 400 Bad Request ("File.Conflict")
        -- so re-uploading to an attachment_id that already has a file on
        the server always fails, regardless of content. See this class's
        docstring and docs/api-analysis/upstream-semantics.md "Attachment
        upload/download flow". Only pass an explicit attachment_id you know
        has never been uploaded to; otherwise omit it and let a fresh id be
        generated.

        workspace_key: workspace key or id.
        workitem_id: workitem UUID (path segment).
        file_name: file name reported to the server for the uploaded part.
        content: file content, either bytes or a binary file-like object.
        content_type: optional MIME type for the uploaded part.
        attachment_id: optional client-chosen attachment UUID; a uuid4() is
        generated when omitted.
        Returns: the attachment_id used for the upload (the one supplied, or
        the generated one).
        POST /workspaces/{workspace}/workitems/{workitem}/attachments/{attachmentId}/upload,
        multipart/form-data with field name "file" (server default max size
        5 GB -- 413 Payload Too Large above that).
        """
        return self._upload(
            workspace_key,
            workitem_id,
            file_name=file_name,
            content=content,
            content_type=content_type,
            attachment_id=attachment_id,
        )

    def delete_all(self, workspace_key: str, *, workitem_id: UUIDStr) -> None:
        """
        Delete every attachment on a workitem.

        workspace_key: workspace key or id.
        workitem_id: workitem UUID (path segment).
        Returns: None.
        DELETE /workspaces/{workspace}/workitems/{workitem}/attachments.
        """
        return self._delete_all(workspace_key, workitem_id)

    def delete(self, workspace_key: str, *, workitem_id: UUIDStr, attachment_id: UUID) -> None:
        """
        Delete one attachment (all of its stored versions).

        workspace_key: workspace key or id.
        workitem_id: workitem UUID (path segment).
        attachment_id: attachment UUID (path segment).
        Returns: None.
        DELETE /workspaces/{workspace}/workitems/{workitem}/attachments/{attachmentId}.
        """
        return self._delete(workspace_key, workitem_id, attachment_id)

    def delete_version(
        self,
        workspace_key: str,
        *,
        workitem_id: UUIDStr,
        attachment_id: UUID,
        version: int,
    ) -> None:
        """
        Delete one specific stored version of one attachment.

        workspace_key: workspace key or id.
        workitem_id: workitem UUID (path segment).
        attachment_id: attachment UUID (path segment).
        version: the attachment version number (path segment).
        Returns: None.
        DELETE /workspaces/{workspace}/workitems/{workitem}/attachments/{attachmentId}/versions/{attachmentVersion}.
        """
        return self._delete_version(workspace_key, workitem_id, attachment_id, version)


class DocumentAttachmentsAPI(_AttachmentsAPIBase):
    """
    File attachments on a single document, including all stored versions.

    Structurally identical to WorkitemAttachmentsAPI (same 9 operations,
    same semantics), scoped to a document instead of a workitem -- see
    docs/api-analysis/upstream-semantics.md "Attachment upload/download
    flow".

    9 ops (DocumentAttachments tag): list, get, download, list_versions,
    get_version, upload, delete_all, delete, delete_version.

    CRITICAL LIMITATION -- re-uploading to an attachment_id that already has
    a file on the server ALWAYS fails with 400 Bad Request. upload() cannot
    be used to add a new version to an existing attachment; see this
    module's top-level docstring (teamstorm/api/attachments.py) for why.
    """

    _parent_segment = "documents"

    def list(self, workspace_key: str, *, document_id: UUIDStr) -> list[AttachmentModel]:
        """
        List every attachment on a document (latest version of each).

        workspace_key: workspace key or id.
        document_id: document UUID (path segment).
        Returns: every AttachmentModel currently attached to the document.
        GET /workspaces/{workspace}/documents/{document}/attachments.
        NOTE: bare-array response, no pagination fields -- uses a plain
        get(), not get_all().
        """
        return self._list(workspace_key, document_id)

    def get(self, workspace_key: str, *, document_id: UUIDStr, attachment_id: UUID) -> AttachmentModel:
        """
        Get one attachment's metadata (its latest version).

        workspace_key: workspace key or id.
        document_id: document UUID (path segment).
        attachment_id: attachment UUID (path segment).
        Returns: the AttachmentModel.
        GET /workspaces/{workspace}/documents/{document}/attachments/{attachmentId}.
        """
        return self._get(workspace_key, document_id, attachment_id)

    def download(self, workspace_key: str, *, document_id: UUIDStr, attachment_id: UUID) -> bytes:
        """
        Download an attachment's raw file content.

        workspace_key: workspace key or id.
        document_id: document UUID (path segment).
        attachment_id: attachment UUID (path segment).
        Returns: the raw file bytes -- no JSON envelope; the server sends
        Content-Type: application/octet-stream.
        GET /workspaces/{workspace}/documents/{document}/attachments/{attachmentId}/download.
        NOTE: a file the antivirus scanner flagged surfaces here as
        423 Locked (ApiError), not as a successful response.
        """
        return self._download(workspace_key, document_id, attachment_id)

    def list_versions(self, workspace_key: str, *, document_id: UUIDStr) -> builtins.list[AttachmentModel]:
        """
        List every attachment on a document across all of their versions.

        workspace_key: workspace key or id.
        document_id: document UUID (path segment).
        Returns: one AttachmentModel per stored version of every attachment
        on the document.
        GET /workspaces/{workspace}/documents/{document}/attachments/versions.
        """
        return self._list_versions(workspace_key, document_id)

    def get_version(
        self,
        workspace_key: str,
        *,
        document_id: UUIDStr,
        attachment_id: UUID,
        version: int,
    ) -> AttachmentModel:
        """
        Get one specific stored version of one attachment.

        workspace_key: workspace key or id.
        document_id: document UUID (path segment).
        attachment_id: attachment UUID (path segment).
        version: the attachment version number (path segment).
        Returns: the AttachmentModel for that version.
        GET /workspaces/{workspace}/documents/{document}/attachments/{attachmentId}/versions/{attachmentVersion}.
        """
        return self._get_version(workspace_key, document_id, attachment_id, version)

    def upload(
        self,
        workspace_key: str,
        *,
        document_id: UUIDStr,
        file_name: str,
        content: bytes | BinaryIO,
        content_type: str | None = None,
        attachment_id: UUID | None = None,
    ) -> UUID:
        """
        Upload a new file attachment to a document.

        There is no create-then-upload handshake: attachmentId is chosen by
        the client, not returned by the server. When attachment_id is not
        supplied, a fresh uuid4() is generated here and returned, since the
        server responds 204 No Content with no body -- this return value is
        the only way to learn the new attachment's id afterwards.

        CANNOT be used to add a new version to an EXISTING attachment_id.
        The public upload route forces the storage-layer fileId to equal
        attachment_id, and the server rejects an upload whose (object,
        fileId) pair already exists with 400 Bad Request ("File.Conflict")
        -- so re-uploading to an attachment_id that already has a file on
        the server always fails, regardless of content. See this class's
        docstring and docs/api-analysis/upstream-semantics.md "Attachment
        upload/download flow". Only pass an explicit attachment_id you know
        has never been uploaded to; otherwise omit it and let a fresh id be
        generated.

        workspace_key: workspace key or id.
        document_id: document UUID (path segment).
        file_name: file name reported to the server for the uploaded part.
        content: file content, either bytes or a binary file-like object.
        content_type: optional MIME type for the uploaded part.
        attachment_id: optional client-chosen attachment UUID; a uuid4() is
        generated when omitted.
        Returns: the attachment_id used for the upload (the one supplied, or
        the generated one).
        POST /workspaces/{workspace}/documents/{document}/attachments/{attachmentId}/upload,
        multipart/form-data with field name "file" (server default max size
        5 GB -- 413 Payload Too Large above that).
        """
        return self._upload(
            workspace_key,
            document_id,
            file_name=file_name,
            content=content,
            content_type=content_type,
            attachment_id=attachment_id,
        )

    def delete_all(self, workspace_key: str, *, document_id: UUIDStr) -> None:
        """
        Delete every attachment on a document.

        workspace_key: workspace key or id.
        document_id: document UUID (path segment).
        Returns: None.
        DELETE /workspaces/{workspace}/documents/{document}/attachments.
        """
        return self._delete_all(workspace_key, document_id)

    def delete(self, workspace_key: str, *, document_id: UUIDStr, attachment_id: UUID) -> None:
        """
        Delete one attachment (all of its stored versions).

        workspace_key: workspace key or id.
        document_id: document UUID (path segment).
        attachment_id: attachment UUID (path segment).
        Returns: None.
        DELETE /workspaces/{workspace}/documents/{document}/attachments/{attachmentId}.
        """
        return self._delete(workspace_key, document_id, attachment_id)

    def delete_version(
        self,
        workspace_key: str,
        *,
        document_id: UUIDStr,
        attachment_id: UUID,
        version: int,
    ) -> None:
        """
        Delete one specific stored version of one attachment.

        workspace_key: workspace key or id.
        document_id: document UUID (path segment).
        attachment_id: attachment UUID (path segment).
        version: the attachment version number (path segment).
        Returns: None.
        DELETE /workspaces/{workspace}/documents/{document}/attachments/{attachmentId}/versions/{attachmentVersion}.
        """
        return self._delete_version(workspace_key, document_id, attachment_id, version)
