import unittest
from datetime import datetime
from unittest.mock import MagicMock
from uuid import uuid4

from pydantic import ValidationError

from teamstorm.api.time_tracking import TimeTrackingAPI


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


def _entry_payload(**overrides) -> dict:
    payload = {
        "id": str(uuid4()),
        "date": "2026-07-01T00:00:00Z",
        "spentTime": 3600,
        "description": "Worked on ticket",
        "createdAt": "2026-07-01T08:00:00Z",
        "updatedAt": "2026-07-01T08:00:00Z",
        "deletedAt": None,
        "deleteUserId": None,
        "deleteUser": None,
        "author": {
            "id": str(uuid4()),
            "displayName": "Ada Lovelace",
            "username": "ada",
            "email": "ada@example.com",
        },
        "workitem": _workitem_payload(),
        "type": {"id": str(uuid4()), "name": "Development"},
    }
    payload.update(overrides)
    return payload


class TimeTrackingAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = TimeTrackingAPI(self.client)

    def test_list_has_no_workspace_segment(self) -> None:
        self.client.get_all.return_value = [_entry_payload()]

        result = self.api.list(start_date="2026-07-01T00:00:00Z")

        self.client.get_all.assert_called_once_with(
            "/workspaces/time-tracking-entries",
            params={"startDate": "2026-07-01T00:00:00Z"},
        )
        self.assertEqual(1, len(result))
        self.assertEqual(3600, result[0].spent_time)

    def test_list_maps_all_optional_filters_and_pagination(self) -> None:
        self.client.get_all.return_value = [_entry_payload()]

        result = self.api.list(
            start_date="2026-07-01T00:00:00Z",
            end_date="2026-07-29T00:00:00Z",
            users="ada,bob",
            from_token="tok-1",
            max_items_count=100,
        )

        self.client.get_all.assert_called_once_with(
            "/workspaces/time-tracking-entries",
            params={
                "startDate": "2026-07-01T00:00:00Z",
                "endDate": "2026-07-29T00:00:00Z",
                "users": "ada,bob",
                "fromToken": "tok-1",
                "maxItemsCount": 100,
            },
        )
        self.assertEqual(1, len(result))

    def test_list_converts_datetime_objects_to_isoformat(self) -> None:
        self.client.get_all.return_value = []
        start = datetime(2026, 7, 1)
        end = datetime(2026, 7, 29)

        self.api.list(start_date=start, end_date=end)

        self.client.get_all.assert_called_once_with(
            "/workspaces/time-tracking-entries",
            params={"startDate": start.isoformat(), "endDate": end.isoformat()},
        )

    def test_list_updates_has_no_workspace_segment_and_maps_with_deleted(self) -> None:
        deleted_entry = _entry_payload(
            deletedAt="2026-07-15T00:00:00Z",
            deleteUserId=str(uuid4()),
            deleteUser={
                "id": str(uuid4()),
                "displayName": "Grace Hopper",
                "username": "grace",
                "email": "grace@example.com",
            },
        )
        self.client.get_all.return_value = [deleted_entry]

        result = self.api.list_updates(
            start_date="2026-07-01T00:00:00Z",
            end_date="2026-07-29T00:00:00Z",
            users="ada",
            with_deleted=True,
            from_token="tok-2",
            max_items_count=200,
        )

        self.client.get_all.assert_called_once_with(
            "/workspaces/time-tracking-entries/updates",
            params={
                "startDate": "2026-07-01T00:00:00Z",
                "endDate": "2026-07-29T00:00:00Z",
                "users": "ada",
                "withDeleted": True,
                "fromToken": "tok-2",
                "maxItemsCount": 200,
            },
        )
        self.assertEqual(1, len(result))
        self.assertIsNotNone(result[0].deleted_at)
        self.assertEqual("grace", result[0].delete_user.username)

    def test_list_updates_with_only_required_param(self) -> None:
        self.client.get_all.return_value = []

        self.api.list_updates(start_date="2026-07-01T00:00:00Z")

        self.client.get_all.assert_called_once_with(
            "/workspaces/time-tracking-entries/updates",
            params={"startDate": "2026-07-01T00:00:00Z"},
        )

    def test_validation_error_on_bad_payload(self) -> None:
        self.client.get_all.return_value = [{"id": str(uuid4())}]
        with self.assertRaises(ValidationError):
            self.api.list(start_date="2026-07-01T00:00:00Z")


if __name__ == "__main__":
    unittest.main()
