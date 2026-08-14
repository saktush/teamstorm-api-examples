import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from pydantic import ValidationError

from teamstorm.api.types import TypesAPI
from teamstorm.models.enums import ProgressType, TypeColor, TypeIcon
from teamstorm.models.types import CreateTypeRequestBody, PatchTypeRequestBody


def _type_payload() -> dict:
    return {
        "id": str(uuid4()),
        "name": "Bug",
        "color": "Red",
        "icon": "BugSolid",
        "workflow": {"id": str(uuid4()), "name": "Default workflow"},
        "attributes": [
            {
                "id": str(uuid4()),
                "name": "Severity",
                "type": "UniSelect",
                "options": [{"id": str(uuid4()), "name": "High"}],
                "workitemTypes": [{"id": str(uuid4()), "name": "Bug"}],
            }
        ],
        "progressType": "ByStatus",
        "estimatesInTime": True,
        "estimatesInStoryPoints": False,
        "showTimeTracking": True,
    }


class TypesAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = TypesAPI(self.client)
        self.workspace = "WS"
        self.type_key = "Bug"
        self.attribute_id = uuid4()

    def test_list_and_get(self) -> None:
        payload = _type_payload()
        self.client.get_all.return_value = [payload]
        self.client.get.return_value = payload

        listed = self.api.list(self.workspace)
        self.client.get_all.assert_called_once_with("/workspaces/WS/types")
        self.assertEqual(1, len(listed))
        self.assertEqual("Bug", listed[0].name)

        got = self.api.get(self.workspace, self.type_key)
        self.client.get.assert_called_once_with("/workspaces/WS/types/Bug")
        self.assertEqual("Bug", got.name)

    def test_create_patch_delete_add_remove_attribute(self) -> None:
        payload = _type_payload()
        self.client.post.return_value = payload
        self.client.patch.return_value = payload
        self.client.delete.return_value = None

        create_body = CreateTypeRequestBody(
            name="Bug",
            workflow="Default workflow",
            color=TypeColor.Red,
            icon=TypeIcon.BugSolid,
            attribute_ids=[self.attribute_id],
            progress_type=ProgressType.ByStatus,
            estimates_in_time=True,
        )
        created = self.api.create(self.workspace, create_body)
        self.assertEqual("Bug", created.name)
        self.client.post.assert_any_call(
            "/workspaces/WS/types",
            {
                "name": "Bug",
                "workflow": "Default workflow",
                "icon": "BugSolid",
                "color": "Red",
                "attributeIds": [str(self.attribute_id)],
                "progressType": "ByStatus",
                "estimatesInTime": True,
            },
        )

        patch_body = PatchTypeRequestBody(name="Bug v2", show_time_tracking=True)
        patched = self.api.patch(self.workspace, type_key=self.type_key, body=patch_body)
        self.assertEqual("Bug", patched.name)
        self.client.patch.assert_any_call(
            "/workspaces/WS/types/Bug",
            {"name": "Bug v2", "showTimeTracking": True},
        )

        deleted = self.api.delete(self.workspace, type_key=self.type_key)
        self.assertIsNone(deleted)
        self.client.delete.assert_any_call("/workspaces/WS/types/Bug")

        added = self.api.add_attribute(self.workspace, type_key=self.type_key, attribute_id=self.attribute_id)
        self.assertEqual("Bug", added.name)
        self.client.post.assert_any_call(
            f"/workspaces/{self.workspace}/types/{self.type_key}/attributes/{self.attribute_id}",
            body={},
        )

        removed = self.api.remove_attribute(self.workspace, type_key=self.type_key, attribute_id=self.attribute_id)
        self.assertIsNone(removed)
        self.client.delete.assert_any_call(
            f"/workspaces/{self.workspace}/types/{self.type_key}/attributes/{self.attribute_id}"
        )

    def test_validation_error_on_bad_payload(self) -> None:
        self.client.get.return_value = {"id": str(uuid4())}
        with self.assertRaises(ValidationError):
            self.api.get(self.workspace, self.type_key)

    def test_patch_uses_exclude_unset_and_keeps_explicit_null(self) -> None:
        payload = _type_payload()
        self.client.patch.return_value = payload

        # name is set to a real value, workflow is explicitly cleared
        # (None), every other field is never touched at all.
        body = PatchTypeRequestBody(name="Bug v2", workflow=None)
        self.api.patch(self.workspace, type_key=self.type_key, body=body)

        self.client.patch.assert_called_once_with(
            "/workspaces/WS/types/Bug",
            {"name": "Bug v2", "workflow": None},
        )

    def test_patch_omits_fields_never_set(self) -> None:
        payload = _type_payload()
        self.client.patch.return_value = payload

        body = PatchTypeRequestBody(name="Bug v2")
        self.api.patch(self.workspace, type_key=self.type_key, body=body)

        # workflow/icon/color/etc were never assigned -> must be entirely
        # absent, not merely null, so the server treats them as "leave
        # unchanged".
        self.client.patch.assert_called_once_with(
            "/workspaces/WS/types/Bug",
            {"name": "Bug v2"},
        )


if __name__ == "__main__":
    unittest.main()
