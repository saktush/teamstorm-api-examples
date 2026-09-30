# teamstorm/models/documents.py
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from .base import TsBaseModel
from .common import UserModel
from .workitems_thumbs import TreeNodeThumbModel


class DocumentStatusModel(TsBaseModel):
    """
    Swagger: DocumentStatusModel
    required: id, name

    A workspace-configurable named status a document can be tagged with (e.g.
    "Draft", "Approved"). Unlike WorkitemModel's StatusModel, there is no
    `category` field here -- document statuses are not grouped into
    to-do/in-progress/done categories anywhere in the spec. There is no fixed
    enum of literal status values either: statuses are workspace-defined data,
    read-only via the public API (no create/patch/delete endpoint exists).
    """

    id: UUID
    name: str


class DocumentsStatusModelList(TsBaseModel):
    """
    Swagger: DocumentsStatusModelList
    required: items

    NOTE: unlike DocumentsModelList/DocumentVersionsModelList below, this
    envelope has no fromToken/maxItemsCount/nextToken fields, and
    ListDocumentStatuses declares no such query params either -- this endpoint
    does not paginate. DocumentStatusesAPI.list() unwraps .items via a plain
    get(), not get_all().
    """

    items: list[DocumentStatusModel]


class DocumentModel(TsBaseModel):
    """
    Swagger: DocumentModel
    required: author, createdAt, documentUrl, id, isBlocked, key, labels,
              name, parent, updatedAt, version, versionUrl, workspaceId

    NOTE: `author` is always populated (TS-15580), and the `userName` of
    author/updatedBy is the real login.

    NOTE: `content` is server-transformed HTML, not necessarily what a caller
    submitted verbatim: the server wraps any line in
    CreateDocumentRequestBody.content that doesn't already look like an HTML
    block tag in <p>...</p> before storing it (verified against server source;
    see docs/api-analysis/upstream-semantics.md, gotcha #3). Round-tripping
    plain text through create -> get is lossy in this predictable way.
    """

    workspace_id: UUID = Field(alias="workspaceId")
    id: UUID
    key: str
    name: str
    document_url: str = Field(alias="documentUrl")
    content: str | None = None
    created_at: datetime = Field(alias="createdAt")
    author: UserModel
    updated_at: datetime = Field(alias="updatedAt")
    updated_by: UserModel | None = Field(default=None, alias="updatedBy")
    parent: TreeNodeThumbModel
    version: int
    version_url: str = Field(alias="versionUrl")
    labels: list[str]
    is_blocked: bool = Field(alias="isBlocked")
    status: DocumentStatusModel | None = None


class DocumentsModelList(TsBaseModel):
    """
    Swagger: DocumentsModelList
    required: items
    """

    from_token: str | None = Field(default=None, alias="fromToken")
    max_items_count: int | None = Field(default=None, alias="maxItemsCount")
    next_token: str | None = Field(default=None, alias="nextToken")
    items: list[DocumentModel]


class DocumentVersionModel(TsBaseModel):
    """
    Swagger: DocumentVersionModel
    required: author, createdDate, versionNumber
    """

    version_number: int = Field(alias="versionNumber")
    author: UserModel
    created_date: datetime = Field(alias="createdDate")
    status: DocumentStatusModel | None = None


class DocumentVersionsModelList(TsBaseModel):
    """
    Swagger: DocumentVersionsModelList
    required: items
    """

    from_token: str | None = Field(default=None, alias="fromToken")
    max_items_count: int | None = Field(default=None, alias="maxItemsCount")
    next_token: str | None = Field(default=None, alias="nextToken")
    items: list[DocumentVersionModel]


class CreateDocumentRequestBody(TsBaseModel):
    """
    Swagger: CreateDocumentRequestBody
    required: content, labels, name, parentId

    parentId gotcha (verified against server source; see
    docs/api-analysis/upstream-semantics.md §6/§9.1): the server's request
    model binds parentId as a non-nullable Guid with no C# [Required]
    validation attribute, so an omitted parentId in raw JSON silently becomes
    Guid.Empty instead of failing validation at the model-binding layer -- and
    Guid.Empty does NOT mean "place at the workspace root" for documents:
    downstream tree-node creation looks up a node by that id and fails with
    "node not found". The workspace's own root tree node is seeded with
    NodeId == WorkspaceId, so to create a top-level document, pass the
    *workspace's own GUID* as parent_id.

    This model keeps parent_id a required field (matching the OpenAPI required
    list, with no default) so the API wrapper itself can never construct a request
    that triggers the omitted-parentId failure mode; do not widen it to
    Optional or silently default it to an empty GUID.

    content gotcha: see DocumentModel's docstring -- the server auto-wraps
    bare lines in <p> tags before storing, so what you read back later may
    differ from what you sent.
    """

    name: str
    content: str
    parent_id: UUID = Field(alias="parentId")
    labels: list[str]


class PatchDocumentRequestBody(TsBaseModel):
    """
    Swagger: PatchDocumentRequestBody
    required: (none -- every field optional, partial-merge PATCH)

    NOTE: `status` is the ONLY patchable field for a document (verified: the
    server reads only `status` from the request body -- there is no way to
    change a document's name or content after creation via the public API;
    see docs/api-analysis/upstream-semantics.md §7).

    The API layer serializes this with exclude_unset=True (and
    exclude_none=False to override TsBaseModel's own default): a field never
    assigned here is omitted from the request entirely (server: leave status
    unchanged), while status explicitly assigned None is sent as JSON null
    (server: clear the document's status).
    """

    status: str | None = None


class CreateDocumentWorkitemLinkRequestBody(TsBaseModel):
    """
    Swagger: CreateDocumentWorkitemLinkRequestBody
    required: workitem, workitemWorkspace

    Request body for POST /workspaces/{workspace}/documents/{document}/workitem-links
    -- links a workitem to a document. Unlike CreateWorkitemLinkRequestBody
    (teamstorm/models/links.py), there is no `type` field: document<->workitem
    links are untyped (docs/api-analysis/upstream-semantics.md, "Links"
    section). `workitem` is the target workitem's key or GUID; unlike
    workitem-to-workitem links (which resolve the target tenant-wide),
    this endpoint additionally requires `workitemWorkspace` -- the workspace
    the workitem lives in.
    """

    workitem: str
    workitem_workspace: str = Field(alias="workitemWorkspace")


class DeleteDocumentWorkitemLinkRequestBody(TsBaseModel):
    """
    Swagger: DeleteDocumentWorkitemLinkRequestBody
    required: workitem, workitemWorkspace

    Request body for DELETE /workspaces/{workspace}/documents/{document}/workitem-links.
    Same shape as CreateDocumentWorkitemLinkRequestBody, but modeled as its
    own class to match the swagger schema name 1:1.

    NOTE: this is the only DELETE operation in the whole spec that carries a
    request body: the route is the bare collection path with no linkId path
    segment or query params, so this body is what identifies exactly which
    linked workitem to remove. TsClient.delete() needed a `body` kwarg added
    to send it (teamstorm/client.py) -- every other DELETE call site is unaffected,
    since that kwarg defaults to None.
    """

    workitem: str
    workitem_workspace: str = Field(alias="workitemWorkspace")
