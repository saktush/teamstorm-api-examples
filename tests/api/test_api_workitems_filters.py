import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from pydantic import ValidationError

from teamstorm.api.workitems import WorkitemsAPI


def _workitem_payload() -> dict:
    return {
        "id": str(uuid4()),
        "key": "WS-1",
        "name": "Task",
        "author": {"id": str(uuid4()), "displayName": "Ada Lovelace", "username": "ada"},
        "folder": {"id": str(uuid4()), "name": "Backlog"},
        "parent": {"id": str(uuid4()), "nodeType": "Folder"},
        "attributes": [
            {
                "type": "UniString",
                "id": str(uuid4()),
                "name": "Text",
                "value": "abc",
            }
        ],
        "portfolios": [],
        "workspace": {
            "id": str(uuid4()),
            "key": "WS",
            "name": "Workspace",
        },
    }


class WorkitemsAPIFiltersTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = WorkitemsAPI(self.client)

    def test_list_maps_all_swagger_filters(self) -> None:
        sprint_id = uuid4()
        portfolio_element_id = uuid4()
        self.client.get_all.return_value = [_workitem_payload()]

        result = self.api.list(
            "WS",
            type="Bug",
            sprint_id=sprint_id,
            portfolio_element_id=portfolio_element_id,
            parent=uuid4(),
            name="Task",
            assignee="john",
            author="kate",
            status="ToDo",
            status_category="InProgress",
            from_token="token-1",
            max_items_count=42,
        )

        self.assertEqual(1, len(result))
        _, kwargs = self.client.get_all.call_args
        params = kwargs["params"]
        self.assertEqual("Bug", params["type"])
        self.assertEqual(str(sprint_id), params["sprintId"])
        self.assertEqual(str(portfolio_element_id), params["portfolioElementId"])
        self.assertEqual("Task", params["name"])
        self.assertEqual("john", params["assignee"])
        self.assertEqual("kate", params["author"])
        self.assertEqual("ToDo", params["status"])
        self.assertEqual("InProgress", params["statusCategory"])
        self.assertEqual("token-1", params["fromToken"])
        self.assertEqual(42, params["maxItemsCount"])

    def test_list_validation_error_on_bad_payload(self) -> None:
        self.client.get_all.return_value = [{"id": str(uuid4())}]
        with self.assertRaises(ValidationError):
            self.api.list("WS")


if __name__ == "__main__":
    unittest.main()
