from __future__ import annotations

import logging

import pandas as pd

from import_toolkit.io.readers.common import validate_dataframes
from import_toolkit.io.readers.contracts import ValidatedImport


def _find_sheet_case_insensitive(sheet_names: list[str], expected_name: str) -> str | None:
    expected = expected_name.strip().casefold()
    for sheet_name in sheet_names:
        if sheet_name.strip().casefold() == expected:
            return sheet_name
    return None


class ExcelReader:
    def load(self, input_path: str, logger: logging.Logger) -> ValidatedImport:
        try:
            xls = pd.ExcelFile(input_path)
        except Exception as e:
            return {}, [], [f"Не удалось открыть Excel: {e}"], []

        if len(xls.sheet_names) == 0:
            return {}, [], ["В Excel отсутствуют листы"], []

        tasks_sheet = _find_sheet_case_insensitive(xls.sheet_names, "tasks")
        sprints_sheet = _find_sheet_case_insensitive(xls.sheet_names, "sprints")

        if tasks_sheet is None:
            if len(xls.sheet_names) >= 2:
                tasks_sheet = xls.sheet_names[1]
            else:
                tasks_sheet = xls.sheet_names[0]

        if sprints_sheet is None and len(xls.sheet_names) >= 2:
            candidate = xls.sheet_names[0]
            if candidate != tasks_sheet:
                sprints_sheet = candidate

        try:
            tasks_df = pd.read_excel(xls, sheet_name=tasks_sheet)
        except Exception as e:
            return {}, [], [f"Не удалось прочитать лист задач {tasks_sheet!r}: {e}"], []

        sprints_df: pd.DataFrame | None = None
        if sprints_sheet is not None:
            try:
                sprints_df = pd.read_excel(xls, sheet_name=sprints_sheet)
            except Exception as e:
                logger.warning(
                    "Не удалось прочитать лист спринтов %r: %s; импорт продолжится без sprint sheet",
                    sprints_sheet,
                    e,
                )

        return validate_dataframes(
            sprints_df,
            tasks_df,
            logger,
            sprint_source_label=sprints_sheet or "sprints (absent)",
            task_source_label=tasks_sheet,
            sprint_row_ref_template=f"{sprints_sheet or 'sprints'} row {{row}}",
            task_row_ref_template=f"{tasks_sheet} row {{row}}",
            summary_label="Excel",
            sprint_lookup_label=sprints_sheet or "sprints",
        )
