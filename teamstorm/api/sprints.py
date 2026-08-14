from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import TypeAdapter

from ._base import BaseAPI
from ..models.sprints import (
    CreateSprintRequestBody,
    PatchSprintRequestBody,
    SprintModel,
)


class SprintsAPI(BaseAPI):
    """
    Agile sprints (iterations), each optionally scoped to a folder/agile
    board -- team membership, dates, and the special "backlog" sprint.

    5 ops (Sprints tag): list, get, create, patch, delete.
    """

    def list(
        self,
        workspace_key: str,
        *,
        folder_id: UUID | None = None,
        name: str | None = None,
    ) -> list[SprintModel]:
        """
        List the sprints in a workspace.

        :param workspace_key: workspace key or id.
        :param folder_id: optional filter to sprints belonging to one folder.
        :param name: optional name filter.
        :return: every matching SprintModel.
        HTTP: GET /workspaces/{workspace}/sprints
        NOTE: this endpoint does not paginate (no fromToken/maxItemsCount on
        the wire) -- a bare array is returned; get_all() is used only as the
        client's generic list-fetch helper.
        """
        params: dict[str, Any] = {}
        if folder_id is not None:
            params["folderId"] = str(folder_id)
        if name is not None:
            params["name"] = name

        data = self.client.get_all(
            f"/workspaces/{workspace_key}/sprints",
            params=params or None,
        )
        return TypeAdapter(list[SprintModel]).validate_python(data)

    def get(self, workspace_key: str, *, sprint_id: UUID) -> SprintModel:
        """
        Fetch a single sprint by id.

        :param workspace_key: workspace key or id the sprint belongs to.
        :param sprint_id: UUID of the sprint to fetch.
        :return: the matching SprintModel.
        HTTP: GET /workspaces/{workspace}/sprints/{sprintId}
        """
        data = self.client.get(f"/workspaces/{workspace_key}/sprints/{sprint_id}")
        return SprintModel.model_validate(data)

    def create(self, workspace_key: str, body: CreateSprintRequestBody) -> SprintModel:
        """
        Create a new sprint.

        :param workspace_key: workspace key or id.
        :param body: CreateSprintRequestBody -- name, dates, folder, and
            initial team membership.
        :return: the created SprintModel.
        HTTP: POST /workspaces/{workspace}/sprints
        """
        payload = body.model_dump(mode="json", exclude_none=True)
        data = self.client.post(f"/workspaces/{workspace_key}/sprints", payload)
        return SprintModel.model_validate(data)

    def patch(
        self,
        workspace_key: str,
        *,
        sprint_id: UUID,
        body: PatchSprintRequestBody,
    ) -> SprintModel:
        """
        Partially update a sprint's name, dates, or team membership.

        :param workspace_key: workspace key or id.
        :param sprint_id: UUID of the sprint to patch.
        :param body: partial sprint fields to update.
        :return: the updated SprintModel.
        HTTP: PATCH /workspaces/{workspace}/sprints/{sprintId}
        NOTE: only fields explicitly set on *body* are sent
        (exclude_unset=True): the server distinguishes a field absent from
        the request body (leave unchanged)
        from one present with value null (clear it). exclude_none is
        explicitly disabled here because TsBaseModel.model_dump() otherwise
        defaults exclude_none=True, which would silently drop an intentional
        "clear this field" null.
        """
        payload = body.model_dump(mode="json", exclude_unset=True, exclude_none=False)
        data = self.client.patch(
            f"/workspaces/{workspace_key}/sprints/{sprint_id}",
            payload,
        )
        return SprintModel.model_validate(data)

    def delete(self, workspace_key: str, *, sprint_id: UUID) -> None:
        """
        Delete a sprint.

        :param workspace_key: workspace key or id the sprint belongs to.
        :param sprint_id: UUID of the sprint to delete.
        :return: None.
        HTTP: DELETE /workspaces/{workspace}/sprints/{sprintId}
        """
        self.client.delete(f"/workspaces/{workspace_key}/sprints/{sprint_id}")
        return None
