import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from pydantic import ValidationError

from teamstorm.client import ApiError
from teamstorm.api.time_metrics import WorkitemTimeMetricsAPI, WorkitemTimeMetricTemplatesAPI
from teamstorm.models.enums import WorkitemTimeMetricStatus, WorkitemTimeMetricTemplateType
from teamstorm.models.time_metrics import (
    EnableWorkitemTimeMetricRequestBody,
    EnableWorkitemTimeMetricResponseBody,
    UpdateWorkitemTimeMetricSettingsRequestBody,
    WorkitemTimeMetricModel,
    WorkitemTimeMetricTemplateModel,
)


def _metric_payload(**overrides) -> dict:
    payload = {
        "id": str(uuid4()),
        "workitemId": str(uuid4()),
        "templateId": str(uuid4()),
        "name": "Resolution time",
        "type": "Sla",
        "limitSeconds": 28800,
        "approachThresholdPercent": 80,
        "workCalendarId": str(uuid4()),
        "status": "NotStarted",
        "elapsedSeconds": 0,
        "isTicking": False,
        "approachAt": None,
        "breachAt": None,
    }
    payload.update(overrides)
    return payload


_BASE = "/workspaces/WS/workitems/WS-1/workitem-time-metrics"


class WorkitemTimeMetricsAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = WorkitemTimeMetricsAPI(self.client)
        self.metric_id = uuid4()

    def test_list_uses_single_get_and_unwraps_items(self) -> None:
        self.client.get.return_value = {"items": [_metric_payload(), _metric_payload(status="InProgress")]}

        result = self.api.list("WS", workitem_id="WS-1")

        self.client.get.assert_called_once_with(_BASE)
        self.client.get_all.assert_not_called()
        self.assertEqual(2, len(result))
        self.assertIsInstance(result[0], WorkitemTimeMetricModel)
        self.assertEqual(WorkitemTimeMetricStatus.InProgress, result[1].status)

    def test_get(self) -> None:
        self.client.get.return_value = _metric_payload(id=str(self.metric_id))

        result = self.api.get("WS", workitem_id="WS-1", metric_id=self.metric_id)

        self.client.get.assert_called_once_with(f"{_BASE}/{self.metric_id}")
        self.assertEqual(self.metric_id, result.id)

    def test_enable_posts_body_without_none_fields(self) -> None:
        template_id = uuid4()
        new_id = uuid4()
        self.client.post.return_value = {"id": str(new_id)}
        body = EnableWorkitemTimeMetricRequestBody(
            template_id=template_id,
            type=WorkitemTimeMetricTemplateType.Ola,
            initial_spent_seconds=120,
        )

        result = self.api.enable("WS", workitem_id="WS-1", body=body)

        self.client.post.assert_called_once_with(
            f"{_BASE}/enable",
            {"templateId": str(template_id), "type": "Ola", "initialSpentSeconds": 120},
        )
        self.assertIsInstance(result, EnableWorkitemTimeMetricResponseBody)
        self.assertEqual(new_id, result.id)

    def test_update_sends_only_set_fields(self) -> None:
        self.client.patch.return_value = None
        body = UpdateWorkitemTimeMetricSettingsRequestBody(limit_seconds=3600)

        result = self.api.update("WS", workitem_id="WS-1", metric_id=self.metric_id, body=body)

        self.assertIsNone(result)
        self.client.patch.assert_called_once_with(f"{_BASE}/{self.metric_id}", {"limitSeconds": 3600})

    def test_update_explicit_null_spent_seconds_is_sent(self) -> None:
        self.client.patch.return_value = None
        body = UpdateWorkitemTimeMetricSettingsRequestBody(spent_seconds=None)

        self.api.update("WS", workitem_id="WS-1", metric_id=self.metric_id, body=body)

        self.client.patch.assert_called_once_with(f"{_BASE}/{self.metric_id}", {"spentSeconds": None})

    def test_update_empty_body_sends_empty_object(self) -> None:
        self.client.patch.return_value = None

        self.api.update(
            "WS",
            workitem_id="WS-1",
            metric_id=self.metric_id,
            body=UpdateWorkitemTimeMetricSettingsRequestBody(),
        )

        self.client.patch.assert_called_once_with(f"{_BASE}/{self.metric_id}", {})

    def test_update_body_rejects_unknown_field(self) -> None:
        with self.assertRaises(ValidationError):
            UpdateWorkitemTimeMetricSettingsRequestBody.model_validate({"bogus": 1})

    def test_state_operations_post_without_body_and_return_none(self) -> None:
        for name in ("disable", "start", "pause", "resume", "stop"):
            with self.subTest(operation=name):
                self.client.post.reset_mock()
                self.client.post.return_value = None

                result = getattr(self.api, name)("WS", workitem_id="WS-1", metric_id=self.metric_id)

                self.assertIsNone(result)
                self.client.post.assert_called_once_with(f"{_BASE}/{self.metric_id}/{name}")

    def test_get_validation_error_on_bad_payload(self) -> None:
        self.client.get.return_value = {"id": str(self.metric_id)}
        with self.assertRaises(ValidationError):
            self.api.get("WS", workitem_id="WS-1", metric_id=self.metric_id)

    def test_list_validation_error_on_bad_payload(self) -> None:
        self.client.get.return_value = {"items": [{"id": str(uuid4())}]}
        with self.assertRaises(ValidationError):
            self.api.list("WS", workitem_id="WS-1")

    def test_start_conflict_propagates_without_retry(self) -> None:
        self.client.post.side_effect = ApiError("conflict", status=409)

        with self.assertRaises(ApiError) as ctx:
            self.api.start("WS", workitem_id="WS-1", metric_id=self.metric_id)

        self.assertEqual(409, ctx.exception.status)
        self.client.post.assert_called_once_with(f"{_BASE}/{self.metric_id}/start")

    def test_enable_conflict_propagates_without_retry(self) -> None:
        self.client.post.side_effect = ApiError("conflict", status=409)
        body = EnableWorkitemTimeMetricRequestBody(template_id=uuid4())

        with self.assertRaises(ApiError) as ctx:
            self.api.enable("WS", workitem_id="WS-1", body=body)

        self.assertEqual(409, ctx.exception.status)
        self.assertEqual(1, self.client.post.call_count)

    def test_workitem_id_is_keyword_only(self) -> None:
        with self.assertRaises(TypeError):
            self.api.list("WS", "WS-1")  # type: ignore[misc]


class WorkitemTimeMetricTemplatesAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = WorkitemTimeMetricTemplatesAPI(self.client)

    def test_list(self) -> None:
        self.client.get.return_value = {
            "items": [
                {"id": str(uuid4()), "name": "Default SLA", "type": "Sla"},
                {"id": str(uuid4()), "name": "Internal", "type": "Custom"},
            ]
        }

        result = self.api.list("WS")

        self.client.get.assert_called_once_with("/workspaces/WS/workitem-metric-templates")
        self.assertEqual(2, len(result))
        self.assertIsInstance(result[0], WorkitemTimeMetricTemplateModel)
        self.assertEqual(WorkitemTimeMetricTemplateType.Custom, result[1].type)


if __name__ == "__main__":
    unittest.main()
