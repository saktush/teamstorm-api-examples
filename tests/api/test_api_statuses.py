import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from pydantic import ValidationError

from teamstorm.api.statuses import StatusesAPI
from teamstorm.models.statuses import CreateStatusRequestBody


def _status_category_payload() -> dict:
    return {"id": str(uuid4()), "name": "In Progress"}


def _status_payload() -> dict:
    return {
        "id": str(uuid4()),
        "name": "In Progress",
        "category": _status_category_payload(),
    }


class StatusesAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = StatusesAPI(self.client)
        self.workspace = "WS"

    def test_list_categories_and_list(self) -> None:
        self.client.get_all.side_effect = [[_status_category_payload()], [_status_payload()]]

        categories = self.api.list_categories()
        self.client.get_all.assert_any_call("/status-categories")
        self.assertEqual(1, len(categories))

        statuses = self.api.list(self.workspace)
        self.client.get_all.assert_any_call("/workspaces/WS/statuses")
        self.assertEqual(1, len(statuses))
        self.assertEqual("In Progress", statuses[0].name)

    def test_get_and_create(self) -> None:
        payload = _status_payload()
        self.client.get.return_value = payload
        self.client.post.return_value = payload

        got = self.api.get(self.workspace, status_key="InProgress")
        self.client.get.assert_called_once_with("/workspaces/WS/statuses/InProgress")
        self.assertEqual("In Progress", got.name)

        created = self.api.create(
            self.workspace,
            CreateStatusRequestBody(name="To Do", category="ToDo"),
        )
        self.assertEqual("In Progress", created.name)
        self.client.post.assert_called_once_with(
            "/workspaces/WS/statuses",
            {"name": "To Do", "category": "ToDo"},
        )

    def test_validation_error_on_bad_payload(self) -> None:
        self.client.get.return_value = {"id": str(uuid4())}
        with self.assertRaises(ValidationError):
            self.api.get(self.workspace, status_key="Broken")


if __name__ == "__main__":
    unittest.main()
