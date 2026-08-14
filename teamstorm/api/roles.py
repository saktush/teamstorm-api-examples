from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import TypeAdapter

from teamstorm.api._base import BaseAPI
from teamstorm.models.roles import CreateRoleRequestBody, PatchRoleRequestBody, RoleModel


class RolesAPI(BaseAPI):
    """
    Workspace-scoped permission roles: a name plus a set of Permission values
    (69-member fixed vocabulary), assignable to users and groups via
    WorkspaceUsersAPI/WorkspaceGroupsAPI.

    5 ops (Roles tag): list, get, create, patch, delete.
    """

    def list(
        self,
        workspace_key: str,
        *,
        name: str | None = None,
        is_system_role: bool | None = None,
    ) -> list[RoleModel]:
        """
        List the roles defined in a workspace.

        :param workspace_key: workspace key or id.
        :param name: optional name filter.
        :param is_system_role: optional filter for built-in vs. custom roles.
        :return: every matching RoleModel.
        HTTP: GET /workspaces/{workspace}/roles
        NOTE: the endpoint is paginated on the wire (fromToken/maxItemsCount),
        but this method does not expose a from_token/max_items_count
        parameter -- get_all() still walks every page regardless, using the
        client's default page size of 500.
        """
        params: dict[str, Any] = {}
        if name is not None:
            params["name"] = name
        if is_system_role is not None:
            params["isSystemRole"] = is_system_role

        data = self.client.get_all(
            f"/workspaces/{workspace_key}/roles",
            params=params or None,
        )
        return TypeAdapter(list[RoleModel]).validate_python(data)

    def get(self, workspace_key: str, *, role_id: UUID) -> RoleModel:
        """
        Fetch a single role by id.

        :param workspace_key: workspace key or id.
        :param role_id: UUID of the role to fetch.
        :return: the matching RoleModel.
        HTTP: GET /workspaces/{workspace}/roles/{roleId}
        """
        data = self.client.get(f"/workspaces/{workspace_key}/roles/{role_id}")
        return RoleModel.model_validate(data)

    def create(self, workspace_key: str, body: CreateRoleRequestBody) -> RoleModel:
        """
        Create a new custom role.

        :param workspace_key: workspace key or id.
        :param body: CreateRoleRequestBody -- required name and permissions
            list (see models.enums-adjacent Permission for the fixed
            vocabulary).
        :return: the created RoleModel.
        HTTP: POST /workspaces/{workspace}/roles
        """
        payload = body.model_dump(mode="json", exclude_none=True)
        data = self.client.post(f"/workspaces/{workspace_key}/roles", payload)
        return RoleModel.model_validate(data)

    def patch(self, workspace_key: str, *, role_id: UUID, body: PatchRoleRequestBody) -> RoleModel:
        """
        Partially update a role's name and/or permissions.

        :param workspace_key: workspace key or id.
        :param role_id: UUID of the role to patch.
        :param body: partial role fields to update.
        :return: the updated RoleModel.
        HTTP: PATCH /workspaces/{workspace}/roles/{roleId}
        NOTE: only fields explicitly set on *body* are sent
        (exclude_unset=True): the server distinguishes a field absent from
        the request body (leave unchanged)
        from one present with value null (clear it). exclude_none is
        explicitly disabled here because TsBaseModel.model_dump() otherwise
        defaults exclude_none=True, which would silently drop an intentional
        "clear this field" null.
        """
        payload = body.model_dump(mode="json", exclude_unset=True, exclude_none=False)
        data = self.client.patch(f"/workspaces/{workspace_key}/roles/{role_id}", payload)
        return RoleModel.model_validate(data)

    def delete(
        self,
        workspace_key: str,
        *,
        role_id: UUID,
        replacement_role_id: UUID | None = None,
    ) -> None:
        """
        Delete a role, optionally reassigning everyone who held it.

        :param workspace_key: workspace key or id.
        :param role_id: UUID of the role to delete.
        :param replacement_role_id: optional UUID of a role to assign in
            place of the deleted one to every user/group that held it; when
            omitted, those principals simply lose the deleted role.
        :return: None.
        HTTP: DELETE /workspaces/{workspace}/roles/{roleId}
        """
        params: dict[str, Any] = {}
        if replacement_role_id is not None:
            params["replacementRoleId"] = str(replacement_role_id)
        self.client.delete(
            f"/workspaces/{workspace_key}/roles/{role_id}",
            params=params or None,
        )
        return None
