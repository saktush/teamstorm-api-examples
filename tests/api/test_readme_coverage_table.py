"""
Guards the API-coverage table in README.md against arithmetic drift.

The table groups the 170 spec operations into functional areas. It was
hand-written once and immediately had a wrong row (26 where the manifest says
24), which summed to 161 against a stated total of 159 (the operation count at the time) -- the kind of error
nobody re-checks by hand on the next edit. This test re-derives the numbers
from tests/api/api_coverage_manifest.py, the same manifest that
test_api_coverage.py pins to the OpenAPI spec.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

from api_coverage_manifest import COVERAGE_MANIFEST  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# The README is published in two languages; the table has to add up in both.
# Each entry is (path, coverage heading, next heading, total-row label).
READMES = (
    ("README.md", "## Покрытие API", "## Примеры", "Итого"),
    ("README.en.md", "## API coverage", "## Examples", "Total"),
)

# A row is "| Area | <ops> | `prop`, `prop` |"; the Total row is bolded.
_ROW_RE = re.compile(r"^\|\s*(?!\*\*)([^|]+?)\s*\|\s*(\d+)\s*\|\s*(.+?)\s*\|$", re.MULTILINE)
_PROPERTY_RE = re.compile(r"`([a-z_]+)`")


def _total_re(label: str) -> re.Pattern[str]:
    return re.compile(rf"^\|\s*\*\*{re.escape(label)}\*\*\s*\|\s*\*\*(\d+)\*\*\s*\|", re.MULTILINE)


def _coverage_table(rel_path: str, start_heading: str, end_heading: str) -> str:
    """Return the API-coverage section of the README at *rel_path*."""
    text = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
    start = text.index(start_heading)
    end = text.index(end_heading, start)
    return text[start:end]


class ReadmeCoverageTableTestCase(unittest.TestCase):
    def test_area_rows_sum_to_the_stated_total(self) -> None:
        for rel_path, start, end, total_label in READMES:
            with self.subTest(readme=rel_path):
                table = _coverage_table(rel_path, start, end)
                rows = _ROW_RE.findall(table)
                self.assertTrue(rows, f"no area rows parsed out of the {rel_path} coverage table")

                stated_total = _total_re(total_label).search(table)
                self.assertIsNotNone(stated_total, f"{rel_path} coverage table has no bolded **{total_label}** row")
                assert stated_total is not None  # for mypy

                summed = sum(int(ops) for _, ops, _ in rows)
                self.assertEqual(
                    int(stated_total.group(1)),
                    summed,
                    f"{rel_path} coverage rows sum to {summed}, but the total row says {stated_total.group(1)}",
                )

    def test_stated_total_equals_the_manifest(self) -> None:
        for rel_path, start, end, total_label in READMES:
            with self.subTest(readme=rel_path):
                stated_total = _total_re(total_label).search(_coverage_table(rel_path, start, end))
                assert stated_total is not None
                self.assertEqual(len(COVERAGE_MANIFEST), int(stated_total.group(1)))

    def test_each_area_row_matches_the_manifest_for_its_properties(self) -> None:
        by_property: dict[str, int] = {}
        for mapping in COVERAGE_MANIFEST:
            by_property[mapping.api_property] = by_property.get(mapping.api_property, 0) + 1

        for rel_path, start, end, _ in READMES:
            covered: set[str] = set()
            for area, ops, properties in _ROW_RE.findall(_coverage_table(rel_path, start, end)):
                names = _PROPERTY_RE.findall(properties)
                with self.subTest(readme=rel_path, area=area):
                    unknown = [n for n in names if n not in by_property]
                    self.assertEqual([], unknown, f"{rel_path} names API properties that do not exist: {unknown}")
                    expected = sum(by_property[n] for n in names)
                    self.assertEqual(
                        expected,
                        int(ops),
                        f"{rel_path} row {area!r} claims {ops} operations; the manifest counts {expected}",
                    )
                    covered.update(names)

            missing = sorted(set(by_property) - covered)
            with self.subTest(readme=rel_path):
                self.assertEqual([], missing, f"API properties absent from the {rel_path} coverage table: {missing}")


if __name__ == "__main__":
    unittest.main()
