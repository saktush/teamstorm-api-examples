from __future__ import annotations

import logging
import re
from datetime import date, datetime
from typing import Any

import pandas as pd

from teamstorm.models.workitems import WorkitemModel
from import_toolkit.io.readers.contracts import SprintImportRow, TaskImportRow, ValidatedImport

SPRINT_REQUIRED_COLUMNS = ["sprint_name", "start_date", "end_date"]
BACKLOG_MARKERS = {"backlog", "backlog data"}
TASK_REQUIRED_COLUMNS = [
    "name",
    "description",
    "start_date",
    "end_date",
    "assignee_username",
    "type",
]


def _normalize_column_key(column_name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", column_name.lower())


def _find_column_name(df: pd.DataFrame, expected_name: str) -> str | None:
    expected_key = _normalize_column_key(expected_name)
    for column in df.columns:
        if _normalize_column_key(str(column)) == expected_key:
            return str(column)
    return None


def _is_backlog_marker(value: str) -> bool:
    return normalize_str(value).casefold() in BACKLOG_MARKERS


def _resolve_columns(df: pd.DataFrame, required_columns: list[str]) -> tuple[dict[str, str], list[str]]:
    resolved: dict[str, str] = {}
    missing: list[str] = []
    for column in required_columns:
        actual = _find_column_name(df, column)
        if actual is None:
            missing.append(column)
        else:
            resolved[column] = actual
    return resolved, missing


def _reserved_task_columns() -> set[str]:
    reserved: set[str] = set()
    for column in TASK_REQUIRED_COLUMNS:
        reserved.add(_normalize_column_key(column))
    # Optional metadata column used by importer for hierarchy resolution.
    reserved.add(_normalize_column_key("parent"))
    # Optional sprint link column in task rows.
    reserved.add(_normalize_column_key("sprint_name"))
    for field_name, field_info in WorkitemModel.model_fields.items():
        reserved.add(_normalize_column_key(field_name))
        if isinstance(field_info.alias, str):
            reserved.add(_normalize_column_key(field_info.alias))
    return reserved


def extract_attribute_columns(tasks_df: pd.DataFrame) -> list[str]:
    reserved = _reserved_task_columns()
    attribute_columns: list[str] = []
    for column in tasks_df.columns:
        if _normalize_column_key(str(column)) not in reserved:
            attribute_columns.append(str(column))
    return attribute_columns


def extract_custom_attributes_for_row(row: pd.Series, attribute_columns: list[str]) -> dict[str, str]:
    custom_attributes_raw: dict[str, str] = {}
    for column in attribute_columns:
        value = normalize_str(row.get(column))
        if value:
            custom_attributes_raw[column] = value
    return custom_attributes_raw


def normalize_str(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def parse_excel_date(value: Any, *, field: str, row_ref: str, errors: list[str]) -> date | None:
    if value is None or (isinstance(value, float) and pd.isna(value)) or (isinstance(value, str) and not value.strip()):
        errors.append(f"{row_ref}: поле {field} пустое")
        return None

    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    try:
        ts = pd.to_datetime(value, dayfirst=True, errors="raise")
        if isinstance(ts, pd.Series):
            ts = ts.iloc[0]
        return ts.date()
    except Exception:
        errors.append(f"{row_ref}: поле {field} имеет неверный формат даты: {value!r}")
        return None


def validate_dataframes(
    sprints_df: pd.DataFrame | None,
    tasks_df: pd.DataFrame,
    logger: logging.Logger,
    *,
    sprint_source_label: str,
    task_source_label: str,
    sprint_row_ref_template: str,
    task_row_ref_template: str,
    summary_label: str,
    sprint_lookup_label: str,
) -> ValidatedImport:
    critical_errors: list[str] = []
    row_errors: list[str] = []

    task_columns, missing_task_cols = _resolve_columns(tasks_df, TASK_REQUIRED_COLUMNS)
    if missing_task_cols:
        critical_errors.append(f"{task_source_label}: отсутствуют колонки: {missing_task_cols}")
    if critical_errors:
        return {}, [], critical_errors, row_errors

    sprints_by_name: dict[str, SprintImportRow] = {}
    if sprints_df is not None:
        sprint_columns, missing_sprint_cols = _resolve_columns(sprints_df, SPRINT_REQUIRED_COLUMNS)
        if missing_sprint_cols:
            logger.warning(
                "%s: отсутствуют колонки: %s; данные спринтов будут проигнорированы",
                sprint_source_label,
                missing_sprint_cols,
            )
        else:
            sprint_row_warnings: list[str] = []
            for idx, r in sprints_df.iterrows():
                row_ref = sprint_row_ref_template.format(row=idx + 2)
                sprint_name = normalize_str(r.get(sprint_columns["sprint_name"]))
                if not sprint_name:
                    sprint_row_warnings.append(f"{row_ref}: sprint_name пустой")
                    continue

                d_errors: list[str] = []
                sd = parse_excel_date(
                    r.get(sprint_columns["start_date"]),
                    field="start_date",
                    row_ref=row_ref,
                    errors=d_errors,
                )
                ed = parse_excel_date(
                    r.get(sprint_columns["end_date"]),
                    field="end_date",
                    row_ref=row_ref,
                    errors=d_errors,
                )
                if d_errors:
                    sprint_row_warnings.extend(d_errors)
                    continue
                assert sd is not None and ed is not None

                if sd > ed:
                    sprint_row_warnings.append(f"{row_ref}: start_date > end_date ({sd} > {ed})")
                    continue

                if sprint_name in sprints_by_name:
                    prev = sprints_by_name[sprint_name]
                    if prev["start_date"] != sd or prev["end_date"] != ed:
                        sprint_row_warnings.append(
                            f"{row_ref}: дубликат sprint_name={sprint_name!r} с конфликтующими датами "
                            f"({prev['start_date']}..{prev['end_date']}) vs ({sd}..{ed})"
                        )
                    continue

                sprints_by_name[sprint_name] = {
                    "name": sprint_name,
                    "start_date": sd,
                    "end_date": ed,
                }

            for warning in sprint_row_warnings:
                logger.warning("%s", warning)

    attribute_columns = extract_attribute_columns(tasks_df)
    parent_column_name = _find_column_name(tasks_df, "parent")
    sprint_column_name = _find_column_name(tasks_df, "sprint_name")
    tasks_rows: list[TaskImportRow] = []
    inferred_sprint_ranges: dict[str, tuple[date, date]] = {}
    for idx, r in tasks_df.iterrows():
        row_ref = task_row_ref_template.format(row=idx + 2)

        name = normalize_str(r.get(task_columns["name"]))
        description = normalize_str(r.get(task_columns["description"]))
        assignee_username = normalize_str(r.get(task_columns["assignee_username"]))
        wi_type = normalize_str(r.get(task_columns["type"]))
        sprint_name_raw = normalize_str(r.get(sprint_column_name)) if sprint_column_name else ""
        use_backlog = _is_backlog_marker(sprint_name_raw)
        sprint_name = "" if use_backlog else sprint_name_raw

        local_errors: list[str] = []
        if not name:
            local_errors.append(f"{row_ref}: name пустой")
        if not assignee_username:
            local_errors.append(f"{row_ref}: assignee_username пустой")
        if not wi_type:
            local_errors.append(f"{row_ref}: type пустой")

        sd = parse_excel_date(
            r.get(task_columns["start_date"]),
            field="start_date",
            row_ref=row_ref,
            errors=local_errors,
        )
        ed = parse_excel_date(
            r.get(task_columns["end_date"]),
            field="end_date",
            row_ref=row_ref,
            errors=local_errors,
        )

        if sd is not None and ed is not None and sd > ed:
            local_errors.append(f"{row_ref}: start_date > end_date ({sd} > {ed})")

        if local_errors:
            row_errors.extend(local_errors)
            continue

        parent_cell = ""
        if parent_column_name is not None:
            parent_cell = normalize_str(r.get(parent_column_name))

        assert sd is not None and ed is not None
        custom_attributes_raw = extract_custom_attributes_for_row(r, attribute_columns)
        tasks_rows.append(
            {
                "row_ref": row_ref,
                "name": name,
                "description": description,
                "assignee_username": assignee_username,
                "sprint_name": sprint_name,
                "use_backlog": use_backlog,
                "type": wi_type,
                "start_date": sd,
                "end_date": ed,
                "parent_cell": parent_cell,
                "custom_attributes_raw": custom_attributes_raw,
            }
        )
        if sprint_name:
            known_range = inferred_sprint_ranges.get(sprint_name)
            if known_range is None:
                inferred_sprint_ranges[sprint_name] = (sd, ed)
            else:
                known_start, known_end = known_range
                inferred_sprint_ranges[sprint_name] = (
                    min(known_start, sd),
                    max(known_end, ed),
                )

    for inferred_name, (inferred_start, inferred_end) in inferred_sprint_ranges.items():
        if inferred_name in sprints_by_name:
            continue
        sprints_by_name[inferred_name] = {
            "name": inferred_name,
            "start_date": inferred_start,
            "end_date": inferred_end,
        }
        logger.warning(
            "%s: sprint_name=%r отсутствует в %s; будет создан по датам задач (%s..%s)",
            summary_label,
            inferred_name,
            sprint_lookup_label,
            inferred_start,
            inferred_end,
        )

    logger.info(
        "%s: спринтов=%d, задач(валидных)=%d, ошибок_строк=%d",
        summary_label,
        len(sprints_by_name),
        len(tasks_rows),
        len(row_errors),
    )
    return sprints_by_name, tasks_rows, critical_errors, row_errors
