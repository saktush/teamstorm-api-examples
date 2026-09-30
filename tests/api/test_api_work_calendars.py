import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from pydantic import ValidationError

from teamstorm.api.work_calendars import WorkCalendarsAPI


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
        self.client.get_all.return_value = [_work_calendar_payload()]

        calendars = self.api.list()

        self.client.get_all.assert_called_once_with("/work-calendars")
        self.assertEqual(1, len(calendars))
        self.assertEqual("Business hours", calendars[0].name)
        self.assertEqual("Europe/Moscow", calendars[0].time_zone)

    def test_validation_error_on_bad_payload(self) -> None:
        self.client.get_all.return_value = [{"id": str(uuid4())}]
        with self.assertRaises(ValidationError):
            self.api.list()


if __name__ == "__main__":
    unittest.main()
