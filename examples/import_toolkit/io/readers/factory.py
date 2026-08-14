from __future__ import annotations

from pathlib import Path

from import_toolkit.io.readers.contracts import Reader
from import_toolkit.io.readers.csv_reader import CsvReader
from import_toolkit.io.readers.excel_reader import ExcelReader

EXCEL_EXTENSIONS = {".xlsx", ".xls"}


def select_reader(input_path: str) -> Reader:
    path = Path(input_path)

    if path.is_dir():
        return CsvReader()
    if path.suffix.lower() in EXCEL_EXTENSIONS:
        return ExcelReader()

    raise ValueError(
        f"Неподдерживаемый input_path={input_path!r}: ожидается .xlsx/.xls файл или директория с sprints.csv и tasks.csv"
    )
