import logging
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from import_toolkit.io.readers import CsvReader, ExcelReader
from import_toolkit.io.readers.common import (
    extract_attribute_columns,
    extract_custom_attributes_for_row,
)


def _make_logger() -> logging.Logger:
    logger = logging.getLogger("test.readers.custom_attributes")
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    return logger


def _base_sprints_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"sprint_name": "Sprint A", "start_date": "2024-01-01", "end_date": "2024-01-10"},
        ]
    )


def _write_excel(path: Path, sprints_df: pd.DataFrame, tasks_df: pd.DataFrame) -> None:
    with pd.ExcelWriter(path) as writer:
        sprints_df.to_excel(writer, index=False, sheet_name="Sheet1")
        tasks_df.to_excel(writer, index=False, sheet_name="Sheet2")


class ReadersCustomAttributesTestCase(unittest.TestCase):
    def test_extract_attribute_columns_excludes_system_aliases(self) -> None:
        tasks_df = pd.DataFrame(
            [
                {
                    "name": "Task 1",
                    "description": "Desc",
                    "start_date": "2024-01-02",
                    "end_date": "2024-01-05",
                    "assignee_username": "john",
                    "sprint_name": "Sprint A",
                    "type": "Task",
                    "startDate": "2024-01-02T00:00:00+03:00",
                    "storyPoints": 5,
                    "Severity": "High",
                    "Custom Team": "Core",
                }
            ]
        )

        columns = extract_attribute_columns(tasks_df)

        self.assertIn("Severity", columns)
        self.assertIn("Custom Team", columns)
        self.assertNotIn("assignee_username", columns)
        self.assertNotIn("sprint_name", columns)
        self.assertNotIn("startDate", columns)
        self.assertNotIn("storyPoints", columns)

    def test_extract_custom_attributes_for_row_skips_empty_values(self) -> None:
        tasks_df = pd.DataFrame(
            [
                {
                    "Severity": "High",
                    "Tag": "",
                    "Story Value": None,
                    "Owner Hint": "Alice",
                }
            ]
        )

        result = extract_custom_attributes_for_row(
            tasks_df.iloc[0],
            ["Severity", "Tag", "Story Value", "Owner Hint"],
        )

        self.assertEqual({"Severity": "High", "Owner Hint": "Alice"}, result)

    def test_reader_rows_always_have_custom_attributes_raw(self) -> None:
        tasks_df = pd.DataFrame(
            [
                {
                    "name": "Task 1",
                    "description": "Desc",
                    "start_date": "2024-01-02",
                    "end_date": "2024-01-05",
                    "assignee_username": "john",
                    "sprint_name": "Sprint A",
                    "type": "Task",
                    "Severity": "High",
                },
                {
                    "name": "Task 2",
                    "description": "Desc 2",
                    "start_date": "2024-01-03",
                    "end_date": "2024-01-06",
                    "assignee_username": "john",
                    "sprint_name": "Sprint A",
                    "type": "Task",
                    "Severity": "",
                },
            ]
        )

        with tempfile.TemporaryDirectory() as tmp:
            excel_path = Path(tmp) / "agile.xlsx"
            _write_excel(excel_path, _base_sprints_df(), tasks_df)
            _, rows, critical_errors, row_errors = ExcelReader().load(str(excel_path), _make_logger())

        self.assertEqual([], critical_errors)
        self.assertEqual([], row_errors)
        self.assertEqual({"Severity": "High"}, rows[0]["custom_attributes_raw"])
        self.assertEqual({}, rows[1]["custom_attributes_raw"])

    def test_csv_excel_parity_for_custom_attributes(self) -> None:
        tasks_df = pd.DataFrame(
            [
                {
                    "name": "Task 1",
                    "description": "Desc",
                    "start_date": "2024-01-02",
                    "end_date": "2024-01-05",
                    "assignee_username": "john",
                    "sprint_name": "Sprint A",
                    "type": "Task",
                    "Severity": "High",
                    "Component": "Backend",
                }
            ]
        )

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            excel_path = base / "agile.xlsx"
            csv_dir = base / "csv_input"
            csv_dir.mkdir(parents=True)

            sprints_df = _base_sprints_df()
            _write_excel(excel_path, sprints_df, tasks_df)
            sprints_df.to_csv(csv_dir / "sprints.csv", index=False)
            tasks_df.to_csv(csv_dir / "tasks.csv", index=False)

            excel_rows = ExcelReader().load(str(excel_path), _make_logger())[1]
            csv_rows = CsvReader().load(str(csv_dir), _make_logger())[1]

        self.assertEqual(excel_rows[0]["custom_attributes_raw"], csv_rows[0]["custom_attributes_raw"])
        self.assertEqual({"Severity": "High", "Component": "Backend"}, csv_rows[0]["custom_attributes_raw"])

    def test_parent_column_is_not_treated_as_custom_attribute(self) -> None:
        tasks_df = pd.DataFrame(
            [
                {
                    "name": "Task 1",
                    "description": "Desc",
                    "start_date": "2024-01-02",
                    "end_date": "2024-01-05",
                    "assignee_username": "john",
                    "sprint_name": "Sprint A",
                    "type": "Task",
                    "Parent": "Epic A",
                    "Severity": "High",
                }
            ]
        )

        with tempfile.TemporaryDirectory() as tmp:
            excel_path = Path(tmp) / "agile.xlsx"
            _write_excel(excel_path, _base_sprints_df(), tasks_df)
            _, rows, critical_errors, row_errors = ExcelReader().load(str(excel_path), _make_logger())

        self.assertEqual([], critical_errors)
        self.assertEqual([], row_errors)
        self.assertEqual("Epic A", rows[0]["parent_cell"])
        self.assertEqual({"Severity": "High"}, rows[0]["custom_attributes_raw"])

    def test_parent_column_name_is_case_insensitive(self) -> None:
        tasks_df = pd.DataFrame(
            [
                {
                    "name": "Task 1",
                    "description": "Desc",
                    "start_date": "2024-01-02",
                    "end_date": "2024-01-05",
                    "assignee_username": "john",
                    "sprint_name": "Sprint A",
                    "type": "Task",
                    "parent": "Epic B",
                }
            ]
        )

        with tempfile.TemporaryDirectory() as tmp:
            excel_path = Path(tmp) / "agile.xlsx"
            _write_excel(excel_path, _base_sprints_df(), tasks_df)
            _, rows, critical_errors, row_errors = ExcelReader().load(str(excel_path), _make_logger())

        self.assertEqual([], critical_errors)
        self.assertEqual([], row_errors)
        self.assertEqual("Epic B", rows[0]["parent_cell"])


if __name__ == "__main__":
    unittest.main()
