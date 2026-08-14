import unittest
from uuid import uuid4

from pydantic import ValidationError

from teamstorm.models.roles import (
    CreateRoleRequestBody,
    PatchRoleRequestBody,
    RoleModel,
    RolesModelList,
    SimpleRoleModelList,
)


class RolesModelsTestCase(unittest.TestCase):
    def test_parse_role_model(self) -> None:
        model = RoleModel.model_validate(
            {
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
                "permissions": ["WorkspaceEdit", "WorkitemCreate"],
            }
        )
        self.assertEqual("Admin", model.name)
        self.assertFalse(model.is_system)
        self.assertEqual(2, len(model.permissions))

    def test_parse_roles_model_list_and_alias_dump(self) -> None:
        model = RolesModelList.model_validate(
            {
                "fromToken": "a",
                "maxItemsCount": 50,
                "nextToken": "b",
                "items": [
                    {
                        "id": str(uuid4()),
                        "name": "Member",
                        "author": {
                            "id": str(uuid4()),
                            "displayName": "Jane",
                            "username": "jane",
                            "email": "jane@example.com",
                            "providerId": None,
                        },
                        "isSystem": True,
                        "permissions": ["WorkspaceContentRead"],
                    }
                ],
            }
        )
        self.assertEqual("a", model.from_token)
        dumped = model.model_dump()
        self.assertIn("fromToken", dumped)
        self.assertIn("maxItemsCount", dumped)
        self.assertIn("nextToken", dumped)
        self.assertIn("isSystem", dumped["items"][0])

    def test_parse_simple_role_model_list(self) -> None:
        model = SimpleRoleModelList.model_validate({"roles": [{"id": str(uuid4()), "name": "Observer"}]})
        self.assertEqual(1, len(model.roles))
        self.assertEqual("Observer", model.roles[0].name)

    def test_create_and_patch_request_models(self) -> None:
        created = CreateRoleRequestBody.model_validate({"name": "Dev", "permissions": ["WorkspaceEdit"]})
        self.assertEqual("Dev", created.name)

        with self.assertRaises(ValidationError):
            CreateRoleRequestBody.model_validate({"name": "Dev"})

        patch_empty = PatchRoleRequestBody.model_validate({})
        self.assertIsNone(patch_empty.name)
        self.assertIsNone(patch_empty.permissions)

        patch_nullable = PatchRoleRequestBody.model_validate({"name": None, "permissions": None})
        self.assertIsNone(patch_nullable.name)
        self.assertIsNone(patch_nullable.permissions)

    def test_extra_fields_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            CreateRoleRequestBody.model_validate({"name": "Dev", "permissions": [], "extra": True})

        with self.assertRaises(ValidationError):
            RoleModel.model_validate(
                {
                    "id": str(uuid4()),
                    "name": "Dev",
                    "author": {
                        "id": str(uuid4()),
                        "displayName": "Jane",
                        "username": "jane",
                        "email": "jane@example.com",
                        "providerId": None,
                    },
                    "isSystem": True,
                    "permissions": [],
                    "unknown": "x",
                }
            )


if __name__ == "__main__":
    unittest.main()
