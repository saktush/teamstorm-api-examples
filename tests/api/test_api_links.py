import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from pydantic import ValidationError

from teamstorm.api.links import LinksAPI
from teamstorm.models.links import CreateWorkitemLinkRequestBody


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


def _link_payload() -> dict:
    return {
        "id": str(uuid4()),
        "type": {"id": str(uuid4()), "name": "Relates to", "key": "RelatesTo"},
        "linkedWorkitem": _workitem_payload(),
    }


def _link_type_payload() -> dict:
    return {"id": str(uuid4()), "name": "Relates to", "key": "RelatesTo"}


class LinksAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = LinksAPI(self.client)
        self.workspace = "WS"
        self.workitem_id = uuid4()
        self.link_id = uuid4()

    def test_list_uses_get_all_on_workitem_nested_path(self) -> None:
        self.client.get_all.return_value = [_link_payload()]

        result = self.api.list(self.workspace, workitem_id=self.workitem_id)

        self.client.get_all.assert_called_once_with(f"/workspaces/{self.workspace}/workitems/{self.workitem_id}/links")
        self.assertEqual(1, len(result))
        self.assertEqual("Relates to", result[0].type.name)

    def test_list_validation_error_on_bad_payload(self) -> None:
        self.client.get_all.return_value = [{"id": str(uuid4())}]
        with self.assertRaises(ValidationError):
            self.api.list(self.workspace, workitem_id=self.workitem_id)

    def test_create_posts_to_workitem_nested_path(self) -> None:
        self.client.post.return_value = _link_payload()
        body = CreateWorkitemLinkRequestBody(type="RelatesTo", linked_workitem="WS-2", linked_workspace="WS-OTHER")

        result = self.api.create(self.workspace, workitem_id=self.workitem_id, body=body)

        self.client.post.assert_called_once_with(
            f"/workspaces/{self.workspace}/workitems/{self.workitem_id}/links",
            {"type": "RelatesTo", "linkedWorkitem": "WS-2", "linkedWorkspace": "WS-OTHER"},
        )
        self.assertEqual("Relates to", result.type.name)

    def test_delete_uses_workspace_scoped_path_not_workitem_nested(self) -> None:
        # The DELETE route is `/workspaces/{workspace}/links/{linkId}` -- NOT
        # nested under the workitem like list()/create() above. This is the
        # one thing most likely to be mirrored wrong from the POST path.
        self.client.delete.return_value = None

        result = self.api.delete(self.workspace, link_id=self.link_id)

        self.client.delete.assert_called_once_with(f"/workspaces/{self.workspace}/links/{self.link_id}")
        self.assertIsNone(result)

        called_path = self.client.delete.call_args.args[0]
        self.assertNotIn("workitems", called_path)
        self.assertEqual(f"/workspaces/{self.workspace}/links/{self.link_id}", called_path)

    def test_list_types_uses_get_all_on_workspace_scoped_path(self) -> None:
        self.client.get_all.return_value = [_link_type_payload()]

        result = self.api.list_types(self.workspace)

        self.client.get_all.assert_called_once_with(f"/workspaces/{self.workspace}/link-types")
        self.assertEqual(1, len(result))
        self.assertEqual("Relates to", result[0].name)

    def test_list_types_validation_error_on_bad_payload(self) -> None:
        self.client.get_all.return_value = [{"id": str(uuid4())}]
        with self.assertRaises(ValidationError):
            self.api.list_types(self.workspace)


if __name__ == "__main__":
    unittest.main()
