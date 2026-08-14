from __future__ import annotations

import builtins
from uuid import UUID

from pydantic import TypeAdapter

from teamstorm.api._base import BaseAPI
from teamstorm.models.common import UUIDStr
from teamstorm.models.links import CreateWorkitemLinkRequestBody, LinkTypeModel, WorkitemLinkModel


class LinksAPI(BaseAPI):
    """
    Workitem-to-workitem links plus the link types configured for a workspace.

    Groups WorkitemLinks (list/create/delete) and LinkTypes (list) into one
    class: link types exist only to feed the "type" field of a workitem link
    and are too small a surface (a single GET) to warrant their own API class.
    """

    def list(self, workspace_key: str, *, workitem_id: UUIDStr) -> list[WorkitemLinkModel]:
        """
        List the links attached to a single workitem.

        workspace_key: workspace key.
        workitem_id: workitem UUID (path segment).
        Returns: every WorkitemLinkModel attached to the workitem.
        GET /workspaces/{workspace}/workitems/{workitem}/links.
        """
        data = self.client.get_all(f"/workspaces/{workspace_key}/workitems/{workitem_id}/links")
        return TypeAdapter(list[WorkitemLinkModel]).validate_python(data)

    def create(
        self,
        workspace_key: str,
        *,
        workitem_id: UUIDStr,
        body: CreateWorkitemLinkRequestBody,
    ) -> WorkitemLinkModel:
        """
        Create a link from one workitem to another.

        workspace_key: workspace key.
        workitem_id: source workitem UUID (path segment).
        body: link type (id or name) plus the target workitem's key/GUID.
        Returns: the created WorkitemLinkModel.
        POST /workspaces/{workspace}/workitems/{workitem}/links.
        """
        payload = body.model_dump(mode="json", exclude_none=True)
        data = self.client.post(f"/workspaces/{workspace_key}/workitems/{workitem_id}/links", payload)
        return WorkitemLinkModel.model_validate(data)

    def delete(self, workspace_key: str, *, link_id: UUID) -> None:
        """
        Delete a workitem link.

        NOTE: this endpoint is workspace-scoped, NOT nested under the
        workitem (unlike list()/create() above) -- the server exposes delete
        via an absolute route override, so its URL does not follow the same
        nested convention as the other workitem-link endpoints even though
        it's handled by the same server-side component
        (docs/api-analysis/upstream-semantics.md, "Links" section).

        workspace_key: workspace key.
        link_id: the link's own UUID (not either workitem's id).
        Returns: None.
        DELETE /workspaces/{workspace}/links/{linkId}.
        """
        self.client.delete(f"/workspaces/{workspace_key}/links/{link_id}")
        return None

    def list_types(self, workspace_key: str) -> builtins.list[LinkTypeModel]:
        """
        List the link types configured for a workspace.

        workspace_key: workspace key.
        Returns: every LinkTypeModel configured for the workspace.
        GET /workspaces/{workspace}/link-types.
        """
        data = self.client.get_all(f"/workspaces/{workspace_key}/link-types")
        return TypeAdapter(list[LinkTypeModel]).validate_python(data)
