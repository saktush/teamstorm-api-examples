import unittest
from uuid import uuid4

from pydantic import ValidationError

from teamstorm.models.statuses import (
    CreateStatusRequestBody,
    StatusCategoryModelList,
    StatusModel,
    StatusModelList,
)


class StatusesModelsTestCase(unittest.TestCase):
    def test_parse_status_category_model_list(self) -> None:
        model = StatusCategoryModelList.model_validate({"items": [{"id": str(uuid4()), "name": "Done"}]})
        self.assertEqual(1, len(model.items))
        self.assertEqual("Done", model.items[0].name)

    def test_parse_status_model_and_list(self) -> None:
        category_id = str(uuid4())
        payload = {
            "id": str(uuid4()),
            "name": "In Progress",
            "category": {"id": category_id, "name": "In Progress"},
        }
        model = StatusModel.model_validate(payload)
        self.assertEqual("In Progress", model.name)
        self.assertEqual(category_id, str(model.category.id))

        model_list = StatusModelList.model_validate({"items": [payload]})
        self.assertEqual(1, len(model_list.items))

    def test_create_status_request_body_requires_name_and_category(self) -> None:
        valid = CreateStatusRequestBody.model_validate({"name": "To Do", "category": "ToDo"})
        self.assertEqual("To Do", valid.name)
        self.assertEqual("ToDo", valid.category)

        with self.assertRaises(ValidationError):
            CreateStatusRequestBody.model_validate({"name": "To Do"})

        with self.assertRaises(ValidationError):
            CreateStatusRequestBody.model_validate({"category": "ToDo"})

    def test_extra_fields_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            StatusModel.model_validate(
                {
                    "id": str(uuid4()),
                    "name": "Done",
                    "category": {"id": str(uuid4()), "name": "Done"},
                    "extra": True,
                }
            )


if __name__ == "__main__":
    unittest.main()
