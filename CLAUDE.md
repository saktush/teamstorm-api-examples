# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Read [`AGENTS.md`](AGENTS.md) and [`.agents/skills/teamstorm-api/SKILL.md`](.agents/skills/teamstorm-api/SKILL.md) first: they hold the safety rules, credential handling, smoke-test procedure and known live-server quirks. (`.claude/skills/teamstorm-api` is a link to the same skill.)

## What this is

A typed Python wrapper (`teamstorm` package: `requests` + pydantic v2) around the TeamStorm CWM Public API (`/cwm/public/api/v1`), plus example applications under `examples/`. It is a reference implementation, never published to a package index (`Private :: Do Not Upload`). Python 3.11+.

## Commands

```bash
uv venv .venv
uv pip install --python .venv/bin/python ".[dev,examples]"   # or: python -m venv + pip install ".[dev,examples]"

# Full quality gate (same as CI, run before finishing)
.venv/bin/python scripts/check_repository_positioning.py
.venv/bin/flake8 teamstorm/ examples/ tests/ scripts/
.venv/bin/black --check teamstorm/ examples/ tests/ scripts/    # line length 120
.venv/bin/mypy teamstorm/                                       # strict-ish: disallow_untyped_defs
.venv/bin/python -m pytest -q

# Single test
.venv/bin/python -m pytest tests/api/test_api_workitems_ops.py::TestName::test_name -q
```

Notes:
- `check_repository_positioning.py` uses `git ls-files`, so it only works inside a Git checkout, and it scans every tracked text file for forbidden legacy/registry-publishing terms (list at the top of the script). Keep new docs free of those terms; it also requires `README*.md` to mention the local-archive install and the `from teamstorm.api import TeamStormAPI` import.
- pytest runs with `pythonpath = ["examples"]`, so tests import `import_toolkit...` directly.
- Import-toolkit scripts are run directly, not installed: `python examples/import_toolkit/import_agile.py --help`.

## Architecture

**Transport → resources → models**

- `teamstorm/client.py` — `TsClient`: the only HTTP layer. Adds the `PrivateToken ` auth prefix (callers pass the bare token), enforces HTTPS unless `allow_insecure=True`, retries/backoff via `RetryConfig`/`TimeoutConfig`, raises `ApiError`. Provides `get/post/patch/put/delete/post_multipart/get_bytes` plus `iter_all`/`get_all` for pagination (token-based). It holds no workspace state, so one client serves many workspaces.
- `teamstorm/api/` — one module per resource area; each class subclasses the frozen, slotted dataclass `BaseAPI` whose only field is `client`. `TeamStormAPI` in `api/_entrypoint.py` is the single entrypoint exposing 35 lazy resource properties (a new `*API` instance per access; no caching, by design). Adding a resource means: module in `api/`, property in `_entrypoint.py`, exports in `api/__init__.py`.
- `teamstorm/models/` — pydantic request/response models on `TsBaseModel` (`populate_by_name=True`, `extra="forbid"`, so unknown server fields fail validation rather than being silently dropped). Its `model_dump` defaults to `by_alias=True, exclude_none=True, mode="json"`.

**Conventions that span files** (details in `docs/api-analysis/conventions.md`; the code wins over that doc, and its `file:line` citations are approximate)
- Workspace-scoped methods take `workspace_key: str` first; all other ids/filters are keyword-only after `*`.
- Public methods take exact request models, not dicts.
- **PATCH bodies must be dumped with `exclude_unset=True, exclude_none=False`**: an omitted field means "leave unchanged", an explicit `None` sends JSON `null` to clear the value. The default `model_dump` cannot express that. Same rule for `WorkitemsAPI.update_attribute`.
- `list()` methods collect all pages; use `client.iter_all()` for large sets.

**API coverage is enforced by tests.** `docs/openapi/swagger-v4.24.0.json` is the committed OpenAPI snapshot; `tests/api/api_coverage_manifest.py` is a hand-maintained manifest mapping all 170 operations to wrapper methods, and `tests/api/test_api_coverage.py` cross-checks it against the snapshot in both directions. Any added/removed endpoint requires updating the manifest and `docs/api-coverage.md` (and the README coverage table, which `test_readme_coverage_table.py` checks). Do not drop the 170-operation invariant, `import teamstorm`, `TsClient`, `TeamStormAPI`, or the typed request models.

**`examples/import_toolkit/`** (not part of the installed package) — Excel/CSV → TeamStorm importer, layered as:
`workflows/imports/` (CLI parsing in `cli.py`, orchestration in `agile.py`, workspace settings/metadata sync) → `controllers/core/` (bootstrap, users, membership, attributes, types, workitems, value mapping) and `controllers/extensions/agile/` (sprints, agile workitems) → `io/readers/` (excel/csv readers behind `factory.select_reader`, producing `SprintImportRow`/`TaskImportRow` contracts). `workflows/sync/` + `sync_uniselect_options.py` copy `UniSelect` attribute options from a master workspace to targets. Both entry points support `--dry-run`. The examples read `BASE_URL`, `API_TOKEN`, `WORKSPACE_KEY` from `.env` (see `.env.template`), whereas README snippets use `TEAMSTORM_*` names.

## Behavior to remember

- Never call a live TeamStorm instance unless the task requires it; confirm workspace/ids before mutations; do not blindly retry non-idempotent writes (create, comment, link, upload). Known live quirks: attaching an attribute to a type can return 500; creating a workitem with an unattached custom attribute can 404; linking a portfolio element may commit and then fail response validation, so read back state before retrying.
- `CreateWorkitemLinkRequestBody` requires `linked_workspace`.
- Do not add registry-upload or release-artifact automation, and do not commit credentials or generated artifacts (`build/`, `*.egg-info/`, `.venv/`, `.claude/` are gitignored).
- Docs are bilingual (`README.md` Russian, `README.en.md` English; same for `examples/`); keep them in step.
