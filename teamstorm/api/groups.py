from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import TypeAdapter

from teamstorm.api._base import BaseAPI
from teamstorm.models.common import GroupModel


class GroupsAPI(BaseAPI):
    """
    Tenant-wide user groups (identity groups, distinct from workspace-scoped
    membership managed by WorkspaceGroupsAPI).

    2 ops (UserGroups tag): list, get. Global (non-workspace-scoped)
    resource -- neither method takes a workspace_key.
    """

    def list(
        self,
        *,
        name: str | None = None,
        provider_id: UUID | None = None,
    ) -> list[GroupModel]:
        """
        List every user group visible on this CWM instance.

        :param name: optional name filter.
        :param provider_id: optional identity provider UUID filter.
        :return: every matching GroupModel.
        HTTP: GET /user-groups
        NOTE: this endpoint does not paginate (no fromToken/maxItemsCount on
        the wire) -- a bare array is returned; get_all() is used only as the
        client's generic list-fetch helper.
        """
        params: dict[str, Any] = {}
        if name is not None:
            params["name"] = name
        if provider_id is not None:
            params["providerId"] = str(provider_id)

        data = self.client.get_all("/user-groups", params=params or None)
        return TypeAdapter(list[GroupModel]).validate_python(data)

    def get(self, group: str, *, provider_id: UUID | None = None) -> GroupModel:
        """
        Fetch a single user group by id or name.

        :param group: group UUID or name (path segment).
        :param provider_id: optional identity provider UUID, used to
            disambiguate a name that exists under more than one provider.
        :return: the matching GroupModel.
        HTTP: GET /user-groups/{group}
        """
        params: dict[str, Any] = {}
        if provider_id is not None:
            params["providerId"] = str(provider_id)

        data = self.client.get(f"/user-groups/{group}", params=params or None)
        return GroupModel.model_validate(data)
