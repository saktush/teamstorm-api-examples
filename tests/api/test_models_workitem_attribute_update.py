import unittest

from pydantic import TypeAdapter, ValidationError

from teamstorm.models.enums import AttributeType
from teamstorm.models.workitems_attributes_update import (
    UpdateDateFieldRequestBody,
    UpdateNumberFieldRequestBody,
    UpdateTagFieldRequestBody,
    UpdateTimeFieldRequestBody,
    UpdateUniSelectFieldRequestBody,
    UpdateUniStringFieldRequestBody,
    UpdateUserFieldRequestBody,
    UpdateWorkitemAttributeRequestBody,
)


class WorkitemAttributeUpdateModelsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = TypeAdapter(UpdateWorkitemAttributeRequestBody)

    def test_discriminator_parses_all_variants(self) -> None:
        cases = [
            ({"type": "UniString", "value": "abc"}, UpdateUniStringFieldRequestBody),
            ({"type": "Number", "value": 1.5}, UpdateNumberFieldRequestBody),
            ({"type": "Date", "value": "2026-03-17T10:00:00Z"}, UpdateDateFieldRequestBody),
            ({"type": "UniSelect", "value": "opt-1"}, UpdateUniSelectFieldRequestBody),
            ({"type": "Tag", "value": ["a", "b"]}, UpdateTagFieldRequestBody),
            (
                {"type": "User", "value": {"id": None, "userName": "john"}},
                UpdateUserFieldRequestBody,
            ),
            ({"type": "TimeDuration", "value": 120}, UpdateTimeFieldRequestBody),
        ]

        for payload, expected_cls in cases:
            with self.subTest(payload=payload["type"]):
                parsed = self.adapter.validate_python(payload)
                self.assertIsInstance(parsed, expected_cls)

    def test_nullable_values_are_allowed(self) -> None:
        parsed = self.adapter.validate_python({"type": "Tag", "value": None})
        self.assertIsNone(parsed.value)

        user = self.adapter.validate_python({"type": "User", "value": {"userName": "anna"}})
        self.assertEqual("anna", user.value.user_name)
        self.assertIn("userName", user.model_dump()["value"])

    def test_concrete_models_require_type_and_value_keys(self) -> None:
        with self.assertRaises(ValidationError):
            UpdateUniStringFieldRequestBody.model_validate({"value": "x"})

        with self.assertRaises(ValidationError):
            UpdateUniStringFieldRequestBody.model_validate({"type": "UniString"})

    def test_model_dump_uses_aliases(self) -> None:
        model = UpdateUserFieldRequestBody.model_validate({"type": AttributeType.User, "value": {"userName": "mike"}})
        dumped = model.model_dump()
        self.assertEqual("User", dumped["type"])
        self.assertEqual("mike", dumped["value"]["userName"])

    def test_extra_fields_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            self.adapter.validate_python({"type": "Number", "value": 1, "extra": True})


if __name__ == "__main__":
    unittest.main()
