from __future__ import annotations

from typing import Any

from pydantic import TypeAdapter

from teamstorm.api._base import BaseAPI
from teamstorm.models.workspaces import (
    CreateWorkspaceRequestBody,
    PatchWorkspaceRequestBody,
    WorkspaceModel,
)


class WorkspacesAPI(BaseAPI):
    """
    Workspaces: the top-level container tenant-wide -- everything else in
    the API wrapper (folders, workitems, documents, roles, ...) hangs off one.

    5 ops (Workspaces tag): list, get, create, patch, delete. This is the one
    resource with no workspace_key parameter of its own on list()/create()
    (there is nothing to scope by yet); get()/patch()/delete() take the key
    of the workspace being operated on directly, not as a parent scope.
    """

    def list(
        self,
        *,
        key: str | None = None,
        name: str | None = None,
        from_token: str | None = None,
        max_items_count: int | None = None,
    ) -> list[WorkspaceModel]:
        """
        List the workspaces visible to the caller.

        :param key: optional key filter.
        :param name: optional name filter.
        :param from_token: pagination cursor from a previous page's
            nextToken.
        :param max_items_count: page size (API wrapper default 500 when omitted).
        :return: every WorkspaceModel across all pages.
        HTTP: GET /workspaces
        NOTE: this endpoint IS paginated (fromToken/maxItemsCount query
        params) -- fetches every page via get_all().
        """
        params: dict[str, Any] = {}
        if key is not None:
            params["key"] = key
        if name is not None:
            params["name"] = name
        if from_token is not None:
            params["fromToken"] = from_token
        if max_items_count is not None:
            params["maxItemsCount"] = max_items_count

        data = self.client.get_all("/workspaces", params=params or None)
        return TypeAdapter(list[WorkspaceModel]).validate_python(data)

    def get(self, workspace_key: str) -> WorkspaceModel:
        """
        Fetch a single workspace by key or id.

        :param workspace_key: workspace key or id.
        :return: the matching WorkspaceModel.
        HTTP: GET /workspaces/{workspace}
        """
        data = self.client.get(f"/workspaces/{workspace_key}")
        return WorkspaceModel.model_validate(data)

    def create(self, body: CreateWorkspaceRequestBody) -> WorkspaceModel:
        """
        Create a new workspace.

        :param body: CreateWorkspaceRequestBody -- required key and name.
        :return: the created WorkspaceModel.
        HTTP: POST /workspaces
        """
        payload = body.model_dump(mode="json", exclude_none=True)
        data = self.client.post("/workspaces", payload)
        return WorkspaceModel.model_validate(data)

    def patch(self, *, workspace_key: str, body: PatchWorkspaceRequestBody) -> WorkspaceModel:
        """
        Partially update a workspace's name.

        :param workspace_key: workspace key or id.
        :param body: partial workspace fields to update.
        :return: the updated WorkspaceModel.
        HTTP: PATCH /workspaces/{workspace}
        NOTE: only fields explicitly set on *body* are sent
        (exclude_unset=True): the server distinguishes a field absent from
        the request body (leave unchanged)
        from one present with value null (clear it). exclude_none is
        explicitly disabled here because TsBaseModel.model_dump() otherwise
        defaults exclude_none=True, which would silently drop an intentional
        "clear this field" null.
        """
        payload = body.model_dump(mode="json", exclude_unset=True, exclude_none=False)
        data = self.client.patch(f"/workspaces/{workspace_key}", payload)
        return WorkspaceModel.model_validate(data)

    def delete(self, *, workspace_key: str) -> None:
        """
        Delete a workspace.

        :param workspace_key: workspace key or id.
        :return: None.
        HTTP: DELETE /workspaces/{workspace}
        """
        self.client.delete(f"/workspaces/{workspace_key}")
        return None
