import unittest
from uuid import uuid4

from pydantic import ValidationError

from teamstorm.models.common import UserModel
from teamstorm.models.enums import TreeNodeType
from teamstorm.models.workitems import (
    CreateWorkitemRequestBody,
    MissingWorkitemFieldError,
    WorkitemModel,
    WorkitemsCountModel,
)
from teamstorm.models.workitems_thumbs import FolderThumbModel, TreeNodeThumbModel, WorkitemPortfolioModel


class CreateWorkitemRequestBodyTestCase(unittest.TestCase):
    def test_serializes_start_date_when_set(self) -> None:
        body = CreateWorkitemRequestBody(
            name="Task",
            parent_id=uuid4(),
            type="Bug",
            start_date="2026-07-31T00:00:00Z",
        )

        dumped = body.model_dump()

        self.assertIn("startDate", dumped)
        self.assertEqual("2026-07-31T00:00:00Z", dumped["startDate"])

    def test_omits_start_date_when_unset(self) -> None:
        body = CreateWorkitemRequestBody(name="Task", parent_id=uuid4(), type="Bug")

        dumped = body.model_dump()

        self.assertNotIn("startDate", dumped)

    def test_missing_required_field(self) -> None:
        with self.assertRaises(ValidationError):
            CreateWorkitemRequestBody(name="Task", type="Bug")


class WorkitemsCountModelTestCase(unittest.TestCase):
    def test_round_trip_from_swagger_shaped_payload(self) -> None:
        payload = {"count": 7}

        model = WorkitemsCountModel.model_validate(payload)

        self.assertEqual(7, model.count)
        self.assertEqual(payload, model.model_dump())

    def test_extra_field_forbidden(self) -> None:
        with self.assertRaises(ValidationError):
            WorkitemsCountModel.model_validate({"count": 1, "unexpected": "x"})

    def test_missing_required_field(self) -> None:
        with self.assertRaises(ValidationError):
            WorkitemsCountModel.model_validate({})


def _full_workitem_payload(**overrides) -> dict:
    payload = {
        "id": str(uuid4()),
        "key": "WS-1",
        "name": "Task",
        "type": {"id": str(uuid4()), "name": "Bug"},
        "workflow": {"id": str(uuid4()), "name": "Default"},
        "status": {
            "id": str(uuid4()),
            "name": "In Progress",
            "category": {"id": str(uuid4()), "name": "InProgress"},
        },
        "assignee": {"id": str(uuid4()), "displayName": "Grace Hopper", "username": "grace"},
        "author": {"id": str(uuid4()), "displayName": "Ada Lovelace", "username": "ada"},
        "changedBy": {"id": str(uuid4()), "displayName": "Ada Lovelace", "username": "ada"},
        "sprint": {"id": str(uuid4()), "name": "Sprint 1"},
        "folder": {"id": str(uuid4()), "name": "Backlog"},
        "parent": {"id": str(uuid4()), "nodeType": "Folder"},
        "attributes": [],
        "portfolios": [
            {
                "id": str(uuid4()),
                "name": "Roadmap",
                "elements": [{"id": str(uuid4()), "name": "Q3"}],
            }
        ],
        "workspace": {"id": str(uuid4()), "key": "WS", "name": "Workspace"},
    }
    payload.update(overrides)
    return payload


class WorkitemModelTestCase(unittest.TestCase):
    def test_round_trip_with_full_swagger_shaped_payload(self) -> None:
        wi = WorkitemModel.model_validate(_full_workitem_payload())

        self.assertIsInstance(wi.author, UserModel)
        self.assertIsInstance(wi.assignee, UserModel)
        self.assertIsInstance(wi.changed_by, UserModel)
        self.assertIsInstance(wi.folder, FolderThumbModel)
        self.assertIsInstance(wi.parent, TreeNodeThumbModel)
        self.assertEqual(TreeNodeType.Folder, wi.parent.node_type)
        self.assertEqual(1, len(wi.portfolios))
        self.assertIsInstance(wi.portfolios[0], WorkitemPortfolioModel)
        self.assertEqual(1, len(wi.portfolios[0].elements))

    def test_status_type_workflow_are_optional(self) -> None:
        payload = _full_workitem_payload()
        del payload["status"]
        del payload["type"]
        del payload["workflow"]

        wi = WorkitemModel.model_validate(payload)

        self.assertIsNone(wi.status)
        self.assertIsNone(wi.type)
        self.assertIsNone(wi.workflow)

    def test_require_returns_value_when_present(self) -> None:
        wi = WorkitemModel.model_validate(_full_workitem_payload())

        self.assertEqual("InProgress", wi.require.status.category.name)

    def test_require_raises_when_absent(self) -> None:
        payload = _full_workitem_payload()
        del payload["status"]
        wi = WorkitemModel.model_validate(payload)

        with self.assertRaises(MissingWorkitemFieldError):
            wi.require.status


if __name__ == "__main__":
    unittest.main()
