import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from teamstorm.api.users import UsersAPI


def _user_payload() -> dict:
    return {
        "id": str(uuid4()),
        "displayName": "John Doe",
        "username": "john",
        "email": "john@example.com",
        "providerId": None,
    }


class UsersAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = UsersAPI(self.client)
        self.user_id = uuid4()

    def test_list_uses_get_all_with_filters_and_parses(self) -> None:
        self.client.get_all.return_value = [_user_payload()]

        result = self.api.list(
            username="john",
            display_name="John",
            email="john@example.com",
            provider_id=self.user_id,
        )

        self.client.get_all.assert_called_once_with(
            "/users",
            params={
                "username": "john",
                "displayName": "John",
                "email": "john@example.com",
                "providerId": str(self.user_id),
            },
        )
        self.assertEqual(1, len(result))
        self.assertEqual("john", result[0].username)

    def test_get_uses_user_path_segment_no_workspace(self) -> None:
        self.client.get.return_value = _user_payload()

        result = self.api.get("john")

        self.client.get.assert_called_once_with("/users/john", params=None)
        self.assertEqual("john", result.username)

    def test_get_passes_provider_id_query_param(self) -> None:
        provider_id = uuid4()
        self.client.get.return_value = _user_payload()

        self.api.get("john", provider_id=provider_id)

        self.client.get.assert_called_once_with(
            "/users/john",
            params={"providerId": str(provider_id)},
        )

    def test_block_is_bodyless_post_verb_before_id(self) -> None:
        self.client.post.return_value = None

        result = self.api.block(self.user_id)

        self.assertIsNone(result)
        self.client.post.assert_called_once_with(f"/users/block/{self.user_id}")

    def test_unblock_is_bodyless_post_verb_before_id(self) -> None:
        self.client.post.return_value = None

        result = self.api.unblock(self.user_id)

        self.assertIsNone(result)
        self.client.post.assert_called_once_with(f"/users/unblock/{self.user_id}")


if __name__ == "__main__":
    unittest.main()
