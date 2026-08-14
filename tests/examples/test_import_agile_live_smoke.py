import importlib.util
import os
import shlex
import subprocess
import tempfile
import unittest
from pathlib import Path


def _load_dotenv_fallback(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]

        os.environ.setdefault(key, value)


@unittest.skipUnless(
    os.getenv("RUN_LIVE_SMOKE") == "1",
    "Set RUN_LIVE_SMOKE=1 to enable the live import smoke test",
)
class ImportAgileLiveSmokeTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[2]
        _load_dotenv_fallback(self.repo_root / ".env")

        self.base_url = os.getenv("BASE_URL")
        self.api_token = os.getenv("API_TOKEN")
        if not self.base_url or not self.api_token:
            self.skipTest("BASE_URL and API_TOKEN must be present in the repo .env before running the smoke test")

        missing_dependencies = [
            name
            for name in ("dotenv", "openpyxl", "pandas", "pydantic", "requests")
            if importlib.util.find_spec(name) is None
        ]
        if missing_dependencies:
            self.skipTest(
                "Missing runtime dependencies required by the live smoke test: "
                + ", ".join(sorted(missing_dependencies))
            )

    def test_live_import_command_succeeds(self) -> None:
        command = [
            "python3",
            "examples/import_toolkit/import_agile.py",
            "--workspace-key",
            "DS",
            "--folder-name",
            "Test",
            "--input-path",
            "examples/data/example_agile.xlsx",
            "--update-settings",
            "--sync-members",
        ]

        with tempfile.TemporaryDirectory(prefix="import-agile-smoke-") as tmpdir:
            log_file = Path(tmpdir) / "import_agile.smoke.log"
            full_command = command + ["--log-file", str(log_file)]
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"

            try:
                result = subprocess.run(
                    full_command,
                    cwd=self.repo_root,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=900,
                )
            except subprocess.TimeoutExpired as exc:
                self.fail(
                    "Live smoke test timed out after 900 seconds.\n"
                    f"Command: {shlex.join(full_command)}\n"
                    f"stdout:\n{exc.stdout or ''}\n"
                    f"stderr:\n{exc.stderr or ''}"
                )

        self.assertEqual(
            0,
            result.returncode,
            msg=(
                "Live smoke test failed.\n"
                f"Command: {shlex.join(full_command)}\n"
                f"Return code: {result.returncode}\n"
                f"stdout:\n{result.stdout}\n"
                f"stderr:\n{result.stderr}"
            ),
        )


if __name__ == "__main__":
    unittest.main()
