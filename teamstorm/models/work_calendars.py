from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from .base import TsBaseModel


class WorkCalendarModel(TsBaseModel):
    """
    Swagger: WorkCalendarModel
    required: id, modifiedDate, name, timeZone

    A work calendar: the schedule against which time is counted in workitem
    time metrics.
    """

    id: UUID
    name: str
    time_zone: str = Field(alias="timeZone")
    modified_date: datetime = Field(alias="modifiedDate")


class WorkCalendarModelList(TsBaseModel):
    """
    Swagger: WorkCalendarModelList
    required: items

    Response envelope for GET /work-calendars (not paginated).
    """

    items: list[WorkCalendarModel]
