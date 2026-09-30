# teamstorm/api/time_metrics.py
from __future__ import annotations

import builtins
from uuid import UUID

from teamstorm.api._base import BaseAPI
from teamstorm.models.common import UUIDStr
from teamstorm.models.time_metrics import (
    EnableWorkitemTimeMetricRequestBody,
    EnableWorkitemTimeMetricResponseBody,
    UpdateWorkitemTimeMetricSettingsRequestBody,
    WorkitemTimeMetricModel,
    WorkitemTimeMetricModelList,
    WorkitemTimeMetricTemplateModel,
    WorkitemTimeMetricTemplateModelList,
)


class WorkitemTimeMetricsAPI(BaseAPI):
    """
    SLA/OLA-style time metrics attached to a single workitem.

    9 ops (WorkitemTimeMetrics tag): list, get, enable, update (PATCH),
    disable, start, pause, resume, stop. Metrics are created from a workspace
    template (see WorkitemTimeMetricTemplatesAPI). A metric is created
    NotStarted and must be started with start().

    Permissions (per the server source, not the spec): list() and get() need
    either the workspace WorkspaceTimeMetrics permission
    (Permission.WorkspaceTimeMetrics) or read access to the workitem; every
    write operation (enable, update, disable, start, pause, resume, stop) and
    the template list need WorkspaceTimeMetrics. Any call may answer 401/403.

    State transitions and 409: start() (NotStarted -> InProgress), stop()
    (-> CompletedInTime / CompletedBreached) and disable() (-> Disabled) answer
    HTTP 409 when the metric is already in the target state / the transition
    is not allowed; enable() answers 409 when the metric cannot be attached
    (e.g. already enabled for the workitem). The spec also lists 409 for
    pause() and resume(), so they are not unconditionally safe: the server
    integration tests (not the spec) show that repeating pause() on a paused
    metric, or resume() on a running one, is answered 204 (idempotent), while
    a transition the current state does not allow still yields 409. Do not
    blindly retry a 409.
    """

    def list(self, workspace_key: str, *, workitem_id: UUIDStr) -> builtins.list[WorkitemTimeMetricModel]:
        """
        List the time metrics attached to a workitem.

        :param workspace_key: workspace key or id.
        :param workitem_id: workitem key or UUID (path segment).
        :return: every WorkitemTimeMetricModel of the workitem.
        HTTP: GET /workspaces/{workspace}/workitems/{workitem}/workitem-time-metrics
        NOTE: not paginated -- the response is a plain {"items": [...]} envelope
        (no fromToken/maxItemsCount), so a single GET is used.
        """
        data = self.client.get(f"/workspaces/{workspace_key}/workitems/{workitem_id}/workitem-time-metrics")
        return WorkitemTimeMetricModelList.model_validate(data).items

    def get(self, workspace_key: str, *, workitem_id: UUIDStr, metric_id: UUID) -> WorkitemTimeMetricModel:
        """
        Get one time metric of a workitem.

        :param workspace_key: workspace key or id.
        :param workitem_id: workitem key or UUID (path segment).
        :param metric_id: time metric UUID (path segment).
        :return: the WorkitemTimeMetricModel.
        HTTP: GET /workspaces/{workspace}/workitems/{workitem}/workitem-time-metrics/{metricId}
        """
        data = self.client.get(f"/workspaces/{workspace_key}/workitems/{workitem_id}/workitem-time-metrics/{metric_id}")
        return WorkitemTimeMetricModel.model_validate(data)

    def enable(
        self,
        workspace_key: str,
        *,
        workitem_id: UUIDStr,
        body: EnableWorkitemTimeMetricRequestBody,
    ) -> EnableWorkitemTimeMetricResponseBody:
        """
        Attach a time metric to a workitem from a template.

        :param workspace_key: workspace key or id.
        :param workitem_id: workitem key or UUID (path segment).
        :param body: template id plus optional overrides (type, limit,
            approach threshold, work calendar, already-spent seconds).
        :return: EnableWorkitemTimeMetricResponseBody holding the new metric id.
        HTTP: POST /workspaces/{workspace}/workitems/{workitem}/workitem-time-metrics/enable
        NOTE: the metric is created in status NotStarted -- call start()
        separately. Answers 409 on conflict (e.g. the metric is already
        enabled); this is a non-idempotent create, so read back with list()
        before retrying an ambiguous failure.
        """
        data = self.client.post(
            f"/workspaces/{workspace_key}/workitems/{workitem_id}/workitem-time-metrics/enable",
            body.model_dump(),
        )
        return EnableWorkitemTimeMetricResponseBody.model_validate(data)

    def update(
        self,
        workspace_key: str,
        *,
        workitem_id: UUIDStr,
        metric_id: UUID,
        body: UpdateWorkitemTimeMetricSettingsRequestBody,
    ) -> None:
        """
        Change the settings of a time metric (partial update).

        :param workspace_key: workspace key or id.
        :param workitem_id: workitem key or UUID (path segment).
        :param metric_id: time metric UUID (path segment).
        :param body: only the fields to change.
        :return: None (the server answers 204 No Content); use get() to read
            the new state.
        HTTP: PATCH /workspaces/{workspace}/workitems/{workitem}/workitem-time-metrics/{metricId}
        NOTE: only fields explicitly set on *body* are sent
        (exclude_unset=True, exclude_none=False): omitted means unchanged.
        An explicit None is serialized as JSON null. null is forbidden for
        type, limit_seconds, approach_threshold_percent and work_calendar_id
        (the server answers HTTP 400); null for spent_seconds is accepted by
        the server, its effect is not documented.
        """
        payload = body.model_dump(mode="json", exclude_unset=True, exclude_none=False)
        self.client.patch(
            f"/workspaces/{workspace_key}/workitems/{workitem_id}/workitem-time-metrics/{metric_id}",
            payload,
        )
        return None

    def disable(self, workspace_key: str, *, workitem_id: UUIDStr, metric_id: UUID) -> None:
        """
        Disable a time metric: counting stops and the status becomes Disabled.

        :param workspace_key: workspace key or id.
        :param workitem_id: workitem key or UUID (path segment).
        :param metric_id: time metric UUID (path segment).
        :return: None (204 No Content).
        HTTP: POST /workspaces/{workspace}/workitems/{workitem}/workitem-time-metrics/{metricId}/disable
        NOTE: answers 409 if the metric is already disabled.
        """
        self.client.post(
            f"/workspaces/{workspace_key}/workitems/{workitem_id}/workitem-time-metrics/{metric_id}/disable"
        )
        return None

    def start(self, workspace_key: str, *, workitem_id: UUIDStr, metric_id: UUID) -> None:
        """
        Start counting time: the metric moves from NotStarted to InProgress.

        :param workspace_key: workspace key or id.
        :param workitem_id: workitem key or UUID (path segment).
        :param metric_id: time metric UUID (path segment).
        :return: None (204 No Content).
        HTTP: POST /workspaces/{workspace}/workitems/{workitem}/workitem-time-metrics/{metricId}/start
        NOTE: answers 409 if the metric has already been started.
        """
        self.client.post(f"/workspaces/{workspace_key}/workitems/{workitem_id}/workitem-time-metrics/{metric_id}/start")
        return None

    def pause(self, workspace_key: str, *, workitem_id: UUIDStr, metric_id: UUID) -> None:
        """
        Pause counting time: accumulated time is kept, status becomes Paused.

        :param workspace_key: workspace key or id.
        :param workitem_id: workitem key or UUID (path segment).
        :param metric_id: time metric UUID (path segment).
        :return: None (204 No Content).
        HTTP: POST /workspaces/{workspace}/workitems/{workitem}/workitem-time-metrics/{metricId}/pause
        NOTE: the spec lists 409 for this operation; server integration tests show that pausing an
        already paused metric is answered 204 (idempotent), other disallowed states give 409.
        """
        self.client.post(f"/workspaces/{workspace_key}/workitems/{workitem_id}/workitem-time-metrics/{metric_id}/pause")
        return None

    def resume(self, workspace_key: str, *, workitem_id: UUIDStr, metric_id: UUID) -> None:
        """
        Resume a paused metric: counting continues from the accumulated time.

        :param workspace_key: workspace key or id.
        :param workitem_id: workitem key or UUID (path segment).
        :param metric_id: time metric UUID (path segment).
        :return: None (204 No Content).
        HTTP: POST /workspaces/{workspace}/workitems/{workitem}/workitem-time-metrics/{metricId}/resume
        NOTE: the spec lists 409 for this operation; server integration tests show that resuming an
        already running metric is answered 204 (idempotent), other disallowed states give 409.
        """
        self.client.post(
            f"/workspaces/{workspace_key}/workitems/{workitem_id}/workitem-time-metrics/{metric_id}/resume"
        )
        return None

    def stop(self, workspace_key: str, *, workitem_id: UUIDStr, metric_id: UUID) -> None:
        """
        Finish a time metric: the status becomes CompletedInTime or
        CompletedBreached depending on whether the limit was exceeded.

        :param workspace_key: workspace key or id.
        :param workitem_id: workitem key or UUID (path segment).
        :param metric_id: time metric UUID (path segment).
        :return: None (204 No Content).
        HTTP: POST /workspaces/{workspace}/workitems/{workitem}/workitem-time-metrics/{metricId}/stop
        NOTE: answers 409 if the metric is already completed.
        """
        self.client.post(f"/workspaces/{workspace_key}/workitems/{workitem_id}/workitem-time-metrics/{metric_id}/stop")
        return None


class WorkitemTimeMetricTemplatesAPI(BaseAPI):
    """
    Workspace-level time metric templates (WorkitemTimeMetricTemplates tag).

    1 op: list. A template holds the default parameters of a metric and is
    referenced by template_id when enabling a metric on a workitem
    (WorkitemTimeMetricsAPI.enable). Read-only via the public API.
    """

    def list(self, workspace_key: str) -> builtins.list[WorkitemTimeMetricTemplateModel]:
        """
        List the time metric templates of a workspace.

        :param workspace_key: workspace key or id.
        :return: every WorkitemTimeMetricTemplateModel.
        HTTP: GET /workspaces/{workspace}/workitem-metric-templates
        NOTE: not paginated -- plain {"items": [...]} envelope, single GET.
        """
        data = self.client.get(f"/workspaces/{workspace_key}/workitem-metric-templates")
        return WorkitemTimeMetricTemplateModelList.model_validate(data).items
