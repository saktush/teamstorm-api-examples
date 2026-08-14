import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from pydantic import ValidationError

from teamstorm.api.documents import (
    DocumentsAPI,
    DocumentStatusesAPI,
    DocumentVersionsAPI,
    DocumentWorkitemLinksAPI,
)
from teamstorm.models.documents import (
    CreateDocumentRequestBody,
    CreateDocumentWorkitemLinkRequestBody,
    DeleteDocumentWorkitemLinkRequestBody,
    PatchDocumentRequestBody,
)
from teamstorm.api import TeamStormAPI


def _workitem_payload(**overrides) -> dict:
    payload = {
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
    payload.update(overrides)
    return payload


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
        "version": 1,
        "versionUrl": "https://example.test/docs/DOC-1/versions/1",
        "labels": [],
        "isBlocked": False,
        "status": None,
    }
    payload.update(overrides)
    return payload


class DocumentsAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = DocumentsAPI(self.client)
        self.workspace = "WS"
        self.document_id = uuid4()
        self.parent_id = uuid4()

    def test_list_uses_get_all_with_pagination_params(self) -> None:
        self.client.get_all.return_value = [_document_payload()]

        result = self.api.list(self.workspace, from_token="t1", max_items_count=25)

        self.client.get_all.assert_called_once_with(
            "/workspaces/WS/documents",
            params={"fromToken": "t1", "maxItemsCount": 25},
        )
        self.assertEqual(1, len(result))
        self.assertEqual("Spec", result[0].name)

    def test_list_with_no_filters_passes_none_params(self) -> None:
        self.client.get_all.return_value = []

        self.api.list(self.workspace)

        self.client.get_all.assert_called_once_with("/workspaces/WS/documents", params=None)

    def test_get_exact_path(self) -> None:
        self.client.get.return_value = _document_payload()

        got = self.api.get(self.workspace, document_id=self.document_id)

        self.client.get.assert_called_once_with(f"/workspaces/{self.workspace}/documents/{self.document_id}")
        self.assertEqual("Spec", got.name)

    def test_create_requires_parent_id_and_serializes_body(self) -> None:
        self.client.post.return_value = _document_payload()
        body = CreateDocumentRequestBody(
            name="Spec",
            content="Hello",
            parent_id=self.parent_id,
            labels=["important"],
        )

        created = self.api.create(self.workspace, body)

        self.client.post.assert_called_once_with(
            "/workspaces/WS/documents",
            {
                "name": "Spec",
                "content": "Hello",
                "parentId": str(self.parent_id),
                "labels": ["important"],
            },
        )
        self.assertEqual("Spec", created.name)

    def test_create_request_body_rejects_missing_parent_id(self) -> None:
        with self.assertRaises(ValidationError):
            CreateDocumentRequestBody(name="Spec", content="Hello", labels=[])

    def test_patch_uses_exclude_unset_and_keeps_explicit_null(self) -> None:
        self.client.patch.return_value = _document_payload()
        body = PatchDocumentRequestBody(status=None)

        patched = self.api.patch(self.workspace, document_id=self.document_id, body=body)

        self.client.patch.assert_called_once_with(
            f"/workspaces/{self.workspace}/documents/{self.document_id}",
            {"status": None},
        )
        self.assertEqual("Spec", patched.name)

    def test_patch_omits_status_never_set(self) -> None:
        self.client.patch.return_value = _document_payload()
        body = PatchDocumentRequestBody()

        self.api.patch(self.workspace, document_id=self.document_id, body=body)

        self.client.patch.assert_called_once_with(
            f"/workspaces/{self.workspace}/documents/{self.document_id}",
            {},
        )

    def test_delete_exact_path(self) -> None:
        self.client.delete.return_value = None

        deleted = self.api.delete(self.workspace, document_id=self.document_id)

        self.client.delete.assert_called_once_with(f"/workspaces/{self.workspace}/documents/{self.document_id}")
        self.assertIsNone(deleted)

    def test_block_is_bodyless_post(self) -> None:
        self.client.post.return_value = _document_payload(isBlocked=True)

        result = self.api.block(self.workspace, document_id=self.document_id)

        self.client.post.assert_called_once_with(f"/workspaces/{self.workspace}/documents/{self.document_id}/block")
        self.assertTrue(result.is_blocked)

    def test_unblock_is_bodyless_post(self) -> None:
        self.client.post.return_value = _document_payload(isBlocked=False)

        result = self.api.unblock(self.workspace, document_id=self.document_id)

        self.client.post.assert_called_once_with(f"/workspaces/{self.workspace}/documents/{self.document_id}/unblock")
        self.assertFalse(result.is_blocked)

    def test_validation_error_on_bad_payload(self) -> None:
        self.client.get.return_value = {"id": str(uuid4())}
        with self.assertRaises(ValidationError):
            self.api.get(self.workspace, document_id=self.document_id)


class DocumentVersionsAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = DocumentVersionsAPI(self.client)
        self.workspace = "WS"
        self.document_id = uuid4()

    def _version_payload(self, **overrides) -> dict:
        payload = {
            "versionNumber": 1,
            "author": _user_payload(),
            "createdDate": "2026-01-01T10:00:00Z",
            "status": None,
        }
        payload.update(overrides)
        return payload

    def test_list_uses_get_all_with_pagination_params(self) -> None:
        self.client.get_all.return_value = [self._version_payload()]

        result = self.api.list(self.workspace, document_id=self.document_id, from_token="t1", max_items_count=10)

        self.client.get_all.assert_called_once_with(
            f"/workspaces/{self.workspace}/documents/{self.document_id}/versions",
            params={"fromToken": "t1", "maxItemsCount": 10},
        )
        self.assertEqual(1, len(result))
        self.assertEqual(1, result[0].version_number)

    def test_list_with_no_filters_passes_none_params(self) -> None:
        self.client.get_all.return_value = []

        self.api.list(self.workspace, document_id=self.document_id)

        self.client.get_all.assert_called_once_with(
            f"/workspaces/{self.workspace}/documents/{self.document_id}/versions",
            params=None,
        )

    def test_get_by_version_returns_document_model(self) -> None:
        self.client.get.return_value = _document_payload(version=2)

        got = self.api.get(self.workspace, document_id=self.document_id, version=2)

        self.client.get.assert_called_once_with(f"/workspaces/{self.workspace}/documents/{self.document_id}/versions/2")
        self.assertEqual(2, got.version)

    def test_delete_exact_path(self) -> None:
        self.client.delete.return_value = None

        deleted = self.api.delete(self.workspace, document_id=self.document_id, version=3)

        self.client.delete.assert_called_once_with(
            f"/workspaces/{self.workspace}/documents/{self.document_id}/versions/3"
        )
        self.assertIsNone(deleted)


class DocumentStatusesAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = DocumentStatusesAPI(self.client)
        self.workspace = "WS"

    def test_list_uses_plain_get_and_unwraps_items(self) -> None:
        self.client.get.return_value = {"items": [_status_payload(), _status_payload()]}

        result = self.api.list(self.workspace)

        self.client.get.assert_called_once_with(f"/workspaces/{self.workspace}/documents-statuses")
        self.client.get_all.assert_not_called()
        self.assertEqual(2, len(result))

    def test_get_exact_path(self) -> None:
        payload = _status_payload()
        self.client.get.return_value = payload

        got = self.api.get(self.workspace, status_key="Draft")

        self.client.get.assert_called_once_with(f"/workspaces/{self.workspace}/documents-statuses/Draft")
        self.assertEqual(payload["name"], got.name)


class DocumentWorkitemLinksAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = DocumentWorkitemLinksAPI(self.client)
        self.workspace = "WS"
        self.document_id = uuid4()
        self.workitem_id = uuid4()

    def test_list_uses_get_all_on_document_scoped_path(self) -> None:
        self.client.get_all.return_value = [_workitem_payload()]

        result = self.api.list(self.workspace, document_id=self.document_id)

        self.client.get_all.assert_called_once_with(
            f"/workspaces/{self.workspace}/documents/{self.document_id}/workitem-links"
        )
        self.assertEqual(1, len(result))
        self.assertEqual("Task", result[0].name)

    def test_list_validation_error_on_bad_payload(self) -> None:
        self.client.get_all.return_value = [{"id": str(uuid4())}]
        with self.assertRaises(ValidationError):
            self.api.list(self.workspace, document_id=self.document_id)

    def test_create_posts_to_document_scoped_path(self) -> None:
        self.client.post.return_value = None
        body = CreateDocumentWorkitemLinkRequestBody(workitem="WI-1", workitem_workspace="WS2")

        result = self.api.create(self.workspace, document_id=self.document_id, body=body)

        self.client.post.assert_called_once_with(
            f"/workspaces/{self.workspace}/documents/{self.document_id}/workitem-links",
            {"workitem": "WI-1", "workitemWorkspace": "WS2"},
        )
        self.assertIsNone(result)

    def test_delete_sends_body_on_collection_path(self) -> None:
        # The DELETE route is the bare collection path -- no linkId. The body
        # identifies which linked workitem to remove; this must NOT delete
        # every workitem-link on the document.
        self.client.delete.return_value = None
        body = DeleteDocumentWorkitemLinkRequestBody(workitem="WI-1", workitem_workspace="WS2")

        result = self.api.delete(self.workspace, document_id=self.document_id, body=body)

        self.client.delete.assert_called_once_with(
            f"/workspaces/{self.workspace}/documents/{self.document_id}/workitem-links",
            body={"workitem": "WI-1", "workitemWorkspace": "WS2"},
        )
        self.assertIsNone(result)

    def test_list_by_workitem_uses_get_all_on_workitem_scoped_path(self) -> None:
        # Reverse direction: workitem-scoped, not nested under /documents/.
        self.client.get_all.return_value = [_document_payload()]

        result = self.api.list_by_workitem(self.workspace, workitem_id=self.workitem_id)

        self.client.get_all.assert_called_once_with(
            f"/workspaces/{self.workspace}/workitems/{self.workitem_id}/document-links"
        )
        called_path = self.client.get_all.call_args.args[0]
        self.assertNotIn("documents", called_path)
        self.assertEqual(1, len(result))
        self.assertEqual("Spec", result[0].name)

    def test_list_by_workitem_validation_error_on_bad_payload(self) -> None:
        self.client.get_all.return_value = [{"id": str(uuid4())}]
        with self.assertRaises(ValidationError):
            self.api.list_by_workitem(self.workspace, workitem_id=self.workitem_id)


class DocumentsApiWiringTestCase(unittest.TestCase):
    def test_grouped_api_exposes_documents_versions_and_statuses(self) -> None:
        client = MagicMock()
        api = TeamStormAPI(client)

        documents = api.documents
        versions = api.document_versions
        statuses = api.document_statuses
        workitem_links = api.document_workitem_links

        self.assertIsInstance(documents, DocumentsAPI)
        self.assertIs(client, documents.client)
        self.assertIsInstance(versions, DocumentVersionsAPI)
        self.assertIs(client, versions.client)
        self.assertIsInstance(statuses, DocumentStatusesAPI)
        self.assertIs(client, statuses.client)
        self.assertIsInstance(workitem_links, DocumentWorkitemLinksAPI)
        self.assertIs(client, workitem_links.client)


if __name__ == "__main__":
    unittest.main()
