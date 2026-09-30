from __future__ import annotations

import builtins
from typing import Any
from uuid import UUID

from pydantic import TypeAdapter

from teamstorm.api._base import BaseAPI
from teamstorm.models.common import GroupModel
from teamstorm.models.roles import SimpleRoleModel, SimpleRoleModelList


class WorkspaceGroupsAPI(BaseAPI):
    """
    Workspace-scoped group membership and roles: which GroupsAPI groups
    belong to a workspace, and which RolesAPI roles each group holds there.

    6 ops (WorkspaceGroups tag): list, add, remove, get_roles, add_role,
    remove_role. The per-user counterpart is WorkspaceUsersAPI.
    """

    def list(
        self,
        workspace_key: str,
        *,
        name: str | None = None,
        role_id: UUID | None = None,
    ) -> list[GroupModel]:
        """
        List the groups that belong to a workspace.

        :param workspace_key: workspace key or id.
        :param name: optional name filter.
        :param role_id: optional filter to groups holding a specific role.
        :return: every matching GroupModel.
        HTTP: GET /workspaces/{workspace}/groups
        NOTE: the endpoint is paginated on the wire (fromToken/maxItemsCount;
        swagger's operationId for this route is oddly named
        "FilterWorkspaceUsers" despite returning groups), but this method
        does not expose a from_token/max_items_count parameter -- get_all()
        still walks every page regardless, using the API wrapper's default page size
        of 500.
        NOTE: the response's nextToken is the offset of the next page and is
        null on the last page; the server filters and sorts (by name, then
        id) before paging (TS-17841). This is compatible with
        client.get_all()/iter_all(), which stop on an empty token.
        """
        params: dict[str, Any] = {}
        if name is not None:
            params["name"] = name
        if role_id is not None:
            params["roleId"] = str(role_id)

        data = self.client.get_all(
            f"/workspaces/{workspace_key}/groups",
            params=params or None,
        )
        return TypeAdapter(list[GroupModel]).validate_python(data)

    def add(self, workspace_key: str, *, group_id: UUID) -> None:
        """
        Add an existing tenant-wide group to a workspace.

        :param workspace_key: workspace key or id.
        :param group_id: UUID of the group to add (from GroupsAPI).
        :return: None.
        HTTP: POST /workspaces/{workspace}/groups/{groupId}
        NOTE: body-less POST -- an empty JSON object is sent as the payload.
        """
        self.client.post(f"/workspaces/{workspace_key}/groups/{group_id}", body={})
        return None

    def remove(self, workspace_key: str, *, group_id: UUID) -> None:
        """
        Remove a group from a workspace (the group itself is untouched).

        :param workspace_key: workspace key or id.
        :param group_id: UUID of the group to remove.
        :return: None.
        HTTP: DELETE /workspaces/{workspace}/groups/{groupId}
        """
        self.client.delete(f"/workspaces/{workspace_key}/groups/{group_id}")
        return None

    def get_roles(self, workspace_key: str, *, group_id: UUID) -> builtins.list[SimpleRoleModel]:
        """
        List the roles a group holds in a workspace.

        :param workspace_key: workspace key or id.
        :param group_id: UUID of the group.
        :return: every SimpleRoleModel assigned to the group in this
            workspace.
        HTTP: GET /workspaces/{workspace}/groups/{groupId}/roles
        NOTE: bare-array-under-"roles"-key response, no pagination fields --
        uses a plain get(), not get_all().
        """
        data = self.client.get(f"/workspaces/{workspace_key}/groups/{group_id}/roles")
        return SimpleRoleModelList.model_validate(data).roles

    def add_role(self, workspace_key: str, *, group_id: UUID, role_id: UUID) -> None:
        """
        Assign a role to a group within a workspace.

        :param workspace_key: workspace key or id.
        :param group_id: UUID of the group.
        :param role_id: UUID of the role to assign.
        :return: None.
        HTTP: POST /workspaces/{workspace}/groups/{groupId}/roles/{roleId}
        NOTE: body-less POST -- an empty JSON object is sent as the payload.
        """
        self.client.post(
            f"/workspaces/{workspace_key}/groups/{group_id}/roles/{role_id}",
            body={},
        )
        return None

    def remove_role(self, workspace_key: str, *, group_id: UUID, role_id: UUID) -> None:
        """
        Unassign a role from a group within a workspace.

        :param workspace_key: workspace key or id.
        :param group_id: UUID of the group.
        :param role_id: UUID of the role to remove.
        :return: None.
        HTTP: DELETE /workspaces/{workspace}/groups/{groupId}/roles/{roleId}
        """
        self.client.delete(f"/workspaces/{workspace_key}/groups/{group_id}/roles/{role_id}")
        return None
