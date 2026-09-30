# Agent instructions

Use [`.agents/skills/teamstorm-api/SKILL.md`](.agents/skills/teamstorm-api/SKILL.md) for TeamStorm automation, endpoint conventions, credentials, smoke tests, and known server behavior.

## Commands

```bash
uv venv .venv
uv pip install --python .venv/bin/python ".[dev,examples]"
.venv/bin/python scripts/check_repository_positioning.py
.venv/bin/flake8 teamstorm/ examples/ tests/ scripts/
.venv/bin/black --check teamstorm/ examples/ tests/ scripts/
.venv/bin/mypy teamstorm/
.venv/bin/python -m pytest -q
```

## Safety

- Never expose tokens, authorization headers, or credential files.
- Do not call a live TeamStorm instance unless the task explicitly requires it.
- Confirm workspace and identifiers before any mutation.
- Do not blindly retry creates, comments, links, uploads, or other non-idempotent calls.
- Preserve `import teamstorm`, `TsClient`, `TeamStormAPI`, typed request models, and the 170-operation coverage test.
- Do not add registry upload or release-artifact automation.
