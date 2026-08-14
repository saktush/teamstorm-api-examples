import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from pydantic import ValidationError

from teamstorm.api.workitems import WorkitemsAPI
from teamstorm.client import ApiError
from teamstorm.models.workitems_attributes_update import (
    UpdateTagFieldRequestBody,
    UpdateUniSelectFieldRequestBody,
    UpdateUniStringFieldRequestBody,
    UpdateUserFieldRequestBody,
    UpdateUserFieldValueModel,
)


def _attribute_payload_uni_string() -> dict:
    return {
        "type": "UniString",
        "id": str(uuid4()),
        "name": "Text attribute",
        "value": "abc",
    }


def _attribute_payload_tag() -> dict:
    return {
        "type": "Tag",
        "id": str(uuid4()),
        "name": "Labels",
        "value": [{"id": str(uuid4()), "name": "A"}],
    }


def _attribute_payload_uniselect_empty() -> dict:
    return {
        "type": "UniSelect",
        "id": str(uuid4()),
        "name": "Severity",
        "value": None,
    }


def _attribute_payload_tag_empty() -> dict:
    return {
        "type": "Tag",
        "id": str(uuid4()),
        "name": "Labels",
        "value": [],
    }


class WorkitemsAPIAttributesTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = WorkitemsAPI(self.client)
        self.workspace = "WS"
        self.workitem_id = uuid4()
        self.attribute_id = uuid4()

    def test_list_attributes(self) -> None:
        self.client.get_all.return_value = [
            _attribute_payload_uni_string(),
            _attribute_payload_tag(),
        ]

        result = self.api.list_attributes(self.workspace, workitem_id=self.workitem_id)

        self.client.get_all.assert_called_once_with(
            f"/workspaces/{self.workspace}/workitems/{self.workitem_id}/attributes"
        )
        self.assertEqual(2, len(result))
        self.assertEqual("UniString", result[0].type.value)
        self.assertEqual("Tag", result[1].type.value)

    def test_update_attribute(self) -> None:
        self.client.put.return_value = _attribute_payload_uni_string()
        body = UpdateUniStringFieldRequestBody(type="UniString", value="updated")

        result = self.api.update_attribute(
            self.workspace,
            workitem_id=self.workitem_id,
            attribute_id=self.attribute_id,
            body=body,
        )

        self.client.put.assert_called_once_with(
            f"/workspaces/{self.workspace}/workitems/{self.workitem_id}/attributes/{self.attribute_id}",
            {"type": "UniString", "value": "updated"},
        )
        self.client.patch.assert_not_called()
        self.assertEqual("UniString", result.type.value)

    def test_update_attribute_sends_explicit_null_to_clear_a_value(self) -> None:
        # `value` is required-and-nullable in the spec: an explicit None is how
        # a caller clears the attribute. Serializing with exclude_none=True
        # would drop the key and turn the clear into a silent no-op.
        self.client.put.return_value = _attribute_payload_uniselect_empty()
        body = UpdateUniStringFieldRequestBody(type="UniString", value=None)

        self.api.update_attribute(
            self.workspace,
            workitem_id=self.workitem_id,
            attribute_id=self.attribute_id,
            body=body,
        )

        self.client.put.assert_called_once_with(
            f"/workspaces/{self.workspace}/workitems/{self.workitem_id}/attributes/{self.attribute_id}",
            {"type": "UniString", "value": None},
        )

    def test_update_attribute_omits_untouched_nested_value_fields(self) -> None:
        # exclude_unset=True still trims the optional keys of a nested value
        # object the caller never set -- here, identify the user by userName
        # without also sending "id": null.
        self.client.put.return_value = _attribute_payload_uni_string()
        body = UpdateUserFieldRequestBody(
            type="User",
            value=UpdateUserFieldValueModel(userName="jdoe"),
        )

        self.api.update_attribute(
            self.workspace,
            workitem_id=self.workitem_id,
            attribute_id=self.attribute_id,
            body=body,
        )

        self.client.put.assert_called_once_with(
            f"/workspaces/{self.workspace}/workitems/{self.workitem_id}/attributes/{self.attribute_id}",
            {"type": "User", "value": {"userName": "jdoe"}},
        )

    def test_update_attribute_fallbacks_to_patch_on_405(self) -> None:
        self.client.put.side_effect = ApiError("method not allowed", status=405)
        self.client.patch.return_value = _attribute_payload_uni_string()
        body = UpdateUniStringFieldRequestBody(type="UniString", value="updated")

        result = self.api.update_attribute(
            self.workspace,
            workitem_id=self.workitem_id,
            attribute_id=self.attribute_id,
            body=body,
        )

        path = f"/workspaces/{self.workspace}/workitems/{self.workitem_id}/attributes/{self.attribute_id}"
        payload = {"type": "UniString", "value": "updated"}
        self.client.put.assert_called_once_with(path, payload)
        self.client.patch.assert_called_once_with(path, payload)
        self.assertEqual("UniString", result.type.value)

    def test_update_attribute_does_not_fallback_on_400(self) -> None:
        self.client.put.side_effect = ApiError("bad request", status=400)
        body = UpdateUniStringFieldRequestBody(type="UniString", value="updated")

        with self.assertRaises(ApiError):
            self.api.update_attribute(
                self.workspace,
                workitem_id=self.workitem_id,
                attribute_id=self.attribute_id,
                body=body,
            )

        self.client.patch.assert_not_called()

    def test_update_attribute_uniselect_empty_response_has_no_compat_retry(self) -> None:
        option_id = str(uuid4())
        self.client.put.return_value = _attribute_payload_uniselect_empty()
        body = UpdateUniSelectFieldRequestBody(type="UniSelect", value=option_id)

        result = self.api.update_attribute(
            self.workspace,
            workitem_id=self.workitem_id,
            attribute_id=self.attribute_id,
            body=body,
        )

        path = f"/workspaces/{self.workspace}/workitems/{self.workitem_id}/attributes/{self.attribute_id}"
        self.client.put.assert_called_once_with(
            path,
            {"type": "UniSelect", "value": option_id},
        )
        self.client.patch.assert_not_called()
        self.assertEqual("UniSelect", result.type.value)
        self.assertIsNone(result.value)

    def test_update_attribute_tag_empty_response_has_no_compat_retry(self) -> None:
        option_ids = [str(uuid4()), str(uuid4())]
        self.client.put.return_value = _attribute_payload_tag_empty()
        body = UpdateTagFieldRequestBody(type="Tag", value=option_ids)

        result = self.api.update_attribute(
            self.workspace,
            workitem_id=self.workitem_id,
            attribute_id=self.attribute_id,
            body=body,
        )

        path = f"/workspaces/{self.workspace}/workitems/{self.workitem_id}/attributes/{self.attribute_id}"
        self.client.put.assert_called_once_with(
            path,
            {"type": "Tag", "value": option_ids},
        )
        self.client.patch.assert_not_called()
        self.assertEqual("Tag", result.type.value)
        self.assertEqual([], result.value)

    def test_validation_error_on_bad_payload(self) -> None:
        self.client.put.return_value = {"id": str(uuid4())}
        body = UpdateUniStringFieldRequestBody(type="UniString", value="updated")
        with self.assertRaises(ValidationError):
            self.api.update_attribute(
                self.workspace,
                workitem_id=self.workitem_id,
                attribute_id=self.attribute_id,
                body=body,
            )


if __name__ == "__main__":
    unittest.main()
