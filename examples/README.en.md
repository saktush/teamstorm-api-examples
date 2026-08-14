# TeamStorm API Examples

[Русская версия](README.md) | **English**

This directory is **not an installed package**. It is available in the Git
checkout, but after `pip install .` nothing under `examples/` is importable --
it exists as a runnable demonstration of consuming the API wrappers.

## Prerequisites

The example scripts need `pandas`/`openpyxl` (Excel/CSV reading) and
`python-dotenv` (`.env` loading), in addition to the API wrappers' own `requests`/`pydantic` dependencies.
Install the `examples` extra from a repo checkout:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[examples]"

cp .env.template .env
# then edit .env and fill in BASE_URL / API_TOKEN
```

`API_TOKEN` holds the bare token: the API wrapper adds the `PrivateToken ` prefix to
the `Authorization` header itself, so do not include it in the value.

`.env` is read via `python-dotenv`; both scripts below fall back to
`--base-url`/`--token` flags if you'd rather not use a `.env` file.

## What's here

- **`quickstart.py`** -- a runnable version of the README's Quickstart snippet,
  reading connection details from the environment. See below.
- **`import_toolkit/`** -- an example application, built entirely on top of the
  public `teamstorm` API wrappers, with two entry points:
  - `import_toolkit/import_agile.py` -- imports sprints and tasks into a
    TeamStorm workspace from an Excel file or a CSV directory.
  - `import_toolkit/sync_uniselect_options.py` -- syncs `UniSelect` attribute
    options from one master workspace to one or more target workspaces.
- **`data/`** -- sample input files for `import_agile.py` (see "Example data
  format" below).

Both scripts are run directly with `python`, not installed as console scripts:

```bash
python examples/import_toolkit/import_agile.py --help
python examples/import_toolkit/sync_uniselect_options.py --help
```

## `quickstart.py`

```bash
export BASE_URL="https://your-cwm-host"
export API_TOKEN="YOUR_API_TOKEN"
export WORKSPACE_KEY="YOUR_WORKSPACE_KEY"
python examples/quickstart.py
```

It prints the workspace name, then lists the workitem types configured in that
workspace and reports how many workitems currently exist. If any of the three
environment variables is missing, or if an API call fails, it prints a clear
message and exits with status 1 -- no traceback.

## `import_agile.py`

Imports sprints and tasks into the CWM Public API from an Excel file or a CSV
directory. Flags (from `import_toolkit/workflows/imports/cli.py`):

| Flag | Description |
|---|---|
| `--base-url` | CWM API base URL. Defaults to `BASE_URL` from the environment/`.env`. |
| `--token` | API token. Defaults to `API_TOKEN` from the environment/`.env`. |
| `--workspace-key` | **Required.** Key of the workspace to import into. |
| `--folder-name` | **Required.** Name of the root folder for the import inside the workspace. |
| `--input-path` | Path to an `.xlsx`/`.xls` file, or to a directory of CSV files. Required in practice: without it (or `--excel-path`) the run stops with exit code 2. |
| `--excel-path` | Deprecated alias for `--input-path`; still accepted but scheduled for removal. If both are given, `--input-path` wins and a warning is logged. |
| `--dry-run` | Validates input and logs planned actions; writes nothing to the API. |
| `--update-settings` | Allows creating missing workspace settings (attributes, types) needed for the import. |
| `--sync-members` | Adds users found in the input to the workspace and tries to assign them the `User` system role. |
| `--allow-insecure` | Allows a non-HTTPS `--base-url` (local/staging use only -- never with a real token). |
| `--log-file` | Path to the log file. Defaults to `./logs/import_agile.log`. |

### Usage examples

If `BASE_URL` and `API_TOKEN` are already in `.env`:

```bash
python examples/import_toolkit/import_agile.py \
  --workspace-key "YOUR_WORKSPACE_KEY" \
  --folder-name "YOUR_FOLDER" \
  --input-path "examples/data/example_agile.xlsx"
```

Passing the URL and token explicitly instead:

```bash
python examples/import_toolkit/import_agile.py \
  --base-url "$BASE_URL" \
  --token "$API_TOKEN" \
  --workspace-key "YOUR_WORKSPACE_KEY" \
  --folder-name "YOUR_FOLDER" \
  --input-path "examples/data/example_agile.xlsx"
```

Dry run (nothing written to the API):

```bash
python examples/import_toolkit/import_agile.py \
  --workspace-key "YOUR_WORKSPACE_KEY" \
  --folder-name "YOUR_FOLDER" \
  --input-path "examples/data/example_agile.xlsx" \
  --dry-run
```

With auto-creation of missing attributes/types:

```bash
python examples/import_toolkit/import_agile.py \
  --workspace-key "YOUR_WORKSPACE_KEY" \
  --folder-name "YOUR_FOLDER" \
  --input-path "examples/data/example_agile.xlsx" \
  --update-settings
```

With member sync on top:

```bash
python examples/import_toolkit/import_agile.py \
  --workspace-key "YOUR_WORKSPACE_KEY" \
  --folder-name "YOUR_FOLDER" \
  --input-path "examples/data/example_agile.xlsx" \
  --update-settings \
  --sync-members
```

CSV directory instead of an Excel file:

```bash
python examples/import_toolkit/import_agile.py \
  --workspace-key "YOUR_WORKSPACE_KEY" \
  --folder-name "YOUR_FOLDER" \
  --input-path "./agile_csv"
```

### What `--update-settings` does

- Creates missing custom attributes found in the `tasks` columns.
- Creates missing workitem types found in the `type` column.
- Binds created (or already-existing) attributes to the right types.
- For `UniSelect`/`Tag` attributes, can auto-create missing options while
  importing values.

It does **not** currently sync statuses, workflows, or roles from an external
source -- those steps are only logged as `skipped`. Without
`--update-settings`, missing attributes/types are not created; the import
continues but logs warnings, and affected fields may be skipped.

### What `--sync-members` does

Collects users from the `assignee_username` column and from any `User`-typed
custom attributes, resolves each by identifier, adds any that are found to the
workspace, and assigns the workspace's `User` system role if one exists.
Without this flag, no membership changes are made.

### Exit codes

- `0` -- import finished; per-row `UniSelect`/`Tag` failures, if any, are
  reported as non-fatal.
- `1` -- import ran, but one or more rows failed; every failure is logged in
  the final summary.
- `2` -- fatal before any writes: no input path, an unreadable or invalid
  input file, missing required columns, or the workspace/root folder could not
  be resolved.

### Example data format

`data/example_agile.xlsx` has two sheets:

- **`sprints`**: `sprint_name`, `start_date`, `end_date`.
- **`tasks`**: `name`, `description`, `start_date`, `end_date`,
  `assignee_username`, `sprint_name`, `type`, `Parent`, plus custom-attribute
  columns named `attribute_name[AttributeType]` -- e.g. `comment[UniString]`,
  `estimate[Number]`, `target_date[Date]`, `severity[UniSelect]`, `tags[Tag]`,
  `reviewer[User]`, `spent[TimeDuration]`.

Column names are matched case-insensitively and ignoring non-alphanumeric
characters, so `Assignee Username` and `assignee_username` are the same column.
Any `tasks` column that is not one of the known ones above is treated as a
custom attribute. The `[AttributeType]` marker is optional and accepts several
spellings (`string`/`text`, `number`/`int`/`float`, `date`, `select`, `tag`,
`user`, `time`/`duration`, ...); a column with no marker, or with an
unrecognized one, is imported as `UniString`.

`data/example_tasks.xlsx` has a single `tasks` sheet in the same column format,
with no `sprints` sheet -- useful for `--input-path` pointed at a plain task
import with no sprint scheduling.

Both `.xlsx` and `.xls` are supported, as is the older sheet-order convention
(first sheet = sprints, second = tasks, regardless of name). For a CSV
directory, `tasks.csv` is required and `sprints.csv` is optional.

**`Parent` column**: empty means the row is created directly under
`--folder-name`; a value matching another task's `name` in the same import
makes this row that task's child; any other value is treated as a subfolder
name under `--folder-name` (found or created automatically). A non-empty
`Parent` sets the current parent context for subsequent rows until a blank
`Parent` resets it back to the root folder.

**`sprint_name` column** (optional): if blank or missing, the task isn't linked
to a sprint. If it names a sprint not present in the `sprints` sheet/file, a
sprint is auto-created spanning `min(start_date)..max(end_date)` of the tasks
that reference it. `backlog`/`backlog data` (case-insensitive) links the task
to the Agile extension's backlog sprint instead. If there's no sprint data at
all, sprint-related setup is skipped entirely.

## `sync_uniselect_options.py`

Syncs **UniSelect attribute options** from one master workspace to one or more
target workspaces. For each attribute named via `--attribute-name`, it reads
the attribute from the master workspace, ensures the same attribute exists in
every target, and makes the target's options an exact mirror of master's:
missing options are created, options whose normalized name (`trim` +
`casefold`) matches are renamed to master's canonical spelling, and extra
options not present in master are deleted.

Only `UniSelect` attributes are supported, and the attribute scope is an
explicit allowlist -- there's no "sync everything" mode. Default mode is
dry-run; real writes need `--apply`. A target whose key equals the master's is
skipped. If one target fails, the others still run, and the process exits
non-zero if any target failed.

Flags (from `import_toolkit/workflows/sync/uniselect_options.py`):

| Flag | Description |
|---|---|
| `--base-url` | CWM API base URL. Defaults to `BASE_URL` from the environment/`.env`. |
| `--token` | API token. Defaults to `API_TOKEN` from the environment/`.env`. |
| `--master-workspace-key` | **Required.** Workspace to copy options from. |
| `--target-workspace-key` | **Repeatable.** One or more workspaces to copy options into; at least one is required (checked at startup, exit code 2). |
| `--attribute-name` | **Repeatable.** One or more `UniSelect` attribute names to sync; at least one is required (checked at startup, exit code 2). |
| `--apply` | Applies real changes. Without it, the script only reports what it would do. |
| `--allow-insecure` | Allows a non-HTTPS `--base-url` (local/staging use only -- never with a real token). |
| `--log-file` | Path to the log file. Defaults to `./logs/sync_uniselect_options.log`. |

### Usage examples

Dry-run preview:

```bash
python examples/import_toolkit/sync_uniselect_options.py \
  --master-workspace-key MASTER_WS \
  --target-workspace-key TEAM_A \
  --target-workspace-key TEAM_B \
  --attribute-name Severity \
  --attribute-name Priority
```

Applying the changes:

```bash
python examples/import_toolkit/sync_uniselect_options.py \
  --master-workspace-key MASTER_WS \
  --target-workspace-key TEAM_A \
  --target-workspace-key TEAM_B \
  --attribute-name Severity \
  --attribute-name Priority \
  --apply
```

Passing auth explicitly instead of via `.env`:

```bash
python examples/import_toolkit/sync_uniselect_options.py \
  --base-url "$BASE_URL" \
  --token "$API_TOKEN" \
  --master-workspace-key MASTER_WS \
  --target-workspace-key TEAM_A \
  --attribute-name Severity \
  --apply
```

### Recommended workflow

1. Run dry-run first and review the logged create/rename/delete plan.
2. Re-run with `--apply` once the plan looks right.
3. Keep the `--attribute-name` list small for a first rollout.

### Exit codes

- `0` -- success, no failed targets.
- `1` -- completed, but one or more target workspaces had failures.
- `2` -- invalid input/config, or a fatal startup/master-read error.

### Common failure scenarios

- The master workspace has no `UniSelect` attribute with one of the requested
  names (an attribute of another type with that name does not count).
- `--attribute-name` was passed twice for names that normalize to the same
  thing (exit code 2).
- Duplicate normalized option names in master or a target (e.g. `"High"` and
  `" high "`) -- that attribute is reported as failed.
- Duplicate normalized `UniSelect` attribute names inside a target -- the whole
  target is skipped as failed.
- API/network/permission errors for one specific target -- processing continues
  for the rest, and the failure is reported in the final summary.

## Environment variables

Both scripts, and `quickstart.py`, read the same three variables (from `.env`
or the real environment):

| Variable | Used for |
|---|---|
| `BASE_URL` | Default for `--base-url` / the CWM instance URL. |
| `API_TOKEN` | Default for `--token` / the API token. |
| `WORKSPACE_KEY` | `quickstart.py` only -- the workspace it queries. |

See `.env.template` at the repository root.
