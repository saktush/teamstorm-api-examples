"""
Guards the documentation's code snippets against drifting from the real API.

Written after a live example went stale: the `workspace_key` constructor
argument was removed from `TsClient`, but a migration snippet in the docs
kept passing it, so the documented upgrade path raised TypeError.

Executing the snippets is not an option (they talk to a server), so instead
this binds every documented `TsClient(...)` / `TeamStormAPI(...)` call
against the real signature with `inspect.Signature.bind_partial`, which
catches a removed, renamed or newly-required parameter without any network
access.
"""

from __future__ import annotations

import ast
import inspect
import unittest
from pathlib import Path

from teamstorm.client import TsClient
from teamstorm.api import TeamStormAPI

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DOCS = (
    "README.md",
    "README.en.md",
    "CONTRIBUTING.md",
    "examples/README.md",
    "examples/README.en.md",
)

# Constructors whose documented call sites must match the real signature.
_CONSTRUCTORS = {
    "TsClient": TsClient,
    "TeamStormAPI": TeamStormAPI,
}

# Snippets showing intentionally old/historical API shapes, keyed by the
# marker comment that opens them. None currently -- kept as an extension
# point for future docs that need to show a deprecated call shape on purpose.
_HISTORICAL_MARKERS: tuple[str, ...] = ()


def _python_blocks(markdown: str) -> list[str]:
    """Return the body of every fenced ```python block in *markdown*."""
    blocks: list[str] = []
    lines = markdown.splitlines()
    inside = False
    current: list[str] = []
    for line in lines:
        if line.strip().startswith("```python"):
            inside, current = True, []
            continue
        if inside and line.strip().startswith("```"):
            blocks.append("\n".join(current))
            inside = False
            continue
        if inside:
            current.append(line)
    return blocks


def _is_historical(block: str) -> bool:
    return any(marker in block for marker in _HISTORICAL_MARKERS)


def _constructor_calls(block: str) -> list[ast.Call]:
    """Parse *block* and return its calls to a known API constructor."""
    try:
        tree = ast.parse(block)
    except SyntaxError:
        # Deliberate fragments (bare signatures, mid-method excerpts) are not
        # constructor call sites; nothing to check.
        return []
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _CONSTRUCTORS
    ]


class DocsSnippetSignatureTestCase(unittest.TestCase):
    def test_documented_constructor_calls_match_the_real_signatures(self) -> None:
        checked = 0
        for rel_path in DOCS:
            path = REPO_ROOT / rel_path
            if not path.exists():
                continue
            for block_no, block in enumerate(_python_blocks(path.read_text(encoding="utf-8")), start=1):
                if _is_historical(block):
                    continue
                for call in _constructor_calls(block):
                    name = call.func.id  # type: ignore[attr-defined]
                    signature = inspect.signature(_CONSTRUCTORS[name])
                    kwargs = {kw.arg: None for kw in call.keywords if kw.arg is not None}
                    positional = [None] * len(call.args)
                    label = f"{rel_path} block {block_no}: {name}(...)"
                    checked += 1
                    with self.subTest(call=label):
                        try:
                            signature.bind_partial(*positional, **kwargs)
                        except TypeError as exc:
                            self.fail(f"{label} does not match {name}{signature}: {exc}")

        self.assertGreater(checked, 0, "no documented constructor calls found -- has the doc layout changed?")


if __name__ == "__main__":
    unittest.main()
