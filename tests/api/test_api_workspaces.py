import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from pydantic import ValidationError

from teamstorm.api.workspaces import WorkspacesAPI
from teamstorm.models.workspaces import CreateWorkspaceRequestBody, PatchWorkspaceRequestBody, WorkspaceModelList


def _workspace_payload() -> dict:
    return {
        "id": str(uuid4()),
        "key": "WS",
        "name": "Workspace",
        "description": "Desc",
    }


class WorkspacesAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = WorkspacesAPI(self.client)

    def test_list_get_create_patch_delete(self) -> None:
        payload = _workspace_payload()
        self.client.get_all.return_value = [payload]
        self.client.get.return_value = payload
        self.client.post.return_value = payload
        self.client.patch.return_value = payload
        self.client.delete.return_value = None

        listed = self.api.list(
            key="WS",
            name="Workspace",
            from_token="t1",
            max_items_count=5,
        )
        self.client.get_all.assert_called_once_with(
            "/workspaces",
            params={
                "key": "WS",
                "name": "Workspace",
                "fromToken": "t1",
                "maxItemsCount": 5,
            },
        )
        self.assertEqual(1, len(listed))

        got = self.api.get("WS")
        self.client.get.assert_called_once_with("/workspaces/WS")
        self.assertEqual("Workspace", got.name)

        created = self.api.create(CreateWorkspaceRequestBody(key="NEW", name="New WS", description="d"))
        self.assertEqual("Workspace", created.name)
        self.client.post.assert_called_once_with(
            "/workspaces",
            {"key": "NEW", "name": "New WS", "description": "d"},
        )

        patched = self.api.patch(
            workspace_key="WS",
            body=PatchWorkspaceRequestBody(name="Renamed"),
        )
        self.assertEqual("Workspace", patched.name)
        self.client.patch.assert_called_once_with(
            "/workspaces/WS",
            {"name": "Renamed"},
        )

        deleted = self.api.delete(workspace_key="WS")
        self.assertIsNone(deleted)
        self.client.delete.assert_called_once_with("/workspaces/WS")

    def test_validation_error_on_bad_payload(self) -> None:
        self.client.get.return_value = {"id": str(uuid4())}
        with self.assertRaises(ValidationError):
            self.api.get("BROKEN")

    def test_patch_uses_exclude_unset_and_keeps_explicit_null(self) -> None:
        payload = _workspace_payload()
        self.client.patch.return_value = payload

        # name is set to a real value, description is explicitly cleared
        # (None).
        body = PatchWorkspaceRequestBody(name="Renamed", description=None)
        self.api.patch(workspace_key="WS", body=body)

        self.client.patch.assert_called_once_with(
            "/workspaces/WS",
            {"name": "Renamed", "description": None},
        )

    def test_patch_omits_fields_never_set(self) -> None:
        payload = _workspace_payload()
        self.client.patch.return_value = payload

        body = PatchWorkspaceRequestBody(name="Renamed")
        self.api.patch(workspace_key="WS", body=body)

        # description was never assigned -> must be entirely absent, not
        # merely null, so the server treats it as "leave unchanged".
        self.client.patch.assert_called_once_with(
            "/workspaces/WS",
            {"name": "Renamed"},
        )


class WorkspaceModelListTestCase(unittest.TestCase):
    def test_round_trips_realistic_paginated_envelope(self) -> None:
        # Regression test for the missing Field(alias=...) on the pagination
        # fields: without them, extra="forbid" rejects a real paginated
        # /workspaces response outright (camelCase keys don't match the
        # unaliased snake_case field names).
        payload = {
            "fromToken": "10",
            "maxItemsCount": 50,
            "nextToken": "20",
            "items": [_workspace_payload()],
        }

        model = WorkspaceModelList.model_validate(payload)

        self.assertEqual("10", model.from_token)
        self.assertEqual(50, model.max_items_count)
        self.assertEqual("20", model.next_token)
        self.assertEqual(1, len(model.items))

        dumped = model.model_dump()
        self.assertIn("fromToken", dumped)
        self.assertIn("maxItemsCount", dumped)
        self.assertIn("nextToken", dumped)
        self.assertNotIn("from_token", dumped)


if __name__ == "__main__":
    unittest.main()
