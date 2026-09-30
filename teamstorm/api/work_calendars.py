from __future__ import annotations

from ._base import BaseAPI
from teamstorm.models.work_calendars import WorkCalendarModel, WorkCalendarModelList


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
        plain `{"items": [...]}` envelope is returned, so a single GET is used
        (get_all() would send an undeclared maxItemsCount parameter).
        """
        data = self.client.get("/work-calendars")
        return WorkCalendarModelList.model_validate(data).items
