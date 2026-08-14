from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

LEGACY_PRODUCT_TERM = "".join(("s", "d", "k"))
PACKAGE_INDEX_TERM = "".join(("p", "y", "p", "i"))
UPLOAD_TOOL_TERM = "".join(("t", "w", "i", "n", "e"))
OLD_DISTRIBUTION = "teamstorm-public-" + LEGACY_PRODUCT_TERM
OLD_GROUPED_ENTRYPOINT_PATH = "teamstorm/" + LEGACY_PRODUCT_TERM + ".py"
OLD_TEST_PATH = "tests/" + LEGACY_PRODUCT_TERM
OLD_COVERAGE_PATH = "docs/" + LEGACY_PRODUCT_TERM + "-coverage.md"
REJECTED_ENTRYPOINT_TERM = "fa" + "cade"
CURRENT_REPOSITORY_URL = "https://github.com/saktush/teamstorm-api-examples"
SENSITIVE_PROVENANCE = (
    "closed" + "-source",
    "private " + "codebase",
    "ahead of " + "publishing",
    "source" + "-derived",
)

FORBIDDEN_TEXT = (
    LEGACY_PRODUCT_TERM,
    PACKAGE_INDEX_TERM,
    UPLOAD_TOOL_TERM,
    OLD_DISTRIBUTION,
    OLD_GROUPED_ENTRYPOINT_PATH,
    OLD_TEST_PATH,
    OLD_COVERAGE_PATH,
    *SENSITIVE_PROVENANCE,
    REJECTED_ENTRYPOINT_TERM,
)

ABSENT = {
    ".github/workflows/publish.yml",
    "MANIFEST.in",
}
REQUIRED = {
    "README.md",
    "README.en.md",
    "AGENTS.md",
    "teamstorm/api/__init__.py",
    "teamstorm/api/_entrypoint.py",
    "docs/api-coverage.md",
    "docs/technical-behavior.md",
    ".agents/skills/teamstorm-api/SKILL.md",
}
LOCAL_ARCHIVE_NAME = "teamstorm-api-examples-1.0.0.zip"
API_ENTRYPOINT_IMPORT = "from teamstorm.api import TeamStormAPI"
RU_WORKSPACE_CONFIGURATION = "Настройки пространства"
EN_WORKSPACE_CONFIGURATION = "Workspace configuration"


def tracked_files() -> list[str]:
    output = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    return [item for item in output.decode().split("\0") if item]


def content_errors(path: str, text: str) -> list[str]:
    """Return positioning/security violations for one tracked text file."""
    low_path = path.lower()
    lowered = text.lower()
    errors: list[str] = []

    if any(term in low_path for term in FORBIDDEN_TEXT):
        errors.append(f"stale filename: {path}")

    if not path.startswith("docs/openapi/"):
        for term in FORBIDDEN_TEXT:
            if term in lowered:
                errors.append(f"stale or sensitive positioning in {path}: {term}")

    if path.startswith(".github/workflows/"):
        registry_action = "gh-action-" + PACKAGE_INDEX_TERM + "-publish"
        forbidden_workflow_fragments = (
            "id-token: write",
            "upload-artifact",
            registry_action,
        )
        for fragment in forbidden_workflow_fragments:
            if fragment in lowered:
                errors.append(f"forbidden workflow capability in {path}: {fragment}")

    return errors


def required_content_errors(files: dict[str, str]) -> list[str]:
    """Validate cross-file documentation, metadata, and API entrypoint invariants."""
    errors: list[str] = []

    for path in ("README.md", "README.en.md", ".agents/skills/teamstorm-api/SKILL.md"):
        text = files.get(path, "")
        if LOCAL_ARCHIVE_NAME not in text:
            errors.append(f"{path} lacks local archive installation")
        if API_ENTRYPOINT_IMPORT not in text:
            errors.append(f"{path} lacks current API entrypoint import")

    if RU_WORKSPACE_CONFIGURATION not in files.get("README.md", ""):
        errors.append("README.md lacks workspace-configuration terminology")
    if EN_WORKSPACE_CONFIGURATION not in files.get("README.en.md", ""):
        errors.append("README.en.md lacks workspace-configuration terminology")

    project = files.get("pyproject.toml", "")
    for required in (
        'name = "teamstorm-api-examples"',
        'version = "1.0.0"',
        '"Private :: Do Not Upload"',
    ):
        if required not in project:
            errors.append(f"pyproject missing: {required}")
    if f'Repository = "{CURRENT_REPOSITORY_URL}"' not in project:
        errors.append("pyproject missing current repository URL")

    return errors


def main() -> int:
    paths = tracked_files()
    lowered_paths = {path.lower() for path in paths}
    errors: list[str] = []
    files: dict[str, str] = {}

    for path in paths:
        file_path = ROOT / path
        if not file_path.is_file():
            continue
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        files[path] = text
        errors.extend(content_errors(path, text))

    for path in ABSENT:
        if path.lower() in lowered_paths:
            errors.append(f"file must be absent: {path}")
    for path in REQUIRED:
        if path.lower() not in lowered_paths:
            errors.append(f"required file missing: {path}")

    errors.extend(required_content_errors(files))

    if errors:
        print("Repository positioning check failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Repository positioning check: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
