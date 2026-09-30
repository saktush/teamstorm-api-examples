from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


def _load_guard():
    root = Path(__file__).resolve().parents[2]
    path = root / "scripts" / "check_repository_positioning.py"
    spec = importlib.util.spec_from_file_location("repository_positioning_guard", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_repository_positioning_guard() -> None:
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "scripts/check_repository_positioning.py"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_guard_rejects_product_and_package_index_positioning() -> None:
    guard = _load_guard()
    legacy = "".join(("s", "d", "k"))
    index = "".join(("p", "y", "p", "i"))
    errors = guard.content_errors(
        "README.md",
        f"Official TeamStorm {legacy}; install from {index} with pip install teamstorm-public-{legacy}",
    )
    assert errors
    assert any(legacy in error for error in errors)
    assert any(index in error for error in errors)


def test_guard_accepts_current_remote_after_rename() -> None:
    guard = _load_guard()
    remote = "github.com/saktush/" + "teamstorm-api-examples"
    errors = guard.content_errors("README.en.md", "git+https://" + remote + ".git")
    assert errors == []


def test_guard_rejects_sensitive_provenance() -> None:
    guard = _load_guard()
    source_derived = "source" + "-derived"
    private_codebase = "private " + "codebase"
    errors = guard.content_errors(
        "docs/api-analysis/notes.md",
        f"These {source_derived} findings came from a {private_codebase} ahead of sharing.",
    )
    assert errors
    assert any(source_derived in error for error in errors)
    assert any(private_codebase in error for error in errors)


def test_guard_rejects_publish_workflow_capabilities() -> None:
    guard = _load_guard()
    errors = guard.content_errors(
        ".github/workflows/ci.yml",
        "permissions:\n  id-token: write\nsteps:\n  - uses: actions/upload-artifact@v4\n",
    )
    assert errors
    assert any("id-token: write" in error for error in errors)
    assert any("upload-artifact" in error for error in errors)


def test_guard_rejects_reintroduced_entrypoint_term() -> None:
    guard = _load_guard()
    rejected = "fa" + "cade"
    errors = guard.content_errors("README.md", f"Use the {rejected} module")
    assert errors
    assert any(rejected in error for error in errors)


def test_guard_requires_archive_first_install_and_api_entrypoint_in_all_guides() -> None:
    guard = _load_guard()
    project = "\n".join(
        (
            "[project]",
            'name = "teamstorm-api-examples"',
            'version = "1.1.0"',
            'classifiers = ["Private :: Do Not Upload"]',
            "[project.urls]",
            'Repository = "https://github.com/saktush/teamstorm-api-examples"',
        )
    )
    files = {
        "README.md": "incomplete",
        "README.en.md": "incomplete",
        ".agents/skills/teamstorm-api/SKILL.md": "incomplete",
        "pyproject.toml": project,
    }
    errors = guard.required_content_errors(files)
    assert len([error for error in errors if "local archive installation" in error]) == 3
    assert len([error for error in errors if "current API entrypoint import" in error]) == 3
    assert "README.md lacks workspace-configuration terminology" in errors
    assert "README.en.md lacks workspace-configuration terminology" in errors


def test_guard_rejects_wrong_version_and_repository_url() -> None:
    guard = _load_guard()
    guide = "## Install from local archive\n" "from teamstorm.api import TeamStormAPI\n"
    project = "\n".join(
        (
            "[project]",
            'name = "teamstorm-api-examples"',
            'version = "0.0.0"',
            'classifiers = ["Private :: Do Not Upload"]',
            "[project.urls]",
            'Repository = "https://example.invalid"',
        )
    )
    files = {
        "README.md": guide,
        "README.en.md": guide,
        ".agents/skills/teamstorm-api/SKILL.md": guide,
        "pyproject.toml": project,
    }
    errors = guard.required_content_errors(files)
    assert 'pyproject missing: version = "1.1.0"' in errors
    assert "pyproject missing current repository URL" in errors
