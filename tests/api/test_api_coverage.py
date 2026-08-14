# tests/api/test_api_coverage.py
"""
Proves that all 159 CWM Public API spec operations are implemented by the
`teamstorm` API wrappers, using the hand-maintained manifest in
tests/api/api_coverage_manifest.py rather than parsing `teamstorm/api/*.py` source.

Why not parse the source directly? An earlier attempt regexed for literal
`self.client.<verb>("...")` call strings and reported 27 false "missing"
operations, because several modules build their request path through a
helper or a local variable instead of a literal string argument passed
directly to the client call (see the module docstring on
tests/api/api_coverage_manifest.py for the exact three cases: attachments.py's
`_AttachmentsAPIBase._attachments_path()`, sharing.py's `path = f"..."`
locals, and workitems.py's `update_attribute`). All 27 are implemented and
correct; the scanner just could not see them. Per this project's standing
guidance, an explicit, correct manifest beats a clever, flaky parser -- this
test suite verifies the manifest is exhaustive and self-consistent, and (when
swagger.json is available) verifies it against the live spec too.

docs/openapi/swagger-v4.18.0.json is a committed snapshot of the OpenAPI spec
fetched from the live server, so the spec cross-check below runs in a fresh
clone and in CI. The tests still skip gracefully when the file is absent.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

from teamstorm.api import TeamStormAPI

# tests/ is not a package (no tests/__init__.py), so plain `import
# api_coverage_manifest` only resolves when something has put tests/api/ itself
# on sys.path. `python -m unittest discover -s tests` does that for us, but
# `python -m unittest tests.api.test_api_coverage` does not -- it imports
# `tests` as an implicit namespace package rooted at the repo root, which is
# on sys.path, while tests/api/ itself never gets added. Add it explicitly
# here so both invocation styles resolve the sibling `api_coverage_manifest`
# module.
_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

from api_coverage_manifest import COVERAGE_MANIFEST  # noqa: E402

SWAGGER_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "openapi" / "swagger-v4.18.0.json"
API_PREFIX = "/cwm/public/api/v1"
_HTTP_VERBS = {"get", "post", "put", "patch", "delete"}

EXPECTED_OPERATION_COUNT = 159


def _load_spec_operations() -> set:
    """
    Read swagger.json and return the {(HTTP_METHOD, path)} set of every
    operation in the spec, with the common API_PREFIX stripped from each
    path so it lines up with the path strings teamstorm/api/*.py modules build
    (TsClient itself prepends API_PREFIX -- see teamstorm/client.py).
    """
    with open(SWAGGER_PATH, encoding="utf-8") as f:
        spec = json.load(f)

    ops = set()
    for path, methods in spec["paths"].items():
        assert path.startswith(API_PREFIX), f"unexpected path shape (no {API_PREFIX} prefix): {path}"
        short_path = path[len(API_PREFIX) :]
        for verb, operation in methods.items():
            if verb.lower() in _HTTP_VERBS:
                ops.add((verb.upper(), short_path))
    return ops


class ManifestSelfConsistencyTestCase(unittest.TestCase):
    """
    Checks that don't require swagger.json -- the manifest must be internally
    well-formed regardless of whether the spec file is present.
    """

    def test_manifest_has_no_duplicate_operations(self) -> None:
        keys = [(m.http_method, m.path) for m in COVERAGE_MANIFEST]
        duplicates = {k for k in keys if keys.count(k) > 1}
        self.assertEqual(set(), duplicates, f"duplicate (method, path) rows in manifest: {duplicates}")

    def test_manifest_has_expected_row_count(self) -> None:
        self.assertEqual(EXPECTED_OPERATION_COUNT, len(COVERAGE_MANIFEST))

    def test_every_manifest_entry_resolves_to_a_real_api_method(self) -> None:
        """
        For every manifest row, TeamStormAPI.<api_property> must exist and the
        object it returns must have a real, callable <api_method> attribute.
        This proves the manifest doesn't merely claim coverage on paper --
        every named (property, method) pair actually exists in the shipped
        API surface today.
        """
        api = TeamStormAPI(client=object())  # placeholder client: properties only need somewhere to store it
        for mapping in COVERAGE_MANIFEST:
            op_label = f"{mapping.http_method} {mapping.path} -> {mapping.api_property}.{mapping.api_method}"
            with self.subTest(op=op_label):
                self.assertTrue(
                    hasattr(api, mapping.api_property),
                    f"TeamStormAPI has no property {mapping.api_property!r} ({op_label})",
                )
                api_instance = getattr(api, mapping.api_property)
                self.assertEqual(
                    mapping.api_class,
                    type(api_instance).__name__,
                    f"TeamStormAPI.{mapping.api_property} is a {type(api_instance).__name__}, "
                    f"manifest expects {mapping.api_class} ({op_label})",
                )
                self.assertTrue(
                    hasattr(api_instance, mapping.api_method),
                    f"{mapping.api_class} has no method {mapping.api_method!r} ({op_label})",
                )
                self.assertTrue(
                    callable(getattr(api_instance, mapping.api_method)),
                    f"{mapping.api_class}.{mapping.api_method} is not callable ({op_label})",
                )


@unittest.skipUnless(
    SWAGGER_PATH.exists(),
    "docs/openapi/swagger-v4.18.0.json not present -- spec cross-check skipped",
)
class ManifestMatchesSpecTestCase(unittest.TestCase):
    """
    Checks that require swagger.json -- these prove the manifest is not just
    internally consistent but actually equal to the live spec's operation
    set, in both directions.
    """

    def test_manifest_operation_set_exactly_equals_spec_operation_set(self) -> None:
        spec_ops = _load_spec_operations()
        manifest_ops = {(m.http_method, m.path) for m in COVERAGE_MANIFEST}

        missing_from_manifest = spec_ops - manifest_ops
        phantom_in_manifest = manifest_ops - spec_ops

        self.assertEqual(
            set(),
            missing_from_manifest,
            f"{len(missing_from_manifest)} spec operation(s) have no manifest entry: "
            f"{sorted(missing_from_manifest)}",
        )
        self.assertEqual(
            set(),
            phantom_in_manifest,
            f"{len(phantom_in_manifest)} manifest entries do not correspond to any spec operation: "
            f"{sorted(phantom_in_manifest)}",
        )

    def test_spec_has_expected_operation_count(self) -> None:
        # A drift guard: if the live spec ever grows/shrinks operation count,
        # this fails loudly instead of the exact-set check silently adjusting.
        self.assertEqual(EXPECTED_OPERATION_COUNT, len(_load_spec_operations()))


if __name__ == "__main__":
    unittest.main()
