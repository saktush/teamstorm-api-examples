import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from pydantic import ValidationError

from teamstorm.api.sharing import DocumentSharingAPI, WorkitemSharingAPI
from teamstorm.api import TeamStormAPI
from teamstorm.models.enums import SharedItemAccessLevel, SharedItemAccessType
from teamstorm.models.sharing import (
    CreateSharedDocumentGroupPermissionBody,
    CreateSharedDocumentUserPermissionBody,
    CreateSharedWorkitemGroupPermissionBody,
    CreateSharedWorkitemUserPermissionBody,
    PatchSharedDocumentPermissionBody,
    PatchSharedWorkitemPermissionBody,
    SharedDocumentGroupPermissionModel,
    SharedDocumentUserPermissionModel,
    SharedWorkitemGroupPermissionModel,
    SharedWorkitemPermissionModel,
    SharedWorkitemUserPermissionModel,
)


def _user_payload() -> dict:
    return {
        "id": str(uuid4()),
        "displayName": "Jane Doe",
        "username": "jane",
        "email": "jane@example.com",
    }


def _group_payload() -> dict:
    return {"id": str(uuid4()), "name": "Reviewers"}


def _workitem_user_permission_payload(**overrides) -> dict:
    payload = {
        "type": "User",
        "permissionId": str(uuid4()),
        "workspaceId": str(uuid4()),
        "workitemId": str(uuid4()),
        "accessLevel": "Read",
        "user": _user_payload(),
    }
    payload.update(overrides)
    return payload


def _workitem_group_permission_payload(**overrides) -> dict:
    payload = {
        "type": "Group",
        "permissionId": str(uuid4()),
        "workspaceId": str(uuid4()),
        "workitemId": str(uuid4()),
        "accessLevel": "Edit",
        "group": _group_payload(),
    }
    payload.update(overrides)
    return payload


def _document_user_permission_payload(**overrides) -> dict:
    payload = {
        "type": "User",
        "permissionId": str(uuid4()),
        "workspaceId": str(uuid4()),
        "documentId": str(uuid4()),
        "accessLevel": "Comment",
        "user": _user_payload(),
    }
    payload.update(overrides)
    return payload


def _document_group_permission_payload(**overrides) -> dict:
    payload = {
        "type": "Group",
        "permissionId": str(uuid4()),
        "workspaceId": str(uuid4()),
        "documentId": str(uuid4()),
        "accessLevel": "Read",
        "group": _group_payload(),
    }
    payload.update(overrides)
    return payload


class WorkitemSharingAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = WorkitemSharingAPI(self.client)
        self.workspace = "WS"
        self.workitem_id = uuid4()
        self.permission_id = uuid4()

    def test_list_uses_get_all_bare_path_and_discriminates(self) -> None:
        self.client.get_all.return_value = [
            _workitem_user_permission_payload(),
            _workitem_group_permission_payload(),
        ]

        result = self.api.list(self.workspace, workitem_id=self.workitem_id)

        self.client.get_all.assert_called_once_with(
            f"/workspaces/{self.workspace}/workitems/{self.workitem_id}/sharing"
        )
        self.assertEqual(2, len(result))
        self.assertIsInstance(result[0], SharedWorkitemUserPermissionModel)
        self.assertEqual("jane", result[0].user.username)
        self.assertIsInstance(result[1], SharedWorkitemGroupPermissionModel)
        self.assertEqual("Reviewers", result[1].group.name)
        self.assertEqual(SharedItemAccessLevel.Edit, result[1].access_level)

    def test_list_validation_error_on_bad_payload(self) -> None:
        self.client.get_all.return_value = [{"type": "User"}]
        with self.assertRaises(ValidationError):
            self.api.list(self.workspace, workitem_id=self.workitem_id)

    def test_create_user_permission_posts_exact_path_and_body(self) -> None:
        self.client.post.return_value = _workitem_user_permission_payload()
        user_id = uuid4()
        body = CreateSharedWorkitemUserPermissionBody(
            access_level=SharedItemAccessLevel.Read,
            user_id=user_id,
        )

        result = self.api.create(self.workspace, workitem_id=self.workitem_id, body=body)

        self.client.post.assert_called_once_with(
            f"/workspaces/{self.workspace}/workitems/{self.workitem_id}/sharing",
            {"type": "User", "accessLevel": "Read", "userId": str(user_id)},
        )
        self.assertIsInstance(result, SharedWorkitemUserPermissionModel)

    def test_create_group_permission_posts_exact_path_and_body(self) -> None:
        self.client.post.return_value = _workitem_group_permission_payload()
        group_id = uuid4()
        body = CreateSharedWorkitemGroupPermissionBody(
            access_level=SharedItemAccessLevel.Edit,
            group_id=group_id,
        )

        result = self.api.create(self.workspace, workitem_id=self.workitem_id, body=body)

        self.client.post.assert_called_once_with(
            f"/workspaces/{self.workspace}/workitems/{self.workitem_id}/sharing",
            {"type": "Group", "accessLevel": "Edit", "groupId": str(group_id)},
        )
        self.assertIsInstance(result, SharedWorkitemGroupPermissionModel)

    def test_patch_sends_only_explicitly_set_access_level(self) -> None:
        self.client.patch.return_value = _workitem_user_permission_payload(accessLevel="Edit")
        body = PatchSharedWorkitemPermissionBody(access_level=SharedItemAccessLevel.Edit)

        result = self.api.patch(
            self.workspace,
            workitem_id=self.workitem_id,
            permission_id=self.permission_id,
            body=body,
        )

        self.client.patch.assert_called_once_with(
            f"/workspaces/{self.workspace}/workitems/{self.workitem_id}/sharing/{self.permission_id}",
            {"accessLevel": "Edit"},
        )
        self.assertEqual(SharedItemAccessLevel.Edit, result.access_level)

    def test_patch_explicit_none_survives_into_request_body(self) -> None:
        # An explicitly-assigned None must reach the server as JSON null, not
        # be silently dropped -- this is the whole point of exclude_none=False.
        self.client.patch.return_value = _workitem_user_permission_payload()
        body = PatchSharedWorkitemPermissionBody(access_level=None)

        self.api.patch(
            self.workspace,
            workitem_id=self.workitem_id,
            permission_id=self.permission_id,
            body=body,
        )

        self.client.patch.assert_called_once_with(
            f"/workspaces/{self.workspace}/workitems/{self.workitem_id}/sharing/{self.permission_id}",
            {"accessLevel": None},
        )

    def test_patch_omits_never_set_field_entirely(self) -> None:
        self.client.patch.return_value = _workitem_user_permission_payload()
        body = PatchSharedWorkitemPermissionBody()

        self.api.patch(
            self.workspace,
            workitem_id=self.workitem_id,
            permission_id=self.permission_id,
            body=body,
        )

        self.client.patch.assert_called_once_with(
            f"/workspaces/{self.workspace}/workitems/{self.workitem_id}/sharing/{self.permission_id}",
            {},
        )

    def test_delete_exact_path(self) -> None:
        self.client.delete.return_value = None

        result = self.api.delete(
            self.workspace,
            workitem_id=self.workitem_id,
            permission_id=self.permission_id,
        )

        self.client.delete.assert_called_once_with(
            f"/workspaces/{self.workspace}/workitems/{self.workitem_id}/sharing/{self.permission_id}"
        )
        self.assertIsNone(result)


class DocumentSharingAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = DocumentSharingAPI(self.client)
        self.workspace = "WS"
        self.document_id = uuid4()
        self.permission_id = uuid4()

    def test_list_uses_get_all_bare_path_and_discriminates(self) -> None:
        self.client.get_all.return_value = [
            _document_user_permission_payload(),
            _document_group_permission_payload(),
        ]

        result = self.api.list(self.workspace, document_id=self.document_id)

        self.client.get_all.assert_called_once_with(
            f"/workspaces/{self.workspace}/documents/{self.document_id}/sharing"
        )
        self.assertEqual(2, len(result))
        self.assertIsInstance(result[0], SharedDocumentUserPermissionModel)
        self.assertIsInstance(result[1], SharedDocumentGroupPermissionModel)

    def test_create_user_permission_posts_exact_path_and_body(self) -> None:
        self.client.post.return_value = _document_user_permission_payload()
        user_id = uuid4()
        body = CreateSharedDocumentUserPermissionBody(
            access_level=SharedItemAccessLevel.Comment,
            user_id=user_id,
        )

        result = self.api.create(self.workspace, document_id=self.document_id, body=body)

        self.client.post.assert_called_once_with(
            f"/workspaces/{self.workspace}/documents/{self.document_id}/sharing",
            {"type": "User", "accessLevel": "Comment", "userId": str(user_id)},
        )
        self.assertIsInstance(result, SharedDocumentUserPermissionModel)

    def test_create_group_permission_posts_exact_path_and_body(self) -> None:
        self.client.post.return_value = _document_group_permission_payload()
        group_id = uuid4()
        body = CreateSharedDocumentGroupPermissionBody(
            access_level=SharedItemAccessLevel.Read,
            group_id=group_id,
        )

        result = self.api.create(self.workspace, document_id=self.document_id, body=body)

        self.client.post.assert_called_once_with(
            f"/workspaces/{self.workspace}/documents/{self.document_id}/sharing",
            {"type": "Group", "accessLevel": "Read", "groupId": str(group_id)},
        )
        self.assertIsInstance(result, SharedDocumentGroupPermissionModel)

    def test_patch_explicit_none_survives_into_request_body(self) -> None:
        self.client.patch.return_value = _document_user_permission_payload()
        body = PatchSharedDocumentPermissionBody(access_level=None)

        self.api.patch(
            self.workspace,
            document_id=self.document_id,
            permission_id=self.permission_id,
            body=body,
        )

        self.client.patch.assert_called_once_with(
            f"/workspaces/{self.workspace}/documents/{self.document_id}/sharing/{self.permission_id}",
            {"accessLevel": None},
        )

    def test_delete_exact_path(self) -> None:
        self.client.delete.return_value = None

        result = self.api.delete(
            self.workspace,
            document_id=self.document_id,
            permission_id=self.permission_id,
        )

        self.client.delete.assert_called_once_with(
            f"/workspaces/{self.workspace}/documents/{self.document_id}/sharing/{self.permission_id}"
        )
        self.assertIsNone(result)


class SharingModelsTestCase(unittest.TestCase):
    def test_workitem_permission_model_round_trips_realistic_payload(self) -> None:
        payload = _workitem_user_permission_payload()

        model = SharedWorkitemUserPermissionModel.model_validate(payload)

        self.assertEqual(SharedItemAccessType.User, model.type)
        self.assertEqual(payload["permissionId"], str(model.permission_id))
        self.assertEqual(payload["workitemId"], str(model.workitem_id))
        self.assertEqual(SharedItemAccessLevel.Read, model.access_level)
        self.assertEqual("jane", model.user.username)

    def test_document_permission_model_round_trips_realistic_payload(self) -> None:
        payload = _document_group_permission_payload()

        model = SharedDocumentGroupPermissionModel.model_validate(payload)

        self.assertEqual(SharedItemAccessType.Group, model.type)
        self.assertEqual(payload["documentId"], str(model.document_id))
        self.assertEqual("Reviewers", model.group.name)

    def test_base_permission_model_rejects_unknown_extra_field(self) -> None:
        payload = _workitem_user_permission_payload()
        payload["unexpectedField"] = "boom"
        with self.assertRaises(ValidationError):
            SharedWorkitemUserPermissionModel.model_validate(payload)

    def test_base_permission_model_missing_required_field_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            SharedWorkitemPermissionModel.model_validate({"type": "User"})

    def test_patch_body_distinguishes_absent_from_explicit_none(self) -> None:
        unset = PatchSharedWorkitemPermissionBody()
        explicit_none = PatchSharedWorkitemPermissionBody(access_level=None)

        self.assertEqual({}, unset.model_dump(exclude_unset=True, exclude_none=False))
        self.assertEqual(
            {"accessLevel": None},
            explicit_none.model_dump(exclude_unset=True, exclude_none=False),
        )


class SharingApiWiringTestCase(unittest.TestCase):
    def test_grouped_api_exposes_workitem_and_document_sharing(self) -> None:
        client = MagicMock()
        api = TeamStormAPI(client)

        workitem_sharing = api.workitem_sharing
        document_sharing = api.document_sharing

        self.assertIsInstance(workitem_sharing, WorkitemSharingAPI)
        self.assertIs(client, workitem_sharing.client)
        self.assertIsInstance(document_sharing, DocumentSharingAPI)
        self.assertIs(client, document_sharing.client)


if __name__ == "__main__":
    unittest.main()
