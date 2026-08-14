from __future__ import annotations

import builtins
from typing import Any
from uuid import UUID

from pydantic import TypeAdapter

from teamstorm.api._base import BaseAPI
from teamstorm.models.common import UserModel
from teamstorm.models.roles import SimpleRoleModel, SimpleRoleModelList


class WorkspaceUsersAPI(BaseAPI):
    """
    Workspace-scoped user membership and roles: which UsersAPI accounts
    belong to a workspace, and which RolesAPI roles each user holds there.

    6 ops (WorkspaceUsers tag): list, add, remove, get_roles, add_role,
    remove_role. The per-group counterpart is WorkspaceGroupsAPI.
    """

    def list(
        self,
        workspace_key: str,
        *,
        display_name: str | None = None,
        role_id: UUID | None = None,
    ) -> list[UserModel]:
        """
        List the users that belong to a workspace.

        :param workspace_key: workspace key or id.
        :param display_name: optional display-name filter.
        :param role_id: optional filter to users holding a specific role.
        :return: every matching UserModel.
        HTTP: GET /workspaces/{workspace}/users
        NOTE: the endpoint is paginated on the wire (fromToken/maxItemsCount),
        but this method does not expose a from_token/max_items_count
        parameter -- get_all() still walks every page regardless, using the
        client's default page size of 500.
        """
        params: dict[str, Any] = {}
        if display_name is not None:
            params["displayName"] = display_name
        if role_id is not None:
            params["roleId"] = str(role_id)

        data = self.client.get_all(
            f"/workspaces/{workspace_key}/users",
            params=params or None,
        )
        return TypeAdapter(list[UserModel]).validate_python(data)

    def add(self, workspace_key: str, *, user_id: UUID) -> None:
        """
        Add an existing tenant-wide user to a workspace.

        :param workspace_key: workspace key or id.
        :param user_id: UUID of the user to add (from UsersAPI).
        :return: None.
        HTTP: POST /workspaces/{workspace}/users/{userId}
        NOTE: body-less POST -- an empty JSON object is sent as the payload.
        """
        self.client.post(f"/workspaces/{workspace_key}/users/{user_id}", body={})
        return None

    def remove(self, workspace_key: str, *, user_id: UUID) -> None:
        """
        Remove a user from a workspace (the user account itself is
        untouched).

        :param workspace_key: workspace key or id.
        :param user_id: UUID of the user to remove.
        :return: None.
        HTTP: DELETE /workspaces/{workspace}/users/{userId}
        """
        self.client.delete(f"/workspaces/{workspace_key}/users/{user_id}")
        return None

    def get_roles(self, workspace_key: str, *, user_id: UUID) -> builtins.list[SimpleRoleModel]:
        """
        List the roles a user holds in a workspace.

        :param workspace_key: workspace key or id.
        :param user_id: UUID of the user.
        :return: every SimpleRoleModel assigned to the user in this
            workspace.
        HTTP: GET /workspaces/{workspace}/users/{userId}/roles
        NOTE: bare-array-under-"roles"-key response, no pagination fields --
        uses a plain get(), not get_all().
        """
        data = self.client.get(f"/workspaces/{workspace_key}/users/{user_id}/roles")
        return SimpleRoleModelList.model_validate(data).roles

    def add_role(self, workspace_key: str, *, user_id: UUID, role_id: UUID) -> None:
        """
        Assign a role to a user within a workspace.

        :param workspace_key: workspace key or id.
        :param user_id: UUID of the user.
        :param role_id: UUID of the role to assign.
        :return: None.
        HTTP: POST /workspaces/{workspace}/users/{userId}/roles/{roleId}
        NOTE: body-less POST -- an empty JSON object is sent as the payload.
        """
        self.client.post(
            f"/workspaces/{workspace_key}/users/{user_id}/roles/{role_id}",
            body={},
        )
        return None

    def remove_role(self, workspace_key: str, *, user_id: UUID, role_id: UUID) -> None:
        """
        Unassign a role from a user within a workspace.

        :param workspace_key: workspace key or id.
        :param user_id: UUID of the user.
        :param role_id: UUID of the role to remove.
        :return: None.
        HTTP: DELETE /workspaces/{workspace}/users/{userId}/roles/{roleId}
        """
        self.client.delete(f"/workspaces/{workspace_key}/users/{user_id}/roles/{role_id}")
        return None
