from __future__ import annotations

from pydantic import TypeAdapter

from ._base import BaseAPI
from teamstorm.models.work_calendars import WorkCalendarModel


class WorkCalendarsAPI(BaseAPI):
    """
    Work calendars: the schedules against which time is counted in workitem
    time metrics.

    1 op: list (WorkCalendars tag, global). Restricted to system
    administrators.
    """

    def list(self) -> list[WorkCalendarModel]:
        """
        List the work calendars.

        The endpoint is available to system administrators only; any other
        caller gets HTTP 403 (raised as ApiError).

        :return: every WorkCalendarModel.
        HTTP: GET /work-calendars
        NOTE: global (non-workspace-scoped), no filters, no pagination -- a
        `{"items": [...]}` envelope is returned; get_all() is used only as
        the client's generic list-fetch helper.
        """
        data = self.client.get_all("/work-calendars")
        return TypeAdapter(list[WorkCalendarModel]).validate_python(data)
