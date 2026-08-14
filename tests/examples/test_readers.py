import logging
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from import_toolkit.io.readers import CsvReader, ExcelReader, select_reader
from import_toolkit.io.readers.csv_reader import CsvReader as CsvReaderClass
from import_toolkit.io.readers.excel_reader import ExcelReader as ExcelReaderClass


def _make_logger() -> logging.Logger:
    logger = logging.getLogger("test.readers")
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    return logger


def _base_sprints_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"sprint_name": "Sprint A", "start_date": "2024-01-01", "end_date": "2024-01-10"},
        ]
    )


def _base_tasks_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "name": "Task 1",
                "description": "Do work",
                "start_date": "2024-01-02",
                "end_date": "2024-01-05",
                "assignee_username": "john",
                "sprint_name": "Sprint A",
                "type": "Task",
            }
        ]
    )


def _write_excel(
    path: Path,
    sprints_df: pd.DataFrame | None,
    tasks_df: pd.DataFrame,
    *,
    sprints_sheet: str = "Sheet1",
    tasks_sheet: str = "Sheet2",
) -> None:
    with pd.ExcelWriter(path) as writer:
        if sprints_df is not None:
            sprints_df.to_excel(writer, index=False, sheet_name=sprints_sheet)
        tasks_df.to_excel(writer, index=False, sheet_name=tasks_sheet)


class ReadersTestCase(unittest.TestCase):
    def test_excel_happy_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            excel_path = Path(tmp) / "agile.xlsx"
            _write_excel(excel_path, _base_sprints_df(), _base_tasks_df())

            sprints, tasks, critical_errors, row_errors = ExcelReader().load(str(excel_path), _make_logger())

            self.assertEqual([], critical_errors)
            self.assertEqual([], row_errors)
            self.assertEqual({"Sprint A"}, set(sprints.keys()))
            self.assertEqual(1, len(tasks))
            self.assertEqual("Sheet2 row 2", tasks[0]["row_ref"])
            self.assertEqual("", tasks[0]["parent_cell"])
            self.assertFalse(tasks[0]["use_backlog"])

    def test_excel_named_sheets_are_preferred(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            excel_path = Path(tmp) / "agile.xlsx"
            _write_excel(
                excel_path,
                _base_sprints_df(),
                _base_tasks_df(),
                sprints_sheet="sprints",
                tasks_sheet="tasks",
            )

            sprints, tasks, critical_errors, row_errors = ExcelReader().load(str(excel_path), _make_logger())

            self.assertEqual([], critical_errors)
            self.assertEqual([], row_errors)
            self.assertEqual({"Sprint A"}, set(sprints.keys()))
            self.assertEqual("tasks row 2", tasks[0]["row_ref"])

    def test_excel_missing_required_column_is_critical(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            excel_path = Path(tmp) / "agile.xlsx"
            bad_tasks = _base_tasks_df().drop(columns=["type"])
            _write_excel(excel_path, _base_sprints_df(), bad_tasks)

            sprints, tasks, critical_errors, row_errors = ExcelReader().load(str(excel_path), _make_logger())

            self.assertEqual({}, sprints)
            self.assertEqual([], tasks)
            self.assertEqual([], row_errors)
            self.assertTrue(any("Sheet2: отсутствуют колонки" in e for e in critical_errors))

    def test_excel_conflicting_duplicate_sprint_is_warning_and_not_critical(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            excel_path = Path(tmp) / "agile.xlsx"
            sprints_df = pd.DataFrame(
                [
                    {
                        "sprint_name": "Sprint A",
                        "start_date": "2024-01-01",
                        "end_date": "2024-01-10",
                    },
                    {
                        "sprint_name": "Sprint A",
                        "start_date": "2024-01-01",
                        "end_date": "2024-01-20",
                    },
                ]
            )
            _write_excel(excel_path, sprints_df, _base_tasks_df())

            with self.assertLogs("test.readers", level="WARNING") as captured:
                sprints, tasks, critical_errors, row_errors = ExcelReader().load(str(excel_path), _make_logger())

            self.assertEqual([], critical_errors)
            self.assertEqual([], row_errors)
            self.assertEqual({"Sprint A"}, set(sprints.keys()))
            self.assertEqual(1, len(tasks))
            self.assertTrue(any("дубликат sprint_name" in line for line in captured.output))

    def test_tasks_missing_sprint_column_are_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            excel_path = Path(tmp) / "agile.xlsx"
            tasks_df = _base_tasks_df().drop(columns=["sprint_name"])
            _write_excel(excel_path, _base_sprints_df(), tasks_df)

            sprints, tasks, critical_errors, row_errors = ExcelReader().load(str(excel_path), _make_logger())

            self.assertEqual([], critical_errors)
            self.assertEqual([], row_errors)
            self.assertEqual(1, len(tasks))
            self.assertEqual("", tasks[0]["sprint_name"])
            self.assertFalse(tasks[0]["use_backlog"])
            self.assertEqual({"Sprint A"}, set(sprints.keys()))

    def test_empty_sprint_cell_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            excel_path = Path(tmp) / "agile.xlsx"
            tasks_df = _base_tasks_df().copy()
            tasks_df.loc[0, "sprint_name"] = ""
            _write_excel(excel_path, _base_sprints_df(), tasks_df)

            sprints, tasks, critical_errors, row_errors = ExcelReader().load(str(excel_path), _make_logger())

            self.assertEqual([], critical_errors)
            self.assertEqual([], row_errors)
            self.assertEqual(1, len(tasks))
            self.assertEqual("", tasks[0]["sprint_name"])
            self.assertFalse(tasks[0]["use_backlog"])
            self.assertEqual({"Sprint A"}, set(sprints.keys()))

    def test_unknown_sprint_is_inferred_from_task_dates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            excel_path = Path(tmp) / "agile.xlsx"
            tasks_df = pd.DataFrame(
                [
                    {
                        "name": "Task 1",
                        "description": "Do work",
                        "start_date": pd.Timestamp("2024-01-02").date(),
                        "end_date": pd.Timestamp("2024-01-05").date(),
                        "assignee_username": "john",
                        "sprint_name": "Sprint B",
                        "type": "Task",
                    },
                    {
                        "name": "Task 2",
                        "description": "Do work 2",
                        "start_date": pd.Timestamp("2024-01-07").date(),
                        "end_date": pd.Timestamp("2024-01-20").date(),
                        "assignee_username": "john",
                        "sprint_name": "Sprint B",
                        "type": "Task",
                    },
                ]
            )
            _write_excel(excel_path, _base_sprints_df(), tasks_df)

            with self.assertLogs("test.readers", level="WARNING") as captured:
                sprints, tasks, critical_errors, row_errors = ExcelReader().load(str(excel_path), _make_logger())

            self.assertEqual([], critical_errors)
            self.assertEqual([], row_errors)
            self.assertEqual(2, len(tasks))
            self.assertIn("Sprint B", sprints)
            self.assertEqual(pd.Timestamp("2024-01-02").date(), sprints["Sprint B"]["start_date"])
            self.assertEqual(pd.Timestamp("2024-01-20").date(), sprints["Sprint B"]["end_date"])
            self.assertTrue(any("будет создан по датам задач" in line for line in captured.output))

    def test_backlog_marker_in_task_sets_use_backlog(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            excel_path = Path(tmp) / "agile.xlsx"
            tasks_df = _base_tasks_df().copy()
            tasks_df.loc[0, "sprint_name"] = "Backlog"
            _write_excel(excel_path, _base_sprints_df(), tasks_df)

            sprints, tasks, critical_errors, row_errors = ExcelReader().load(str(excel_path), _make_logger())

            self.assertEqual([], critical_errors)
            self.assertEqual([], row_errors)
            self.assertEqual(1, len(tasks))
            self.assertTrue(tasks[0]["use_backlog"])
            self.assertEqual("", tasks[0]["sprint_name"])
            self.assertNotIn("Backlog", sprints)

    def test_backlog_data_marker_in_task_sets_use_backlog(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            excel_path = Path(tmp) / "agile.xlsx"
            tasks_df = _base_tasks_df().copy()
            tasks_df.loc[0, "sprint_name"] = "  backlog data  "
            _write_excel(excel_path, _base_sprints_df(), tasks_df)

            sprints, tasks, critical_errors, row_errors = ExcelReader().load(str(excel_path), _make_logger())

            self.assertEqual([], critical_errors)
            self.assertEqual([], row_errors)
            self.assertEqual(1, len(tasks))
            self.assertTrue(tasks[0]["use_backlog"])
            self.assertEqual("", tasks[0]["sprint_name"])
            self.assertNotIn("backlog data", {k.casefold() for k in sprints.keys()})

    def test_csv_happy_path_matches_excel_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            sprints_df = _base_sprints_df()
            tasks_df = _base_tasks_df()
            excel_path = base / "agile.xlsx"
            csv_dir = base / "csv_input"
            csv_dir.mkdir(parents=True)

            _write_excel(excel_path, sprints_df, tasks_df)
            sprints_df.to_csv(csv_dir / "sprints.csv", index=False)
            tasks_df.to_csv(csv_dir / "tasks.csv", index=False)

            excel_result = ExcelReader().load(str(excel_path), _make_logger())
            csv_result = CsvReader().load(str(csv_dir), _make_logger())

            self.assertEqual(excel_result[0], csv_result[0])
            self.assertEqual([], csv_result[2])
            self.assertEqual([], csv_result[3])
            self.assertEqual(1, len(csv_result[1]))
            self.assertEqual("tasks.csv row 2", csv_result[1][0]["row_ref"])

    def test_csv_missing_tasks_file_is_critical(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_dir = Path(tmp) / "csv_input"
            csv_dir.mkdir(parents=True)
            _base_sprints_df().to_csv(csv_dir / "sprints.csv", index=False)

            sprints, tasks, critical_errors, row_errors = CsvReader().load(str(csv_dir), _make_logger())

            self.assertEqual({}, sprints)
            self.assertEqual([], tasks)
            self.assertEqual([], row_errors)
            self.assertTrue(any("tasks.csv" in e for e in critical_errors))

    def test_csv_missing_sprints_file_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_dir = Path(tmp) / "csv_input"
            csv_dir.mkdir(parents=True)
            tasks_df = _base_tasks_df().drop(columns=["sprint_name"])
            tasks_df.to_csv(csv_dir / "tasks.csv", index=False)

            sprints, tasks, critical_errors, row_errors = CsvReader().load(str(csv_dir), _make_logger())

            self.assertEqual([], critical_errors)
            self.assertEqual([], row_errors)
            self.assertEqual({}, sprints)
            self.assertEqual(1, len(tasks))
            self.assertEqual("", tasks[0]["sprint_name"])

    def test_factory_selects_excel_or_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_dir = Path(tmp) / "csv_input"
            csv_dir.mkdir(parents=True)

            self.assertIsInstance(select_reader(str(csv_dir)), CsvReaderClass)
            self.assertIsInstance(select_reader(str(Path(tmp) / "agile.xlsx")), ExcelReaderClass)

    def test_factory_unsupported_path(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            select_reader("/tmp/not_supported.txt")

        self.assertIn("Неподдерживаемый input_path", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
