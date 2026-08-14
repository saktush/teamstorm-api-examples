import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from pydantic import ValidationError

from teamstorm.api.attributes import AttributesAPI
from teamstorm.models.attributes import (
    CreateAttributeOptionRequestBody,
    CreateAttributeRequestBody,
    PatchAttributeOptionRequestBody,
    PatchAttributeRequestBody,
)
from teamstorm.models.enums import AttributeType


def _attribute_payload() -> dict:
    return {
        "id": str(uuid4()),
        "name": "Severity",
        "description": "Ticket severity",
        "type": "UniSelect",
        "options": [{"id": str(uuid4()), "name": "High"}],
        "workitemTypes": [{"id": str(uuid4()), "name": "Bug"}],
    }


class AttributesAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = AttributesAPI(self.client)
        self.workspace = "WS"
        self.attribute_id = uuid4()
        self.option_id = uuid4()

    def test_list_uses_get_all_with_filters_and_parses(self) -> None:
        self.client.get_all.return_value = [_attribute_payload()]

        result = self.api.list(
            self.workspace,
            name="Severity",
            is_full_name_matching=True,
            type=AttributeType.UniSelect,
        )

        self.client.get_all.assert_called_once_with(
            "/workspaces/WS/attributes",
            params={
                "name": "Severity",
                "isFullNameMatching": True,
                "type": "UniSelect",
            },
        )
        self.assertEqual(1, len(result))
        self.assertEqual("Severity", result[0].name)

    def test_get_create_patch_delete_and_options(self) -> None:
        payload = _attribute_payload()
        self.client.get.return_value = payload
        self.client.post.return_value = payload
        self.client.patch.return_value = payload
        self.client.delete.return_value = None

        got = self.api.get(self.workspace, attribute_id=self.attribute_id)
        self.assertEqual("Severity", got.name)
        self.client.get.assert_called_once_with(f"/workspaces/{self.workspace}/attributes/{self.attribute_id}")

        created = self.api.create(
            self.workspace,
            CreateAttributeRequestBody(name="Severity", type=AttributeType.UniSelect),
        )
        self.assertEqual("Severity", created.name)
        self.client.post.assert_any_call(
            f"/workspaces/{self.workspace}/attributes",
            {"name": "Severity", "type": "UniSelect"},
        )

        patched = self.api.patch(
            self.workspace,
            attribute_id=self.attribute_id,
            body=PatchAttributeRequestBody(name="Priority"),
        )
        self.assertEqual("Severity", patched.name)
        self.client.patch.assert_any_call(
            f"/workspaces/{self.workspace}/attributes/{self.attribute_id}",
            {"name": "Priority"},
        )

        deleted = self.api.delete(self.workspace, attribute_id=self.attribute_id)
        self.assertIsNone(deleted)
        self.client.delete.assert_any_call(f"/workspaces/{self.workspace}/attributes/{self.attribute_id}")

        self.api.add_option(
            self.workspace,
            attribute_id=self.attribute_id,
            body=CreateAttributeOptionRequestBody(id=None, name="Critical"),
        )
        self.client.post.assert_any_call(
            f"/workspaces/{self.workspace}/attributes/{self.attribute_id}/options",
            {"name": "Critical"},
        )

        self.api.patch_option(
            self.workspace,
            attribute_id=self.attribute_id,
            body=PatchAttributeOptionRequestBody(id=self.option_id, name="Blocker"),
        )
        self.client.patch.assert_any_call(
            f"/workspaces/{self.workspace}/attributes/{self.attribute_id}/options",
            {"id": str(self.option_id), "name": "Blocker"},
        )

        deleted_option = self.api.delete_option(
            self.workspace,
            attribute_id=self.attribute_id,
            option_id=self.option_id,
        )
        self.assertIsNone(deleted_option)
        self.client.delete.assert_any_call(
            f"/workspaces/{self.workspace}/attributes/{self.attribute_id}/options/{self.option_id}"
        )

    def test_validation_error_on_bad_payload(self) -> None:
        self.client.get.return_value = {"id": str(uuid4())}
        with self.assertRaises(ValidationError):
            self.api.get(self.workspace, attribute_id=self.attribute_id)

    def test_patch_uses_exclude_unset_and_keeps_explicit_null(self) -> None:
        payload = _attribute_payload()
        self.client.patch.return_value = payload

        # name is set to a real value, description is explicitly cleared
        # (None), options is never touched at all.
        body = PatchAttributeRequestBody(name="Priority", description=None)
        self.api.patch(self.workspace, attribute_id=self.attribute_id, body=body)

        self.client.patch.assert_called_once_with(
            f"/workspaces/{self.workspace}/attributes/{self.attribute_id}",
            {"name": "Priority", "description": None},
        )

    def test_patch_omits_fields_never_set(self) -> None:
        payload = _attribute_payload()
        self.client.patch.return_value = payload

        body = PatchAttributeRequestBody(name="Priority")
        self.api.patch(self.workspace, attribute_id=self.attribute_id, body=body)

        # description/options were never assigned -> must be entirely absent,
        # not merely null, so the server treats them as "leave unchanged".
        self.client.patch.assert_called_once_with(
            f"/workspaces/{self.workspace}/attributes/{self.attribute_id}",
            {"name": "Priority"},
        )


if __name__ == "__main__":
    unittest.main()
