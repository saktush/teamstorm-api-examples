import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from pydantic import ValidationError

from teamstorm.api.roles import RolesAPI
from teamstorm.models.roles import CreateRoleRequestBody, PatchRoleRequestBody


def _role_payload() -> dict:
    return {
        "id": str(uuid4()),
        "name": "Admin",
        "author": {
            "id": str(uuid4()),
            "displayName": "John Doe",
            "username": "john",
            "email": "john@example.com",
            "providerId": None,
        },
        "isSystem": False,
        "permissions": ["WorkspaceEdit"],
    }


class RolesAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = RolesAPI(self.client)
        self.workspace = "WS"
        self.role_id = uuid4()

    def test_list_get_create_patch_delete(self) -> None:
        payload = _role_payload()
        self.client.get_all.return_value = [payload]
        self.client.get.return_value = payload
        self.client.post.return_value = payload
        self.client.patch.return_value = payload
        self.client.delete.return_value = None

        listed = self.api.list(self.workspace, name="Admin", is_system_role=False)
        self.client.get_all.assert_called_once_with(
            "/workspaces/WS/roles",
            params={"name": "Admin", "isSystemRole": False},
        )
        self.assertEqual(1, len(listed))

        got = self.api.get(self.workspace, role_id=self.role_id)
        self.client.get.assert_called_once_with(f"/workspaces/WS/roles/{self.role_id}")
        self.assertEqual("Admin", got.name)

        created = self.api.create(
            self.workspace,
            CreateRoleRequestBody(name="Admin", permissions=["WorkspaceEdit"]),
        )
        self.assertEqual("Admin", created.name)
        self.client.post.assert_any_call(
            "/workspaces/WS/roles",
            {"name": "Admin", "permissions": ["WorkspaceEdit"]},
        )

        patched = self.api.patch(
            self.workspace,
            role_id=self.role_id,
            body=PatchRoleRequestBody(name="Admin2"),
        )
        self.assertEqual("Admin", patched.name)
        self.client.patch.assert_any_call(
            f"/workspaces/WS/roles/{self.role_id}",
            {"name": "Admin2"},
        )

        deleted = self.api.delete(
            self.workspace,
            role_id=self.role_id,
            replacement_role_id=uuid4(),
        )
        self.assertIsNone(deleted)
        args, kwargs = self.client.delete.call_args
        self.assertEqual(f"/workspaces/WS/roles/{self.role_id}", args[0])
        self.assertIn("replacementRoleId", kwargs["params"])

    def test_validation_error_on_bad_payload(self) -> None:
        self.client.get.return_value = {"id": str(uuid4())}
        with self.assertRaises(ValidationError):
            self.api.get(self.workspace, role_id=self.role_id)

    def test_patch_uses_exclude_unset_and_keeps_explicit_null(self) -> None:
        payload = _role_payload()
        self.client.patch.return_value = payload

        # name is set to a real value, permissions is explicitly cleared
        # (None).
        body = PatchRoleRequestBody(name="Admin2", permissions=None)
        self.api.patch(self.workspace, role_id=self.role_id, body=body)

        self.client.patch.assert_called_once_with(
            f"/workspaces/WS/roles/{self.role_id}",
            {"name": "Admin2", "permissions": None},
        )

    def test_patch_omits_fields_never_set(self) -> None:
        payload = _role_payload()
        self.client.patch.return_value = payload

        body = PatchRoleRequestBody(name="Admin2")
        self.api.patch(self.workspace, role_id=self.role_id, body=body)

        # permissions was never assigned -> must be entirely absent, not
        # merely null, so the server treats it as "leave unchanged".
        self.client.patch.assert_called_once_with(
            f"/workspaces/WS/roles/{self.role_id}",
            {"name": "Admin2"},
        )


if __name__ == "__main__":
    unittest.main()
