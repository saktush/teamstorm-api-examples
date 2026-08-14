import unittest
from uuid import uuid4

from pydantic import ValidationError

from teamstorm.models.attachments import AttachmentModel, AttachmentModelList
from teamstorm.models.enums import AntivirusScanVerdict


def _user_payload() -> dict:
    return {
        "id": str(uuid4()),
        "displayName": "Ada Lovelace",
        "username": "ada",
        "email": "ada@example.com",
    }


def _attachment_payload(**overrides) -> dict:
    payload = {
        "attachmentId": str(uuid4()),
        "workspaceId": str(uuid4()),
        "createdBy": _user_payload(),
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


class AttachmentModelTestCase(unittest.TestCase):
    def test_round_trips_realistic_payload(self) -> None:
        payload = _attachment_payload()

        model = AttachmentModel.model_validate(payload)

        self.assertEqual(payload["attachmentId"], str(model.attachment_id))
        self.assertEqual(payload["workspaceId"], str(model.workspace_id))
        self.assertEqual("Ada Lovelace", model.created_by.display_name)
        self.assertEqual(payload["fileId"], model.file_id)
        self.assertEqual("report.pdf", model.name)
        self.assertEqual(1, model.version)
        self.assertEqual("pdf", model.type)
        self.assertEqual(1024, model.size)
        self.assertEqual(AntivirusScanVerdict.NotDetected, model.antivirus_verdict)

        dumped = model.model_dump()
        self.assertEqual(payload["attachmentId"], dumped["attachmentId"])
        self.assertEqual("NotDetected", dumped["antivirusVerdict"])

    def test_every_antivirus_scan_verdict_round_trips(self) -> None:
        for verdict in AntivirusScanVerdict:
            with self.subTest(verdict=verdict):
                model = AttachmentModel.model_validate(_attachment_payload(antivirusVerdict=verdict.value))
                self.assertEqual(verdict, model.antivirus_verdict)

    def test_extra_field_is_rejected(self) -> None:
        payload = _attachment_payload()
        payload["unexpectedField"] = "boom"
        with self.assertRaises(ValidationError):
            AttachmentModel.model_validate(payload)

    def test_missing_required_field_rejected(self) -> None:
        payload = _attachment_payload()
        del payload["antivirusVerdict"]
        with self.assertRaises(ValidationError):
            AttachmentModel.model_validate(payload)


class AttachmentModelListTestCase(unittest.TestCase):
    def test_round_trips_bare_items_envelope(self) -> None:
        payload = {"items": [_attachment_payload(), _attachment_payload(version=2)]}

        model = AttachmentModelList.model_validate(payload)

        self.assertEqual(2, len(model.items))
        self.assertEqual(1, model.items[0].version)
        self.assertEqual(2, model.items[1].version)

    def test_extra_field_is_rejected(self) -> None:
        payload = {"items": [], "unexpectedField": "boom"}
        with self.assertRaises(ValidationError):
            AttachmentModelList.model_validate(payload)


if __name__ == "__main__":
    unittest.main()
