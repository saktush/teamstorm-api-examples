import unittest
from uuid import uuid4

from pydantic import ValidationError

from teamstorm.models.work_calendars import WorkCalendarModel, WorkCalendarModelList


def _payload() -> dict:
    return {
        "id": str(uuid4()),
        "name": "Business hours",
        "timeZone": "Europe/Moscow",
        "modifiedDate": "2026-07-01T09:00:00Z",
    }


class WorkCalendarsModelsTestCase(unittest.TestCase):
    def test_parse_work_calendar_model_and_list(self) -> None:
        model = WorkCalendarModel.model_validate(_payload())
        self.assertEqual("Business hours", model.name)
        self.assertEqual("Europe/Moscow", model.time_zone)
        self.assertEqual(2026, model.modified_date.year)

        model_list = WorkCalendarModelList.model_validate({"items": [_payload()]})
        self.assertEqual(1, len(model_list.items))

    def test_required_fields(self) -> None:
        for field in ("id", "name", "timeZone", "modifiedDate"):
            payload = _payload()
            del payload[field]
            with self.assertRaises(ValidationError, msg=field):
                WorkCalendarModel.model_validate(payload)

    def test_serializes_by_alias(self) -> None:
        dumped = WorkCalendarModel.model_validate(_payload()).model_dump()
        self.assertIn("timeZone", dumped)
        self.assertIn("modifiedDate", dumped)

    def test_extra_fields_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            WorkCalendarModel.model_validate({**_payload(), "extra": True})


if __name__ == "__main__":
    unittest.main()
