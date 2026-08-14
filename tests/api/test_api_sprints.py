import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from pydantic import ValidationError

from teamstorm.api.sprints import SprintsAPI
from teamstorm.models.sprints import CreateSprintRequestBody, PatchSprintRequestBody


def _sprint_payload(**overrides) -> dict:
    payload = {
        "id": str(uuid4()),
        "name": "Sprint 1",
        "description": "First sprint",
        "startDate": "2026-08-01T00:00:00Z",
        "endDate": "2026-08-14T00:00:00Z",
        "state": "New",
        "workdays": 10,
        "isBacklog": False,
        "team": [],
    }
    payload.update(overrides)
    return payload


class SprintsAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = SprintsAPI(self.client)
        self.workspace = "WS"
        self.sprint_id = uuid4()
        self.agile_id = uuid4()
        self.folder_id = uuid4()

    def test_list_uses_get_all_with_filters_and_parses(self) -> None:
        self.client.get_all.return_value = [_sprint_payload()]

        result = self.api.list(self.workspace, folder_id=self.folder_id, name="Sprint 1")

        self.client.get_all.assert_called_once_with(
            "/workspaces/WS/sprints",
            params={"folderId": str(self.folder_id), "name": "Sprint 1"},
        )
        self.assertEqual(1, len(result))
        self.assertEqual("Sprint 1", result[0].name)

    def test_create(self) -> None:
        payload = _sprint_payload()
        self.client.post.return_value = payload

        body = CreateSprintRequestBody(
            agile_id=self.agile_id,
            name="Sprint 1",
            start_date="2026-08-01T00:00:00Z",
            end_date="2026-08-14T00:00:00Z",
            workdays=10,
        )
        created = self.api.create(self.workspace, body)

        self.assertEqual("Sprint 1", created.name)
        self.client.post.assert_called_once_with(
            "/workspaces/WS/sprints",
            {
                "agileId": str(self.agile_id),
                "name": "Sprint 1",
                "startDate": "2026-08-01T00:00:00Z",
                "endDate": "2026-08-14T00:00:00Z",
                "workdays": 10,
            },
        )

    def test_get(self) -> None:
        payload = _sprint_payload()
        self.client.get.return_value = payload

        got = self.api.get(self.workspace, sprint_id=self.sprint_id)

        self.client.get.assert_called_once_with(f"/workspaces/{self.workspace}/sprints/{self.sprint_id}")
        self.assertEqual("Sprint 1", got.name)

    def test_patch(self) -> None:
        payload = _sprint_payload(name="Sprint 1 renamed")
        self.client.patch.return_value = payload

        body = PatchSprintRequestBody(name="Sprint 1 renamed")
        patched = self.api.patch(self.workspace, sprint_id=self.sprint_id, body=body)

        self.assertEqual("Sprint 1 renamed", patched.name)
        self.client.patch.assert_called_once_with(
            f"/workspaces/{self.workspace}/sprints/{self.sprint_id}",
            {"name": "Sprint 1 renamed"},
        )

    def test_patch_uses_exclude_unset_and_keeps_explicit_null(self) -> None:
        payload = _sprint_payload(name="Sprint 1 renamed")
        self.client.patch.return_value = payload

        # name is set to a real value, description is explicitly cleared
        # (None), every other field is never touched at all.
        body = PatchSprintRequestBody(name="Sprint 1 renamed", description=None)
        self.api.patch(self.workspace, sprint_id=self.sprint_id, body=body)

        self.client.patch.assert_called_once_with(
            f"/workspaces/{self.workspace}/sprints/{self.sprint_id}",
            {"name": "Sprint 1 renamed", "description": None},
        )

    def test_patch_omits_fields_never_set(self) -> None:
        payload = _sprint_payload(name="Sprint 1 renamed")
        self.client.patch.return_value = payload

        body = PatchSprintRequestBody(name="Sprint 1 renamed")
        self.api.patch(self.workspace, sprint_id=self.sprint_id, body=body)

        # description/dates/workdays/team were never assigned -> must be
        # entirely absent, not merely null, so the server treats them as
        # "leave unchanged".
        self.client.patch.assert_called_once_with(
            f"/workspaces/{self.workspace}/sprints/{self.sprint_id}",
            {"name": "Sprint 1 renamed"},
        )

    def test_delete(self) -> None:
        self.client.delete.return_value = None

        deleted = self.api.delete(self.workspace, sprint_id=self.sprint_id)

        self.assertIsNone(deleted)
        self.client.delete.assert_called_once_with(f"/workspaces/{self.workspace}/sprints/{self.sprint_id}")

    def test_validation_error_on_bad_payload(self) -> None:
        self.client.get.return_value = {"id": str(uuid4())}
        with self.assertRaises(ValidationError):
            self.api.get(self.workspace, sprint_id=self.sprint_id)


if __name__ == "__main__":
    unittest.main()
