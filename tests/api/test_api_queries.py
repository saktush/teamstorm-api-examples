import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from pydantic import ValidationError

from teamstorm.api.queries import QueriesAPI
from teamstorm.models.enums import PrincipalType, QueryVisibilityType
from teamstorm.models.queries import UpdateQueryPrincipalModel, UpdateQueryVisibilitySettingsRequestBody


def _workitem_payload() -> dict:
    return {
        "id": str(uuid4()),
        "key": "WS-1",
        "name": "Task",
        "author": {"id": str(uuid4()), "displayName": "Ada Lovelace", "username": "ada"},
        "folder": {"id": str(uuid4()), "name": "Backlog"},
        "parent": {"id": str(uuid4()), "nodeType": "Folder"},
        "attributes": [],
        "portfolios": [],
        "workspace": {
            "id": str(uuid4()),
            "key": "WS",
            "name": "Workspace",
        },
    }


def _visibility_payload(**overrides) -> dict:
    payload = {
        "visibilityType": "OnlySelected",
        "accessList": [
            {
                "id": str(uuid4()),
                "type": "User",
                "user": {
                    "id": str(uuid4()),
                    "displayName": "Ada Lovelace",
                    "username": "ada",
                    "email": "ada@example.com",
                },
            },
            {
                "id": str(uuid4()),
                "type": "Group",
                "group": {
                    "id": str(uuid4()),
                    "name": "QA Team",
                },
            },
        ],
    }
    payload.update(overrides)
    return payload


class QueriesAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = QueriesAPI(self.client)
        self.workspace = "WS"
        self.query_id = uuid4()

    def test_list_workitems_has_no_workspace_segment(self) -> None:
        self.client.get_all.return_value = [_workitem_payload()]

        result = self.api.list_workitems(self.query_id, from_token="tok-1", max_items_count=25)

        self.client.get_all.assert_called_once_with(
            f"/queries/{self.query_id}/workitems",
            params={"fromToken": "tok-1", "maxItemsCount": 25},
        )
        self.assertEqual(1, len(result))
        self.assertEqual("Task", result[0].name)

    def test_list_workitems_without_optional_params(self) -> None:
        self.client.get_all.return_value = [_workitem_payload()]

        self.api.list_workitems(self.query_id)

        self.client.get_all.assert_called_once_with(
            f"/queries/{self.query_id}/workitems",
            params=None,
        )

    def test_get_visibility_is_workspace_scoped_and_parses_mixed_access_list(self) -> None:
        self.client.get.return_value = _visibility_payload()

        result = self.api.get_visibility(self.workspace, query_id=self.query_id)

        self.client.get.assert_called_once_with(f"/workspaces/{self.workspace}/queries/{self.query_id}/visibility")
        self.assertEqual(QueryVisibilityType.OnlySelected, result.visibility_type)
        self.assertEqual(2, len(result.access_list))
        self.assertEqual(PrincipalType.User, result.access_list[0].type)
        self.assertEqual("ada", result.access_list[0].user.username)
        self.assertEqual(PrincipalType.Group, result.access_list[1].type)
        self.assertEqual("QA Team", result.access_list[1].group.name)

    def test_update_visibility_is_workspace_scoped_and_serializes_body(self) -> None:
        self.client.put.return_value = _visibility_payload()
        user_id = uuid4()

        body = UpdateQueryVisibilitySettingsRequestBody(
            visibility_type=QueryVisibilityType.OnlySelected,
            access_list=[UpdateQueryPrincipalModel(id=user_id, type=PrincipalType.User)],
        )

        result = self.api.update_visibility(self.workspace, query_id=self.query_id, body=body)

        self.client.put.assert_called_once_with(
            f"/workspaces/{self.workspace}/queries/{self.query_id}/visibility",
            {
                "visibilityType": "OnlySelected",
                "accessList": [{"id": str(user_id), "type": "User"}],
            },
        )
        self.assertEqual(QueryVisibilityType.OnlySelected, result.visibility_type)

    def test_get_visibility_validation_error_on_bad_payload(self) -> None:
        self.client.get.return_value = {"visibilityType": "OnlySelected"}  # missing accessList
        with self.assertRaises(ValidationError):
            self.api.get_visibility(self.workspace, query_id=self.query_id)


if __name__ == "__main__":
    unittest.main()
