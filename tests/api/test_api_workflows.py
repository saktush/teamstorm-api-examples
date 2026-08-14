import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from pydantic import ValidationError

from teamstorm.api.workflows import WorkflowsAPI
from teamstorm.models.workflows import (
    CreateTransitionRequestBody,
    CreateWorkflowRequestBody,
    CreateWorkflowStatusRequestBody,
    PatchTransitionRequestBody,
    PatchWorkflowRequestBody,
    PatchWorkflowStatusRequestBody,
)


def _workflow_payload() -> dict:
    category_id = str(uuid4())
    status_id = str(uuid4())
    return {
        "id": str(uuid4()),
        "name": "Default WF",
        "type": "Workitem",
        "transitions": [
            {
                "transitionId": str(uuid4()),
                "fromStatus": None,
                "nextStatus": {
                    "id": status_id,
                    "name": "To Do",
                    "category": {"id": category_id, "name": "To Do"},
                },
                "fromAllStatuses": True,
                "isInitial": True,
            }
        ],
        "statuses": [
            {
                "id": status_id,
                "name": "To Do",
                "category": {"id": category_id, "name": "To Do"},
                "positionX": 1,
                "positionY": 2,
            }
        ],
    }


class WorkflowsAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = WorkflowsAPI(self.client)
        self.workspace = "WS"

    def test_list_get_create_patch_delete(self) -> None:
        payload = _workflow_payload()
        self.client.get_all.return_value = [payload]
        self.client.get.return_value = payload
        self.client.post.return_value = payload
        self.client.patch.return_value = payload
        self.client.delete.return_value = None

        listed = self.api.list(self.workspace, name="Default")
        self.client.get_all.assert_called_once_with(
            "/workspaces/WS/workflows",
            params={"name": "Default"},
        )
        self.assertEqual(1, len(listed))

        got = self.api.get(self.workspace, "Default WF")
        self.client.get.assert_called_once_with("/workspaces/WS/workflows/Default WF")
        self.assertEqual("Default WF", got.name)

        create_body = CreateWorkflowRequestBody(
            name="WF",
            transitions=[
                CreateTransitionRequestBody(
                    from_status_id=None,
                    next_status_id=uuid4(),
                    is_initial=True,
                )
            ],
            statuses=[
                CreateWorkflowStatusRequestBody(
                    status_id=uuid4(),
                    position_x=0,
                    position_y=0,
                )
            ],
        )
        created = self.api.create(self.workspace, create_body)
        self.assertEqual("Default WF", created.name)
        self.client.post.assert_any_call(
            "/workspaces/WS/workflows",
            {
                "name": "WF",
                "transitions": [
                    {
                        "nextStatusId": str(create_body.transitions[0].next_status_id),
                        "isInitial": True,
                    }
                ],
                "statuses": [
                    {
                        "statusId": str(create_body.statuses[0].status_id),
                        "positionX": 0,
                        "positionY": 0,
                    }
                ],
            },
        )

        patch_body = PatchWorkflowRequestBody(
            name="WF2",
            transitions=[
                PatchTransitionRequestBody(
                    transition_id=uuid4(),
                    from_status_id=None,
                    next_status_id=uuid4(),
                    is_initial=False,
                )
            ],
            statuses=[
                PatchWorkflowStatusRequestBody(
                    status_id=uuid4(),
                    position_x=3,
                    position_y=4,
                )
            ],
        )
        patched = self.api.patch(self.workspace, workflow_key="WF", body=patch_body)
        self.assertEqual("Default WF", patched.name)
        self.client.patch.assert_any_call(
            "/workspaces/WS/workflows/WF",
            {
                "name": "WF2",
                "transitions": [
                    {
                        "transitionId": str(patch_body.transitions[0].transition_id),
                        "fromStatusId": None,
                        "nextStatusId": str(patch_body.transitions[0].next_status_id),
                        "isInitial": False,
                    }
                ],
                "statuses": [
                    {
                        "statusId": str(patch_body.statuses[0].status_id),
                        "positionX": 3,
                        "positionY": 4,
                    }
                ],
            },
        )

        deleted = self.api.delete(self.workspace, workflow_key="WF")
        self.assertIsNone(deleted)
        self.client.delete.assert_called_once_with("/workspaces/WS/workflows/WF")

    def test_validation_error_on_bad_payload(self) -> None:
        self.client.get.return_value = {"id": str(uuid4())}
        with self.assertRaises(ValidationError):
            self.api.get(self.workspace, "Broken")

    def test_patch_uses_exclude_unset_and_keeps_explicit_null(self) -> None:
        payload = _workflow_payload()
        self.client.patch.return_value = payload

        # name is set to a real value, transitions is explicitly cleared
        # (None), statuses is never touched at all.
        body = PatchWorkflowRequestBody(name="WF2", transitions=None)
        self.api.patch(self.workspace, workflow_key="WF", body=body)

        self.client.patch.assert_called_once_with(
            "/workspaces/WS/workflows/WF",
            {"name": "WF2", "transitions": None},
        )

    def test_patch_omits_fields_never_set(self) -> None:
        payload = _workflow_payload()
        self.client.patch.return_value = payload

        body = PatchWorkflowRequestBody(name="WF2")
        self.api.patch(self.workspace, workflow_key="WF", body=body)

        # transitions/statuses were never assigned -> must be entirely
        # absent, not merely null, so the server treats them as "leave
        # unchanged".
        self.client.patch.assert_called_once_with(
            "/workspaces/WS/workflows/WF",
            {"name": "WF2"},
        )


if __name__ == "__main__":
    unittest.main()
