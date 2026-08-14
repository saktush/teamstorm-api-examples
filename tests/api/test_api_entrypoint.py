from __future__ import annotations

import importlib.util
from pathlib import Path

from teamstorm.api import TeamStormAPI
from teamstorm.client import TsClient

ROOT = Path(__file__).resolve().parents[2]


def test_teamstorm_api_is_the_public_grouped_entrypoint() -> None:
    client = TsClient(base_url="https://teamstorm.example", token="test-token")
    api = TeamStormAPI(client)

    assert api.client is client
    assert api.workspaces.client is client


def test_rejected_legacy_entrypoint_module_is_absent() -> None:
    rejected_name = "fa" + "cade"
    assert not (ROOT / "teamstorm" / f"{rejected_name}.py").exists()
    assert importlib.util.find_spec(f"teamstorm.{rejected_name}") is None


def test_workspace_configuration_uses_product_terminology() -> None:
    forbidden = {
        "Справочники",
        "синхронизация справочников",
        "Catalog configuration",
        "catalog synchronization",
    }
    files = (ROOT / "README.md", ROOT / "README.en.md")

    for path in files:
        text = path.read_text(encoding="utf-8")
        for phrase in forbidden:
            assert phrase not in text, f"{path.name} still contains {phrase!r}"

    assert "Настройки пространства" in (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Workspace configuration" in (ROOT / "README.en.md").read_text(encoding="utf-8")
