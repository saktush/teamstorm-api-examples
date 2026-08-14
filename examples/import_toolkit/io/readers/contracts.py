from __future__ import annotations

import logging
from datetime import date
from typing import Protocol, TypedDict


class SprintImportRow(TypedDict):
    name: str
    start_date: date
    end_date: date


class TaskImportRow(TypedDict):
    row_ref: str
    name: str
    description: str
    assignee_username: str
    sprint_name: str
    use_backlog: bool
    type: str
    start_date: date
    end_date: date
    parent_cell: str
    custom_attributes_raw: dict[str, str]


ValidatedImport = tuple[
    dict[str, SprintImportRow],
    list[TaskImportRow],
    list[str],
    list[str],
]


class Reader(Protocol):
    def load(self, input_path: str, logger: logging.Logger) -> ValidatedImport: ...
