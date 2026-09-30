---
name: teamstorm-api
description: Use TeamStorm API Examples from Python for typed CWM Public API automation, reusable scripts, batching, and endpoint coverage beyond a simple MCP call.
---

# TeamStorm API automation

## When to use

Use this repository for reusable Python automation, batching, composition, typed request/response handling, or endpoints unavailable through another integration. For a simple one-off action already covered by TeamStorm MCP, prefer the MCP tool.

The repository is a reference implementation and example collection. Treat the committed OpenAPI snapshot, resource modules, and live TeamStorm responses as the sources of truth; inspect current signatures instead of guessing.

## Install and import

Prefer the versioned local release archive. It can be transferred to a machine without Git access:

```bash
python3 -m zipfile -e teamstorm-api-examples-1.1.0.zip .
python3 -m venv .venv
.venv/bin/python -m pip install ./teamstorm-api-examples-1.1.0
```

Verify the archive with its published `SHA256SUMS` before installation. The archive does not bundle third-party dependencies; stage compatible wheels separately for a fully offline target.

Git installation is an alternative for users with repository access. Pin a trusted commit:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install \
  "git+https://github.com/saktush/teamstorm-api-examples.git@<commit>"
```

The import package remains `teamstorm`:

```python
import os

from teamstorm.client import TsClient
from teamstorm.api import TeamStormAPI

client = TsClient(
    base_url=os.environ["TEAMSTORM_BASE_URL"],
    token=os.environ["TEAMSTORM_API_TOKEN"],
)
api = TeamStormAPI(client)
```

Python 3.11+ is required. Runtime dependencies are `requests` and pydantic v2.

## Authentication and client behavior

- `TsClient` adds the `PrivateToken ` authorization prefix. Pass only the bare token.
- Use HTTPS with real credentials. `allow_insecure=True` is only for a local mock server without real secrets.
- Reuse one client across workspaces; workspace-scoped methods receive `workspace_key` explicitly.
- Configure timeouts and retries with `TimeoutConfig` and `RetryConfig` when defaults are unsuitable.
- Transport and non-success HTTP failures raise `ApiError`; preserve status/method/path in diagnostics and redact headers, tokens, URLs containing secrets, and sensitive bodies.
- Low-level methods include `get`, `get_all`, `iter_all`, `get_bytes`, `post`, `post_multipart`, `put`, `patch`, and `delete`. Prefer typed resource methods and do not guess raw paths.

With Hermes HTTP MCP, the active credential may be in `mcp_servers.teamstorm.headers.Authorization` rather than the server process environment. Use the same request-header source, remove exactly one `PrivateToken ` prefix, and pass the remainder to `TsClient`. Never print either value.

## Core calling rules

1. Pass `workspace_key` first for workspace-scoped methods.
2. Build the exact pydantic request model; do not guess dictionaries, field aliases, enum values, or identifiers.
3. Keep string workitem/document keys as strings. Use `UUID` only where the model requires it.
4. Prefer keyword arguments after the workspace key when a method signature uses keyword-only parameters.
5. Most `list()` methods collect all pages. For very large datasets, use `client.iter_all()` and validate each raw item with the matching model.
6. Use `model_dump(mode="json", exclude_none=True)` for ordinary custom serialization.
7. PATCH methods distinguish an omitted field from an explicitly supplied `None`: omitted means unchanged; explicit `None` is sent as JSON `null`.
8. Treat create, patch, delete, membership, sharing, comments, links, uploads, and token operations as side effects.
9. Do not retry a non-idempotent call until read-back proves that the first attempt did not commit.
10. Inspect exact signatures when uncertain:

```python
import inspect
print(inspect.signature(api.workitems.list))
```

## Grouped API

`TeamStormAPI` exposes 35 lazy resource properties:

- Core: `workspaces`, `folders`, `workitems`, `users`, `groups`.
- Planning: `agile`, `sprints`, `portfolios`, `portfolio_elements`.
- Configuration: `types`, `workflows`, `statuses`, `attributes`, `roles`.
- Membership: `workspace_users`, `workspace_groups`.
- Collaboration: `workitem_comments`, `document_comments`, `links`, `workitem_sharing`, `document_sharing`.
- Documents/files: `documents`, `document_versions`, `document_statuses`, `document_workitem_links`, `workitem_attachments`, `document_attachments`.
- Integrations/reporting: `providers`, `open_id`, `git_integration_tokens`, `queries`, `time_tracking`.
- Time metrics (SLA/OLA, v4.24.0): `workitem_time_metrics`, `workitem_metric_templates`, `work_calendars` (system administrators only).

The exact map of all 170 committed OpenAPI operations to wrapper methods is in `docs/api-coverage.md`. Resource implementations are under `teamstorm/api/`; request and response models are under `teamstorm/models/`.

## High-value method guide

- Workspaces: `create`, `get`, `list`, `patch`, `delete`.
- Folders: `create`, `get`, `list`, `patch`, `delete`.
- Workitems: `create`, `get`, `list`, `list_by_parent`, `list_updates`, `count`, `patch`, `delete`, `list_attributes`, `update_attribute`.
- Agile: `create`, `create_simple`, `get`, `list`, `delete`.
- Sprints: `create`, `get`, `list`, `patch`, `delete`.
- Attributes: CRUD plus `add_option`, `patch_option`, `delete_option`.
- Types: CRUD plus `add_attribute` and `remove_attribute`.
- Users and groups: tenant lookup/management plus workspace membership and role assignment through `workspace_users` and `workspace_groups`.
- Documents: CRUD, block/unblock, versions, statuses, comments, links, sharing, and attachments.
- Workitems: comments, sharing, typed links, attachments, custom attribute values, portfolio pinning, and time tracking.
- Integrations: provider reads, OpenID connections/users, Git integration tokens, and saved-query operations.

Always confirm the method signature and request model in the current checkout before a mutation.

## Common request models

Typical imports include:

- `CreateWorkitemRequestBody`, `PatchWorkitemRequestBody` from `teamstorm.models.workitems`.
- `CreateFolderRequestBody` from `teamstorm.models.folders`.
- `CreateSprintRequestBody` from `teamstorm.models.sprints`.
- `CreateDocumentRequestBody` and document patch bodies from `teamstorm.models.documents`.
- `CreateCommentRequestBody` from `teamstorm.models.comments`.
- Portfolio and portfolio-element bodies from `teamstorm.models.portfolios`.
- Attribute/type/workflow/role bodies from their matching modules.
- Shared enums such as `AttributeType`, `EstimatesType`, `SprintStates`, `SharedItemAccessLevel`, `ProgressType`, `TypeIcon`, and `TypeColor` come from `teamstorm.models.enums`; `Permission` comes from `teamstorm.models.roles` (and is re-exported by `teamstorm.models`).

Example:

```python
from uuid import UUID

from teamstorm.models.workitems import CreateWorkitemRequestBody

body = CreateWorkitemRequestBody(
    name="Validate integration",
    type="Task",
    parent_id=UUID("00000000-0000-0000-0000-000000000001"),
)
item = api.workitems.create("SPACE", body)
print(item.id, item.name)
```

Workitem custom attributes are discriminated by `type`; values differ for strings, numbers, dates, selections, tags, users, and time durations. Inspect `teamstorm.models.workitems_attributes_create` and the target type before constructing them.

## Safe operational patterns

### Read before update

```python
items = api.workitems.list("SPACE", name="release", max_items_count=50)
for item in items:
    print(item.id, item.name, item.status)
```

Before patching, confirm the selected item and current state. After patching, call `get` in a separate step and compare returned fields.

### Pagination

Do not report totals from a single server page. Typed `list()` methods normally collect all pages. With `iter_all()`, use the exact resource path from the implementation and validate every raw record.

### Attachments and links

Uploads, comments, and links are non-idempotent. Use a deterministic small fixture, record returned identifiers, and read back the parent object before retrying an ambiguous failure.

## Known live behavior

Observed behavior is instance/version specific and must be rechecked against the current server:

- Explicit type-to-attribute binding may return HTTP 500.
- A custom attribute that exists but is not attached to the workitem type may produce `AttributeNotFound`/404 during workitem creation.
- A portfolio-element link may commit and then return a shape that fails response-model validation. Read the portfolio element and linked workitems before any retry.

Use `references/swagger-attribute-binding.md` for the isolated diagnostic. Do not alter an existing production type to investigate it.

## Real API smoke testing

Follow `references/smoke-testing.md`.

1. Install a pinned commit in a fresh environment.
2. Start with a harmless authenticated read such as `api.workspaces.list()`.
3. Stop before any write on 401/403; do not substitute MCP-created objects for Python-wrapper coverage.
4. Use a uniquely named dedicated workspace for mutations.
5. Record every created identifier and redacted error.
6. Verify created state from a new process.
7. Leave cleanup to an explicit instruction.

A blocked authentication preflight is not evidence that the wrappers are broken.

## Verification checklist

- [ ] Trusted Git revision installed in the intended environment.
- [ ] `teamstorm`, `TsClient`, and `TeamStormAPI` imports succeed.
- [ ] Base URL uses HTTPS and the token comes from a secret source.
- [ ] Correct `TeamStormAPI` property, method signature, and request model selected.
- [ ] Workspace and identifier types verified.
- [ ] Pagination handled before totals are reported.
- [ ] Side effects explicitly authorized and scoped.
- [ ] Non-idempotent failures read back before retry.
- [ ] Responses verified through typed fields or `model_dump()`.
- [ ] Tokens and authorization headers absent from logs and artifacts.
