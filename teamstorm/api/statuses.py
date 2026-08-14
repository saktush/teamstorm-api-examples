from __future__ import annotations

from pydantic import TypeAdapter

from ._base import BaseAPI
from teamstorm.models.statuses import (
    CreateStatusRequestBody,
    StatusCategoryModel,
    StatusModel,
)


class StatusesAPI(BaseAPI):
    """
    Workflow statuses (e.g. "To Do", "In Progress", "Done") and the fixed,
    global set of status categories they roll up to.

    5 ops: list_categories (StatusCategories tag, global), plus list/get/
    create (Statuses tag, workspace-scoped). There is no patch/delete for a
    workspace status via the public API.
    """

    def list_categories(self) -> list[StatusCategoryModel]:
        """
        List the fixed, global set of status categories every workspace
        status maps to (e.g. "To Do"/"In Progress"/"Done" equivalents).

        :return: every StatusCategoryModel.
        HTTP: GET /status-categories
        NOTE: global (non-workspace-scoped), no filters, no pagination.
        """
        data = self.client.get_all("/status-categories")
        return TypeAdapter(list[StatusCategoryModel]).validate_python(data)

    def list(self, workspace_key: str) -> list[StatusModel]:
        """
        List every status defined in a workspace.

        :param workspace_key: workspace key or id.
        :return: every StatusModel in the workspace.
        HTTP: GET /workspaces/{workspace}/statuses
        NOTE: this endpoint does not paginate (no fromToken/maxItemsCount on
        the wire) -- a bare array is returned; get_all() is used only as the
        client's generic list-fetch helper.
        """
        data = self.client.get_all(f"/workspaces/{workspace_key}/statuses")
        return TypeAdapter(list[StatusModel]).validate_python(data)

    def get(self, workspace_key: str, *, status_key: str) -> StatusModel:
        """
        Fetch a single status by id or name.

        :param workspace_key: workspace key or id.
        :param status_key: status UUID or name (path segment).
        :return: the matching StatusModel.
        HTTP: GET /workspaces/{workspace}/statuses/{status}
        """
        data = self.client.get(f"/workspaces/{workspace_key}/statuses/{status_key}")
        return StatusModel.model_validate(data)

    def create(self, workspace_key: str, body: CreateStatusRequestBody) -> StatusModel:
        """
        Create a new workspace status.

        :param workspace_key: workspace key or id.
        :param body: CreateStatusRequestBody -- required name and category.
        :return: the created StatusModel.
        HTTP: POST /workspaces/{workspace}/statuses
        """
        payload = body.model_dump(mode="json", exclude_none=True)
        data = self.client.post(f"/workspaces/{workspace_key}/statuses", payload)
        return StatusModel.model_validate(data)
