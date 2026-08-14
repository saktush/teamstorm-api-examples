from __future__ import annotations

from pydantic import TypeAdapter

from teamstorm.api._base import BaseAPI
from teamstorm.models.workflows import (
    CreateWorkflowRequestBody,
    PatchWorkflowRequestBody,
    WorkflowModel,
)


class WorkflowsAPI(BaseAPI):
    """
    Workflows: the named graph of statuses and transitions that a
    TypesAPI.TypeModel is bound to.

    5 ops (Workflows tag): list, get, create, patch, delete.
    """

    def list(self, workspace_key: str, *, name: str | None = None) -> list[WorkflowModel]:
        """
        List the workflows defined in a workspace.

        :param workspace_key: workspace key or id.
        :param name: optional name filter.
        :return: every matching WorkflowModel.
        HTTP: GET /workspaces/{workspace}/workflows
        NOTE: this endpoint does not paginate (no fromToken/maxItemsCount on
        the wire) -- a bare array is returned; get_all() is used only as the
        client's generic list-fetch helper.
        """
        params: dict[str, str] = {}
        if name is not None:
            params["name"] = name

        data = self.client.get_all(
            f"/workspaces/{workspace_key}/workflows",
            params=params or None,
        )
        return TypeAdapter(list[WorkflowModel]).validate_python(data)

    def get(self, workspace_key: str, workflow_key: str) -> WorkflowModel:
        """
        Fetch a single workflow by id or name.

        :param workspace_key: workspace key or id.
        :param workflow_key: workflow UUID or name (path segment).
        :return: the matching WorkflowModel.
        HTTP: GET /workspaces/{workspace}/workflows/{workflow}
        """
        data = self.client.get(f"/workspaces/{workspace_key}/workflows/{workflow_key}")
        return WorkflowModel.model_validate(data)

    def create(self, workspace_key: str, body: CreateWorkflowRequestBody) -> WorkflowModel:
        """
        Create a new workflow.

        :param workspace_key: workspace key or id.
        :param body: CreateWorkflowRequestBody -- required name; statuses and
            transitions default to empty lists (no server-side minimum is
            enforced at the schema level).
        :return: the created WorkflowModel.
        HTTP: POST /workspaces/{workspace}/workflows
        """
        payload = body.model_dump(mode="json", exclude_none=True)
        data = self.client.post(f"/workspaces/{workspace_key}/workflows", payload)
        return WorkflowModel.model_validate(data)

    def patch(
        self,
        workspace_key: str,
        *,
        workflow_key: str,
        body: PatchWorkflowRequestBody,
    ) -> WorkflowModel:
        """
        Partially update a workflow's name/statuses/transitions.

        :param workspace_key: workspace key or id.
        :param workflow_key: workflow UUID or name (path segment).
        :param body: partial workflow fields to update.
        :return: the updated WorkflowModel.
        HTTP: PATCH /workspaces/{workspace}/workflows/{workflow}
        NOTE: only fields explicitly set on *body* are sent
        (exclude_unset=True): the server distinguishes a field absent from
        the request body (leave unchanged)
        from one present with value null (clear it). exclude_none is
        explicitly disabled here because TsBaseModel.model_dump() otherwise
        defaults exclude_none=True, which would silently drop an intentional
        "clear this field" null.
        """
        payload = body.model_dump(mode="json", exclude_unset=True, exclude_none=False)
        data = self.client.patch(f"/workspaces/{workspace_key}/workflows/{workflow_key}", payload)
        return WorkflowModel.model_validate(data)

    def delete(self, workspace_key: str, *, workflow_key: str) -> None:
        """
        Delete a workflow.

        :param workspace_key: workspace key or id.
        :param workflow_key: workflow UUID or name (path segment).
        :return: None.
        HTTP: DELETE /workspaces/{workspace}/workflows/{workflow}
        """
        self.client.delete(f"/workspaces/{workspace_key}/workflows/{workflow_key}")
        return None
