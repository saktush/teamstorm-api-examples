# teamstorm/models/time_metrics.py
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from .base import TsBaseModel
from .enums import WorkitemTimeMetricStatus, WorkitemTimeMetricTemplateType


class WorkitemTimeMetricTemplateModel(TsBaseModel):
    """
    Swagger: WorkitemTimeMetricTemplateModel
    required: id, name, type

    A workspace-level time metric template: holds the default parameters of a
    metric and is referenced by `EnableWorkitemTimeMetricRequestBody.templateId`.
    """

    id: UUID
    name: str
    type: WorkitemTimeMetricTemplateType


class WorkitemTimeMetricTemplateModelList(TsBaseModel):
    """
    Swagger: WorkitemTimeMetricTemplateModelList
    required: items

    Plain (non-paginated) envelope: there is no fromToken/nextToken.
    """

    items: list[WorkitemTimeMetricTemplateModel]


class WorkitemTimeMetricModel(TsBaseModel):
    """
    Swagger: WorkitemTimeMetricModel
    required: approachAt, approachThresholdPercent, breachAt, elapsedSeconds,
    id, isTicking, limitSeconds, name, status, templateId, type,
    workCalendarId, workitemId

    NOTE: approachAt and breachAt are listed as *required* and are also
    *nullable* (date-time) -- modeled as `datetime | None = None`, following the
    repo's precedent for required-but-nullable fields (e.g.
    TimeTrackingEntryModel.deleted_at). The other required fields are not
    nullable in the spec and are required here. limitSeconds and
    approachThresholdPercent are int32, elapsedSeconds is int64.
    """

    id: UUID
    workitem_id: UUID = Field(alias="workitemId")
    template_id: UUID = Field(alias="templateId")
    name: str
    type: WorkitemTimeMetricTemplateType
    limit_seconds: int = Field(alias="limitSeconds")
    approach_threshold_percent: int = Field(alias="approachThresholdPercent")
    work_calendar_id: UUID = Field(alias="workCalendarId")
    status: WorkitemTimeMetricStatus
    elapsed_seconds: int = Field(alias="elapsedSeconds")
    is_ticking: bool = Field(alias="isTicking")
    approach_at: datetime | None = Field(default=None, alias="approachAt")
    breach_at: datetime | None = Field(default=None, alias="breachAt")


class WorkitemTimeMetricModelList(TsBaseModel):
    """
    Swagger: WorkitemTimeMetricModelList
    required: items

    Plain (non-paginated) envelope: there is no fromToken/nextToken.
    """

    items: list[WorkitemTimeMetricModel]


class EnableWorkitemTimeMetricRequestBody(TsBaseModel):
    """
    Swagger: EnableWorkitemTimeMetricRequestBody
    required: templateId

    Every optional field (nullable in the spec) overrides the corresponding
    template value when supplied; omit it to keep the template default. The
    default `model_dump()` (exclude_none) is correct for this POST body.
    limitSeconds/approachThresholdPercent are int32; initialSpentSeconds is
    int64 (time already spent when the metric is attached).
    """

    template_id: UUID = Field(alias="templateId")
    type: WorkitemTimeMetricTemplateType | None = None
    limit_seconds: int | None = Field(default=None, alias="limitSeconds")
    approach_threshold_percent: int | None = Field(default=None, alias="approachThresholdPercent")
    work_calendar_id: UUID | None = Field(default=None, alias="workCalendarId")
    initial_spent_seconds: int | None = Field(default=None, alias="initialSpentSeconds")


class EnableWorkitemTimeMetricResponseBody(TsBaseModel):
    """
    Swagger: EnableWorkitemTimeMetricResponseBody
    required: id
    """

    id: UUID


class UpdateWorkitemTimeMetricSettingsRequestBody(TsBaseModel):
    """
    Swagger: UpdateWorkitemTimeMetricSettingsRequestBody
    required: (none)

    PATCH body: dump with `exclude_unset=True, exclude_none=False` (see
    WorkitemTimeMetricsAPI.update). All fields are nullable in the schema, but
    per the operation description only `spentSeconds` accepts an explicit
    `null`; sending null for type, limitSeconds, approachThresholdPercent or
    workCalendarId is rejected by the server with HTTP 400. limitSeconds and
    approachThresholdPercent are int32; spentSeconds is int64.
    """

    type: WorkitemTimeMetricTemplateType | None = None
    limit_seconds: int | None = Field(default=None, alias="limitSeconds")
    approach_threshold_percent: int | None = Field(default=None, alias="approachThresholdPercent")
    work_calendar_id: UUID | None = Field(default=None, alias="workCalendarId")
    spent_seconds: int | None = Field(default=None, alias="spentSeconds")


__all__ = [
    "EnableWorkitemTimeMetricRequestBody",
    "EnableWorkitemTimeMetricResponseBody",
    "UpdateWorkitemTimeMetricSettingsRequestBody",
    "WorkitemTimeMetricModel",
    "WorkitemTimeMetricModelList",
    "WorkitemTimeMetricTemplateModel",
    "WorkitemTimeMetricTemplateModelList",
]
