import unittest
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

from pydantic import ValidationError

from teamstorm.api.attachments import DocumentAttachmentsAPI, WorkitemAttachmentsAPI


def _attachment_payload(**overrides) -> dict:
    payload = {
        "attachmentId": str(uuid4()),
        "workspaceId": str(uuid4()),
        "createdBy": {
            "id": str(uuid4()),
            "displayName": "Ada Lovelace",
            "username": "ada",
            "email": "ada@example.com",
        },
        "fileId": str(uuid4()),
        "name": "report.pdf",
        "version": 1,
        "type": "pdf",
        "size": 1024,
        "createdAt": "2026-01-15T12:00:00Z",
        "antivirusVerdict": "NotDetected",
    }
    payload.update(overrides)
    return payload


class WorkitemAttachmentsAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = WorkitemAttachmentsAPI(self.client)
        self.workspace = "WS"
        self.workitem_id = uuid4()
        self.attachment_id = uuid4()

    def test_list_uses_get_not_get_all_and_parses(self) -> None:
        self.client.get.return_value = {"items": [_attachment_payload()]}

        result = self.api.list(self.workspace, workitem_id=self.workitem_id)

        self.client.get.assert_called_once_with(
            f"/workspaces/{self.workspace}/workitems/{self.workitem_id}/attachments"
        )
        self.client.get_all.assert_not_called()
        self.assertEqual(1, len(result))
        self.assertEqual("report.pdf", result[0].name)

    def test_get(self) -> None:
        self.client.get.return_value = _attachment_payload(attachmentId=str(self.attachment_id))

        result = self.api.get(self.workspace, workitem_id=self.workitem_id, attachment_id=self.attachment_id)

        self.client.get.assert_called_once_with(
            f"/workspaces/{self.workspace}/workitems/{self.workitem_id}/attachments/{self.attachment_id}"
        )
        self.assertEqual(self.attachment_id, result.attachment_id)

    def test_download_returns_bytes_via_get_bytes(self) -> None:
        self.client.get_bytes.return_value = b"\x89PNG raw file bytes"

        result = self.api.download(self.workspace, workitem_id=self.workitem_id, attachment_id=self.attachment_id)

        self.client.get_bytes.assert_called_once_with(
            f"/workspaces/{self.workspace}/workitems/{self.workitem_id}" f"/attachments/{self.attachment_id}/download"
        )
        self.assertIsInstance(result, bytes)
        self.assertEqual(b"\x89PNG raw file bytes", result)

    def test_list_versions_uses_get_not_get_all(self) -> None:
        self.client.get.return_value = {"items": [_attachment_payload(version=1), _attachment_payload(version=2)]}

        result = self.api.list_versions(self.workspace, workitem_id=self.workitem_id)

        self.client.get.assert_called_once_with(
            f"/workspaces/{self.workspace}/workitems/{self.workitem_id}/attachments/versions"
        )
        self.client.get_all.assert_not_called()
        self.assertEqual(2, len(result))

    def test_get_version(self) -> None:
        self.client.get.return_value = _attachment_payload(attachmentId=str(self.attachment_id), version=3)

        result = self.api.get_version(
            self.workspace,
            workitem_id=self.workitem_id,
            attachment_id=self.attachment_id,
            version=3,
        )

        self.client.get.assert_called_once_with(
            f"/workspaces/{self.workspace}/workitems/{self.workitem_id}" f"/attachments/{self.attachment_id}/versions/3"
        )
        self.assertEqual(3, result.version)

    def test_upload_generates_attachment_id_when_not_supplied(self) -> None:
        self.client.post_multipart.return_value = None
        generated = uuid4()

        with patch("teamstorm.api.attachments.uuid4", return_value=generated) as mock_uuid4:
            result = self.api.upload(
                self.workspace,
                workitem_id=self.workitem_id,
                file_name="report.pdf",
                content=b"file bytes",
            )

        mock_uuid4.assert_called_once()
        self.assertEqual(generated, result)
        self.assertIsInstance(result, UUID)
        self.client.post_multipart.assert_called_once_with(
            f"/workspaces/{self.workspace}/workitems/{self.workitem_id}/attachments/{generated}/upload",
            file_name="report.pdf",
            content=b"file bytes",
            content_type=None,
            field_name="file",
        )

    def test_upload_uses_supplied_attachment_id_and_does_not_generate_one(self) -> None:
        self.client.post_multipart.return_value = None

        with patch("teamstorm.api.attachments.uuid4") as mock_uuid4:
            result = self.api.upload(
                self.workspace,
                workitem_id=self.workitem_id,
                file_name="report.pdf",
                content=b"file bytes",
                content_type="application/pdf",
                attachment_id=self.attachment_id,
            )

        mock_uuid4.assert_not_called()
        self.assertEqual(self.attachment_id, result)
        self.client.post_multipart.assert_called_once_with(
            f"/workspaces/{self.workspace}/workitems/{self.workitem_id}" f"/attachments/{self.attachment_id}/upload",
            file_name="report.pdf",
            content=b"file bytes",
            content_type="application/pdf",
            field_name="file",
        )

    def test_upload_two_calls_without_attachment_id_generate_different_ids(self) -> None:
        self.client.post_multipart.return_value = None

        first = self.api.upload(self.workspace, workitem_id=self.workitem_id, file_name="a.txt", content=b"a")
        second = self.api.upload(self.workspace, workitem_id=self.workitem_id, file_name="b.txt", content=b"b")

        self.assertIsInstance(first, UUID)
        self.assertIsInstance(second, UUID)
        self.assertNotEqual(first, second)

    def test_delete_all(self) -> None:
        self.client.delete.return_value = None

        result = self.api.delete_all(self.workspace, workitem_id=self.workitem_id)

        self.assertIsNone(result)
        self.client.delete.assert_called_once_with(
            f"/workspaces/{self.workspace}/workitems/{self.workitem_id}/attachments"
        )

    def test_delete_one(self) -> None:
        self.client.delete.return_value = None

        result = self.api.delete(self.workspace, workitem_id=self.workitem_id, attachment_id=self.attachment_id)

        self.assertIsNone(result)
        self.client.delete.assert_called_once_with(
            f"/workspaces/{self.workspace}/workitems/{self.workitem_id}/attachments/{self.attachment_id}"
        )

    def test_delete_version(self) -> None:
        self.client.delete.return_value = None

        result = self.api.delete_version(
            self.workspace,
            workitem_id=self.workitem_id,
            attachment_id=self.attachment_id,
            version=2,
        )

        self.assertIsNone(result)
        self.client.delete.assert_called_once_with(
            f"/workspaces/{self.workspace}/workitems/{self.workitem_id}" f"/attachments/{self.attachment_id}/versions/2"
        )

    def test_validation_error_on_bad_payload(self) -> None:
        self.client.get.return_value = {"attachmentId": str(uuid4())}  # missing required fields
        with self.assertRaises(ValidationError):
            self.api.get(self.workspace, workitem_id=self.workitem_id, attachment_id=self.attachment_id)


class DocumentAttachmentsAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = DocumentAttachmentsAPI(self.client)
        self.workspace = "WS"
        self.document_id = uuid4()
        self.attachment_id = uuid4()

    def test_list_uses_get_not_get_all_and_parses(self) -> None:
        self.client.get.return_value = {"items": [_attachment_payload()]}

        result = self.api.list(self.workspace, document_id=self.document_id)

        self.client.get.assert_called_once_with(
            f"/workspaces/{self.workspace}/documents/{self.document_id}/attachments"
        )
        self.client.get_all.assert_not_called()
        self.assertEqual(1, len(result))

    def test_get(self) -> None:
        self.client.get.return_value = _attachment_payload(attachmentId=str(self.attachment_id))

        result = self.api.get(self.workspace, document_id=self.document_id, attachment_id=self.attachment_id)

        self.client.get.assert_called_once_with(
            f"/workspaces/{self.workspace}/documents/{self.document_id}/attachments/{self.attachment_id}"
        )
        self.assertEqual(self.attachment_id, result.attachment_id)

    def test_download_returns_bytes_via_get_bytes(self) -> None:
        self.client.get_bytes.return_value = b"raw document bytes"

        result = self.api.download(self.workspace, document_id=self.document_id, attachment_id=self.attachment_id)

        self.client.get_bytes.assert_called_once_with(
            f"/workspaces/{self.workspace}/documents/{self.document_id}" f"/attachments/{self.attachment_id}/download"
        )
        self.assertIsInstance(result, bytes)
        self.assertEqual(b"raw document bytes", result)

    def test_list_versions_uses_get_not_get_all(self) -> None:
        self.client.get.return_value = {"items": [_attachment_payload()]}

        result = self.api.list_versions(self.workspace, document_id=self.document_id)

        self.client.get.assert_called_once_with(
            f"/workspaces/{self.workspace}/documents/{self.document_id}/attachments/versions"
        )
        self.client.get_all.assert_not_called()
        self.assertEqual(1, len(result))

    def test_get_version(self) -> None:
        self.client.get.return_value = _attachment_payload(attachmentId=str(self.attachment_id), version=5)

        result = self.api.get_version(
            self.workspace,
            document_id=self.document_id,
            attachment_id=self.attachment_id,
            version=5,
        )

        self.client.get.assert_called_once_with(
            f"/workspaces/{self.workspace}/documents/{self.document_id}" f"/attachments/{self.attachment_id}/versions/5"
        )
        self.assertEqual(5, result.version)

    def test_upload_generates_attachment_id_when_not_supplied(self) -> None:
        self.client.post_multipart.return_value = None
        generated = uuid4()

        with patch("teamstorm.api.attachments.uuid4", return_value=generated) as mock_uuid4:
            result = self.api.upload(
                self.workspace,
                document_id=self.document_id,
                file_name="spec.docx",
                content=b"doc bytes",
            )

        mock_uuid4.assert_called_once()
        self.assertEqual(generated, result)
        self.client.post_multipart.assert_called_once_with(
            f"/workspaces/{self.workspace}/documents/{self.document_id}/attachments/{generated}/upload",
            file_name="spec.docx",
            content=b"doc bytes",
            content_type=None,
            field_name="file",
        )

    def test_upload_uses_supplied_attachment_id(self) -> None:
        self.client.post_multipart.return_value = None

        with patch("teamstorm.api.attachments.uuid4") as mock_uuid4:
            result = self.api.upload(
                self.workspace,
                document_id=self.document_id,
                file_name="spec.docx",
                content=b"doc bytes",
                attachment_id=self.attachment_id,
            )

        mock_uuid4.assert_not_called()
        self.assertEqual(self.attachment_id, result)
        self.client.post_multipart.assert_called_once_with(
            f"/workspaces/{self.workspace}/documents/{self.document_id}" f"/attachments/{self.attachment_id}/upload",
            file_name="spec.docx",
            content=b"doc bytes",
            content_type=None,
            field_name="file",
        )

    def test_delete_all(self) -> None:
        self.client.delete.return_value = None

        result = self.api.delete_all(self.workspace, document_id=self.document_id)

        self.assertIsNone(result)
        self.client.delete.assert_called_once_with(
            f"/workspaces/{self.workspace}/documents/{self.document_id}/attachments"
        )

    def test_delete_one(self) -> None:
        self.client.delete.return_value = None

        result = self.api.delete(self.workspace, document_id=self.document_id, attachment_id=self.attachment_id)

        self.assertIsNone(result)
        self.client.delete.assert_called_once_with(
            f"/workspaces/{self.workspace}/documents/{self.document_id}/attachments/{self.attachment_id}"
        )

    def test_delete_version(self) -> None:
        self.client.delete.return_value = None

        result = self.api.delete_version(
            self.workspace,
            document_id=self.document_id,
            attachment_id=self.attachment_id,
            version=4,
        )

        self.assertIsNone(result)
        self.client.delete.assert_called_once_with(
            f"/workspaces/{self.workspace}/documents/{self.document_id}" f"/attachments/{self.attachment_id}/versions/4"
        )

    def test_validation_error_on_bad_payload(self) -> None:
        self.client.get.return_value = {"attachmentId": str(uuid4())}  # missing required fields
        with self.assertRaises(ValidationError):
            self.api.get(self.workspace, document_id=self.document_id, attachment_id=self.attachment_id)


if __name__ == "__main__":
    unittest.main()
