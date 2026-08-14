import unittest
from uuid import uuid4

from pydantic import ValidationError

from teamstorm.models.enums import ProgressType, TypeColor, TypeIcon
from teamstorm.models.types import CreateTypeRequestBody, PatchTypeRequestBody, TypeModel


class TypesModelsTestCase(unittest.TestCase):
    def test_parse_type_model_swagger_shape(self) -> None:
        type_id = str(uuid4())
        workflow_id = str(uuid4())
        attribute_id = str(uuid4())
        workitem_type_id = str(uuid4())

        payload = {
            "id": type_id,
            "name": "Bug",
            "color": "Red",
            "icon": "BugSolid",
            "workflow": {"id": workflow_id, "name": "Default workflow"},
            "attributes": [
                {
                    "id": attribute_id,
                    "name": "Severity",
                    "type": "UniSelect",
                    "options": [{"id": str(uuid4()), "name": "High"}],
                    "workitemTypes": [{"id": workitem_type_id, "name": "Bug"}],
                }
            ],
            "progressType": "ByStatus",
            "estimatesInTime": True,
            "estimatesInStoryPoints": False,
            "showTimeTracking": True,
        }

        model = TypeModel.model_validate(payload)
        self.assertEqual(TypeColor.Red, model.color)
        self.assertEqual(TypeIcon.BugSolid, model.icon)
        self.assertEqual(ProgressType.ByStatus, model.progress_type)
        dumped = model.model_dump()
        self.assertIn("progressType", dumped)
        self.assertIn("estimatesInTime", dumped)
        self.assertIn("showTimeTracking", dumped)

    def test_create_and_patch_type_request_aliases(self) -> None:
        attribute_id = str(uuid4())

        create_model = CreateTypeRequestBody.model_validate(
            {
                "name": "Task",
                "workflow": "Default workflow",
                "attributeIds": [attribute_id],
                "progressType": "ByChildren",
                "estimatesInTime": True,
            }
        )
        self.assertEqual(ProgressType.ByChildren, create_model.progress_type)
        create_dump = create_model.model_dump()
        self.assertIn("attributeIds", create_dump)
        self.assertIn("progressType", create_dump)

        patch_model = PatchTypeRequestBody.model_validate(
            {
                "name": "Task Updated",
                "attributeIds": [],
                "estimatesInStoryPoints": True,
            }
        )
        patch_dump = patch_model.model_dump()
        self.assertIn("attributeIds", patch_dump)
        self.assertIn("estimatesInStoryPoints", patch_dump)

    def test_create_requires_name_and_workflow(self) -> None:
        with self.assertRaises(ValidationError):
            CreateTypeRequestBody.model_validate({"name": "Task"})

        with self.assertRaises(ValidationError):
            CreateTypeRequestBody.model_validate({"workflow": "wf"})

    def test_extra_fields_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            CreateTypeRequestBody.model_validate({"name": "Task", "workflow": "wf", "unknown": True})

        with self.assertRaises(ValidationError):
            TypeModel.model_validate(
                {
                    "id": str(uuid4()),
                    "name": "Bug",
                    "color": "Red",
                    "icon": "BugSolid",
                    "workflow": {"id": str(uuid4()), "name": "Wf"},
                    "attributes": [],
                    "estimatesInTime": True,
                    "estimatesInStoryPoints": False,
                    "showTimeTracking": True,
                    "extra": "bad",
                }
            )


if __name__ == "__main__":
    unittest.main()
