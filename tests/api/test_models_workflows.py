import unittest
from uuid import uuid4

from pydantic import ValidationError

from teamstorm.models.enums import WorkflowType
from teamstorm.models.workflows import (
    CreateTransitionRequestBody,
    CreateWorkflowRequestBody,
    CreateWorkflowStatusRequestBody,
    PatchTransitionRequestBody,
    PatchWorkflowRequestBody,
    PatchWorkflowStatusRequestBody,
    WorkflowModel,
)


class WorkflowsModelsTestCase(unittest.TestCase):
    def _status_payload(self, status_id: str, category_id: str) -> dict:
        return {
            "id": status_id,
            "name": "In Progress",
            "category": {"id": category_id, "name": "In Progress"},
        }

    def test_parse_workflow_model_with_transitions_and_statuses(self) -> None:
        status_id = str(uuid4())
        next_status_id = str(uuid4())
        category_id = str(uuid4())

        model = WorkflowModel.model_validate(
            {
                "id": str(uuid4()),
                "name": "Default WF",
                "type": "Workitem",
                "description": "workflow",
                "transitions": [
                    {
                        "transitionId": str(uuid4()),
                        "fromStatus": None,
                        "nextStatus": self._status_payload(next_status_id, category_id),
                        "fromAllStatuses": True,
                        "isInitial": True,
                    }
                ],
                "statuses": [
                    {
                        "id": status_id,
                        "name": "To Do",
                        "category": {"id": category_id, "name": "To Do"},
                        "positionX": 10,
                        "positionY": 20,
                    }
                ],
            }
        )

        self.assertEqual(WorkflowType.Workitem, model.type)
        dumped = model.model_dump()
        self.assertIn("fromAllStatuses", dumped["transitions"][0])
        self.assertIn("positionX", dumped["statuses"][0])

    def test_create_and_patch_request_aliases(self) -> None:
        status_id = str(uuid4())
        from_status_id = str(uuid4())

        create = CreateWorkflowRequestBody.model_validate(
            {
                "name": "New WF",
                "transitions": [
                    {
                        "fromStatusId": from_status_id,
                        "nextStatusId": status_id,
                        "isInitial": True,
                    }
                ],
                "statuses": [{"statusId": status_id, "positionX": 0, "positionY": 0}],
            }
        )
        create_dump = create.model_dump()
        self.assertIn("fromStatusId", create_dump["transitions"][0])
        self.assertIn("statusId", create_dump["statuses"][0])

        patch = PatchWorkflowRequestBody.model_validate(
            {
                "name": "Renamed WF",
                "transitions": [
                    {
                        "transitionId": str(uuid4()),
                        "fromStatusId": None,
                        "nextStatusId": status_id,
                        "isInitial": False,
                    }
                ],
                "statuses": [{"statusId": status_id, "positionX": 1, "positionY": 2}],
            }
        )
        patch_dump = patch.model_dump()
        self.assertIn("transitionId", patch_dump["transitions"][0])
        self.assertIn("positionY", patch_dump["statuses"][0])

    def test_required_fields_in_transition_and_status_requests(self) -> None:
        with self.assertRaises(ValidationError):
            CreateTransitionRequestBody.model_validate({"isInitial": True})

        with self.assertRaises(ValidationError):
            PatchTransitionRequestBody.model_validate({"nextStatusId": str(uuid4())})

        with self.assertRaises(ValidationError):
            CreateWorkflowStatusRequestBody.model_validate({"statusId": str(uuid4())})

        with self.assertRaises(ValidationError):
            PatchWorkflowStatusRequestBody.model_validate({"statusId": str(uuid4())})

    def test_patch_workflow_nullable_and_partial(self) -> None:
        empty_patch = PatchWorkflowRequestBody.model_validate({})
        self.assertIsNone(empty_patch.name)
        self.assertIsNone(empty_patch.transitions)
        self.assertIsNone(empty_patch.statuses)

        nullable_patch = PatchWorkflowRequestBody.model_validate({"name": None})
        self.assertIsNone(nullable_patch.name)

    def test_unknown_fields_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            WorkflowModel.model_validate(
                {
                    "id": str(uuid4()),
                    "name": "WF",
                    "type": "Portfolio",
                    "transitions": [],
                    "statuses": [],
                    "unknown": 1,
                }
            )

        with self.assertRaises(ValidationError):
            CreateWorkflowRequestBody.model_validate({"name": "WF", "transitions": [], "statuses": [], "extra": True})


if __name__ == "__main__":
    unittest.main()
