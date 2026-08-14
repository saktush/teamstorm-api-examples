import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from pydantic import ValidationError

from teamstorm.api.folders import FoldersAPI
from teamstorm.models.folders import CreateFolderRequestBody, PatchFolderRequestBody


def _folder_payload(**overrides) -> dict:
    payload = {
        "id": str(uuid4()),
        "name": "Backlog",
        "description": "Top-level backlog folder",
        "parentId": str(uuid4()),
    }
    payload.update(overrides)
    return payload


class FoldersAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = FoldersAPI(self.client)
        self.workspace = "WS"
        self.folder_id = uuid4()
        self.parent_id = uuid4()

    def test_list_uses_get_all_with_filters_and_parses(self) -> None:
        self.client.get_all.return_value = [_folder_payload()]

        result = self.api.list(self.workspace, name="Backlog", parent_id=self.parent_id)

        self.client.get_all.assert_called_once_with(
            "/workspaces/WS/folders",
            params={"name": "Backlog", "parentId": str(self.parent_id)},
        )
        self.assertEqual(1, len(result))
        self.assertEqual("Backlog", result[0].name)

    def test_create_serializes_with_mode_json(self) -> None:
        payload = _folder_payload(parentId=str(self.parent_id))
        self.client.post.return_value = payload

        body = CreateFolderRequestBody(name="Backlog", parent_id=self.parent_id)
        created = self.api.create(self.workspace, body)

        self.assertEqual("Backlog", created.name)
        # exact verb + path + body, with mode="json" turning parent_id (a UUID)
        # into a plain str in the dumped payload.
        self.client.post.assert_called_once_with(
            "/workspaces/WS/folders",
            body={"name": "Backlog", "parentId": str(self.parent_id)},
        )

    def test_get(self) -> None:
        payload = _folder_payload()
        self.client.get.return_value = payload

        got = self.api.get(self.workspace, folder_id=self.folder_id)

        self.client.get.assert_called_once_with(f"/workspaces/{self.workspace}/folders/{self.folder_id}")
        self.assertEqual("Backlog", got.name)

    def test_patch_uses_exclude_unset_and_keeps_explicit_null(self) -> None:
        payload = _folder_payload(name="Renamed")
        self.client.patch.return_value = payload

        # name is set to a real value, description is explicitly cleared
        # (None), parentId is never touched at all.
        body = PatchFolderRequestBody(name="Renamed", description=None)
        patched = self.api.patch(self.workspace, folder_id=self.folder_id, body=body)

        self.assertEqual("Renamed", patched.name)
        self.client.patch.assert_called_once_with(
            f"/workspaces/{self.workspace}/folders/{self.folder_id}",
            {"name": "Renamed", "description": None},
        )

    def test_patch_omits_fields_never_set(self) -> None:
        payload = _folder_payload(name="Renamed")
        self.client.patch.return_value = payload

        body = PatchFolderRequestBody(name="Renamed")
        self.api.patch(self.workspace, folder_id=self.folder_id, body=body)

        # description/parentId were never assigned -> must be entirely absent,
        # not merely null, so the server treats them as "leave unchanged".
        self.client.patch.assert_called_once_with(
            f"/workspaces/{self.workspace}/folders/{self.folder_id}",
            {"name": "Renamed"},
        )

    def test_delete(self) -> None:
        self.client.delete.return_value = None

        deleted = self.api.delete(self.workspace, folder_id=self.folder_id)

        self.assertIsNone(deleted)
        self.client.delete.assert_called_once_with(f"/workspaces/{self.workspace}/folders/{self.folder_id}")

    def test_validation_error_on_bad_payload(self) -> None:
        self.client.get.return_value = {"id": str(uuid4())}
        with self.assertRaises(ValidationError):
            self.api.get(self.workspace, folder_id=self.folder_id)


if __name__ == "__main__":
    unittest.main()
