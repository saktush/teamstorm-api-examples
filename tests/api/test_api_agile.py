import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from pydantic import ValidationError

from teamstorm.api.agile import AgileAPI
from teamstorm.models.agile import CreateAgileRequestBody


def _agile_payload(**overrides) -> dict:
    payload = {
        "id": str(uuid4()),
        "name": "Agile board",
        "folderId": str(uuid4()),
        "estimatesType": "EstimatesInTime",
    }
    payload.update(overrides)
    return payload


class AgileAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = AgileAPI(self.client)
        self.workspace = "WS"
        self.agile_id = uuid4()
        self.folder_id = uuid4()

    def test_list_uses_get_all_with_folder_filter_and_parses(self) -> None:
        self.client.get_all.return_value = [_agile_payload()]

        result = self.api.list(self.workspace, folder_id=self.folder_id)

        self.client.get_all.assert_called_once_with(
            "/workspaces/WS/agile/list",
            params={"folderId": str(self.folder_id)},
        )
        self.assertEqual(1, len(result))
        self.assertEqual("Agile board", result[0].name)

    def test_create(self) -> None:
        payload = _agile_payload()
        self.client.post.return_value = payload

        body = CreateAgileRequestBody(folder_id=self.folder_id, estimates_type="EstimatesInTime")
        created = self.api.create(self.workspace, body=body)

        self.assertEqual("Agile board", created.name)
        self.client.post.assert_called_once_with(
            "/workspaces/WS/agile",
            body={"folderId": str(self.folder_id), "estimatesType": "EstimatesInTime"},
        )

    def test_create_simple(self) -> None:
        payload = _agile_payload()
        self.client.post.return_value = payload

        created = self.api.create_simple(self.workspace, folder_id=self.folder_id)

        self.assertEqual("Agile board", created.name)
        self.client.post.assert_called_once_with(
            "/workspaces/WS/agile",
            body={"folderId": str(self.folder_id), "estimatesType": "EstimatesInTime"},
        )

    def test_get(self) -> None:
        payload = _agile_payload()
        self.client.get.return_value = payload

        got = self.api.get(self.workspace, agile_id=self.agile_id)

        self.client.get.assert_called_once_with(f"/workspaces/{self.workspace}/agile/{self.agile_id}")
        self.assertEqual("Agile board", got.name)

    def test_delete(self) -> None:
        self.client.delete.return_value = None

        deleted = self.api.delete(self.workspace, agile_id=self.agile_id)

        self.assertIsNone(deleted)
        self.client.delete.assert_called_once_with(f"/workspaces/{self.workspace}/agile/{self.agile_id}")

    def test_validation_error_on_bad_payload(self) -> None:
        self.client.get.return_value = {"id": str(uuid4())}
        with self.assertRaises(ValidationError):
            self.api.get(self.workspace, agile_id=self.agile_id)


if __name__ == "__main__":
    unittest.main()
