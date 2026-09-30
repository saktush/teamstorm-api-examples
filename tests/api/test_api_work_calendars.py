import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from pydantic import ValidationError

from teamstorm.api.work_calendars import WorkCalendarsAPI
from teamstorm.client import ApiError


def _work_calendar_payload() -> dict:
    return {
        "id": str(uuid4()),
        "name": "Business hours",
        "timeZone": "Europe/Moscow",
        "modifiedDate": "2026-07-01T09:00:00Z",
    }


class WorkCalendarsAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = WorkCalendarsAPI(self.client)

    def test_list(self) -> None:
        self.client.get.return_value = {"items": [_work_calendar_payload()]}

        calendars = self.api.list()

        self.client.get.assert_called_once_with("/work-calendars")
        self.client.get_all.assert_not_called()
        self.assertEqual(1, len(calendars))
        self.assertEqual("Business hours", calendars[0].name)
        self.assertEqual("Europe/Moscow", calendars[0].time_zone)

    def test_validation_error_on_bad_payload(self) -> None:
        self.client.get.return_value = {"items": [{"id": str(uuid4())}]}
        with self.assertRaises(ValidationError):
            self.api.list()

    def test_forbidden_propagates_without_retry(self) -> None:
        self.client.get.side_effect = ApiError("forbidden", status=403)

        with self.assertRaises(ApiError) as ctx:
            self.api.list()

        self.assertEqual(403, ctx.exception.status)
        self.client.get.assert_called_once_with("/work-calendars")


if __name__ == "__main__":
    unittest.main()
