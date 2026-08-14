import re
import unittest
from pathlib import Path


def _is_vendored(path: Path, repo_root: Path) -> bool:
    """
    True when *path* belongs to a virtualenv, a build artifact or a cache
    rather than to the repository's own source.

    Skipping a hardcoded ``.venv`` is not enough: a contributor whose
    environment is named anything else (``venv``, ``.v``, ``env``, a tox or
    nox env) makes this test walk into ``site-packages`` and report
    third-party files as offenders. Virtualenvs are detected by the
    ``pyvenv.cfg`` marker PEP 405 requires at their root, so the name does
    not matter.
    """
    parts = set(path.parts)
    if parts & {"__pycache__", "site-packages", "build", "dist", ".tox", ".nox", ".eggs"}:
        return True
    if any(part.endswith(".egg-info") for part in path.parts):
        return True
    for ancestor in path.parents:
        if ancestor == repo_root.parent:
            break
        if (ancestor / "pyvenv.cfg").exists():
            return True
    return False


class NoLegacyModulesImportsTestCase(unittest.TestCase):
    def test_repo_python_files_do_not_import_legacy_modules_package(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        legacy_prefix = "modules" + "."
        legacy_from = "from " + "modules" + " import"
        legacy_import = "import " + "modules"
        pattern = re.compile(rf"(^|\s)({re.escape(legacy_from)}|{re.escape(legacy_import)}|{re.escape(legacy_prefix)})")

        offenders: list[str] = []
        scanned = 0
        for path in repo_root.rglob("*.py"):
            if _is_vendored(path, repo_root):
                continue

            scanned += 1
            contents = path.read_text(encoding="utf-8")
            if pattern.search(contents):
                offenders.append(str(path.relative_to(repo_root)))

        self.assertEqual([], offenders)
        # Guard against the exclusions above silently swallowing the whole
        # tree and turning this into a test that can never fail.
        self.assertGreater(scanned, 50, f"only {scanned} source files scanned -- exclusions are too broad")


if __name__ == "__main__":
    unittest.main()
