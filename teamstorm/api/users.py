from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import TypeAdapter

from ._base import BaseAPI
from ..models.common import UserModel


class UsersAPI(BaseAPI):
    """
    Tenant-wide user accounts: lookup, and blocking/unblocking sign-in.

    4 ops (Users tag): list, get, block, unblock. Global
    (non-workspace-scoped) resource -- no method takes a workspace_key.
    Workspace membership and per-workspace roles live in WorkspaceUsersAPI.
    """

    def list(
        self,
        *,
        username: str | None = None,
        display_name: str | None = None,
        email: str | None = None,
        provider_id: UUID | None = None,
    ) -> list[UserModel]:
        """
        GET /users with query params username/displayName/email/providerId. [1]
        """
        params: dict[str, Any] = {}
        if username is not None:
            params["username"] = username
        if display_name is not None:
            params["displayName"] = display_name
        if email is not None:
            params["email"] = email
        if provider_id is not None:
            params["providerId"] = str(provider_id)

        data = self.client.get_all("/users", params=params or None)

        # If get_all returns list[dict] items:
        return TypeAdapter(list[UserModel]).validate_python(data)

        # If get_all returns full UserModelList object:
        # model_list = UserModelList.model_validate(data)
        # return model_list.items

    def get(self, user: str, *, provider_id: UUID | None = None) -> UserModel:
        """
        Retrieve a single user by id or username.

        This is a global (non-workspace-scoped) resource.

        Args:
            user: user id (UUID) or username identifying the account.
            provider_id: optional identity provider UUID, used to disambiguate
                a username that exists under more than one provider.

        Returns:
            UserModel: the matching user.

        HTTP: GET /users/{user}
        """
        params: dict[str, Any] = {}
        if provider_id is not None:
            params["providerId"] = str(provider_id)

        data = self.client.get(f"/users/{user}", params=params or None)
        return UserModel.model_validate(data)

    def block(self, user_id: UUID) -> None:
        """
        Block a user account, changing its state so the user can no longer sign in.

        This is a body-less POST: no request payload is sent. This is a
        global (non-workspace-scoped) operation.

        Args:
            user_id: UUID of the user to block.

        Returns:
            None.

        HTTP: POST /users/block/{userId}
        """
        self.client.post(f"/users/block/{user_id}")
        return None

    def unblock(self, user_id: UUID) -> None:
        """
        Unblock a previously blocked user account, restoring its ability to sign in.

        This is a body-less POST: no request payload is sent. This is a
        global (non-workspace-scoped) operation.

        Args:
            user_id: UUID of the user to unblock.

        Returns:
            None.

        HTTP: POST /users/unblock/{userId}
        """
        self.client.post(f"/users/unblock/{user_id}")
        return None
