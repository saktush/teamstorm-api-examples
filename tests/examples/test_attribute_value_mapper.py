import unittest
from datetime import datetime, timezone
from uuid import uuid4

from teamstorm.models.enums import AttributeType
from teamstorm.models.workitems_attributes_create import (
    CreateTagFieldRequestBody,
    CreateUniSelectFieldRequestBody,
    CreateUserFieldRequestBody,
)
from teamstorm.models.workitems_attributes_update import (
    UpdateTagFieldRequestBody,
    UpdateUniSelectFieldRequestBody,
)
from import_toolkit.controllers.core.attribute_value_mapper import (
    build_create_attribute_value,
    build_update_attribute_value,
    normalize_attribute_cell,
)


class AttributeValueMapperTestCase(unittest.TestCase):
    def test_normalize_attribute_cell_all_types(self) -> None:
        self.assertEqual("abc", normalize_attribute_cell(AttributeType.UniString, " abc "))
        self.assertEqual(12.5, normalize_attribute_cell(AttributeType.Number, "12,5"))
        self.assertEqual(
            ["A", "B"],
            normalize_attribute_cell(AttributeType.Tag, "A, B;A"),
        )
        self.assertEqual("opt", normalize_attribute_cell(AttributeType.UniSelect, " opt "))
        self.assertEqual("john", normalize_attribute_cell(AttributeType.User, " john "))
        self.assertEqual(120, normalize_attribute_cell(AttributeType.TimeDuration, "120"))
        self.assertEqual(900, normalize_attribute_cell(AttributeType.TimeDuration, "15m"))
        self.assertEqual(54000, normalize_attribute_cell(AttributeType.TimeDuration, "15h"))

        parsed_date = normalize_attribute_cell(AttributeType.Date, "2026-03-18")
        self.assertIsInstance(parsed_date, datetime)
        assert isinstance(parsed_date, datetime)
        self.assertEqual(timezone.utc, parsed_date.tzinfo)

    def test_build_create_uniselect_and_tag_use_option_ids(self) -> None:
        attribute_id = uuid4()

        select_payload = build_create_attribute_value(
            attribute_id=attribute_id,
            attribute_type=AttributeType.UniSelect,
            raw_value="High",
            resolve_option_id=lambda option: "opt-1" if option == "High" else None,
        )
        self.assertIsInstance(select_payload, CreateUniSelectFieldRequestBody)
        assert isinstance(select_payload, CreateUniSelectFieldRequestBody)
        self.assertEqual("opt-1", select_payload.value)

        tag_payload = build_create_attribute_value(
            attribute_id=attribute_id,
            attribute_type=AttributeType.Tag,
            raw_value="a,b",
            resolve_option_id=lambda option: {"a": "id-a", "b": "id-b"}.get(option),
        )
        self.assertIsInstance(tag_payload, CreateTagFieldRequestBody)
        assert isinstance(tag_payload, CreateTagFieldRequestBody)
        self.assertEqual(["id-a", "id-b"], tag_payload.value)

    def test_build_update_uniselect_and_tag_use_option_ids(self) -> None:
        select_payload = build_update_attribute_value(
            attribute_type=AttributeType.UniSelect,
            raw_value="High",
            resolve_option_id=lambda option: "opt-1" if option == "High" else None,
        )
        self.assertIsInstance(select_payload, UpdateUniSelectFieldRequestBody)
        assert isinstance(select_payload, UpdateUniSelectFieldRequestBody)
        self.assertEqual("opt-1", select_payload.value)

        tag_payload = build_update_attribute_value(
            attribute_type=AttributeType.Tag,
            raw_value="x;y",
            resolve_option_id=lambda option: {"x": "id-x", "y": "id-y"}.get(option),
        )
        self.assertIsInstance(tag_payload, UpdateTagFieldRequestBody)
        assert isinstance(tag_payload, UpdateTagFieldRequestBody)
        self.assertEqual(["id-x", "id-y"], tag_payload.value)

    def test_user_unresolved_warns_and_omits(self) -> None:
        attribute_id = uuid4()
        warnings: list[str] = []

        payload = build_create_attribute_value(
            attribute_id=attribute_id,
            attribute_type=AttributeType.User,
            raw_value="unknown-user",
            resolve_user=lambda _: None,
            warn=warnings.append,
        )
        self.assertIsNone(payload)
        self.assertEqual(1, len(warnings))

    def test_user_resolved_create_payload(self) -> None:
        attribute_id = uuid4()
        payload = build_create_attribute_value(
            attribute_id=attribute_id,
            attribute_type=AttributeType.User,
            raw_value="john",
            resolve_user=lambda _: (uuid4(), "john"),
        )
        self.assertIsInstance(payload, CreateUserFieldRequestBody)

    def test_empty_values_return_none(self) -> None:
        attribute_id = uuid4()
        payload = build_create_attribute_value(
            attribute_id=attribute_id,
            attribute_type=AttributeType.UniString,
            raw_value="  ",
        )
        self.assertIsNone(payload)


if __name__ == "__main__":
    unittest.main()
