import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

from pydantic import ValidationError

from teamstorm.api.workitems import WorkitemsAPI
from teamstorm.models.workitems import PatchWorkitemRequestBody


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


class WorkitemsAPIGetDeleteTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = WorkitemsAPI(self.client)
        self.workspace = "WS"
        self.workitem_id = uuid4()

    def test_get_returns_workitem_model(self) -> None:
        self.client.get.return_value = _workitem_payload()

        result = self.api.get(self.workspace, workitem_id=self.workitem_id)

        self.client.get.assert_called_once_with(f"/workspaces/{self.workspace}/workitems/{self.workitem_id}")
        self.assertEqual("WS-1", result.key)

    def test_get_accepts_human_readable_key_instead_of_uuid(self) -> None:
        # The server resolves human-readable keys like "WS-42" for the
        # {workitem} path segment (docs/api-analysis/upstream-semantics.md
        # §9) -- workitem_id is typed UUIDStr precisely so callers aren't
        # forced to have a UUID in hand.
        self.client.get.return_value = _workitem_payload()

        result = self.api.get(self.workspace, workitem_id="WS-42")

        self.client.get.assert_called_once_with(f"/workspaces/{self.workspace}/workitems/WS-42")
        self.assertEqual("WS-1", result.key)

    def test_get_validation_error_on_bad_payload(self) -> None:
        self.client.get.return_value = {"id": str(uuid4())}
        with self.assertRaises(ValidationError):
            self.api.get(self.workspace, workitem_id=self.workitem_id)

    def test_delete_returns_none_and_calls_correct_path(self) -> None:
        self.client.delete.return_value = None

        result = self.api.delete(self.workspace, workitem_id=self.workitem_id)

        self.assertIsNone(result)
        self.client.delete.assert_called_once_with(f"/workspaces/{self.workspace}/workitems/{self.workitem_id}")

    def test_delete_docstring_documents_cascading_hard_delete(self) -> None:
        doc = self.api.delete.__doc__ or ""
        self.assertIn("cascad", doc.lower())
        self.assertIn("hard delete", doc.lower())

    def test_patch_uses_exclude_unset_and_keeps_explicit_null(self) -> None:
        payload = _workitem_payload()
        self.client.patch.return_value = payload

        # name is set to a real value, assignee is explicitly cleared
        # (None), every other field is never touched at all.
        body = PatchWorkitemRequestBody(name="Task renamed", assignee=None)
        self.api.patch(self.workspace, workitem_id=self.workitem_id, body=body)

        self.client.patch.assert_called_once_with(
            f"/workspaces/{self.workspace}/workitems/{self.workitem_id}",
            {"name": "Task renamed", "assignee": None},
        )

    def test_patch_omits_fields_never_set(self) -> None:
        payload = _workitem_payload()
        self.client.patch.return_value = payload

        body = PatchWorkitemRequestBody(name="Task renamed")
        self.api.patch(self.workspace, workitem_id=self.workitem_id, body=body)

        # assignee/status/dates/etc were never assigned -> must be entirely
        # absent, not merely null, so the server treats them as "leave
        # unchanged".
        self.client.patch.assert_called_once_with(
            f"/workspaces/{self.workspace}/workitems/{self.workitem_id}",
            {"name": "Task renamed"},
        )


class WorkitemsAPIListByParentTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = WorkitemsAPI(self.client)
        self.workspace = "WS"
        self.parent_id = uuid4()

    def test_list_by_parent_without_sub_items(self) -> None:
        self.client.get_all.return_value = [_workitem_payload()]

        result = self.api.list_by_parent(self.workspace, parent_id=self.parent_id)

        self.client.get_all.assert_called_once_with(
            f"/workspaces/{self.workspace}/workitems/by-parent/{self.parent_id}",
            params=None,
        )
        self.assertEqual(1, len(result))

    def test_list_by_parent_with_sub_items(self) -> None:
        self.client.get_all.return_value = [_workitem_payload()]

        result = self.api.list_by_parent(self.workspace, parent_id=self.parent_id, with_sub_items=True)

        self.client.get_all.assert_called_once_with(
            f"/workspaces/{self.workspace}/workitems/by-parent/{self.parent_id}",
            params={"withSubItems": True},
        )
        self.assertEqual(1, len(result))

    def test_list_by_parent_validation_error_on_bad_payload(self) -> None:
        self.client.get_all.return_value = [{"id": str(uuid4())}]
        with self.assertRaises(ValidationError):
            self.api.list_by_parent(self.workspace, parent_id=self.parent_id)


class WorkitemsAPICountTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = WorkitemsAPI(self.client)
        self.workspace = "WS"

    def test_count_unwraps_count_envelope_and_returns_int(self) -> None:
        self.client.get.return_value = {"count": 42}

        result = self.api.count(self.workspace)

        self.client.get.assert_called_once_with(f"/workspaces/{self.workspace}/workitems/count")
        self.assertEqual(42, result)
        self.assertIsInstance(result, int)


class WorkitemsAPIListUpdatesTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = WorkitemsAPI(self.client)
        self.workspace = "WS"

    def test_list_updates_with_required_param_only(self) -> None:
        self.client.get_all.return_value = [_workitem_payload()]

        result = self.api.list_updates(self.workspace, changed_from_date="2026-07-01T00:00:00Z")

        self.client.get_all.assert_called_once_with(
            f"/workspaces/{self.workspace}/workitems/updates",
            params={"changedFromDate": "2026-07-01T00:00:00Z"},
        )
        self.assertEqual(1, len(result))

    def test_list_updates_with_all_params(self) -> None:
        self.client.get_all.return_value = [_workitem_payload()]

        result = self.api.list_updates(
            self.workspace,
            changed_from_date="2026-07-01T00:00:00Z",
            changed_to_date="2026-07-28T00:00:00Z",
            from_token="tok-1",
            max_items_count=100,
        )

        self.client.get_all.assert_called_once_with(
            f"/workspaces/{self.workspace}/workitems/updates",
            params={
                "changedFromDate": "2026-07-01T00:00:00Z",
                "changedToDate": "2026-07-28T00:00:00Z",
                "fromToken": "tok-1",
                "maxItemsCount": 100,
            },
        )
        self.assertEqual(1, len(result))

    def test_list_updates_accepts_datetime_objects(self) -> None:
        self.client.get_all.return_value = []
        changed_from = datetime(2026, 7, 1, tzinfo=timezone.utc)
        changed_to = datetime(2026, 7, 28, tzinfo=timezone.utc)

        self.api.list_updates(
            self.workspace,
            changed_from_date=changed_from,
            changed_to_date=changed_to,
        )

        self.client.get_all.assert_called_once_with(
            f"/workspaces/{self.workspace}/workitems/updates",
            params={
                "changedFromDate": changed_from.isoformat(),
                "changedToDate": changed_to.isoformat(),
            },
        )

    def test_list_updates_validation_error_on_bad_payload(self) -> None:
        self.client.get_all.return_value = [{"id": str(uuid4())}]
        with self.assertRaises(ValidationError):
            self.api.list_updates(self.workspace, changed_from_date="2026-07-01T00:00:00Z")


if __name__ == "__main__":
    unittest.main()
