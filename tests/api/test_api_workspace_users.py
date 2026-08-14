import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from teamstorm.api.workspace_users import WorkspaceUsersAPI


def _user_payload() -> dict:
    return {
        "id": str(uuid4()),
        "displayName": "John Doe",
        "username": "john",
        "email": "john@example.com",
        "providerId": None,
    }


class WorkspaceUsersAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = WorkspaceUsersAPI(self.client)
        self.workspace = "WS"
        self.user_id = uuid4()
        self.role_id = uuid4()

    def test_list_add_remove_get_roles_add_role_remove_role(self) -> None:
        self.client.get_all.return_value = [_user_payload()]
        self.client.get.return_value = {"roles": [{"id": str(self.role_id), "name": "Admin"}]}
        self.client.post.return_value = None
        self.client.delete.return_value = None

        listed = self.api.list(
            self.workspace,
            display_name="John",
            role_id=self.role_id,
        )
        self.client.get_all.assert_called_once_with(
            "/workspaces/WS/users",
            params={"displayName": "John", "roleId": str(self.role_id)},
        )
        self.assertEqual(1, len(listed))
        self.assertEqual("john", listed[0].username)

        self.assertIsNone(self.api.add(self.workspace, user_id=self.user_id))
        self.client.post.assert_any_call(f"/workspaces/WS/users/{self.user_id}", body={})

        self.assertIsNone(self.api.remove(self.workspace, user_id=self.user_id))
        self.client.delete.assert_any_call(f"/workspaces/WS/users/{self.user_id}")

        roles = self.api.get_roles(self.workspace, user_id=self.user_id)
        self.client.get.assert_called_once_with(f"/workspaces/WS/users/{self.user_id}/roles")
        self.assertEqual(1, len(roles))
        self.assertEqual("Admin", roles[0].name)

        self.assertIsNone(self.api.add_role(self.workspace, user_id=self.user_id, role_id=self.role_id))
        self.client.post.assert_any_call(
            f"/workspaces/WS/users/{self.user_id}/roles/{self.role_id}",
            body={},
        )

        self.assertIsNone(self.api.remove_role(self.workspace, user_id=self.user_id, role_id=self.role_id))
        self.client.delete.assert_any_call(f"/workspaces/WS/users/{self.user_id}/roles/{self.role_id}")


if __name__ == "__main__":
    unittest.main()
