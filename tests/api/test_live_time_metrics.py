"""Opt-in live lifecycle test for the v4.24.0 workitem time metrics.

Runs against a real TeamStorm instance and WRITES data: it creates one throwaway workitem and
attaches, drives and disables one time metric on it. The public API cannot delete workitems, so
the workitem is left behind (named ``API smoke v4.24 <UTC timestamp>``) and cleanup is manual.

Enable with ``RUN_LIVE_SMOKE=1``. Configuration comes from the repo ``.env`` / environment:

- ``BASE_URL``, ``API_TOKEN``, ``WORKSPACE_KEY`` -- as in ``.env.template``.
- ``SMOKE_PARENT_ID`` -- UUID of a folder the throwaway workitem is created in.
- ``SMOKE_WORKITEM_TYPE`` -- workitem type name or key used for the throwaway workitem.
- ``SMOKE_ATTRIBUTES_JSON`` (optional) -- JSON list of create-attribute bodies, for workspaces
  that require attributes on create, e.g. ``[{"type": "UniSelect", "id": "<uuid>", "value": "x"}]``.
- ``SMOKE_DESCRIPTION`` (optional) -- description, for workspaces that require one.
- ``SMOKE_METRIC_TEMPLATE_ID`` (optional) -- template to enable; defaults to the first template.

The user needs the ``WorkspaceTimeMetrics`` permission and the workspace needs a metric template.
"""

import datetime as dt
import json
import os
import time
import unittest
from pathlib import Path
from uuid import UUID

from teamstorm.api import TeamStormAPI
from teamstorm.client import ApiError, TsClient
from teamstorm.models import (
    EnableWorkitemTimeMetricRequestBody,
    UpdateWorkitemTimeMetricSettingsRequestBody,
    WorkitemTimeMetricModel,
    WorkitemTimeMetricStatus,
)
from teamstorm.models.workitems import CreateWorkitemRequestBody

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv_fallback(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ.setdefault(key.strip(), value)


@unittest.skipUnless(
    os.getenv("RUN_LIVE_SMOKE") == "1",
    "Set RUN_LIVE_SMOKE=1 to enable the live time-metrics lifecycle test (it writes data)",
)
class TimeMetricsLiveLifecycleTestCase(unittest.TestCase):
    def setUp(self) -> None:
        _load_dotenv_fallback(_REPO_ROOT / ".env")
        self.base_url = os.getenv("BASE_URL")
        self.token = os.getenv("API_TOKEN")
        self.workspace = os.getenv("WORKSPACE_KEY")
        self.parent_id = os.getenv("SMOKE_PARENT_ID")
        self.workitem_type = os.getenv("SMOKE_WORKITEM_TYPE")
        missing = [
            name
            for name, value in (
                ("BASE_URL", self.base_url),
                ("API_TOKEN", self.token),
                ("WORKSPACE_KEY", self.workspace),
                ("SMOKE_PARENT_ID", self.parent_id),
                ("SMOKE_WORKITEM_TYPE", self.workitem_type),
            )
            if not value
        ]
        if missing:
            self.skipTest("Missing live-test settings: " + ", ".join(missing))

    def _api(self) -> TeamStormAPI:
        return TeamStormAPI(TsClient(base_url=self.base_url, token=self.token))

    def _state(self, api: TeamStormAPI, workitem_id: UUID, metric_id: UUID) -> WorkitemTimeMetricModel:
        return api.workitem_time_metrics.get(self.workspace, workitem_id=workitem_id, metric_id=metric_id)

    def test_metric_lifecycle(self) -> None:
        api = self._api()
        metrics = api.workitem_time_metrics
        ws = self.workspace

        templates = api.workitem_metric_templates.list(ws)
        self.assertTrue(templates, "the workspace has no workitem metric template")
        wanted = os.getenv("SMOKE_METRIC_TEMPLATE_ID")
        template = next((t for t in templates if wanted and str(t.id) == wanted), templates[0])

        body = CreateWorkitemRequestBody.model_validate(
            {
                "name": "API smoke v4.24 " + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
                "parentId": self.parent_id,
                "type": self.workitem_type,
                "description": os.getenv("SMOKE_DESCRIPTION") or "Throwaway workitem for the API wrapper live test",
                "attributes": json.loads(os.getenv("SMOKE_ATTRIBUTES_JSON") or "null"),
            }
        )
        workitem = api.workitems.create(ws, body)
        print(f"created throwaway workitem {workitem.key} ({workitem.id})")

        self.assertEqual([], metrics.list(ws, workitem_id=workitem.id))
        metric_id = metrics.enable(
            ws,
            workitem_id=workitem.id,
            body=EnableWorkitemTimeMetricRequestBody(template_id=template.id, limit_seconds=3600),
        ).id

        def status() -> WorkitemTimeMetricStatus:
            return self._state(api, workitem.id, metric_id).status

        def call(operation: str) -> None:
            getattr(metrics, operation)(ws, workitem_id=workitem.id, metric_id=metric_id)

        metric = self._state(api, workitem.id, metric_id)
        self.assertEqual(WorkitemTimeMetricStatus.NotStarted, metric.status)
        self.assertFalse(metric.is_ticking)
        self.assertEqual(3600, metric.limit_seconds)

        # A second enable for the same template conflicts (WorkitemTimeMetric.AlreadyExists).
        with self.assertRaises(ApiError) as already:
            metrics.enable(
                ws,
                workitem_id=workitem.id,
                body=EnableWorkitemTimeMetricRequestBody(template_id=template.id),
            )
        self.assertEqual(409, already.exception.status)

        call("start")
        self.assertEqual(WorkitemTimeMetricStatus.InProgress, status())
        self.assertTrue(self._state(api, workitem.id, metric_id).is_ticking)
        with self.assertRaises(ApiError) as repeat_start:  # a repeated start is a conflict
            call("start")
        self.assertEqual(409, repeat_start.exception.status)

        call("resume")  # resume on a running metric is a no-op (204)
        self.assertEqual(WorkitemTimeMetricStatus.InProgress, status())
        time.sleep(1)
        call("pause")
        self.assertEqual(WorkitemTimeMetricStatus.Paused, status())
        self.assertFalse(self._state(api, workitem.id, metric_id).is_ticking)
        call("pause")  # pause on a paused metric is a no-op (204)
        self.assertEqual(WorkitemTimeMetricStatus.Paused, status())
        call("resume")
        self.assertEqual(WorkitemTimeMetricStatus.InProgress, status())

        # PATCH semantics: fields left unset stay unchanged.
        metrics.update(
            ws,
            workitem_id=workitem.id,
            metric_id=metric_id,
            body=UpdateWorkitemTimeMetricSettingsRequestBody(limit_seconds=7200),
        )
        self.assertEqual(7200, self._state(api, workitem.id, metric_id).limit_seconds)

        call("stop")
        self.assertIn(
            status(),
            (WorkitemTimeMetricStatus.CompletedInTime, WorkitemTimeMetricStatus.CompletedBreached),
        )
        for operation in ("stop", "pause", "resume"):  # terminal state: transitions conflict
            with self.subTest(operation=operation), self.assertRaises(ApiError) as terminal:
                call(operation)
            self.assertEqual(409, terminal.exception.status)

        call("disable")
        self.assertEqual(WorkitemTimeMetricStatus.Disabled, status())
        with self.assertRaises(ApiError) as repeat_disable:
            call("disable")
        self.assertEqual(409, repeat_disable.exception.status)

        # Read the final state back through a brand-new client.
        fresh = self._api().workitem_time_metrics.list(ws, workitem_id=workitem.id)
        self.assertEqual([metric_id], [m.id for m in fresh])
        self.assertEqual(WorkitemTimeMetricStatus.Disabled, fresh[0].status)


if __name__ == "__main__":
    unittest.main()
