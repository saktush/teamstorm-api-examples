import unittest
from uuid import uuid4

from pydantic import ValidationError

from teamstorm.models.links import (
    CreateWorkitemLinkRequestBody,
    LinkTypeModel,
    LinkTypeModelList,
    WorkitemLinkModel,
)


def _workitem_payload() -> dict:
    return {
        "id": str(uuid4()),
        "key": "WS-1",
        "name": "Task",
        "author": {"id": str(uuid4()), "displayName": "Ada Lovelace", "username": "ada"},
        "folder": {"id": str(uuid4()), "name": "Backlog"},
        "parent": {"id": str(uuid4()), "nodeType": "Folder"},
        "attributes": [],
        "portfolios": [],
        "workspace": {
            "id": str(uuid4()),
            "key": "WS",
            "name": "Workspace",
        },
    }


class LinkTypeModelTestCase(unittest.TestCase):
    def test_round_trip_from_swagger_shaped_payload(self) -> None:
        payload = {"id": str(uuid4()), "name": "Relates to", "key": "RelatesTo"}

        model = LinkTypeModel.model_validate(payload)

        self.assertEqual("Relates to", model.name)
        self.assertEqual("RelatesTo", model.key)
        self.assertEqual(payload, model.model_dump())

    def test_key_is_nullable(self) -> None:
        payload = {"id": str(uuid4()), "name": "Blocks", "key": None}

        model = LinkTypeModel.model_validate(payload)

        self.assertIsNone(model.key)

    def test_extra_field_forbidden(self) -> None:
        with self.assertRaises(ValidationError):
            LinkTypeModel.model_validate({"id": str(uuid4()), "name": "Blocks", "unexpected": "x"})

    def test_missing_required_field(self) -> None:
        with self.assertRaises(ValidationError):
            LinkTypeModel.model_validate({"id": str(uuid4())})


class LinkTypeModelListTestCase(unittest.TestCase):
    def test_round_trip_items_envelope(self) -> None:
        payload = {
            "items": [
                {"id": str(uuid4()), "name": "Relates to", "key": "RelatesTo"},
                {"id": str(uuid4()), "name": "Blocks", "key": None},
            ]
        }

        model = LinkTypeModelList.model_validate(payload)

        self.assertEqual(2, len(model.items))
        self.assertEqual("Relates to", model.items[0].name)


class WorkitemLinkModelTestCase(unittest.TestCase):
    def test_round_trip_from_swagger_shaped_payload(self) -> None:
        link_type_id = str(uuid4())
        payload = {
            "id": str(uuid4()),
            "type": {"id": link_type_id, "name": "Relates to", "key": "RelatesTo"},
            "linkedWorkitem": _workitem_payload(),
        }

        model = WorkitemLinkModel.model_validate(payload)

        self.assertEqual("Relates to", model.type.name)
        self.assertEqual("WS-1", model.linked_workitem.key)
        dumped = model.model_dump()
        self.assertIn("linkedWorkitem", dumped)
        self.assertNotIn("linked_workitem", dumped)

    def test_extra_field_forbidden(self) -> None:
        payload = {
            "id": str(uuid4()),
            "type": {"id": str(uuid4()), "name": "Relates to"},
            "linkedWorkitem": _workitem_payload(),
            "unexpected": "x",
        }
        with self.assertRaises(ValidationError):
            WorkitemLinkModel.model_validate(payload)

    def test_missing_required_field(self) -> None:
        with self.assertRaises(ValidationError):
            WorkitemLinkModel.model_validate({"id": str(uuid4())})


class CreateWorkitemLinkRequestBodyTestCase(unittest.TestCase):
    def test_dump_uses_camel_case_alias(self) -> None:
        body = CreateWorkitemLinkRequestBody(type="RelatesTo", linked_workitem="WS-2", linked_workspace="WS")

        dumped = body.model_dump(mode="json", exclude_none=True)

        self.assertEqual({"type": "RelatesTo", "linkedWorkitem": "WS-2", "linkedWorkspace": "WS"}, dumped)

    def test_construct_by_alias(self) -> None:
        body = CreateWorkitemLinkRequestBody.model_validate(
            {"type": "Blocks", "linkedWorkitem": "WS-3", "linkedWorkspace": "OTHER"}
        )

        self.assertEqual("Blocks", body.type)
        self.assertEqual("WS-3", body.linked_workitem)
        self.assertEqual("OTHER", body.linked_workspace)

    def test_linked_workspace_round_trips_by_alias(self) -> None:
        body = CreateWorkitemLinkRequestBody(type="Blocks", linked_workitem="WS-3", linked_workspace="OTHER")

        dumped = body.model_dump(by_alias=True)

        self.assertEqual({"type": "Blocks", "linkedWorkitem": "WS-3", "linkedWorkspace": "OTHER"}, dumped)

    def test_missing_required_field(self) -> None:
        with self.assertRaises(ValidationError):
            CreateWorkitemLinkRequestBody.model_validate({"type": "Blocks"})

    def test_missing_linked_workspace_raises(self) -> None:
        with self.assertRaises(ValidationError):
            CreateWorkitemLinkRequestBody.model_validate({"type": "Blocks", "linkedWorkitem": "WS-3"})

    def test_extra_field_forbidden(self) -> None:
        with self.assertRaises(ValidationError):
            CreateWorkitemLinkRequestBody.model_validate(
                {
                    "type": "Blocks",
                    "linkedWorkitem": "WS-3",
                    "linkedWorkspace": "WS",
                    "unexpected": "x",
                }
            )


if __name__ == "__main__":
    unittest.main()
