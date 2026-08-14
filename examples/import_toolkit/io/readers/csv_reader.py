from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from import_toolkit.io.readers.common import validate_dataframes
from import_toolkit.io.readers.contracts import ValidatedImport


class CsvReader:
    def load(self, input_path: str, logger: logging.Logger) -> ValidatedImport:
        base_dir = Path(input_path)
        sprints_path = base_dir / "sprints.csv"
        tasks_path = base_dir / "tasks.csv"

        if not tasks_path.exists():
            return (
                {},
                [],
                [f"В каталоге CSV отсутствует файл tasks.csv: {tasks_path}"],
                [],
            )

        try:
            tasks_df = pd.read_csv(tasks_path)
        except Exception as e:
            return {}, [], [f"Не удалось прочитать CSV: {e}"], []

        sprints_df: pd.DataFrame | None = None
        if sprints_path.exists():
            try:
                sprints_df = pd.read_csv(sprints_path)
            except Exception as e:
                logger.warning(
                    "Не удалось прочитать sprints.csv (%s); импорт продолжится без sprint sheet",
                    e,
                )

        return validate_dataframes(
            sprints_df,
            tasks_df,
            logger,
            sprint_source_label="sprints.csv",
            task_source_label="tasks.csv",
            sprint_row_ref_template="sprints.csv row {row}",
            task_row_ref_template="tasks.csv row {row}",
            summary_label="CSV",
            sprint_lookup_label="sprints.csv",
        )
