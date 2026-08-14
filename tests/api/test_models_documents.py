import unittest
from uuid import uuid4

from pydantic import ValidationError

from teamstorm.models.documents import (
    CreateDocumentRequestBody,
    CreateDocumentWorkitemLinkRequestBody,
    DeleteDocumentWorkitemLinkRequestBody,
    DocumentModel,
    DocumentsModelList,
    DocumentsStatusModelList,
    DocumentStatusModel,
    DocumentVersionModel,
    DocumentVersionsModelList,
    PatchDocumentRequestBody,
)


def _user_payload() -> dict:
    return {
        "id": str(uuid4()),
        "displayName": "Jane Doe",
        "username": "jane",
        "email": "jane@example.com",
    }


def _status_payload() -> dict:
    return {"id": str(uuid4()), "name": "Draft"}


def _document_payload(**overrides) -> dict:
    payload = {
        "workspaceId": str(uuid4()),
        "id": str(uuid4()),
        "key": "DOC-1",
        "name": "Spec",
        "documentUrl": "https://example.test/docs/DOC-1",
        "content": "<p>Hello</p>",
        "createdAt": "2026-01-01T10:00:00Z",
        "author": _user_payload(),
        "updatedAt": "2026-01-02T11:00:00Z",
        "updatedBy": None,
        "parent": {"id": str(uuid4()), "nodeType": "Folder"},
        "version": 3,
        "versionUrl": "https://example.test/docs/DOC-1/versions/3",
        "labels": ["important"],
        "isBlocked": False,
        "status": _status_payload(),
    }
    payload.update(overrides)
    return payload


class DocumentModelTestCase(unittest.TestCase):
    def test_round_trips_realistic_payload(self) -> None:
        payload = _document_payload()

        doc = DocumentModel.model_validate(payload)

        self.assertEqual("Spec", doc.name)
        self.assertEqual("DOC-1", doc.key)
        self.assertEqual("<p>Hello</p>", doc.content)
        self.assertEqual("Jane Doe", doc.author.display_name)
        self.assertIsNone(doc.updated_by)
        self.assertEqual("Folder", doc.parent.node_type)
        self.assertEqual(3, doc.version)
        self.assertEqual(["important"], doc.labels)
        self.assertFalse(doc.is_blocked)
        self.assertEqual("Draft", doc.status.name)

    def test_nullable_fields_accept_none(self) -> None:
        payload = _document_payload(content=None, updatedBy=None, status=None)

        doc = DocumentModel.model_validate(payload)

        self.assertIsNone(doc.content)
        self.assertIsNone(doc.updated_by)
        self.assertIsNone(doc.status)

    def test_extra_fields_rejected(self) -> None:
        payload = _document_payload()
        payload["unexpectedField"] = "boom"
        with self.assertRaises(ValidationError):
            DocumentModel.model_validate(payload)

    def test_missing_required_field_rejected(self) -> None:
        payload = _document_payload()
        del payload["isBlocked"]
        with self.assertRaises(ValidationError):
            DocumentModel.model_validate(payload)


class DocumentsModelListTestCase(unittest.TestCase):
    def test_round_trips_paginated_envelope(self) -> None:
        payload = {
            "fromToken": None,
            "maxItemsCount": 50,
            "nextToken": "next-page",
            "items": [_document_payload()],
        }

        parsed = DocumentsModelList.model_validate(payload)

        self.assertEqual(1, len(parsed.items))
        self.assertEqual("next-page", parsed.next_token)


class DocumentVersionModelTestCase(unittest.TestCase):
    def test_round_trips_realistic_payload(self) -> None:
        payload = {
            "versionNumber": 2,
            "author": _user_payload(),
            "createdDate": "2026-01-01T10:00:00Z",
            "status": _status_payload(),
        }

        version = DocumentVersionModel.model_validate(payload)

        self.assertEqual(2, version.version_number)
        self.assertEqual("jane", version.author.username)
        self.assertEqual("Draft", version.status.name)

    def test_status_nullable(self) -> None:
        payload = {
            "versionNumber": 1,
            "author": _user_payload(),
            "createdDate": "2026-01-01T10:00:00Z",
            "status": None,
        }

        version = DocumentVersionModel.model_validate(payload)

        self.assertIsNone(version.status)


class DocumentVersionsModelListTestCase(unittest.TestCase):
    def test_round_trips_paginated_envelope(self) -> None:
        payload = {
            "fromToken": None,
            "maxItemsCount": 50,
            "nextToken": None,
            "items": [
                {
                    "versionNumber": 1,
                    "author": _user_payload(),
                    "createdDate": "2026-01-01T10:00:00Z",
                    "status": None,
                }
            ],
        }

        parsed = DocumentVersionsModelList.model_validate(payload)

        self.assertEqual(1, len(parsed.items))
        self.assertIsNone(parsed.next_token)


class DocumentStatusModelTestCase(unittest.TestCase):
    def test_round_trips_realistic_payload(self) -> None:
        payload = _status_payload()

        status = DocumentStatusModel.model_validate(payload)

        self.assertEqual("Draft", status.name)

    def test_extra_fields_rejected(self) -> None:
        payload = _status_payload()
        payload["category"] = {"id": str(uuid4()), "name": "boom"}
        with self.assertRaises(ValidationError):
            DocumentStatusModel.model_validate(payload)


class DocumentsStatusModelListTestCase(unittest.TestCase):
    def test_round_trips_bare_items_envelope(self) -> None:
        payload = {"items": [_status_payload(), _status_payload()]}

        parsed = DocumentsStatusModelList.model_validate(payload)

        self.assertEqual(2, len(parsed.items))

    def test_has_no_pagination_fields(self) -> None:
        # Unlike DocumentsModelList/DocumentVersionsModelList, this envelope
        # has no fromToken/maxItemsCount/nextToken -- extra="forbid" would
        # reject them if the server ever sent one unexpectedly.
        payload = {"items": [_status_payload()], "nextToken": "should-not-exist"}
        with self.assertRaises(ValidationError):
            DocumentsStatusModelList.model_validate(payload)


class CreateDocumentRequestBodyTestCase(unittest.TestCase):
    def test_requires_parent_id(self) -> None:
        with self.assertRaises(ValidationError):
            CreateDocumentRequestBody(name="Spec", content="Hello", labels=[])

    def test_serializes_with_parent_id(self) -> None:
        parent_id = uuid4()
        body = CreateDocumentRequestBody(
            name="Spec",
            content="Hello",
            parent_id=parent_id,
            labels=["important"],
        )

        dumped = body.model_dump(mode="json", exclude_none=True)

        self.assertEqual(
            {
                "name": "Spec",
                "content": "Hello",
                "parentId": str(parent_id),
                "labels": ["important"],
            },
            dumped,
        )


class PatchDocumentRequestBodyTestCase(unittest.TestCase):
    def test_unset_status_is_excluded_from_dump(self) -> None:
        body = PatchDocumentRequestBody()

        dumped = body.model_dump(mode="json", exclude_unset=True, exclude_none=False)

        self.assertEqual({}, dumped)

    def test_explicit_none_status_is_serialized_as_null(self) -> None:
        body = PatchDocumentRequestBody(status=None)

        dumped = body.model_dump(mode="json", exclude_unset=True, exclude_none=False)

        self.assertEqual({"status": None}, dumped)

    def test_set_status_is_serialized(self) -> None:
        body = PatchDocumentRequestBody(status="Approved")

        dumped = body.model_dump(mode="json", exclude_unset=True, exclude_none=False)

        self.assertEqual({"status": "Approved"}, dumped)


class CreateDocumentWorkitemLinkRequestBodyTestCase(unittest.TestCase):
    def test_serializes_required_fields(self) -> None:
        body = CreateDocumentWorkitemLinkRequestBody(workitem="WI-1", workitem_workspace="WS2")

        dumped = body.model_dump(mode="json", exclude_none=True)

        self.assertEqual({"workitem": "WI-1", "workitemWorkspace": "WS2"}, dumped)

    def test_requires_both_fields(self) -> None:
        with self.assertRaises(ValidationError):
            CreateDocumentWorkitemLinkRequestBody(workitem="WI-1")
        with self.assertRaises(ValidationError):
            CreateDocumentWorkitemLinkRequestBody(workitem_workspace="WS2")

    def test_extra_fields_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            CreateDocumentWorkitemLinkRequestBody(
                workitem="WI-1",
                workitem_workspace="WS2",
                type="RelatesTo",
            )


class DeleteDocumentWorkitemLinkRequestBodyTestCase(unittest.TestCase):
    def test_serializes_required_fields(self) -> None:
        body = DeleteDocumentWorkitemLinkRequestBody(workitem="WI-1", workitem_workspace="WS2")

        dumped = body.model_dump(mode="json", exclude_none=True)

        self.assertEqual({"workitem": "WI-1", "workitemWorkspace": "WS2"}, dumped)

    def test_requires_both_fields(self) -> None:
        with self.assertRaises(ValidationError):
            DeleteDocumentWorkitemLinkRequestBody(workitem="WI-1")
        with self.assertRaises(ValidationError):
            DeleteDocumentWorkitemLinkRequestBody(workitem_workspace="WS2")


if __name__ == "__main__":
    unittest.main()
