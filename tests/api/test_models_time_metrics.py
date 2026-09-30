import unittest
from datetime import datetime
from uuid import UUID, uuid4

from pydantic import ValidationError

from teamstorm.models.enums import WorkitemTimeMetricStatus, WorkitemTimeMetricTemplateType
from teamstorm.models.time_metrics import (
    EnableWorkitemTimeMetricRequestBody,
    EnableWorkitemTimeMetricResponseBody,
    UpdateWorkitemTimeMetricSettingsRequestBody,
    WorkitemTimeMetricModel,
    WorkitemTimeMetricModelList,
    WorkitemTimeMetricTemplateModel,
    WorkitemTimeMetricTemplateModelList,
)


def _metric_payload(**overrides) -> dict:
    payload = {
        "id": str(uuid4()),
        "workitemId": str(uuid4()),
        "templateId": str(uuid4()),
        "name": "First response",
        "type": "Sla",
        "limitSeconds": 14400,
        "approachThresholdPercent": 80,
        "workCalendarId": str(uuid4()),
        "status": "InProgress",
        "elapsedSeconds": 3600,
        "isTicking": True,
        "approachAt": "2026-09-30T12:00:00Z",
        "breachAt": "2026-09-30T14:00:00Z",
    }
    payload.update(overrides)
    return payload


class TimeMetricsModelsTestCase(unittest.TestCase):
    def test_parse_template_model_and_list(self) -> None:
        payload = {"id": str(uuid4()), "name": "Default SLA", "type": "Ola"}
        model = WorkitemTimeMetricTemplateModel.model_validate(payload)
        self.assertEqual("Default SLA", model.name)
        self.assertEqual(WorkitemTimeMetricTemplateType.Ola, model.type)

        model_list = WorkitemTimeMetricTemplateModelList.model_validate({"items": [payload]})
        self.assertEqual(1, len(model_list.items))

    def test_template_model_rejects_unknown_field_and_bad_type(self) -> None:
        payload = {"id": str(uuid4()), "name": "T", "type": "Sla"}
        with self.assertRaises(ValidationError):
            WorkitemTimeMetricTemplateModel.model_validate({**payload, "extra": 1})
        with self.assertRaises(ValidationError):
            WorkitemTimeMetricTemplateModel.model_validate({**payload, "type": "Unknown"})
        with self.assertRaises(ValidationError):
            WorkitemTimeMetricTemplateModel.model_validate({"id": str(uuid4()), "name": "T"})

    def test_parse_metric_round_trip(self) -> None:
        payload = _metric_payload()
        model = WorkitemTimeMetricModel.model_validate(payload)

        self.assertEqual(UUID(payload["id"]), model.id)
        self.assertEqual(UUID(payload["workitemId"]), model.workitem_id)
        self.assertEqual(WorkitemTimeMetricStatus.InProgress, model.status)
        self.assertEqual(WorkitemTimeMetricTemplateType.Sla, model.type)
        self.assertEqual(3600, model.elapsed_seconds)
        self.assertTrue(model.is_ticking)
        self.assertIsInstance(model.approach_at, datetime)
        self.assertEqual(payload["limitSeconds"], model.model_dump()["limitSeconds"])
        self.assertEqual(model, WorkitemTimeMetricModel.model_validate(model.model_dump()))

    def test_metric_nullable_dates_and_required_fields(self) -> None:
        model = WorkitemTimeMetricModel.model_validate(
            _metric_payload(status="NotStarted", isTicking=False, approachAt=None, breachAt=None)
        )
        self.assertIsNone(model.approach_at)
        self.assertIsNone(model.breach_at)
        self.assertFalse(model.is_ticking)

        payload = _metric_payload()
        del payload["elapsedSeconds"]
        with self.assertRaises(ValidationError):
            WorkitemTimeMetricModel.model_validate(payload)

    def test_metric_rejects_unknown_field_and_bad_status(self) -> None:
        with self.assertRaises(ValidationError):
            WorkitemTimeMetricModel.model_validate(_metric_payload(unexpected="x"))
        with self.assertRaises(ValidationError):
            WorkitemTimeMetricModel.model_validate(_metric_payload(status="Running"))

    def test_parse_metric_list(self) -> None:
        model_list = WorkitemTimeMetricModelList.model_validate(
            {"items": [_metric_payload(), _metric_payload(status="Disabled", isTicking=False)]}
        )
        self.assertEqual(2, len(model_list.items))
        self.assertEqual(WorkitemTimeMetricStatus.Disabled, model_list.items[1].status)

    def test_enable_request_body_requires_template_id_and_omits_none(self) -> None:
        template_id = uuid4()
        body = EnableWorkitemTimeMetricRequestBody(template_id=template_id)
        self.assertEqual({"templateId": str(template_id)}, body.model_dump())

        full = EnableWorkitemTimeMetricRequestBody(
            template_id=template_id,
            type=WorkitemTimeMetricTemplateType.Custom,
            limit_seconds=7200,
            approach_threshold_percent=75,
            work_calendar_id=uuid4(),
            initial_spent_seconds=10_000_000_000,
        )
        dumped = full.model_dump()
        self.assertEqual("Custom", dumped["type"])
        self.assertEqual(7200, dumped["limitSeconds"])
        self.assertEqual(75, dumped["approachThresholdPercent"])
        self.assertEqual(10_000_000_000, dumped["initialSpentSeconds"])

        with self.assertRaises(ValidationError):
            EnableWorkitemTimeMetricRequestBody.model_validate({})
        with self.assertRaises(ValidationError):
            EnableWorkitemTimeMetricRequestBody.model_validate({"templateId": str(template_id), "foo": 1})

    def test_enable_response_body(self) -> None:
        metric_id = uuid4()
        model = EnableWorkitemTimeMetricResponseBody.model_validate({"id": str(metric_id)})
        self.assertEqual(metric_id, model.id)
        with self.assertRaises(ValidationError):
            EnableWorkitemTimeMetricResponseBody.model_validate({})

    def test_update_body_distinguishes_unset_from_explicit_null(self) -> None:
        empty = UpdateWorkitemTimeMetricSettingsRequestBody()
        self.assertEqual({}, empty.model_dump(exclude_unset=True, exclude_none=False))

        body = UpdateWorkitemTimeMetricSettingsRequestBody(limit_seconds=600, spent_seconds=None)
        self.assertEqual(
            {"limitSeconds": 600, "spentSeconds": None},
            body.model_dump(exclude_unset=True, exclude_none=False),
        )
        self.assertEqual({"limitSeconds": 600}, body.model_dump())

    def test_update_body_rejects_unknown_field(self) -> None:
        with self.assertRaises(ValidationError):
            UpdateWorkitemTimeMetricSettingsRequestBody.model_validate({"initialSpentSeconds": 1})


if __name__ == "__main__":
    unittest.main()
