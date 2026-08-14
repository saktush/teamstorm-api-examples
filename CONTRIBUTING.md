# Contributing

## Setup

```bash
uv venv .venv
uv pip install --python .venv/bin/python ".[dev,examples]"
```

A standard `python3 -m venv .venv` followed by `.venv/bin/python -m pip install ".[dev,examples]"` also works.

## Quality gate

Run before opening a pull request:

```bash
.venv/bin/python scripts/check_repository_positioning.py
.venv/bin/flake8 teamstorm/ examples/ tests/ scripts/
.venv/bin/black --check teamstorm/ examples/ tests/ scripts/
.venv/bin/mypy teamstorm/
.venv/bin/python -m pytest -q
```

The same checks run in GitHub Actions for pull requests and updates to `main`.

## Contribution flow

1. Branch from current `main`.
2. Keep HTTP behavior changes separate from documentation-only changes.
3. Add or update tests for every behavioral change.
4. Run the full quality gate.
5. Open a pull request describing affected endpoints, safety considerations, and verification evidence.

## Updating the OpenAPI snapshot

1. Replace `docs/openapi/swagger-v4.18.0.json` with a verified current snapshot and rename it to the real TeamStorm release version when needed.
2. Update `tests/api/api_coverage_manifest.py` for added, removed, or changed operations.
3. Update `docs/api-coverage.md`.
4. Run the full test suite; the coverage test compares the manifest and snapshot in both directions.

## Repository scope

This repository contains examples plus reusable API wrappers. Its preferred distribution is the versioned source archive attached to a GitHub release; installation from a pinned Git commit remains an alternative. Do not add package-registry upload automation, generated artifacts to the tracked tree, or credentials. Release archives and checksums are generated from a verified Git tag and attached to the GitHub release.

## Style and safety

- Python 3.11+ with type hints on public functions.
- Use pydantic request models and preserve JSON aliases.
- Never print tokens or authorization headers.
- Do not retry non-idempotent writes until server state has been checked.
- Live mutation tests require explicit authorization and a dedicated workspace.
