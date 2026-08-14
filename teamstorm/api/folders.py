from __future__ import annotations

from typing import Any
from uuid import UUID
from pydantic import TypeAdapter

from ._base import BaseAPI
from ..models.folders import CreateFolderRequestBody, FolderModel, PatchFolderRequestBody


class FoldersAPI(BaseAPI):
    """
    Folders: the tree structure that organizes agile boards, sprints and
    workitems within a workspace.

    5 ops (Folders tag): list, get, create, patch, delete.
    """

    def list(
        self,
        workspace_key: str,
        *,
        name: str | None = None,
        parent_id: UUID | None = None,
    ) -> list[FolderModel]:
        """
        List the folders in a workspace.

        :param workspace_key: workspace key or id.
        :param name: optional name filter.
        :param parent_id: optional filter to direct children of one folder.
        :return: every matching FolderModel.
        HTTP: GET /workspaces/{workspace}/folders
        NOTE: the endpoint is paginated on the wire (fromToken/maxItemsCount),
        but this method does not expose a from_token/max_items_count
        parameter -- get_all() still walks every page regardless, using the
        client's default page size of 500.
        """
        params: dict[str, Any] = {}
        if name is not None:
            params["name"] = name
        if parent_id is not None:
            params["parentId"] = str(parent_id)

        data = self.client.get_all(
            f"/workspaces/{workspace_key}/folders",
            params=params or None,
        )
        return TypeAdapter(list[FolderModel]).validate_python(data)

    def get(self, workspace_key: str, *, folder_id: UUID) -> FolderModel:
        """
        Fetch a single folder by id.

        :param workspace_key: workspace key or id the folder belongs to.
        :param folder_id: UUID of the folder to fetch.
        :return: the matching FolderModel.
        HTTP: GET /workspaces/{workspace}/folders/{folderId}
        """
        data = self.client.get(f"/workspaces/{workspace_key}/folders/{folder_id}")
        return FolderModel.model_validate(data)

    def create(self, workspace_key: str, body: CreateFolderRequestBody) -> FolderModel:
        """
        Create a new folder.

        :param workspace_key: workspace key or id.
        :param body: CreateFolderRequestBody -- required name; parent_id is
            nullable in the spec but should still be provided (pass the
            workspace's own GUID to place the folder at the workspace root --
            see the model's own docstring for the underlying server quirk).
        :return: the created FolderModel.
        HTTP: POST /workspaces/{workspace}/folders
        """
        data = self.client.post(
            f"/workspaces/{workspace_key}/folders",
            body=body.model_dump(mode="json", exclude_none=True),
        )
        return FolderModel.model_validate(data)

    def patch(self, workspace_key: str, *, folder_id: UUID, body: PatchFolderRequestBody) -> FolderModel:
        """
        Partially update a folder.

        Only fields explicitly set on *body* are sent to the server
        (exclude_unset=True): the server distinguishes a field absent from
        the request body (leave unchanged)
        from one present with value null (clear it). exclude_none is
        explicitly disabled here because TsBaseModel.model_dump() otherwise
        defaults exclude_none=True, which would silently drop an intentional
        "clear this field" null.

        :param workspace_key: workspace key or id the folder belongs to.
        :param folder_id: UUID of the folder to patch.
        :param body: partial folder fields to update.
        :return: the updated FolderModel.
        HTTP: PATCH /workspaces/{workspace}/folders/{folderId}
        """
        payload = body.model_dump(mode="json", exclude_unset=True, exclude_none=False)
        data = self.client.patch(f"/workspaces/{workspace_key}/folders/{folder_id}", payload)
        return FolderModel.model_validate(data)

    def delete(self, workspace_key: str, *, folder_id: UUID) -> None:
        """
        Delete a folder.

        :param workspace_key: workspace key or id the folder belongs to.
        :param folder_id: UUID of the folder to delete.
        :return: None.
        HTTP: DELETE /workspaces/{workspace}/folders/{folderId}
        """
        self.client.delete(f"/workspaces/{workspace_key}/folders/{folder_id}")
        return None
