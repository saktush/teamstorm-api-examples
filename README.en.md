# TeamStorm API Examples

[Русская версия](README.md) | **English**

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Practical typed examples and reusable Python wrappers for the **TeamStorm CWM Public API** (`/cwm/public/api/v1`). The repository contains an HTTP client, pydantic models, 35 resource interfaces covering 170 OpenAPI operations, and runnable automation examples.

This is a **reference implementation and example collection**, not a separate official product. The preferred distribution method is a versioned local archive that can be transferred without Git access. It is not published to a package registry and carries no support commitment.

## Install from a local archive — preferred

Python 3.11 or newer is required. Obtain `teamstorm-api-examples-1.0.0.zip` from the repository owner or the [1.0.0 release](https://github.com/saktush/teamstorm-api-examples/releases/tag/v1.0.0), then run:

```bash
python3 -m zipfile -e teamstorm-api-examples-1.0.0.zip .
python3 -m venv .venv
.venv/bin/python -m pip install ./teamstorm-api-examples-1.0.0
```

The archive contains the project sources and metadata, but not third-party dependencies. For a fully isolated machine, transfer compatible wheels for `requests`, `pydantic`, and their dependencies, then install them from a local directory with `pip --no-index --find-links`.

Keep the archive with the published `SHA256SUMS` file and verify it before installation:

```bash
sha256sum --check SHA256SUMS
```

## Install from Git — alternative

Users with access to the private repository may install a pinned commit:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install \
  "git+https://github.com/saktush/teamstorm-api-examples.git@<commit>"
```

Or install a local checkout:

```bash
gh repo clone saktush/teamstorm-api-examples
cd teamstorm-api-examples
python3 -m venv .venv
.venv/bin/python -m pip install .
```

The import name remains `teamstorm`.

Behavioral compatibility notes for existing automations are collected in [`docs/technical-behavior.md`](docs/technical-behavior.md).

## Quick start

```python
import os
from teamstorm.client import TsClient
from teamstorm.api import TeamStormAPI

client = TsClient(
    base_url=os.environ["TEAMSTORM_BASE_URL"],
    token=os.environ["TEAMSTORM_API_TOKEN"],
)
api = TeamStormAPI(client)
workspace = api.workspaces.get("YOUR_WORKSPACE_KEY")
print(workspace.name)
```

See [`examples/quickstart.py`](examples/quickstart.py) for a runnable version. It uses the [`.env.template`](.env.template) names `BASE_URL`, `API_TOKEN`, and `WORKSPACE_KEY`; the `TEAMSTORM_*` names above belong only to the standalone snippet.

## Authentication and safety

`TsClient` adds an authorization header with the `PrivateToken` prefix. Store only the bare token in `TEAMSTORM_API_TOKEN`; never commit or log credentials. HTTPS is required by default. `allow_insecure=True` is only for a local mock server without real credentials.

With Hermes HTTP MCP, the working credential may come from request-header configuration rather than the server process environment. For a direct Python call, use the same source, remove exactly one `PrivateToken ` prefix, and pass the remainder to `TsClient`.

## Calling convention

Construct the exact request model rather than passing an arbitrary dictionary:

```python
from uuid import UUID
from teamstorm.models.workitems import CreateWorkitemRequestBody

body = CreateWorkitemRequestBody(
    name="Validate integration",
    type="Task",
    parent_id=UUID("00000000-0000-0000-0000-000000000001"),
)
item = api.workitems.create("SPACE", body)
```

Workspace-scoped methods take the workspace key first. Most `list()` methods collect all pages; use `client.iter_all()` for large result sets and validate each item with the matching model. PATCH calls distinguish an omitted field from an explicitly supplied `None`.

`TeamStormAPI` exposes 35 lazy resource properties for workspaces, folders, workitems, documents, agile, sprints, users, roles, attributes, comments, links, attachments, portfolios, integrations, queries, time tracking, time metrics (SLA/OLA), and more. The complete 170-operation map is in [`docs/api-coverage.md`](docs/api-coverage.md).

## Time metrics (SLA/OLA) and work calendars

Spec version 4.24.0 adds workitem time metrics. `enable` answers `409` when a metric for that template already exists on the workitem, even a disabled one; `start`, `stop` and `disable` answer `409` when the metric is already in the requested state; per the server source (the spec lists `409`), repeating `pause`/`resume` in the same state returns `204`, but a disallowed transition gives `409`. Do not retry a `409` blindly. Per the server source, `list`/`get` need `WorkspaceTimeMetrics` or read access to the workitem, while all write operations and the template list need `WorkspaceTimeMetrics`; listing work calendars is for system administrators only. Details: [`docs/api-analysis/upstream-semantics.md`](docs/api-analysis/upstream-semantics.md).

```python
from uuid import UUID
from teamstorm.models.time_metrics import (
    EnableWorkitemTimeMetricRequestBody,
    UpdateWorkitemTimeMetricSettingsRequestBody,
)

# 1. Pick a template and attach the metric to a workitem (it is created as NotStarted).
template = api.workitem_metric_templates.list("SPACE")[0]
created = api.workitem_time_metrics.enable(
    "SPACE",
    workitem_id="SPACE-1",
    body=EnableWorkitemTimeMetricRequestBody(template_id=template.id, limit_seconds=28800),
)
metric_id: UUID = created.id

# 2. Drive the timer: start -> pause -> resume -> stop.
metrics = api.workitem_time_metrics
metrics.start("SPACE", workitem_id="SPACE-1", metric_id=metric_id)
metrics.pause("SPACE", workitem_id="SPACE-1", metric_id=metric_id)
metrics.resume("SPACE", workitem_id="SPACE-1", metric_id=metric_id)
metrics.stop("SPACE", workitem_id="SPACE-1", metric_id=metric_id)

# 3. PATCH: only the fields you set are sent (unset = unchanged, explicit None = JSON null;
#    null is forbidden for type/limit_seconds/approach_threshold_percent/work_calendar_id, server 400).
metrics.update(
    "SPACE",
    workitem_id="SPACE-1",
    metric_id=metric_id,
    body=UpdateWorkitemTimeMetricSettingsRequestBody(limit_seconds=14400, spent_seconds=3600),
)

# 4. Work calendars are for system administrators only (HTTP 403 otherwise).
calendars = api.work_calendars.list()
```

## API coverage

| Area | Ops | API properties |
|---|---|---|
| Workspaces and folders | 10 | `workspaces`, `folders` |
| Agile and sprints | 9 | `agile`, `sprints` |
| Workitems | 10 | `workitems` |
| Comments | 9 | `workitem_comments`, `document_comments` |
| Links | 8 | `links`, `document_workitem_links` |
| Sharing | 8 | `workitem_sharing`, `document_sharing` |
| Attachments | 18 | `workitem_attachments`, `document_attachments` |
| Workspace configuration | 24 | `attributes`, `types`, `workflows`, `statuses` |
| Roles | 5 | `roles` |
| Users and groups | 18 | `users`, `groups`, `workspace_users`, `workspace_groups` |
| Documents | 12 | `documents`, `document_versions`, `document_statuses` |
| Portfolios | 12 | `portfolios`, `portfolio_elements` |
| Time tracking and queries | 5 | `time_tracking`, `queries` |
| Time metrics (SLA/OLA) and work calendars | 11 | `workitem_time_metrics`, `workitem_metric_templates`, `work_calendars` |
| Integrations | 11 | `git_integration_tokens`, `open_id`, `providers` |
| **Total** | **170** | 35 properties |

## Examples

- [`examples/quickstart.py`](examples/quickstart.py) — minimal read;
- [`examples/import_toolkit/`](examples/import_toolkit/) — Excel/CSV import and workspace-configuration synchronization;
- [`examples/README.en.md`](examples/README.en.md) — setup and commands;
- [`.agents/skills/teamstorm-api/`](.agents/skills/teamstorm-api/) — an operational guide for AI agents.

## Known live-API behavior

- Explicitly attaching an attribute to a workitem type returned HTTP 500 on the tested instance.
- Creating a workitem with an unattached custom attribute can return `AttributeNotFound`/404 even when the definition exists.
- Linking a portfolio element may commit server-side and then fail response-model validation because of an unexpected response shape. Read back state before retrying.

## Development

```bash
uv venv .venv
uv pip install --python .venv/bin/python ".[dev,examples]"
.venv/bin/python scripts/check_repository_positioning.py
.venv/bin/flake8 teamstorm/ examples/ tests/ scripts/
.venv/bin/black --check teamstorm/ examples/ tests/ scripts/
.venv/bin/mypy teamstorm/
.venv/bin/python -m pytest -q
```

CI runs on pull requests, pushes to `main`, and manual dispatch. See [`CONTRIBUTING.md`](CONTRIBUTING.md), [`AGENTS.md`](AGENTS.md), and the [MIT license](LICENSE).
