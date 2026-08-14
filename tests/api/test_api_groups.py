import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from pydantic import ValidationError

from teamstorm.api.groups import GroupsAPI


def _group_payload() -> dict:
    return {
        "id": str(uuid4()),
        "name": "Team A",
        "providerId": None,
    }


class GroupsAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = GroupsAPI(self.client)

    def test_list_and_get(self) -> None:
        provider_id = uuid4()
        payload = _group_payload()
        self.client.get_all.return_value = [payload]
        self.client.get.return_value = payload

        listed = self.api.list(name="Team", provider_id=provider_id)
        self.client.get_all.assert_called_once_with(
            "/user-groups",
            params={"name": "Team", "providerId": str(provider_id)},
        )
        self.assertEqual(1, len(listed))
        self.assertEqual("Team A", listed[0].name)

        got = self.api.get("Team A", provider_id=provider_id)
        self.client.get.assert_called_once_with(
            "/user-groups/Team A",
            params={"providerId": str(provider_id)},
        )
        self.assertEqual("Team A", got.name)

    def test_list_without_filters(self) -> None:
        self.client.get_all.return_value = [_group_payload()]

        listed = self.api.list()

        self.client.get_all.assert_called_once_with("/user-groups", params=None)
        self.assertEqual(1, len(listed))

    def test_validation_error_on_bad_payload(self) -> None:
        self.client.get.return_value = {"id": str(uuid4())}
        with self.assertRaises(ValidationError):
            self.api.get("broken")


if __name__ == "__main__":
    unittest.main()
