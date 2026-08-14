# TeamStorm API wrappers — conventions guide

Evidence-based, read-before-you-code reference for adding new modules to the `teamstorm` API wrappers
(TeamStorm CWM Public API client).

**Provenance.** This guide was originally written against commit `64ed8f5` on branch `dev`
(2026-07-15), before the `cwm` → `teamstorm` rename and typing modernization. It was
subsequently revised to reflect the rename, type annotations, docstrings, and
PATCH-serialization behavior in the current code.

**On `file:line` citations: treat them as indicative, not exact.** Every public
definition in `teamstorm/` gained a docstring during the implementation work (commits `7bcaa89`
and `5780f4f`), which shifted most line numbers — in places by more than 150 lines —
without moving the code they describe. A citation like `teamstorm/api/workitems.py:86`
means "this symbol lives in this file somewhere near here," not "open this file and
look at line 86." If a citation and the file disagree, **search the file by symbol
name** and trust what you find there.

**When this document and the code disagree, the code wins.** The current, authoritative
sources are, in order: the code itself, `docs/openapi/swagger-v4.18.0.json` (the committed
spec snapshot), `docs/api-coverage.md` (generated, cross-checked coverage), and
`tests/api/` (behavior pinned by tests). This document is a map, not the territory —
useful for orientation, not a substitute for reading the file you're about to change.

Jump to section 11 for ready-to-paste templates.

---

## 1. API class pattern

**Base class.** Every `*API` class subclasses `BaseAPI`:

```python
# teamstorm/api/_base.py -- BaseAPI (docstring omitted for brevity)
from __future__ import annotations

from dataclasses import dataclass

from teamstorm.client import TsClient


@dataclass(frozen=True, slots=True)
class BaseAPI:
    client: TsClient
```

`@dataclass(frozen=True, slots=True)` is the exact decorator/params used — frozen
(immutable) and slotted. `TeamStormAPI` itself (`teamstorm/api/_entrypoint.py`) uses the
identical `@dataclass(frozen=True, slots=True)` decorator.

**Subclassing** is a one-liner, no `__init__` override, no extra fields:

```python
# teamstorm/api/workitems.py
class WorkitemsAPI(BaseAPI):
```

```python
# teamstorm/api/attributes.py
class AttributesAPI(BaseAPI):
```

**Method naming.** Verbs map directly onto HTTP semantics:
- `list(...)` — GET collection, always returns `list[Model]`
- `get(...)` — GET single resource
- `create(...)` — POST
- `patch(...)` — PATCH, a true partial-merge (see §4)
- `delete(...)` — DELETE, always returns `None`

**No method is literally named `put`**, but `TsClient.put()` (a real, named transport
method — not merely a fallback) backs several `*API` methods that are full-replace by
spec and are named `update(...)` / `update_visibility(...)` / `refresh(...)` instead of
`patch`: comment update and comment/query visibility (`teamstorm/api/comments.py`,
`teamstorm/api/queries.py`), and git-integration-token update/refresh
(`teamstorm/api/integrations.py`). `WorkitemsAPI.update_attribute`
(`teamstorm/api/workitems.py`, symbol `update_attribute`) is the one place PUT is used
with a PATCH fallback on 404/405 — see gotcha in §10 — every other `put()` call site is
a plain, unconditional PUT with no fallback. Resource-specific extra verbs exist and are
named after the sub-resource, not generically: `list_categories`
(`teamstorm/api/statuses.py`), `list_attributes` / `update_attribute`
(`teamstorm/api/workitems.py`),
`add_option` / `patch_option` / `delete_option` (`teamstorm/api/attributes.py`),
`add` / `remove` / `get_roles` / `add_role` / `remove_role`
(`teamstorm/api/workspace_users.py`, `teamstorm/api/workspace_groups.py`),
`add_attribute` / `remove_attribute` (`teamstorm/api/types.py`), and one
"friendly overload" `create_simple` that wraps `create` (`teamstorm/api/agile.py`).

**Workspace path segment.** For workspace-scoped resources, `workspace_key: str`
is always the **first positional parameter**, and every other filter/id is
keyword-only after `*`:

```python
# teamstorm/api/attributes.py -- AttributesAPI.list
def list(
    self,
    workspace_key: str,
    *,
    name: str | None = None,
    is_full_name_matching: bool | None = None,
    type: AttributeType | None = None,
) -> list[AttributeModel]:
```

Global (non-workspace) resources simply omit `workspace_key`, e.g.
`WorkspacesAPI.list` (`teamstorm/api/workspaces.py`), `UsersAPI.list`
(`teamstorm/api/users.py`), `GroupsAPI.list` (`teamstorm/api/groups.py`).

**Path construction.** Plain f-strings — there is **no path-builder helper**.
Every API module builds the path inline:

```python
# teamstorm/api/workitems.py -- inside WorkitemsAPI.list
data = self.client.get_all(
    f"/workspaces/{workspace_key}/workitems",
    params=params or None,
)
```

```python
# teamstorm/api/types.py -- TypesAPI.add_attribute
def add_attribute(self, workspace_key: str, *, type_key: str, attribute_id: UUID) -> TypeModel:
    data = self.client.post(
        f"/workspaces/{workspace_key}/types/{type_key}/attributes/{attribute_id}",
        body={},
    )
```

UUID path segments are interpolated directly (f-strings call `str()` implicitly);
UUID **query-param** values are explicitly cast, see §10.

**Return types.** Every non-delete method returns a pydantic model or
`list[model]` — **never a raw dict**. `TsClient` (the transport layer) always
returns untyped JSON (`Any`/`dict`/`list`, see `teamstorm/client.py`, methods
`get`/`post`/`patch`/`put`/`delete`); the
`*API` layer is exclusively responsible for turning that into typed, validated
domain objects. This is the entire reason the split between `teamstorm/client.py` and
`teamstorm/api/*.py` exists: the transport stays generic and endpoint-agnostic, and
validation/typing is centralized at the API boundary (proven by
`tests/api/test_api_attributes.py` and `tests/api/test_api_workitems_filters.py`
(search each for `ValidationError`), which assert that a `pydantic.ValidationError`
is raised from the API method itself when the raw payload doesn't match the
schema — the client never validates anything).

Concretely:
- list → `TypeAdapter(list[Model]).validate_python(data)`
- get/create/patch → `Model.model_validate(data)`
- delete → `self.client.delete(...); return None`

---

## 2. Pagination

`TsClient` owns pagination; `*API` classes never see raw tokens.

```python
# teamstorm/client.py -- TsClient.iter_all / TsClient.get_all (abridged)
def iter_all(self, path: str, *, params: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
    """
    Lazy generator over all paginated items at *path*.
    ...
    """
    ...

def get_all(self, path: str, *, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """
    Collect all paginated items at *path* into a list.
    ...
    """
    return list(self.iter_all(path, params=params))
```

**Hard rule observed in every single `*API` class:** `list()` methods call
`self.client.get_all(...)`, never `self.client.iter_all(...)` directly. Grep
confirms this — `iter_all` is referenced only inside `teamstorm/client.py` itself (its
own definition, its docstring, and `get_all`'s one-line body); no file under
`teamstorm/api/`, `examples/import_toolkit/controllers/`, or
`examples/import_toolkit/workflows/` calls `iter_all` directly. So today, **every `list()` method is
eager and returns a materialized `list[Model]`** — there is no lazy/generator
return type anywhere in the `*API` layer. `iter_all` exists on `TsClient` as a
memory-conscious escape hatch for future large-collection consumers, but no
existing convention shows how to expose it through an `*API` class — if you add
one, you are establishing new precedent, not following one.

**Signature convention** for any `list()`:
```python
def list(
    self,
    workspace_key: str,        # omit for global resources
    *,
    <filter_1>: X | None = None,
    ...
    from_token: str | None = None,        # only if the endpoint's swagger exposes it
    max_items_count: int | None = None,    # only if the endpoint's swagger exposes it
) -> list[Model]:
    params: dict[str, Any] = {}
    if <filter_1> is not None:
        params["<camelCaseFilter1>"] = <filter_1>
    ...
    data = self.client.get_all(f"/workspaces/{workspace_key}/<resource>", params=params or None)
    return TypeAdapter(list[Model]).validate_python(data)
```
See `WorkitemsAPI.list` (`teamstorm/api/workitems.py`) and `WorkspacesAPI.list`
(`teamstorm/api/workspaces.py`) for the two fullest real examples (workitems has
11 filters, workspaces has pagination params).

---

## 3. Pydantic conventions

**Pydantic v2**, confirmed by `pyproject.toml`'s `[project.dependencies]`
(`"pydantic>=2.0"`) and the installed venv (`pydantic==2.12.5`). All model-layer
code uses v2-only APIs: `model_validate`, `model_dump`,
`model_config = ConfigDict(...)`, `TypeAdapter`.

**Canonical base class** — always use this one for new models:

```python
# teamstorm/models/base.py -- TsBaseModel
class TsBaseModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        kwargs.setdefault("by_alias", True)
        kwargs.setdefault("exclude_none", True)
        kwargs.setdefault("mode", "json")
        return super().model_dump(**kwargs)

    def model_dump_json(self, **kwargs: Any) -> str:
        kwargs.setdefault("by_alias", True)
        kwargs.setdefault("exclude_none", True)
        return super().model_dump_json(**kwargs)
```

Config: `populate_by_name=True` (lets you construct with either the Python
snake_case field name or the JSON alias) + `extra="forbid"` (strict — unknown
fields raise `ValidationError`, proven by `tests/api/test_models_types.py:82-102`).
`model_dump`/`model_dump_json` are overridden so that **by default** every dump
is `by_alias=True, exclude_none=True, mode="json"` — callers don't have to
remember this, but see §4/§10 for how the API layer calls it anyway.

There used to be two additional base classes here — a discouraged legacy base
`CwmModel` (`teamstorm/models/common.py`) and a deliberately loose placeholder
`UnknownModel` (`teamstorm/models/base.py`) for not-yet-modeled nested objects.
Both were verified dead (unused anywhere in `teamstorm/`, `tests/`, or
`examples/` — every field that used to fall back to `UnknownModel`, e.g.
`WorkitemModel.author`/`.assignee`/`.folder`/`.changed_by`, is now typed with a
real model) and were deleted during the Task 4 typing/pydantic audit. Do not
reintroduce either; model every field with a real, strict `TsBaseModel`
subclass instead.

**camelCase ↔ snake_case mapping**: every JSON-camelCase field gets a
snake_case Python attribute plus an explicit `Field(alias="camelCase")`:

```python
# teamstorm/models/common.py -- UserModel
class UserModel(TsBaseModel):
    id: UUID
    display_name: str = Field(alias="displayName")
    username: str
    email: str | None = None
    provider_id: UUID | None = Field(default=None, alias="providerId")
```

There is no `alias_generator` anywhere in the codebase (checked — none of the
`ConfigDict(...)` calls set one). Aliasing is always done per-field with
`Field(alias=...)`. Fields whose JSON name already matches Python (`id`, `name`,
`type`, `description`, `username`, `email`, `workdays`, ...) get no `Field(...)`
at all.

**Optional fields**: `X | None = None` (PEP 604) or, when aliased,
`X | None = Field(default=None, alias="camelCase")`. Required aliased fields
use `Field(alias="camelCase")` with no default, e.g.
`parent_id: UUID = Field(alias="parentId")` (`teamstorm/models/folders.py`,
`FolderModel.parent_id`). See §9 for the typing style this codebase actually
uses now — it is not `Optional[X]`.

**Enums**: stdlib `enum.StrEnum` (requires Python ≥3.11; `pyproject.toml` now
correctly declares `requires-python = ">=3.11"` — see §9), member value always
equal to the literal API string:

```python
# teamstorm/models/enums.py -- AttributeType
from enum import StrEnum

class AttributeType(StrEnum):
    UniString = "UniString"
    Number = "Number"
    Date = "Date"
    UniSelect = "UniSelect"
    Tag = "Tag"
    User = "User"
    TimeDuration = "TimeDuration"
```

Discriminated unions (polymorphic "attribute value" shapes) use
`Literal[EnumMember]` as a tag plus `Field(discriminator="type")`:

```python
# teamstorm/models/attributes.py -- AttributeFieldValue
AttributeFieldValue = Annotated[
    UniStringFieldValueModel
    | NumberFieldValueModel
    | DateFieldValueModel
    | UniSelectFieldValueModel
    | TagFieldValueModel
    | UserFieldValueModel
    | TimeFieldValueModel,
    Field(discriminator="type"),
]
```

**Datetime handling**: two patterns coexist. (1) A loose alias
`DateTimeLike = datetime | str` (`teamstorm/models/common.py`) used for
response/request date fields that the API is inconsistent about
(e.g. `teamstorm/models/workitems.py`'s `start_date`/`due_date`/`end_date`/`created_date`
fields, `teamstorm/models/sprints.py`'s `start_date`/`end_date`). (2) A strict
`datetime` type used directly where the swagger schema is unambiguous
(`teamstorm/models/workitems_attributes_create.py`'s `CreateDateFieldRequestBody.value:
datetime`, `teamstorm/models/workitems_attributes_update.py`'s `UpdateDateFieldRequestBody.value:
datetime | None`).

---

## 4. Model → API wiring

**Validating a response** — two exact call forms, chosen by cardinality:

```python
# single object -- teamstorm/api/workspaces.py, WorkspacesAPI.get
data = self.client.get(f"/workspaces/{workspace_key}")
return WorkspaceModel.model_validate(data)
```

```python
# list -- teamstorm/api/workitems.py, inside WorkitemsAPI.list
return TypeAdapter(list[WorkitemModel]).validate_python(data)
```

`TypeAdapter(list[Model])` (not `parse_obj_as`, not a hand-rolled loop) is the
only pattern used for list validation across every `*API` class (32 of them,
per §6).

**Serializing a request body — two different rules depending on the verb.**

**POST/PUT (full representation)** — the exact, dominant call is:

```python
# teamstorm/api/workitems.py -- WorkitemsAPI.create (identical form repeated in
# attributes.py, types.py, sprints.py, workflows.py, agile.py, roles.py, workspaces.py, ...)
payload = body.model_dump(mode="json", exclude_none=True)
data = self.client.post(f"/workspaces/{workspace_key}/workitems", payload)
```

Note this is technically redundant with `TsBaseModel.model_dump`'s own
defaults (`by_alias=True, exclude_none=True, mode="json"` are already the
defaults per §3) — but the house style is to spell out `mode="json",
exclude_none=True` explicitly at every call site anyway.

**PATCH (true partial-merge — see `docs/api-analysis/upstream-semantics.md`
§7)** — the required call is the opposite of the POST/PUT one:

```python
# teamstorm/api/folders.py -- FoldersAPI.patch (identical form in attributes.py, roles.py,
# sprints.py, types.py, workflows.py, workspaces.py, workitems.py, documents.py,
# portfolios.py)
payload = body.model_dump(mode="json", exclude_unset=True, exclude_none=False)
data = self.client.patch(f"/workspaces/{workspace_key}/folders/{folder_id}", payload)
```

The server's partial-update handling distinguishes
a JSON key that is **absent** (leave the field unchanged) from one **present
with value `null`** (clear the field). `TsBaseModel.model_dump()` defaults to
`exclude_none=True`, which collapses that distinction — an explicit "clear
this field" `None` would be silently dropped and become a no-op "leave
unchanged" instead. Every true partial-merge PATCH call site must override
both `exclude_unset=True` and `exclude_none=False` explicitly; do not rely on
the base class defaults for a PATCH body.

**Exceptions — these do NOT need the PATCH treatment above and keep
`exclude_none=True` despite the verb:**
- Attribute-*option* rename (`AttributesAPI.patch_option`,
  `PATCH .../attributes/{attributeId}/options`) — both `id` and `name` are
  required, non-nullable fields, so there is no nullable field to clear.
- Comment update, comment/query visibility, and git-integration-token
  update/refresh — PUT full-replace bodies, so the POST/PUT rule above applies.

**Two borderline cases where the partial-merge form is used anyway, and that
is fine:**
- `PortfoliosAPI.patch` (`PATCH /portfolios/{id}`) — a mandatory single-field
  rename with no server-side `IsPresent` tracking. `name` is required, so
  `exclude_unset=True` always emits it; the payload is byte-identical either way.
- `DocumentsAPI.patch` (`PATCH /documents/{document}`) — the body only carries
  `status`. Same reasoning.

**One PUT that DOES need the partial-merge form** despite being a full replace:
`WorkitemsAPI.update_attribute`. Its `Update*FieldRequestBody.value` is
required *and* nullable — `value: null` is the documented way to clear an
attribute — so `exclude_none=True` would drop a required key and turn the
clear into a silent no-op. `exclude_unset=True` is safe here because both
`type` and `value` are required (never unset), while it still trims the
untouched optional keys of a nested value object such as
`UpdateUserFieldValueModel`.

`mode="json"` matters because it forces `UUID`/`datetime`/enum values to be
turned into plain `str` in the dumped dict so `requests`'s `json=` kwarg can
serialize it — see the inline comment in `teamstorm/api/agile.py`
(`AgileAPI.create`):
```python
# Важно: mode="json" чтобы UUID стал str и ушёл в JSON без ошибок
payload = body.model_dump(mode="json", exclude_none=True)
```

*(Corrected: an earlier revision of this guide flagged `teamstorm/api/folders.py`'s
`create()` as the one call site omitting `mode="json"`. That was fixed during the
`cwm` → `teamstorm` rename, well before this branch — `folders.py` now uses the
same explicit `mode="json", exclude_none=True` form as every other module. There
is no known deviation from the dominant POST/PUT form today.)*

---

## 5. Exports

**`teamstorm/api/__init__.py`** (currently 68 lines): imports every concrete
`*API` class plus `BaseAPI`, then repeats every name in a single `__all__` list
sorted **alphabetically by class name**:
```python
from teamstorm.api._base import BaseAPI
from teamstorm.api.agile import AgileAPI
from teamstorm.api.attributes import AttributesAPI
from teamstorm.api.folders import FoldersAPI
...
__all__ = [
    "BaseAPI",
    "AgileAPI",
    "AttributesAPI",
    "FoldersAPI",
    ...
]
```

**`teamstorm/models/__init__.py`** (currently 328 lines): imports symbols
**grouped by source module** (`from .attributes import (...)`, `from .common
import (...)`, etc., each import block alphabetized internally), then a single
flat `__all__` list at the bottom, alphabetically sorted across all modules.

**Important gap — not a bug to "fix" silently, but a fact to know:** the workitems
family is only *partially* re-exported. `teamstorm/models/__init__.py` imports
`WorkitemsCountModel` from `.workitems` and the `Update*FieldRequestBody` /
`UpdateWorkitemAttributeRequestBody` variants from `.workitems_attributes_update`
— those ARE importable as `from teamstorm.models import ...` today. But
`WorkitemModel`, `CreateWorkitemRequestBody`, and `PatchWorkitemRequestBody`
(also in `.workitems`), the whole of `teamstorm/models/workitems_thumbs.py`, and
the whole of `teamstorm/models/workitems_attributes_create.py` are **not**
re-exported (verified: `from teamstorm.models import WorkitemModel` raises
`ImportError`). Every real call site imports the unexported ones directly from
their submodule:
```python
# teamstorm/api/workitems.py -- current import block
from teamstorm.models.workitems import (
    CreateWorkitemRequestBody,
    PatchWorkitemRequestBody,
    WorkitemModel,
    WorkitemsCountModel,
)
from teamstorm.models.workitems_attributes_update import UpdateWorkitemAttributeRequestBody
```
For a **new top-level resource module**, the default

... [OUTPUT TRUNCATED - 6,731 chars omitted out of 56,659 total] ...

e none. The
one place this does *not* extend to is `examples/import_toolkit/` (the example
toolkit): still zero docstrings there as of this writing — don't assume the
wrapper convention carries over to the examples.

**The style is not perfectly uniform, but converges on a common shape.** The
dominant form is Sphinx-ish: a short prose summary, then `:param name:` lines,
a `:return:` line, and a trailing `HTTP: <VERB> <path>` line naming the exact
endpoint (cross-checked against `docs/openapi/swagger-v4.18.0.json` and the coverage
manifest when it was written — no mismatches found at the time):

```python
# teamstorm/api/folders.py -- FoldersAPI.create (dominant style)
def create(self, workspace_key: str, body: CreateFolderRequestBody) -> FolderModel:
    """
    Create a new folder.

    :param workspace_key: workspace key or id.
    :param body: CreateFolderRequestBody -- required name; parent_id is
        nullable in the spec but should still be provided (pass the
        workspace's own GUID to place the folder at the workspace root --
        see the model's own docstring for the underlying server quirk).
    :return: the created FolderModel.
    HTTP: POST /workspaces/{workspace}/folders
    """
```

A minority of methods (notably in `teamstorm/api/users.py`) instead use a
Google-style `Args:`/`Returns:` block, still ending in the same `HTTP:` line:

```python
# teamstorm/api/users.py -- UsersAPI.get (minority style, same file as the
# doc's old "only docstring in the repo" example -- that claim is long obsolete)
def get(self, user: str, *, provider_id: UUID | None = None) -> UserModel:
    """
    Retrieve a single user by id or username.

    This is a global (non-workspace-scoped) resource.

    Args:
        user: user id (UUID) or username identifying the account.
        provider_id: optional identity provider UUID, used to disambiguate
            a username that exists under more than one provider.

    Returns:
        UserModel: the matching user.

    HTTP: GET /users/{user}
    """
```

Both are "in convention" — the one hard rule is that the `HTTP: <VERB> <path>`
line is present on essentially every `*API` method, since that's what makes the
docstring cross-checkable against the spec without opening `swagger-v4.18.0.json` in
another window. When adding a new method, either style is acceptable; match
whichever style already dominates the file you're editing.

`TsClient`'s own docstrings follow the same short-imperative-paragraph shape,
e.g. `iter_all`/`get_all` (`teamstorm/client.py`) explain the lazy-vs-eager
tradeoff and the pagination safety guards (max page count, repeated-token
detection).

**Model classes** are documented separately and more tersely, as a
"Swagger: X / required: ..." note (this part of the guide was already accurate
and still is):
```python
# teamstorm/models/folders.py -- FolderModel
class FolderModel(TsBaseModel):
    """
    Swagger: FolderModel [1]
    required: id, name, parentId
    """
```

**Language note**: docstrings and model notes are English. Some inline
*comments* and all runtime `ApiError` messages are Russian (e.g.
`teamstorm/client.py`'s `f"HTTP ошибка {method} {path}: {e}"` and
`f"API вернул {resp.status_code} для {method} {path}"`,
`teamstorm/api/agile.py`'s `# query params должны быть строками`). There is no
single enforced language — match whatever the surrounding file already uses.

---

## 8. Testing conventions

**Framework: stdlib `unittest`**, not pytest-style. 56 `test_*.py` files under
`tests/` do `import unittest`, define `class XTestCase(unittest.TestCase)`,
and end with:
```python
if __name__ == "__main__":
    unittest.main()
```
None import `pytest` or use fixtures/`conftest.py` (there is none) — **the test
code itself is unittest-style throughout**, even though `pytest -q` is now the
documented way to *run* the suite (see "How tests are run" below and
`CONTRIBUTING.md`). `pytest` happily discovers and runs `unittest.TestCase`
classes, so the two are not in tension: it's the runner, not the framework.
Don't be misled into writing pytest-style fixtures or `@pytest.mark` decorators
just because `pytest` is the command you type — there is still no `conftest.py`
anywhere in the repo, and new tests should keep using `unittest.TestCase` +
`MagicMock`. The `.pytest_cache/` directory in the repo root is an expected
artifact of normal `pytest -q` usage now, not a stray leftover.

**Mocking approach**: a bare `unittest.mock.MagicMock()` stands in for the
whole `TsClient`; the real `*API` class is instantiated around it (no fake
client subclass, no HTTP-level interception, no `requests_mock`). Return
values are set per-method on the mock, and calls are asserted with
`assert_called_once_with` / `assert_any_call`. The one exception is
`tests/api/test_client.py`, which patches `client.session.request` directly with
`unittest.mock.patch.object`, because that file tests the transport itself
(`TsClient`), not an `*API` wrapper.

**Complete, real, copy-pasteable example** (`tests/api/test_api_attributes.py`,
lines 1-55 verbatim as of this writing — the pattern to imitate for any new
resource):
```python
import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from pydantic import ValidationError

from teamstorm.api.attributes import AttributesAPI
from teamstorm.models.attributes import (
    CreateAttributeOptionRequestBody,
    CreateAttributeRequestBody,
    PatchAttributeOptionRequestBody,
    PatchAttributeRequestBody,
)
from teamstorm.models.enums import AttributeType


def _attribute_payload() -> dict:
    return {
        "id": str(uuid4()),
        "name": "Severity",
        "description": "Ticket severity",
        "type": "UniSelect",
        "options": [{"id": str(uuid4()), "name": "High"}],
        "workitemTypes": [{"id": str(uuid4()), "name": "Bug"}],
    }


class AttributesAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = AttributesAPI(self.client)
        self.workspace = "WS"
        self.attribute_id = uuid4()
        self.option_id = uuid4()

    def test_list_uses_get_all_with_filters_and_parses(self) -> None:
        self.client.get_all.return_value = [_attribute_payload()]

        result = self.api.list(
            self.workspace,
            name="Severity",
            is_full_name_matching=True,
            type=AttributeType.UniSelect,
        )

        self.client.get_all.assert_called_once_with(
            "/workspaces/WS/attributes",
            params={
                "name": "Severity",
                "isFullNameMatching": True,
                "type": "UniSelect",
            },
        )
        self.assertEqual(1, len(result))
        self.assertEqual("Severity", result[0].name)
```
(Full file also covers `get`/`create`/`patch`/`delete`/options and a
`ValidationError`-on-bad-payload test — see §11 for the ready-to-copy template
built from this exact shape.)

**Layout**: the suite is split the same way the repo is — `tests/api/` covers the
`teamstorm` package, `tests/examples/` covers the example import
toolkit under `examples/import_toolkit/`. `tests/api/` must pass with
`examples/` off `sys.path`; that is what proves the wrapper core is standalone.

**File naming convention**:
- `tests/api/test_api_<resource>.py` — API-layer tests (`test_api_attributes.py`,
  `test_api_workflows.py`, `test_api_workspaces.py`, ...)
- `tests/api/test_models_<area>.py` — model/validation-only tests
  (`test_models_types.py`, `test_models_enums.py`, `test_models_roles.py`, ...)
- `tests/api/test_<feature>.py` — cross-cutting wrapper tests (`test_client.py`,
  `test_no_legacy_modules_imports.py`, `test_api_coverage.py`, ...)
- `tests/examples/test_<feature>.py` — import-toolkit tests (`test_cli_args.py`,
  `test_readers.py`, `test_import_agile_end_to_end_mocked.py`, ...)

**How tests are run** (`CONTRIBUTING.md`):
```bash
pytest -q
```
Plus an opt-in live smoke test (`CONTRIBUTING.md`, "Live smoke test"):
```bash
RUN_LIVE_SMOKE=1 python3 -m unittest tests.examples.test_import_agile_live_smoke -v
```

---

## 9. Typing / lint

**The style guidance in this section used to recommend the opposite of what is
now enforced.** An older revision of this guide said `Optional[X]`/`List[...]`/
`Dict[...]` were "the dominant style, prefer it." That was true against commit
`64ed8f5`; it has not been true since the typing modernization
(commits `ca321dd`, `37a0a70`) converted the entire package. If you paste code
from an old copy of this guide (or from git blame on a pre-1.0 commit), convert
it before committing — flake8/review will flag `typing.Optional`/`List`/`Dict`/
`Union` as off-style today.

**Current rule, verified by grep (zero remaining hits in `teamstorm/` outside
prose comments describing hypothetical alternatives):**
- `from __future__ import annotations` is the **first (or second, after an
  optional `# path/to/file.py` header comment) line of every module** in
  `teamstorm/api/` and `teamstorm/models/`. No exceptions remain (a former compatibility exception was deleted — see gotcha 1 in §10).
- **PEP 604 unions**: `X | None` everywhere a field or parameter is optional —
  never `Optional[X]`. E.g. `provider_id: UUID | None = Field(default=None,
  alias="providerId")` (`teamstorm/models/common.py`, `UserModel`).
- **PEP 585 builtin generics**: `list[X]` / `dict[K, V]` everywhere — never
  `typing.List[X]` / `typing.Dict[K, V]`. E.g. `TypeAdapter(list[Model])`, and
  `permissions: list[Permission]` (`teamstorm/models/roles.py`).
  **Exception**: a class that defines its own `list()` method cannot use bare
  `list[X]` as the return annotation of any *other* method in that same class
  (mypy resolves `list` against the class's own namespace first) — those
  methods spell it `builtins.list[X]` instead. This is gotcha 13 in §10; don't
  duplicate that explanation here, just know it's why you'll see
  `import builtins` at the top of seven `*API` modules.
- **Discriminated unions** still use `Union`-shaped `X | Y | Z` (PEP 604 syntax,
  not `typing.Union[X, Y, Z]`) tagged with `Literal[...]` plus
  `Field(discriminator="type")` — see §3's `AttributeFieldValue` example.
- "Type alias by bare assignment" (no `typing.TypeAlias` keyword anywhere) is
  still the pattern, but the aliased types are PEP 604 unions too:
  `UUIDStr = UUID | str` and `DateTimeLike = datetime | str`
  (`teamstorm/models/common.py`), `EstimatesType = str`
  (`teamstorm/models/agile.py:7` — **note this collides in name, not in identity,
  with the unrelated `EstimatesType` `StrEnum` in `teamstorm/models/enums.py`**,
  see gotcha in §10).
- Line length: **120**, for both tools (`pyproject.toml`'s `[tool.black]
  line-length = 120` and `[tool.flake8] max-line-length = 120`).
- flake8 ignore list (`pyproject.toml`'s `[tool.flake8] ignore`):
  `["E203", "E266", "E501", "E704", "W503", "F403", "F401"]` — notably `F401`
  (unused import) and `F403` (star import) are both silenced repo-wide, which
  is what makes the `__init__.py` re-export style (§5) lint-clean without
  `# noqa` comments; `E704` (statement on same line as def) was added later
  for the one-line `@property` stubs in some templates.
- `Literal[...]` is used specifically as the discriminator-tag type in
  polymorphic attribute-value models (§3).
- `requires-python = ">=3.11"` in `pyproject.toml` — this is a hard requirement,
  not a latent gotcha: `enum.StrEnum` (used throughout `teamstorm/models/enums.py`)
  doesn't exist before 3.11. See §3.

---

## 10. Gotchas — things a newcomer will get wrong

1. Import the grouped entrypoint with `from teamstorm.api import TeamStormAPI`;
   resource classes remain in their individual modules under `teamstorm.api`.
   The previous entrypoint module was removed after its usages were verified absent.

2. **`tests/api/test_no_legacy_modules_imports.py`** bans importing a pre-refactor
   top-level package literally named `modules` anywhere in the repo (it was
   removed during the `teamstorm/` restructuring — see `git log -- modules/`). The
   test does a regex scan over every `*.py` file (outside `.venv`/
   `__pycache__`) for `import modules`, `from modules import`, or a bare
   `modules.` prefix, and fails if any hit is found. Don't reintroduce a
   `modules` package or reference one in an import statement, even in a
   comment that looks like code.

3. **`WorkitemModel`, `CreateWorkitemRequestBody`, `PatchWorkitemRequestBody`
   (all in `teamstorm.models.workitems`), plus the whole of `workitems_thumbs`
   and `workitems_attributes_create`, are not re-exported** from
   `teamstorm/models/__init__.py` — always import them from their submodule
   directly, not `from teamstorm.models import WorkitemModel` (§5). Note this
   is now a *partial* gap, not a total one: `WorkitemsCountModel` (also in
   `.workitems`) and everything in `.workitems_attributes_update` (including
   `UpdateWorkitemAttributeRequestBody`) genuinely are re-exported and importable
   as `from teamstorm.models import ...` — don't assume the whole workitems
   family is submodule-only.

4. **Two different `EstimatesType` symbols exist**: a two-member `StrEnum`
   (`teamstorm/models/enums.py`, values `"EstimatesInTime"` /
   `"EstimatesInStoryPoints"`) and a plain `EstimatesType = str` alias local to
   `teamstorm/models/agile.py:7` (exact match — this one line number hasn't
   drifted). `teamstorm/api/agile.py` imports the **agile.py** one
   (`from ..models.agile import AgileModel, CreateAgileRequestBody,
   EstimatesType`) — make sure you import the one you actually mean.

5. **`CwmModel` and `UnknownModel` were removed** during the Task 4 typing/pydantic
   audit — both were verified dead (no usages anywhere in `teamstorm/`, `tests/`,
   or `examples/`). Always use `TsBaseModel` from `teamstorm/models/base.py` for
   new models; there is no "loose placeholder" base to reach for anymore — model
   every field with a real, strict schema.

6. **Request-body serialization is almost always spelled out explicitly**,
   but the exact form depends on the verb (see §4): POST/PUT full-representation
   bodies use `body.model_dump(mode="json", exclude_none=True)` even though
   `TsBaseModel.model_dump()` already defaults to that; true partial-merge
   PATCH bodies must instead use `body.model_dump(mode="json",
   exclude_unset=True, exclude_none=False)` — relying on the base class's
   `exclude_none=True` default on a PATCH body silently drops an explicit
   "clear this field" `None` and turns it into a no-op. See §4 for the full
   list of PATCH exceptions that keep `exclude_none=True` despite the verb.

7. **`WorkitemsAPI.update_attribute`** (`teamstorm/api/workitems.py`, the last
   method in the file) does a PUT-then-PATCH-on-404/405-fallback dance
   specifically for `UniSelect`/`Tag` attribute types, with extra debug
   logging gated on `is_select_or_tag`. This is the *only* PUT-with-fallback
   in the codebase — every other `self.client.put(...)` call site (comments,
   comment/query visibility, git-integration-token update/refresh — see §1) is
   a plain, unconditional PUT with no fallback. Do not generalize
   `update_attribute`'s fallback into a general pattern unless you've
   independently confirmed the same server quirk applies to your endpoint.

8. **UUID values must be explicitly `str()`-ed when placed into a `params`
   dict** for query strings (e.g. `params["sprintId"] = str(sprint_id)` inside
   `WorkitemsAPI.list`), even though f-string path segments stringify a UUID
   automatically with no explicit cast needed. See the inline comment in
   `AgileAPI.list` (`teamstorm/api/agile.py`): `params={"folderId":
   str(folder_id)},  # query params должны быть строками`.

9. **Docstrings are now the rule, not the exception** — see §7 (rewritten;
   an older version of this guide said the opposite). Every public `*API`
   method, `TsClient` method, `TeamStormAPI` property, and model class has one. A
   missing docstring on a *new* `*API` method is worth a review comment now,
   and should be caught during review.

10. **Some files carry a leading `# teamstorm/path/to/file.py` comment as line 1**
    (before `from __future__ import annotations`) — e.g.
    `teamstorm/api/agile.py:1`, `teamstorm/api/types.py:1`, `teamstorm/api/__init__.py:1`,
    `teamstorm/models/attributes.py:1`, `teamstorm/models/folders.py:1`,
    `teamstorm/models/__init__.py:1` — while most files (`teamstorm/api/workitems.py`,
    `teamstorm/api/workspaces.py`, `teamstorm/api/statuses.py`, `teamstorm/api/roles.py`, ...)
    do not. This is optional/inconsistent; either way is fine for new files.

11. **`StrEnum` requires Python ≥3.11**, and `pyproject.toml` declares
    `requires-python = ">=3.11"` to match — see §9. There is no
    inconsistency to worry about here today; this gotcha exists only because
    an earlier revision of this guide flagged a `>=3.10`/`>=3.11` mismatch
    that no longer exists.

12. **A `.pytest_cache/` directory in the repo root is expected**, not stray —
    `pytest -q` is the documented command (`CONTRIBUTING.md`, §8) and running
    it creates that directory. This does *not* mean the tests themselves use
    pytest fixtures or `conftest.py` — they remain `unittest.TestCase` +
    `MagicMock` throughout (§8). Don't confuse "run via pytest" with
    "written in pytest style."

13. **A class that defines a method named `list` cannot use bare `list[X]`**
    as the return annotation of any *other* method in that same class --
    mypy resolves the name `list` against the class's own namespace first
    (to support forward references to nested classes), and once `def
    list(self, ...)` has bound the name `list` to a method, every later
    `-> list[X]` in that class resolves to *that method*, not the builtin,
    producing `error: Function "...ClassName.list" is not valid as a type
    [valid-type]`. Confirmed with a minimal repro: `class Foo: def list(self)
    -> list[int]: ... ; def list_other(self) -> list[int]: ...` -- only the
    second method's annotation errors; a method's own return annotation
    referencing `list[X]` on the same line as its own `def list(...)`
    resolves fine (verified in this session). This bit every non-`list()`
    method returning a bare `List[X]` across seven `*API` modules during the
    typing modernization (`workitems.py`, `attachments.py`,
    `documents.py`, `time_tracking.py`, `links.py`, `workspace_users.py`,
    `workspace_groups.py`) -- e.g. `WorkitemsAPI.list_by_parent`,
    `WorkitemAttachmentsAPI.list_versions`, `WorkspaceUsersAPI.get_roles`.
    **Fix used**: `import builtins` and spell the annotation as
    `builtins.list[X]` for exactly those methods, keeping bare `list[X]`
    everywhere else (including the class's own `list()` method, which is
    unaffected). This was chosen over falling back to `typing.List[X]` for
    those methods because it keeps full PEP 585 builtin-generic syntax
    (no reintroduced `typing` import) and because grepping a file for
    `List[` to check "is this file modernized yet" stays a reliable signal.
    If you add a new `*API` class with both a `list()` method and another
    method that also returns a bare list type, use `builtins.list[X]` for
    the second one from the start.

---

## 11. Copy-pasteable templates

The templates below implement a hypothetical new workspace-scoped resource,
**Labels** (`GET/POST/PATCH/DELETE /workspaces/{workspace_key}/labels[/...]`),
chosen because it mirrors the shape of `AttributesAPI`/`RolesAPI` closely
enough to generalize from directly. Rename `Label`/`label`/`labels` throughout
for your real resource.

### (a) New model module — `teamstorm/models/labels.py`

```python
# teamstorm/models/labels.py
from __future__ import annotations

from uuid import UUID

from pydantic import Field

from .base import TsBaseModel


class LabelModel(TsBaseModel):
    """
    Swagger: LabelModel [1]
    required: id, name
    """

    id: UUID
    name: str
    description: str | None = None


class LabelModelList(TsBaseModel):
    """
    Swagger: LabelModelList [1]
    Paginated response envelope for GET /workspaces/{workspace}/labels.
    """

    from_token: str | None = Field(default=None, alias="fromToken")
    max_items_count: int | None = Field(default=None, alias="maxItemsCount")
    next_token: str | None = Field(default=None, alias="nextToken")
    items: list[LabelModel]


class CreateLabelRequestBody(TsBaseModel):
    """
    Swagger: CreateLabelRequestBody
    required: name
    """

    name: str
    description: str | None = None


class PatchLabelRequestBody(TsBaseModel):
    """
    Swagger: PatchLabelRequestBody
    Partial-merge body -- see §4. Both fields are nullable, so this must be
    serialized with exclude_unset=True, exclude_none=False, never the
    exclude_none=True POST/PUT default.
    """

    name: str | None = None
    description: str | None = None
```

### (b) New API class — `teamstorm/api/labels.py`

```python
# teamstorm/api/labels.py
from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import TypeAdapter

from teamstorm.api._base import BaseAPI
from teamstorm.models.labels import CreateLabelRequestBody, LabelModel, PatchLabelRequestBody


class LabelsAPI(BaseAPI):
    """
    Hypothetical Labels resource, used in this guide as the copy-paste
    template for a new workspace-scoped `*API` class.
    """

    def list(
        self,
        workspace_key: str,
        *,
        name: str | None = None,
    ) -> list[LabelModel]:
        """
        List labels defined in a workspace.

        :param workspace_key: workspace key or id.
        :param name: optional name filter.
        :return: every LabelModel across all pages.
        HTTP: GET /workspaces/{workspace}/labels
        """
        params: dict[str, Any] = {}
        if name is not None:
            params["name"] = name

        data = self.client.get_all(
            f"/workspaces/{workspace_key}/labels",
            params=params or None,
        )
        return TypeAdapter(list[LabelModel]).validate_python(data)

    def get(self, workspace_key: str, *, label_id: UUID) -> LabelModel:
        """
        Fetch a single label by id.

        :param workspace_key: workspace key or id.
        :param label_id: UUID of the label to fetch.
        :return: the matching LabelModel.
        HTTP: GET /workspaces/{workspace}/labels/{labelId}
        """
        data = self.client.get(f"/workspaces/{workspace_key}/labels/{label_id}")
        return LabelModel.model_validate(data)

    def create(self, workspace_key: str, body: CreateLabelRequestBody) -> LabelModel:
        """
        Create a new label.

        :param workspace_key: workspace key or id.
        :param body: CreateLabelRequestBody -- required name.
        :return: the created LabelModel.
        HTTP: POST /workspaces/{workspace}/labels
        """
        payload = body.model_dump(mode="json", exclude_none=True)
        data = self.client.post(f"/workspaces/{workspace_key}/labels", payload)
        return LabelModel.model_validate(data)

    def patch(
        self,
        workspace_key: str,
        *,
        label_id: UUID,
        body: PatchLabelRequestBody,
    ) -> LabelModel:
        """
        Partially update a label.

        Only fields explicitly set on *body* are sent to the server
        (exclude_unset=True); exclude_none is disabled so an intentional
        "clear this field" null is not silently dropped -- see §4.

        :param workspace_key: workspace key or id.
        :param label_id: UUID of the label to patch.
        :param body: partial label fields to update.
        :return: the updated LabelModel.
        HTTP: PATCH /workspaces/{workspace}/labels/{labelId}
        """
        payload = body.model_dump(mode="json", exclude_unset=True, exclude_none=False)
        data = self.client.patch(
            f"/workspaces/{workspace_key}/labels/{label_id}",
            payload,
        )
        return LabelModel.model_validate(data)

    def delete(self, workspace_key: str, *, label_id: UUID) -> None:
        """
        Delete a label.

        :param workspace_key: workspace key or id.
        :param label_id: UUID of the label to delete.
        :return: None.
        HTTP: DELETE /workspaces/{workspace}/labels/{labelId}
        """
        self.client.delete(f"/workspaces/{workspace_key}/labels/{label_id}")
        return None
```

### (c) New test file — `tests/api/test_api_labels.py`

```python
import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from pydantic import ValidationError

from teamstorm.api.labels import LabelsAPI
from teamstorm.models.labels import CreateLabelRequestBody, PatchLabelRequestBody


def _label_payload() -> dict:
    return {
        "id": str(uuid4()),
        "name": "Urgent",
        "description": "High priority label",
    }


class LabelsAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = LabelsAPI(self.client)
        self.workspace = "WS"
        self.label_id = uuid4()

    def test_list_uses_get_all_with_filters_and_parses(self) -> None:
        self.client.get_all.return_value = [_label_payload()]

        result = self.api.list(self.workspace, name="Urgent")

        self.client.get_all.assert_called_once_with(
            "/workspaces/WS/labels",
            params={"name": "Urgent"},
        )
        self.assertEqual(1, len(result))
        self.assertEqual("Urgent", result[0].name)

    def test_get_create_patch_delete(self) -> None:
        payload = _label_payload()
        self.client.get.return_value = payload
        self.client.post.return_value = payload
        self.client.patch.return_value = payload
        self.client.delete.return_value = None

        got = self.api.get(self.workspace, label_id=self.label_id)
        self.assertEqual("Urgent", got.name)
        self.client.get.assert_called_once_with(
            f"/workspaces/{self.workspace}/labels/{self.label_id}"
        )

        created = self.api.create(self.workspace, CreateLabelRequestBody(name="Urgent"))
        self.assertEqual("Urgent", created.name)
        self.client.post.assert_any_call(
            f"/workspaces/{self.workspace}/labels",
            {"name": "Urgent"},
        )

        patched = self.api.patch(
            self.workspace,
            label_id=self.label_id,
            body=PatchLabelRequestBody(name="Renamed"),
        )
        self.assertEqual("Urgent", patched.name)
        self.client.patch.assert_any_call(
            f"/workspaces/{self.workspace}/labels/{self.label_id}",
            {"name": "Renamed"},
        )

        deleted = self.api.delete(self.workspace, label_id=self.label_id)
        self.assertIsNone(deleted)
        self.client.delete.assert_any_call(
            f"/workspaces/{self.workspace}/labels/{self.label_id}"
        )

    def test_validation_error_on_bad_payload(self) -> None:
        self.client.get.return_value = {"id": str(uuid4())}
        with self.assertRaises(ValidationError):
            self.api.get(self.workspace, label_id=self.label_id)


if __name__ == "__main__":
    unittest.main()
```

### (d) Grouped API registration — edit `teamstorm/api/_entrypoint.py`

Add the `TYPE_CHECKING`-only import (module scope) and one more `@property` to
the `TeamStormAPI` dataclass, anywhere among the existing ones (no ordering
requirement observed, but grouping near conceptually-related resources, e.g.
near `attributes`/`roles`, is the existing loose pattern). Per §6, the
property needs a concrete return-type annotation, not a bare `def labels(self):`:

```python
if TYPE_CHECKING:
    from teamstorm.api.labels import LabelsAPI
    # ... existing TYPE_CHECKING-only imports ...


class TeamStormAPI:
    ...

    @property
    def labels(self) -> LabelsAPI:
        from teamstorm.api.labels import LabelsAPI

        return LabelsAPI(self.client)
```

### (e) `__init__.py` export updates

**`teamstorm/api/__init__.py`** — add the import (alphabetically among the existing
`from teamstorm.api.X import XAPI` lines) and add the class name to `__all__`
(alphabetically):

```python
from teamstorm.api.groups import GroupsAPI
from teamstorm.api.labels import LabelsAPI          # <-- new, alphabetically after groups
from teamstorm.api.roles import RolesAPI
...

__all__ = [
    "BaseAPI",
    "AgileAPI",
    "AttributesAPI",
    "FoldersAPI",
    "GroupsAPI",
    "LabelsAPI",                                # <-- new, alphabetically after GroupsAPI
    "RolesAPI",
    ...
]
```

**`teamstorm/models/__init__.py`** — add a new `from .labels import (...)` block
(alphabetically among the existing `from .X import (...)` blocks) and add
each symbol to `__all__` (alphabetically):

```python
from .folders import FolderModel, CreateFolderRequestBody
from .labels import CreateLabelRequestBody, LabelModel, LabelModelList, PatchLabelRequestBody
from .roles import (
    ...
)
...

__all__ = [
    ...
    "CreateFolderRequestBody",
    "CreateLabelRequestBody",                   # <-- new
    "CreateRoleRequestBody",
    ...
    "LabelModel",                                # <-- new
    "LabelModelList",                             # <-- new
    ...
    "PatchLabelRequestBody",                     # <-- new
    "PatchRoleRequestBody",
    ...
]
```

After all five edits, run:
```bash
pytest -q
flake8 teamstorm/
black --check --diff teamstorm/
```