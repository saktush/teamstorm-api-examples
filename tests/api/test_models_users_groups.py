import unittest
from uuid import uuid4

from pydantic import ValidationError

from teamstorm.models.common import GroupModel, GroupModelList, UserModel, UserModelList, UsersModelList


class UsersGroupsModelsTestCase(unittest.TestCase):
    def _user_payload(self) -> dict:
        return {
            "id": str(uuid4()),
            "displayName": "John Doe",
            "username": "john",
            "email": "john@example.com",
            "providerId": None,
        }

    def test_parse_group_model_with_provider_alias(self) -> None:
        provider_id = str(uuid4())
        model = GroupModel.model_validate({"id": str(uuid4()), "name": "Team A", "providerId": provider_id})
        self.assertEqual("Team A", model.name)
        self.assertEqual(provider_id, str(model.provider_id))
        self.assertIn("providerId", model.model_dump())

    def test_parse_group_and_user_model_lists_with_pagination_aliases(self) -> None:
        groups = GroupModelList.model_validate(
            {
                "fromToken": "g1",
                "maxItemsCount": 10,
                "nextToken": "g2",
                "items": [{"id": str(uuid4()), "name": "Team A", "providerId": None}],
            }
        )
        self.assertEqual("g1", groups.from_token)
        groups_dump = groups.model_dump()
        self.assertIn("fromToken", groups_dump)
        self.assertIn("maxItemsCount", groups_dump)
        self.assertIn("nextToken", groups_dump)

        users = UserModelList.model_validate(
            {
                "fromToken": "u1",
                "maxItemsCount": 20,
                "nextToken": "u2",
                "items": [self._user_payload()],
            }
        )
        self.assertEqual("u2", users.next_token)
        users_dump = users.model_dump()
        self.assertIn("fromToken", users_dump)
        self.assertIn("displayName", users_dump["items"][0])

    def test_parse_users_model_list_for_global_users(self) -> None:
        model = UsersModelList.model_validate({"items": [self._user_payload()]})
        self.assertEqual(1, len(model.items))
        self.assertEqual("john", model.items[0].username)

    def test_parse_user_model_with_null_email(self) -> None:
        # swagger.json marks UserModel.email as nullable (and required: the key is
        # always present, but its value may be null). A real server response can
        # therefore send {"email": null}; this must parse without raising.
        payload = self._user_payload()
        payload["email"] = None

        model = UserModel.model_validate(payload)

        self.assertIsNone(model.email)
        self.assertNotIn("email", model.model_dump())

    def test_extra_fields_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            GroupModel.model_validate({"id": str(uuid4()), "name": "Team A", "providerId": None, "extra": True})

        with self.assertRaises(ValidationError):
            UsersModelList.model_validate({"items": [self._user_payload()], "unexpected": 1})


if __name__ == "__main__":
    unittest.main()
