"""Engine for the opt-in live end-to-end scenario: operation catalog, call recording, steps, report, sweep.

Nothing here talks to a server by itself; ``scenario.py`` holds the steps and ``test_live_e2e.py`` runs them.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, NoReturn
from uuid import UUID

from teamstorm.api import TeamStormAPI
from teamstorm.client import ApiError, TsClient
from teamstorm.models.workspaces import WorkspaceModel

_API_TESTS_DIR = Path(__file__).resolve().parents[1] / "api"
if str(_API_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_API_TESTS_DIR))

from api_coverage_manifest import COVERAGE_MANIFEST, OpMapping  # noqa: E402


def op_key(row: OpMapping) -> str:
    return row.operation_id or f"{row.http_method} {row.path}"


OPERATIONS: dict[str, OpMapping] = {op_key(row): row for row in COVERAGE_MANIFEST}

EXCLUDED: dict[str, str] = {
    "BlockUser": "changes an existing user account",
    "UnblockUser": "changes an existing user account",
    "GetConnections": "instance admin settings (OpenID)",
    "CreateConnection": "instance admin settings (OpenID)",
    "DeleteConnection": "instance admin settings (OpenID)",
    "CreateUser": "instance admin settings (OpenID)",
    "UpdateQueryVisibilitySettings": "changes a saved query the run does not own",
}

# Fewer placeholders first, so ".../workitems/count" beats ".../workitems/{workitem}".
_TEMPLATES: list[tuple[re.Pattern[str], str, str]] = sorted(
    (
        (re.compile("^" + re.sub(r"\\\{[^/]+?\\\}", "[^/]+", re.escape(row.path)) + "$"), row.http_method, key)
        for key, row in OPERATIONS.items()
    ),
    key=lambda item: item[0].pattern.count("[^/]+"),
)


def match_operation(method: str, path: str) -> str | None:
    path = path.split("?", 1)[0].rstrip("/")
    for pattern, verb, key in _TEMPLATES:
        if verb == method.upper() and pattern.match(path):
            return key
    return None


@dataclass
class Call:
    op: str | None
    method: str
    path: str
    step: str
    status: int | None
    seconds: float
    error: str | None = None
    counts: bool = True


class RecordingClient(TsClient):
    """A TsClient that records every request it sends, with the step that sent it."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.calls: list[Call] = []
        self.current_step = ""
        self.counts = True

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        started = time.monotonic()
        call = Call(match_operation(method, path), method, path, self.current_step, None, 0.0, counts=self.counts)
        self.calls.append(call)
        try:
            result = super()._request(method, path, **kwargs)
        except ApiError as e:
            call.status, call.error = e.status, _short(f"{e} {e.details or ''}")
            raise
        finally:
            call.seconds = time.monotonic() - started
        call.status = 200
        return result


def _short(text: str, limit: int = 300) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit] + "…"


class StepSkipped(Exception):
    pass


class RecordedFailure(Exception):
    """A step failure the step already attributed to the right call; ``run_steps`` must not re-attribute it."""


@dataclass
class Ctx:
    api: TeamStormAPI
    client: RecordingClient
    prefix: str
    started: dt.datetime
    env: Mapping[str, str]
    reg: dict[str, Any] = field(default_factory=dict)
    op_skips: dict[str, str] = field(default_factory=dict)
    soft_failures: list[str] = field(default_factory=list)

    def skip(self, reason: str) -> NoReturn:
        raise StepSkipped(reason)

    def soft(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Run one independent call; on failure record it on that call and let the step go on (it still FAILs)."""
        first_call = len(self.client.calls)
        try:
            return fn(*args, **kwargs)
        except Exception as e:  # noqa: BLE001 -- surfaced through soft_failures
            reason = _short(f"{type(e).__name__}: {e}")
            own = self.client.calls[first_call:]
            if own and own[-1].error is None:
                own[-1].error = reason
            self.soft_failures.append(reason)
            return None

    def skip_op(self, op: str, reason: str) -> None:
        """Mark one operation of a step as skipped while the rest of the step goes on."""
        self.op_skips[op] = f"{self.client.current_step}: {reason}"


@dataclass(frozen=True)
class Step:
    name: str
    ops: tuple[str, ...]
    fn: Callable[[Ctx], None]
    needs: tuple[str, ...] = ()
    cleanup: bool = False
    counts: bool = True


@dataclass
class StepResult:
    name: str
    status: str
    reason: str = ""
    seconds: float = 0.0


def run_steps(ctx: Ctx, steps: list[Step]) -> list[StepResult]:
    """Run steps in order; a step whose ``needs`` are missing from ``ctx.reg`` is skipped, never aborts the run."""
    results: list[StepResult] = []
    for step in steps:
        missing = [need for need in step.needs if need not in ctx.reg]
        if missing:
            results.append(StepResult(step.name, "SKIP", "missing " + ", ".join(missing)))
            continue
        ctx.client.current_step, ctx.client.counts = step.name, step.counts
        first_call = len(ctx.client.calls)
        started = time.monotonic()
        ctx.soft_failures = []
        try:
            step.fn(ctx)
            if ctx.soft_failures:
                raise RecordedFailure("; ".join(ctx.soft_failures))
            result = StepResult(step.name, "PASS")
        except StepSkipped as e:
            result = StepResult(step.name, "SKIP", str(e))
        except Exception as e:  # noqa: BLE001 -- a failed step must not stop the run
            result = StepResult(step.name, "FAIL", _short(f"{type(e).__name__}: {e}"))
            own_calls = ctx.client.calls[first_call:]
            if not isinstance(e, (ApiError, RecordedFailure)) and own_calls and own_calls[-1].error is None:
                # A 2xx answer that the step could not use (usually a model validation error).
                own_calls[-1].error = result.reason
        result.seconds = time.monotonic() - started
        results.append(result)
    ctx.client.current_step, ctx.client.counts = "", True
    return results


@dataclass
class OpStatus:
    op: str
    method: str
    path: str
    status: str
    steps: str = ""
    seconds: float = 0.0
    detail: str = ""


def op_statuses(
    steps: list[Step], results: list[StepResult], calls: list[Call], op_skips: Mapping[str, str] | None = None
) -> dict[str, OpStatus]:
    by_step = {result.name: result for result in results}
    declared: dict[str, list[str]] = {}
    for step in steps:
        for op in step.ops:
            declared.setdefault(op, []).append(step.name)
    statuses: dict[str, OpStatus] = {}
    for key, row in OPERATIONS.items():
        own = [call for call in calls if call.op == key and call.counts]
        status = OpStatus(key, row.http_method, row.path, "PASS")
        status.steps = ", ".join(sorted({call.step for call in own} or set(declared.get(key, []))))
        status.seconds = sum(call.seconds for call in own)
        failed = [call for call in own if call.error]
        if key in EXCLUDED:
            status.status, status.detail = "EXCLUDED", EXCLUDED[key]
        elif failed:
            status.status, status.detail = "FAIL", failed[0].error or ""
        elif own:
            pass
        else:
            own_steps = [by_step[name] for name in declared.get(key, []) if name in by_step]
            reasons = [f"{result.name}: {result.reason}" for result in own_steps if result.status != "PASS"]
            if op_skips and key in op_skips:
                reasons.append(op_skips[key])
            # Not reached because its step failed or was skipped: the failure itself is reported where it happened.
            status.status = "SKIP" if reasons else "FAIL"
            status.detail = "; ".join(reasons) or "declared but never called"
        statuses[key] = status
    return statuses


# Workspace keys allow at most 10 uppercase letters/digits: "E2E" + 6 base36 chars of the epoch second + "A"/"B".
# shortcut: 6 base36 chars hold epoch seconds until 2038-10; widen the code (and shorten "E2E") before then.
STALE_KEY = re.compile(r"^E2E([0-9A-Z]{6})[AB]$")
MARKER = "teamstorm-api-examples live e2e run "
_B36 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def run_prefix(started: dt.datetime) -> str:
    seconds, code = int(started.timestamp()), ""
    for _ in range(6):
        seconds, digit = divmod(seconds, 36)
        code = _B36[digit] + code
    return "E2E" + code


def prefix_time(code: str) -> dt.datetime:
    return dt.datetime.fromtimestamp(int(code, 36), dt.timezone.utc)


def run_marker(prefix: str) -> str:
    return MARKER + prefix


def is_stale_e2e_workspace(
    ws: WorkspaceModel,
    *,
    owner_id: UUID,
    now: dt.datetime,
    current_prefix: str,
    min_age: dt.timedelta = dt.timedelta(hours=6),
) -> bool:
    """True only for a workspace an earlier run of this scenario left behind (every condition must hold)."""
    found = STALE_KEY.match(ws.key)
    if not found or ws.key.startswith(current_prefix):
        return False
    prefix = ws.key[:-1]
    if run_marker(prefix) not in (ws.description or ""):
        return False
    if ws.author is None or ws.author.id != owner_id:
        return False
    return now - prefix_time(found.group(1)) > min_age


def write_report(
    stem: Path,
    meta: dict[str, Any],
    results: list[StepResult],
    statuses: dict[str, OpStatus],
    sweep: list[dict[str, Any]],
) -> str:
    """Write ``<stem>.md`` and ``<stem>.json``; return the console summary."""
    stem.parent.mkdir(parents=True, exist_ok=True)
    totals: dict[str, int] = {}
    for status in statuses.values():
        totals[status.status] = totals.get(status.status, 0) + 1
    in_scope = len(statuses) - totals.get("EXCLUDED", 0)
    summary = (
        f"E2E {meta.get('prefix')}: PASS {totals.get('PASS', 0)}/{in_scope}, FAIL {totals.get('FAIL', 0)}, "
        f"SKIP {totals.get('SKIP', 0)}, EXCLUDED {totals.get('EXCLUDED', 0)} (of {len(statuses)} operations)"
    )
    stem.with_suffix(".json").write_text(
        json.dumps(
            {
                "meta": meta,
                "totals": totals,
                "steps": [asdict(result) for result in results],
                "operations": [asdict(status) for status in statuses.values()],
                "sweep": sweep,
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    lines = [f"# {summary}", ""]
    lines += [f"- **{key}**: {value}" for key, value in meta.items()]
    lines += ["", "## Steps", "", "| step | status | s | reason |", "|---|---|---|---|"]
    lines += [f"| {r.name} | {r.status} | {r.seconds:.1f} | {_cell(r.reason)} |" for r in results]
    lines += ["", "## Operations", "", "| operation | method | path | status | steps | s | detail |"]
    lines += ["|---|---|---|---|---|---|---|"]
    order = {"FAIL": 0, "SKIP": 1, "PASS": 2, "EXCLUDED": 3}
    for s in sorted(statuses.values(), key=lambda s: (order[s.status], s.op)):
        lines.append(
            f"| {s.op} | {s.method} | `{s.path}` | {s.status} | {s.steps} | {s.seconds:.2f} | {_cell(s.detail)} |"
        )
    lines += ["", "## Sweep of earlier runs", ""]
    lines += [f"- {item}" for item in sweep] or ["- nothing to sweep"]
    stem.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    lines = [summary] + [f"  FAIL {s.op}: {s.detail}" for s in statuses.values() if s.status == "FAIL"]
    lines += [f"  {r.status} step {r.name}: {r.reason}" for r in results if r.status != "PASS"]
    return "\n".join(lines)


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")
