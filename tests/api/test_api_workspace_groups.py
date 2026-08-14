import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from teamstorm.api.workspace_groups import WorkspaceGroupsAPI


def _group_payload() -> dict:
    return {
        "id": str(uuid4()),
        "name": "Team A",
        "providerId": None,
    }


class WorkspaceGroupsAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = WorkspaceGroupsAPI(self.client)
        self.workspace = "WS"
        self.group_id = uuid4()
        self.role_id = uuid4()

    def test_list_add_remove_get_roles_add_role_remove_role(self) -> None:
        self.client.get_all.return_value = [_group_payload()]
        self.client.get.return_value = {"roles": [{"id": str(self.role_id), "name": "Member"}]}
        self.client.post.return_value = None
        self.client.delete.return_value = None

        listed = self.api.list(self.workspace, name="Team", role_id=self.role_id)
        self.client.get_all.assert_called_once_with(
            "/workspaces/WS/groups",
            params={"name": "Team", "roleId": str(self.role_id)},
        )
        self.assertEqual(1, len(listed))
        self.assertEqual("Team A", listed[0].name)

        self.assertIsNone(self.api.add(self.workspace, group_id=self.group_id))
        self.client.post.assert_any_call(f"/workspaces/WS/groups/{self.group_id}", body={})

        self.assertIsNone(self.api.remove(self.workspace, group_id=self.group_id))
        self.client.delete.assert_any_call(f"/workspaces/WS/groups/{self.group_id}")

        roles = self.api.get_roles(self.workspace, group_id=self.group_id)
        self.client.get.assert_called_once_with(f"/workspaces/WS/groups/{self.group_id}/roles")
        self.assertEqual(1, len(roles))
        self.assertEqual("Member", roles[0].name)

        self.assertIsNone(self.api.add_role(self.workspace, group_id=self.group_id, role_id=self.role_id))
        self.client.post.assert_any_call(
            f"/workspaces/WS/groups/{self.group_id}/roles/{self.role_id}",
            body={},
        )

        self.assertIsNone(self.api.remove_role(self.workspace, group_id=self.group_id, role_id=self.role_id))
        self.client.delete.assert_any_call(f"/workspaces/WS/groups/{self.group_id}/roles/{self.role_id}")


if __name__ == "__main__":
    unittest.main()
