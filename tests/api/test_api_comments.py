import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from pydantic import ValidationError

from teamstorm.api.comments import DocumentCommentsAPI, WorkitemCommentsAPI
from teamstorm.api import TeamStormAPI
from teamstorm.models.comments import (
    CommentModel,
    CommentVisibilitySettingsModel,
    CreateCommentRequestBody,
    GroupPrincipalModel,
    UpdateCommentPrincipalModel,
    UpdateCommentRequestBody,
    UpdateCommentVisibilitySettingsRequestBody,
    UserPrincipalModel,
)
from teamstorm.models.enums import CommentVisibilityType, PrincipalType


def _user_payload() -> dict:
    return {
        "id": str(uuid4()),
        "displayName": "Jane Doe",
        "username": "jane",
        "email": "jane@example.com",
    }


def _group_payload() -> dict:
    return {"id": str(uuid4()), "name": "Reviewers"}


def _comment_payload(**overrides) -> dict:
    payload = {
        "id": str(uuid4()),
        "text": "Looks good to me",
        "author": _user_payload(),
        "createdAt": "2026-01-01T10:00:00Z",
        "updatedAt": "2026-01-02T11:00:00Z",
        "visibilityType": "All",
    }
    payload.update(overrides)
    return payload


def _visibility_payload() -> dict:
    return {
        "visibilityType": "OnlySelected",
        "accessList": [
            {"id": str(uuid4()), "type": "User", "user": _user_payload()},
            {"id": str(uuid4()), "type": "Group", "group": _group_payload()},
        ],
    }


class WorkitemCommentsAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = WorkitemCommentsAPI(self.client)
        self.workspace = "WS"
        self.workitem_id = uuid4()
        self.comment_id = uuid4()

    def test_list_uses_plain_get_and_unwraps_items(self) -> None:
        self.client.get.return_value = {"items": [_comment_payload()]}

        result = self.api.list(self.workspace, workitem_id=self.workitem_id)

        self.client.get.assert_called_once_with(f"/workspaces/{self.workspace}/workitems/{self.workitem_id}/comments")
        self.client.get_all.assert_not_called()
        self.assertEqual(1, len(result))
        self.assertIsInstance(result[0], CommentModel)
        self.assertEqual("Looks good to me", result[0].text)

    def test_list_validation_error_on_bad_payload(self) -> None:
        self.client.get.return_value = {"items": [{"id": str(uuid4())}]}
        with self.assertRaises(ValidationError):
            self.api.list(self.workspace, workitem_id=self.workitem_id)

    def test_create_posts_exact_path_and_body(self) -> None:
        self.client.post.return_value = _comment_payload()
        body = CreateCommentRequestBody(text="Looks good to me")

        result = self.api.create(self.workspace, workitem_id=self.workitem_id, body=body)

        self.client.post.assert_called_once_with(
            f"/workspaces/{self.workspace}/workitems/{self.workitem_id}/comments",
            {"text": "Looks good to me"},
        )
        self.assertEqual("Looks good to me", result.text)

    def test_update_uses_put_not_patch_with_exclude_none_true(self) -> None:
        self.client.put.return_value = _comment_payload(text="Edited")
        body = UpdateCommentRequestBody(text="Edited")

        result = self.api.update(
            self.workspace,
            workitem_id=self.workitem_id,
            comment_id=self.comment_id,
            body=body,
        )

        self.client.put.assert_called_once_with(
            f"/workspaces/{self.workspace}/workitems/{self.workitem_id}/comments/{self.comment_id}",
            {"text": "Edited"},
        )
        self.client.patch.assert_not_called()
        self.assertEqual("Edited", result.text)

    def test_delete_exact_path(self) -> None:
        self.client.delete.return_value = None

        result = self.api.delete(self.workspace, workitem_id=self.workitem_id, comment_id=self.comment_id)

        self.client.delete.assert_called_once_with(
            f"/workspaces/{self.workspace}/workitems/{self.workitem_id}/comments/{self.comment_id}"
        )
        self.assertIsNone(result)

    def test_get_visibility_exact_path_and_parses_discriminated_access_list(self) -> None:
        self.client.get.return_value = _visibility_payload()

        result = self.api.get_visibility(
            self.workspace,
            workitem_id=self.workitem_id,
            comment_id=self.comment_id,
        )

        self.client.get.assert_called_once_with(
            f"/workspaces/{self.workspace}/workitems/{self.workitem_id}/comments/{self.comment_id}/visibility"
        )
        self.assertIsInstance(result, CommentVisibilitySettingsModel)
        self.assertEqual(CommentVisibilityType.OnlySelected, result.visibility_type)
        self.assertEqual(2, len(result.access_list))
        self.assertIsInstance(result.access_list[0], UserPrincipalModel)
        self.assertEqual("jane", result.access_list[0].user.username)
        self.assertIsInstance(result.access_list[1], GroupPrincipalModel)
        self.assertEqual("Reviewers", result.access_list[1].group.name)

    def test_update_visibility_uses_put_exact_path_and_body(self) -> None:
        self.client.put.return_value = _visibility_payload()
        principal_id = uuid4()
        body = UpdateCommentVisibilitySettingsRequestBody(
            visibility_type=CommentVisibilityType.OnlySelected,
            access_list=[UpdateCommentPrincipalModel(id=principal_id, type=PrincipalType.User)],
        )

        result = self.api.update_visibility(
            self.workspace,
            workitem_id=self.workitem_id,
            comment_id=self.comment_id,
            body=body,
        )

        self.client.put.assert_called_once_with(
            f"/workspaces/{self.workspace}/workitems/{self.workitem_id}/comments/{self.comment_id}/visibility",
            {
                "visibilityType": "OnlySelected",
                "accessList": [{"id": str(principal_id), "type": "User"}],
            },
        )
        self.assertIsInstance(result, CommentVisibilitySettingsModel)


class DocumentCommentsAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = DocumentCommentsAPI(self.client)
        self.workspace = "WS"
        self.document_id = uuid4()
        self.comment_id = uuid4()

    def test_list_uses_plain_get_and_unwraps_items(self) -> None:
        self.client.get.return_value = {"items": [_comment_payload()]}

        result = self.api.list(self.workspace, document_id=self.document_id)

        self.client.get.assert_called_once_with(f"/workspaces/{self.workspace}/documents/{self.document_id}/comments")
        self.client.get_all.assert_not_called()
        self.assertEqual(1, len(result))
        self.assertIsInstance(result[0], CommentModel)

    def test_create_posts_exact_path_and_body(self) -> None:
        self.client.post.return_value = _comment_payload(text="Nice draft")
        body = CreateCommentRequestBody(text="Nice draft")

        result = self.api.create(self.workspace, document_id=self.document_id, body=body)

        self.client.post.assert_called_once_with(
            f"/workspaces/{self.workspace}/documents/{self.document_id}/comments",
            {"text": "Nice draft"},
        )
        self.assertEqual("Nice draft", result.text)

    def test_delete_exact_path(self) -> None:
        self.client.delete.return_value = None

        result = self.api.delete(self.workspace, document_id=self.document_id, comment_id=self.comment_id)

        self.client.delete.assert_called_once_with(
            f"/workspaces/{self.workspace}/documents/{self.document_id}/comments/{self.comment_id}"
        )
        self.assertIsNone(result)

    def test_no_update_method_exists(self) -> None:
        # DocumentComments (3 ops: list/create/delete) has no update endpoint,
        # unlike WorkitemComments -- do not add one for symmetry.
        self.assertFalse(hasattr(self.api, "update"))
        self.assertFalse(hasattr(self.api, "get_visibility"))
        self.assertFalse(hasattr(self.api, "update_visibility"))


class CommentModelsTestCase(unittest.TestCase):
    def test_comment_model_round_trips_realistic_payload(self) -> None:
        payload = _comment_payload()

        comment = CommentModel.model_validate(payload)

        self.assertEqual(payload["text"], comment.text)
        self.assertEqual("Jane Doe", comment.author.display_name)
        self.assertEqual(CommentVisibilityType.All, comment.visibility_type)

    def test_visibility_settings_discriminates_user_and_group_principals(self) -> None:
        settings = CommentVisibilitySettingsModel.model_validate(_visibility_payload())

        self.assertIsInstance(settings.access_list[0], UserPrincipalModel)
        self.assertEqual(PrincipalType.User, settings.access_list[0].type)
        self.assertIsInstance(settings.access_list[1], GroupPrincipalModel)
        self.assertEqual(PrincipalType.Group, settings.access_list[1].type)

    def test_extra_fields_rejected(self) -> None:
        payload = _comment_payload()
        payload["unexpectedField"] = "boom"
        with self.assertRaises(ValidationError):
            CommentModel.model_validate(payload)


class CommentsApiWiringTestCase(unittest.TestCase):
    def test_grouped_api_exposes_workitem_and_document_comments(self) -> None:
        client = MagicMock()
        api = TeamStormAPI(client)

        workitem_comments = api.workitem_comments
        document_comments = api.document_comments

        self.assertIsInstance(workitem_comments, WorkitemCommentsAPI)
        self.assertIs(client, workitem_comments.client)
        self.assertIsInstance(document_comments, DocumentCommentsAPI)
        self.assertIs(client, document_comments.client)


if __name__ == "__main__":
    unittest.main()
