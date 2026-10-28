"""Opt-in live end-to-end run over the whole CWM Public API (design: docs/superpowers/specs/*live-e2e*).

Runs against a real TeamStorm instance and WRITES data, but only inside two workspaces it creates
(``E2E<base36 time>A`` / ``B``) and deletes at the end. Existing data and instance admin settings are never touched.

Enable with ``RUN_LIVE_E2E=1``; run with ``-s`` to see the summary. Settings come from the repo ``.env``/environment:

- ``BASE_URL``, ``API_TOKEN`` -- as in ``.env.template``. The instance needs users ``demo.user1`` .. ``demo.user4``.
- ``E2E_GROUP`` (optional) -- user group name for the workspace-group steps; defaults to the first group.
- ``E2E_QUERY_ID`` + ``E2E_QUERY_WORKSPACE`` (optional) -- an existing saved query to read; otherwise SKIP.
- ``E2E_CLEANUP_ONLY=1`` -- only sweep workspaces left by earlier runs; ``E2E_OWNER`` (token owner's login) makes it
  delete them, without it the candidates are only listed.

Reports go to ``build/e2e/<prefix>.md`` and ``.json``. The test fails when any operation or step is FAIL.
"""

from __future__ import annotations

import datetime as dt
import os
import subprocess
import unittest
from pathlib import Path
from urllib.parse import urlsplit

from e2e.runner import Ctx, RecordingClient, is_stale_e2e_workspace, op_statuses, run_prefix, run_steps, write_report
from e2e.scenario import build_steps, sweep
from teamstorm.api import TeamStormAPI
from teamstorm.client import RetryConfig

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


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=_REPO_ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


@unittest.skipUnless(
    os.getenv("RUN_LIVE_E2E") == "1", "Set RUN_LIVE_E2E=1 to run the live e2e scenario (it writes data)"
)
class LiveE2ETestCase(unittest.TestCase):
    def setUp(self) -> None:
        _load_dotenv_fallback(_REPO_ROOT / ".env")
        base_url, token = os.getenv("BASE_URL"), os.getenv("API_TOKEN")
        if not base_url or not token:
            self.skipTest("Missing live-test settings: BASE_URL, API_TOKEN")
        self.host = urlsplit(base_url).hostname or "?"
        # One attempt: never resend a non-idempotent write (create, comment, link, upload) on a 5xx.
        self.client = RecordingClient(base_url, token, retry=RetryConfig(max_attempts=1))
        started = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
        self.ctx = Ctx(TeamStormAPI(self.client), self.client, run_prefix(started), started, os.environ)

    def test_whole_api(self) -> None:
        ctx = self.ctx
        if os.getenv("E2E_CLEANUP_ONLY") == "1":
            self._cleanup_only()
            return
        steps = build_steps()
        results = []
        try:
            results = run_steps(ctx, steps)
        finally:
            leftovers = self._safety_net()
            statuses = op_statuses(steps, results, ctx.client.calls, ctx.op_skips)
            meta = {
                "prefix": ctx.prefix,
                "commit": _git_commit(),
                "host": self.host,
                "started_utc": ctx.started.isoformat(),
                "finished_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
                "workspaces": f"{ctx.prefix}A, {ctx.prefix}B",
                "mutations": any(call.method != "GET" for call in ctx.client.calls),
                "left_behind": ", ".join(leftovers) or "nothing",
            }
            summary = write_report(
                _REPO_ROOT / "build" / "e2e" / ctx.prefix, meta, results, statuses, ctx.reg.get("sweep_log", [])
            )
            print("\n" + summary + f"\nreport: build/e2e/{ctx.prefix}.md")
        failed = sorted(key for key, status in statuses.items() if status.status == "FAIL")
        failed += [f"step {result.name}" for result in results if result.status == "FAIL"]
        self.assertEqual([], failed, summary)

    def _safety_net(self) -> list[str]:
        """Delete the run's own workspaces if the cleanup steps did not; return the keys that are still there."""
        left = []
        self.client.current_step, self.client.counts = "safety net", False
        for name in ("ws_b", "ws_a"):
            ws = self.ctx.reg.get(name)
            if ws is None:
                continue
            try:
                self.ctx.api.workspaces.delete(workspace_key=ws.key)
                self.ctx.reg.pop(name)
            except Exception:  # noqa: BLE001 -- report it; the next run's sweep removes it
                left.append(ws.key)
        return left

    def _cleanup_only(self) -> None:
        self.client.current_step, self.client.counts = "sweep", False
        owner = os.getenv("E2E_OWNER")
        owner_id = self.ctx.api.users.get(owner).id if owner else None
        if owner_id is None:
            print("\nE2E_OWNER is not set: listing candidates of any author, deleting nothing")
            now = dt.datetime.now(dt.timezone.utc)
            for ws in self.ctx.api.workspaces.list():
                author = ws.author
                if author and is_stale_e2e_workspace(ws, owner_id=author.id, now=now, current_prefix=self.ctx.prefix):
                    print(f"  candidate {ws.key} (author {author.username})")
            return
        sweep(self.ctx, owner_id, delete=True)
        for item in self.ctx.reg.get("sweep_log", []) or ["nothing to sweep"]:
            print(f"  {item}")
