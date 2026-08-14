from __future__ import annotations

import logging
from typing import Mapping, Optional, Sequence
from uuid import UUID

from teamstorm.client import ApiError
from teamstorm.api import TeamStormAPI

from import_toolkit.controllers.core.contracts import SyncContext
from import_toolkit.controllers.core.utils import normalize_str
from import_toolkit.controllers.core.workitems import upsert_workitems
from import_toolkit.io.readers.contracts import TaskImportRow


def upsert_agile_workitems(
    api: TeamStormAPI,
    *,
    workspace_key: str,
    folder_id: UUID,
    sprint_id_by_name: Mapping[str, UUID],
    tasks_rows: Sequence[TaskImportRow],
    sync_context: SyncContext,
    update_settings: bool,
    counters,
    dry_run: bool,
    log: logging.Logger,
    warnings: list[str],
    errors: list[str],
    non_fatal_select_tag_errors: list[str],
) -> None:
    backlog_sprint_id_cache: Optional[UUID] = None
    backlog_sprint_resolution_attempted = False
    backlog_sprint_resolution_error: Optional[str] = None

    def _get_backlog_sprint_id(*, row_ref: str) -> UUID:
        nonlocal backlog_sprint_id_cache
        nonlocal backlog_sprint_resolution_attempted
        nonlocal backlog_sprint_resolution_error

        if backlog_sprint_resolution_attempted:
            if backlog_sprint_resolution_error:
                raise ApiError(f"{row_ref}: {backlog_sprint_resolution_error}")
            assert backlog_sprint_id_cache is not None
            return backlog_sprint_id_cache

        backlog_sprint_resolution_attempted = True
        sprints = api.sprints.list(workspace_key, folder_id=folder_id)
        backlog_sprints = [s for s in sprints if getattr(s, "is_backlog", False)]

        if len(backlog_sprints) == 1:
            backlog_sprint_id_cache = backlog_sprints[0].id
            return backlog_sprint_id_cache

        if len(backlog_sprints) == 0:
            backlog_sprint_resolution_error = "backlog sprint (isBacklog=true) не найден для agile folder"
            raise ApiError(f"{row_ref}: {backlog_sprint_resolution_error}")

        backlog_sprint_resolution_error = "найдено >1 backlog sprint (isBacklog=true) для agile folder"
        raise ApiError(f"{row_ref}: {backlog_sprint_resolution_error}")

    def resolve_sprint_id(row_index: int, row: TaskImportRow) -> Optional[UUID]:
        del row_index
        row_ref = row["row_ref"]
        use_backlog = bool(row.get("use_backlog", False))
        sprint_name = normalize_str(row.get("sprint_name", ""))
        if use_backlog:
            return _get_backlog_sprint_id(row_ref=row_ref)
        if sprint_name:
            sprint_id = sprint_id_by_name.get(sprint_name)
            if not sprint_id or str(sprint_id).startswith("<dry-run"):
                if not dry_run or not sprint_id:
                    raise ApiError(f"{row_ref}: sprintId не найден для sprint_name={sprint_name!r}")
            return sprint_id
        return None

    upsert_workitems(
        api,
        workspace_key=workspace_key,
        folder_id=folder_id,
        tasks_rows=tasks_rows,
        sync_context=sync_context,
        update_settings=update_settings,
        counters=counters,
        dry_run=dry_run,
        log=log,
        warnings=warnings,
        errors=errors,
        non_fatal_select_tag_errors=non_fatal_select_tag_errors,
        resolve_sprint_id=resolve_sprint_id,
    )
