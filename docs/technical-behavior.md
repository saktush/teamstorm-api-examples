# Technical behavior and migration notes

This document preserves behavioral knowledge that matters when adapting existing TeamStorm automation to this repository. It is not a release history or a compatibility promise.

## Current imports

Use the transport and grouped API directly:

```python
from teamstorm.client import TsClient
from teamstorm.api import TeamStormAPI

client = TsClient(base_url="https://your-cwm-host", token="YOUR_API_TOKEN")
api = TeamStormAPI(client)
workspace = api.workspaces.get("WS")
```

The import package remains `teamstorm`. Earlier grouped-entrypoint names and paths are intentionally not retained: this repository presents reusable API wrappers and examples rather than a separately supported client product. Existing automation should import `TeamStormAPI` from `teamstorm.api` before following future changes.

## Client workspace handling

`TsClient` does not accept or store a workspace key. The transport is reusable across workspaces. Pass the workspace key to each workspace-scoped resource method:

```python
first = api.workspaces.get("SPACE_A")
second = api.workspaces.get("SPACE_B")
```

## Workitem links

`CreateWorkitemLinkRequestBody` requires `linked_workspace`, in addition to the link type and linked workitem. The server already rejects incomplete requests.

```python
from teamstorm.models.links import CreateWorkitemLinkRequestBody

body = CreateWorkitemLinkRequestBody(
    type="RELATES",
    linked_workspace="TARGET_SPACE",
    linked_workitem="TS-42",
)
```

`linked_workspace` is the key or ID of the workspace containing the target workitem. See [`api-analysis/upstream-semantics.md`](api-analysis/upstream-semantics.md#links) for the wire-level semantics.

## Explicit `None` in partial updates

A partial-update body distinguishes:

- an omitted field — leave the server value unchanged;
- a field explicitly set to `None` — send JSON `null` and clear the server value where supported.

The resource wrappers therefore serialize true partial-update bodies with:

```python
body.model_dump(mode="json", exclude_unset=True, exclude_none=False)
```

Audit existing call sites that pass `None`: it is a requested clear operation, not a no-op. The same rule applies to `WorkitemsAPI.update_attribute`, where a required nullable `value` is used to clear an attribute. Detailed exceptions and rationale are in [`api-analysis/conventions.md`](api-analysis/conventions.md).

## Import toolkit execution

The import toolkit is an example application under `examples/import_toolkit/`; it is not installed as command-line entry points. From a checkout, install the example dependencies and run the scripts directly:

```bash
python -m pip install -e ".[examples]"
python examples/import_toolkit/import_agile.py --help
python examples/import_toolkit/sync_uniselect_options.py --help
```

See [`../examples/README.en.md`](../examples/README.en.md) or [`../examples/README.md`](../examples/README.md) for the complete options, file formats, dry-run behavior, and safety workflow.

## Removed loose placeholders

The intentionally loose or superseded model placeholders from earlier revisions are not part of the current surface. Use the concrete request and response models under `teamstorm.models`; unknown fields are rejected by default so schema drift is visible rather than silently accepted.
