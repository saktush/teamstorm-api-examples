import unittest
from uuid import uuid4

from pydantic import ValidationError

from teamstorm.models.attributes import (
    AttributeModel,
    AttributesModelList,
    CreateAttributeOptionRequestBody,
    CreateAttributeRequestBody,
    PatchAttributeOptionRequestBody,
    PatchAttributeRequestBody,
)
from teamstorm.models.enums import AttributeType


class AttributesConfigurationModelsTestCase(unittest.TestCase):
    def test_parse_attribute_model_swagger_shape(self) -> None:
        attribute_id = str(uuid4())
        option_id = str(uuid4())
        type_id = str(uuid4())

        model = AttributeModel.model_validate(
            {
                "id": attribute_id,
                "name": "Severity",
                "description": "Ticket severity",
                "type": "UniSelect",
                "options": [{"id": option_id, "name": "High"}],
                "workitemTypes": [{"id": type_id, "name": "Bug"}],
            }
        )

        self.assertEqual(AttributeType.UniSelect, model.type)
        self.assertEqual(1, len(model.options or []))
        self.assertEqual("High", model.options[0].name)  # type: ignore[index]
        self.assertEqual(1, len(model.workitem_types))
        self.assertIn("workitemTypes", model.model_dump())

    def test_parse_attributes_model_list_with_pagination_aliases(self) -> None:
        model = AttributesModelList.model_validate(
            {
                "fromToken": "a",
                "maxItemsCount": 50,
                "nextToken": "b",
                "items": [],
            }
        )

        self.assertEqual("a", model.from_token)
        self.assertEqual(50, model.max_items_count)
        self.assertEqual("b", model.next_token)
        dumped = model.model_dump()
        self.assertIn("fromToken", dumped)
        self.assertIn("maxItemsCount", dumped)
        self.assertIn("nextToken", dumped)

    def test_create_attribute_request_body_with_enum_and_options(self) -> None:
        model = CreateAttributeRequestBody.model_validate(
            {
                "name": "Story points",
                "type": "Number",
                "options": [{"name": "IgnoredForNumber"}],
            }
        )

        self.assertEqual(AttributeType.Number, model.type)
        self.assertEqual("Story points", model.name)
        self.assertEqual("IgnoredForNumber", model.options[0].name)  # type: ignore[index]

    def test_create_attribute_option_request_body_requires_id_key_but_allows_none(self) -> None:
        model = CreateAttributeOptionRequestBody.model_validate({"id": None, "name": "New option"})
        self.assertIsNone(model.id)
        self.assertEqual("New option", model.name)

        with self.assertRaises(ValidationError):
            CreateAttributeOptionRequestBody.model_validate({"name": "Missing id"})

    def test_patch_attribute_option_request_body_rejects_none_id(self) -> None:
        with self.assertRaises(ValidationError):
            PatchAttributeOptionRequestBody.model_validate({"id": None, "name": "Renamed"})

    def test_patch_attribute_request_body_allows_partial_and_nullable(self) -> None:
        model_empty = PatchAttributeRequestBody.model_validate({})
        self.assertIsNone(model_empty.name)
        self.assertIsNone(model_empty.description)
        self.assertIsNone(model_empty.options)

        model_nullable = PatchAttributeRequestBody.model_validate({"description": None})
        self.assertIsNone(model_nullable.description)

    def test_extra_fields_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            AttributeModel.model_validate(
                {
                    "id": str(uuid4()),
                    "name": "Severity",
                    "type": "UniString",
                    "workitemTypes": [{"id": str(uuid4()), "name": "Task"}],
                    "unexpected": "x",
                }
            )

        with self.assertRaises(ValidationError):
            CreateAttributeRequestBody.model_validate(
                {
                    "name": "Severity",
                    "type": "UniString",
                    "extra": True,
                }
            )


if __name__ == "__main__":
    unittest.main()
