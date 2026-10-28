"""Offline checks for the live e2e engine and scenario: no network, runs in every ``pytest``."""

from __future__ import annotations

import datetime as dt
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from uuid import UUID, uuid4

import requests

from e2e.runner import (
    EXCLUDED,
    OPERATIONS,
    Ctx,
    RecordingClient,
    Step,
    is_stale_e2e_workspace,
    match_operation,
    op_statuses,
    prefix_time,
    run_marker,
    run_prefix,
    run_steps,
    write_report,
)
from e2e.scenario import build_steps
from teamstorm.api import TeamStormAPI
from teamstorm.client import RetryConfig
from teamstorm.models.workspaces import WorkspaceModel


def _response(status: int, payload: object) -> requests.Response:
    resp = requests.Response()
    resp.status_code = status
    resp._content = json.dumps(payload).encode()
    return resp


def _ctx() -> Ctx:
    client = RecordingClient("https://example.test", "t", retry=RetryConfig(max_attempts=1))
    return Ctx(TeamStormAPI(client), client, "E2E000000", dt.datetime.now(dt.timezone.utc), {})


class OperationCatalogTestCase(unittest.TestCase):
    def test_match_prefers_literal_segments(self) -> None:
        self.assertEqual("GetWorkitemsCount", match_operation("GET", "/workspaces/WS/workitems/count"))
        self.assertEqual("GetWorkitemById", match_operation("GET", "/workspaces/WS/workitems/abc"))
        self.assertEqual("GetTimeTrackingEntries", match_operation("GET", "/workspaces/time-tracking-entries"))
        self.assertEqual("GetWorkspace", match_operation("GET", "/workspaces/WS"))
        self.assertIsNone(match_operation("GET", "/nowhere"))

    def test_match_all_manifest_templates_roundtrip(self) -> None:
        for key, row in OPERATIONS.items():
            path = re.sub(r"\{[^/]+?\}", "x1", row.path)
            with self.subTest(key=key):
                self.assertEqual(key, match_operation(row.http_method, path))

    def test_recording_client_records_success_and_api_error(self) -> None:
        ctx = _ctx()
        ctx.client.current_step = "s"
        with mock.patch.object(ctx.client.session, "request", return_value=_response(200, {"providers": []})):
            ctx.api.providers.list()
        with mock.patch.object(ctx.client.session, "request", return_value=_response(404, {"m": "no"})):
            with self.assertRaises(Exception):
                ctx.api.workspaces.get("WS")
        first, second = ctx.client.calls
        self.assertEqual(("GetProviders", 200, None, "s"), (first.op, first.status, first.error, first.step))
        self.assertEqual(("GetWorkspace", 404), (second.op, second.status))
        self.assertIn("404", second.error or "")


class StepEngineTestCase(unittest.TestCase):
    def test_failed_step_skips_dependents_not_cleanup(self) -> None:
        ctx = _ctx()
        ran: list[str] = []

        def boom(c: Ctx) -> None:
            raise RuntimeError("x")

        steps = [
            Step("make", ("CreateFolder",), boom),
            Step("use", ("GetFolder",), lambda c: ran.append("use"), needs=("folder",)),
            Step("drop", ("DeleteFolder",), lambda c: ran.append("drop"), cleanup=True),
        ]
        results = run_steps(ctx, steps)
        self.assertEqual(["FAIL", "SKIP", "PASS"], [r.status for r in results])
        self.assertEqual(["drop"], ran)
        statuses = op_statuses(steps, results, ctx.client.calls)
        self.assertEqual("SKIP", statuses["GetFolder"].status)
        self.assertEqual(
            ("SKIP", "make: RuntimeError: x"), (statuses["CreateFolder"].status, statuses["CreateFolder"].detail)
        )

    def test_validation_error_marks_last_call_failed(self) -> None:
        ctx = _ctx()
        steps = [Step("read", ("GetProviders",), lambda c: c.api.providers.list())]
        with mock.patch.object(ctx.client.session, "request", return_value=_response(200, {"providers": [{"bad": 1}]})):
            results = run_steps(ctx, steps)
        self.assertEqual("FAIL", results[0].status)
        self.assertEqual("FAIL", op_statuses(steps, results, ctx.client.calls)["GetProviders"].status)

    def test_any_failed_call_fails_op(self) -> None:
        ctx = _ctx()
        responses = [_response(200, {"providers": []}), _response(500, {})]

        def twice(c: Ctx) -> None:
            c.api.providers.list()
            c.api.providers.list()

        steps = [Step("twice", ("GetProviders",), twice)]
        with mock.patch.object(ctx.client.session, "request", side_effect=responses):
            results = run_steps(ctx, steps)
        self.assertEqual("FAIL", op_statuses(steps, results, ctx.client.calls)["GetProviders"].status)

    def test_soft_failure_continues_step_and_fails_it(self) -> None:
        ctx = _ctx()
        responses = [_response(500, {}), _response(200, {"providers": []})]

        def step(c: Ctx) -> None:
            c.soft(c.api.workspaces.get, "WS")
            c.api.providers.list()

        steps = [Step("soft", ("GetWorkspace", "GetProviders"), step)]
        with mock.patch.object(ctx.client.session, "request", side_effect=responses):
            results = run_steps(ctx, steps)
        statuses = op_statuses(steps, results, ctx.client.calls)
        self.assertEqual("FAIL", results[0].status)
        self.assertEqual(("FAIL", "PASS"), (statuses["GetWorkspace"].status, statuses["GetProviders"].status))

    def test_skip_op_and_uncalled_op(self) -> None:
        ctx = _ctx()
        steps = [Step("s", ("GetProviders", "GetWorkCalendars"), lambda c: c.skip_op("GetProviders", "no data"))]
        statuses = op_statuses(steps, run_steps(ctx, steps), ctx.client.calls, ctx.op_skips)
        self.assertEqual("SKIP", statuses["GetProviders"].status)
        self.assertEqual("FAIL", statuses["GetWorkCalendars"].status)
        self.assertEqual("EXCLUDED", statuses["BlockUser"].status)


class SweepPredicateTestCase(unittest.TestCase):
    owner = uuid4()
    now = dt.datetime(2026, 10, 28, 12, 0, tzinfo=dt.timezone.utc)

    def _key(self, hours_ago: float, suffix: str = "A") -> str:
        return run_prefix(self.now - dt.timedelta(hours=hours_ago)) + suffix

    def _ws(self, key: str, *, author: UUID | None = None, description: str | None = None) -> WorkspaceModel:
        return WorkspaceModel.model_validate(
            {
                "id": str(uuid4()),
                "key": key,
                "name": key,
                "description": run_marker(key[:-1]) if description is None else description,
                "author": {"id": str(author or self.owner), "displayName": "o", "username": "o"},
            }
        )

    def _stale(self, ws: WorkspaceModel) -> bool:
        return is_stale_e2e_workspace(ws, owner_id=self.owner, now=self.now, current_prefix=run_prefix(self.now))

    def test_prefix_fits_key_rules_and_roundtrips(self) -> None:
        prefix = run_prefix(self.now)
        self.assertRegex(prefix + "B", r"^[A-Z][A-Z0-9]{0,9}$")
        self.assertEqual(self.now, prefix_time(prefix[3:]))
        self.assertEqual(9, len(run_prefix(dt.datetime(2038, 10, 1, tzinfo=dt.timezone.utc))))

    def test_stale_predicate_accepts_old_marked_own(self) -> None:
        self.assertTrue(self._stale(self._ws(self._key(30))))
        self.assertTrue(self._stale(self._ws(self._key(7, "B"))))

    def test_stale_predicate_rejects(self) -> None:
        old = self._key(30)
        cases = {
            "fresh": self._ws(self._key(2, "B")),
            "foreign_author": self._ws(old, author=uuid4()),
            "no_marker": self._ws(old, description="handmade"),
            "marker_mismatch": self._ws(old, description=run_marker(self._key(40)[:-1])),
            "current_run": self._ws(run_prefix(self.now) + "A"),
            "bad_key": self._ws(old[:-1] + "C"),
            "not_e2e": self._ws("PROD" + old[3:]),
        }
        for name, ws in cases.items():
            with self.subTest(name):
                self.assertFalse(self._stale(ws))


class ReportTestCase(unittest.TestCase):
    def test_report_counts(self) -> None:
        ctx = _ctx()
        steps = [Step("s", ("GetProviders",), lambda c: c.api.providers.list())]
        with mock.patch.object(ctx.client.session, "request", return_value=_response(200, {"providers": []})):
            results = run_steps(ctx, steps)
        statuses = op_statuses(steps, results, ctx.client.calls)
        with tempfile.TemporaryDirectory() as tmp:
            summary = write_report(Path(tmp) / "run", {"prefix": "P"}, results, statuses, [])
            data = json.loads((Path(tmp) / "run.json").read_text(encoding="utf-8"))
            self.assertTrue((Path(tmp) / "run.md").read_text(encoding="utf-8").startswith("# E2E P"))
        self.assertEqual(1, data["totals"]["PASS"])
        self.assertEqual(len(EXCLUDED), data["totals"]["EXCLUDED"])
        self.assertIn(f"PASS 1/{len(OPERATIONS) - len(EXCLUDED)}", summary)


class ScenarioCompletenessTestCase(unittest.TestCase):
    def test_declared_ops_plus_excluded_equal_manifest(self) -> None:
        declared = {op for step in build_steps() for op in step.ops}
        self.assertEqual(set(), declared - set(OPERATIONS), "steps declare unknown operations")
        self.assertEqual(set(), declared & set(EXCLUDED), "excluded operations must not be declared")
        self.assertEqual(set(), set(OPERATIONS) - declared - set(EXCLUDED), "operations without a step")
        self.assertEqual(170, len(OPERATIONS))

    def test_step_names_unique(self) -> None:
        names = [step.name for step in build_steps()]
        self.assertEqual(len(names), len(set(names)))
