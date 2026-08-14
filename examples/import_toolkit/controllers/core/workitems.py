from __future__ import annotations

import logging
from typing import Callable, Optional, Sequence
from uuid import UUID

from teamstorm.client import ApiError
from teamstorm.models.folders import CreateFolderRequestBody
from teamstorm.models.workitems import (
    CreateWorkitemRequestBody,
    PatchWorkitemRequestBody,
    WorkitemModel,
)
from teamstorm.api import TeamStormAPI

from import_toolkit.controllers.core.contracts import SyncContext
from import_toolkit.controllers.core.custom_attributes import (
    build_create_custom_attributes_for_row,
    maybe_update_existing_workitem_custom_attributes,
)
from import_toolkit.controllers.core.utils import (
    _date_to_iso_datetime,
    format_api_error,
    normalize_str,
    pick_single,
)
from import_toolkit.io.readers.contracts import TaskImportRow


def _name_key(value: str) -> str:
    return normalize_str(value).casefold()


def upsert_workitems(
    api: TeamStormAPI,
    *,
    workspace_key: str,
    folder_id: UUID,
    tasks_rows: Sequence[TaskImportRow],
    sync_context: SyncContext,
    update_settings: bool,
    counters,
    dry_run: bool,
    log: logging.Logger,
    warnings: list[str],
    errors: list[str],
    non_fatal_select_tag_errors: list[str],
    resolve_sprint_id: Callable[[int, TaskImportRow], Optional[UUID]],
) -> None:
    user_cache: dict[str, str] = {}
    type_cache: dict[str, bool] = {}
    subfolder_id_cache: dict[str, UUID] = {}
    workitem_id_by_row_index: dict[int, UUID] = {}
    dry_run_created_id_by_row_index: dict[int, UUID] = {}

    # Parent context is stateful:
    # - non-empty Parent cell sets the current parent context
    # - empty Parent cell resets context to root import folder
    effective_parent_name_by_row_index: dict[int, str] = {}
    current_parent_context = ""
    for row_index, row in enumerate(tasks_rows):
        parent_cell = normalize_str(row.get("parent_cell", ""))
        if parent_cell:
            current_parent_context = parent_cell
        else:
            current_parent_context = ""
        effective_parent_name_by_row_index[row_index] = current_parent_context

    task_row_indexes_by_name: dict[str, list[int]] = {}
    for row_index, row in enumerate(tasks_rows):
        task_name_key = _name_key(row["name"])
        task_row_indexes_by_name.setdefault(task_name_key, []).append(row_index)

    parent_task_row_index_by_row_index: dict[int, int] = {}
    for row_index, parent_name in effective_parent_name_by_row_index.items():
        if not parent_name:
            continue
        task_matches = task_row_indexes_by_name.get(_name_key(parent_name), [])
        if not task_matches:
            continue

        chosen_parent_row_index = task_matches[0]
        parent_task_row_index_by_row_index[row_index] = chosen_parent_row_index

        if len(task_matches) > 1:
            row_ref = tasks_rows[row_index]["row_ref"]
            chosen_ref = tasks_rows[chosen_parent_row_index]["row_ref"]
            match_refs = ", ".join(tasks_rows[i]["row_ref"] for i in task_matches)
            warning = (
                f"{row_ref}: Parent={parent_name!r} неоднозначен; совпадения: {match_refs}; "
                f"используется {chosen_ref}"
            )
            warnings.append(warning)
            log.warning(warning)

    def _get_or_create_subfolder_id(*, row_ref: str, folder_name: str) -> UUID:
        folder_name_key = _name_key(folder_name)
        cached = subfolder_id_cache.get(folder_name_key)
        if cached is not None:
            return cached

        folders = api.folders.list(
            workspace_key,
            name=folder_name,
            parent_id=folder_id,
        )
        if len(folders) == 0:
            created = api.folders.create(
                workspace_key,
                CreateFolderRequestBody(
                    name=folder_name,
                    parentId=folder_id,
                ),
            )
            subfolder_id_cache[folder_name_key] = created.id
            log.info(
                "%s: Subfolder %r не найдена в parentId=%s, создана: id=%s",
                row_ref,
                folder_name,
                folder_id,
                created.id,
            )
            return created.id

        folder = pick_single(
            folders,
            f"{row_ref}: Folder name={folder_name!r} parentId={folder_id}",
        )
        subfolder_id_cache[folder_name_key] = folder.id
        return folder.id

    def _upsert_single_row(*, row_index: int, row: TaskImportRow, parent_id: UUID) -> Optional[UUID]:
        row_ref = row["row_ref"]
        name = row["name"]
        log.info(
            "%s: Workitem UPSERT start: name=%r parentId=%s dry_run=%s",
            row_ref,
            name,
            parent_id,
            dry_run,
        )

        sprint_id = resolve_sprint_id(row_index, row)
        sprint_name = normalize_str(row.get("sprint_name", ""))

        username = row["assignee_username"]
        if username in user_cache:
            user_id = user_cache[username]
        else:
            users = api.users.list(username=username)
            exact = [u for u in users if normalize_str(u.username) == username]
            if len(exact) == 0:
                raise ApiError(f"{row_ref}: пользователь username={username!r} не найден")
            if len(exact) > 1:
                raise ApiError(f"{row_ref}: пользователь username={username!r} найден >1 (неоднозначно)")
            user_id = str(exact[0].id)
            user_cache[username] = user_id

        wi_type = row["type"]
        log.info(
            "%s: Workitem UPSERT resolved: sprintId=%s assignee=%r type=%s",
            row_ref,
            sprint_id,
            username,
            wi_type,
        )
        if wi_type not in type_cache:
            if wi_type in sync_context.known_types:
                type_cache[wi_type] = True
            else:
                _ = api.types.get(workspace_key, wi_type)
                type_cache[wi_type] = True

        start_iso = _date_to_iso_datetime(row["start_date"])
        end_iso = _date_to_iso_datetime(row["end_date"])
        description = row["description"]

        if dry_run and sprint_name and (sprint_id is None or str(sprint_id).startswith("<dry-run")):
            log.info(
                "%s: dry-run: пропуск поиска/создания workitem, т.к. sprintId не реальный; было бы: upsert %r",
                row_ref,
                name,
            )
            counters.rows_skipped += 1
            return None

        if sprint_id is None:
            found_wi_all: list[WorkitemModel] = api.workitems.list(
                workspace_key,
                parent=parent_id,
                name=name,
            )
            found_wi = [wi for wi in found_wi_all if wi.sprint is None]
        else:
            found_wi = api.workitems.list(
                workspace_key,
                sprint_id=sprint_id,
                parent=parent_id,
                name=name,
            )

        if len(found_wi) == 0:
            is_existing_workitem = False
            if dry_run:
                workitem_id = dry_run_created_id_by_row_index.get(row_index)
                if workitem_id is None:
                    workitem_id = UUID(int=row_index + 1)
                    dry_run_created_id_by_row_index[row_index] = workitem_id
                log.info(
                    "%s: Workitem CREATE: %r (parentId=%s, type=%s) затем PATCH (sprintId=%s)",
                    row_ref,
                    name,
                    parent_id,
                    wi_type,
                    sprint_id,
                )
                counters.rows_skipped += 1
                return workitem_id

            log.info(
                "%s: Workitem UPSERT action: create new workitem name=%r sprintId=%s parentId=%s",
                row_ref,
                name,
                sprint_id,
                parent_id,
            )
            body = CreateWorkitemRequestBody(
                name=name,
                parentId=parent_id,
                type=wi_type,
                sprintId=sprint_id,
                assignee=user_id,
                dueDate=end_iso,
                description=description or None,
                attributes=build_create_custom_attributes_for_row(
                    api,
                    workspace_key=workspace_key,
                    row=row,
                    sync_context=sync_context,
                    update_settings=update_settings,
                    dry_run=dry_run,
                    log=log,
                    warnings=warnings,
                )
                or None,
            )
            log.debug(
                "%s: Workitem CREATE payload=%r",
                row_ref,
                body.model_dump(mode="json"),
            )

            created = api.workitems.create(workspace_key, body)
            workitem_id = created.id
            counters.workitems_created += 1

        elif len(found_wi) == 1:
            is_existing_workitem = True
            workitem_id = found_wi[0].id
            log.info(
                "%s: Workitem UPSERT action: reuse existing id=%s name=%r",
                row_ref,
                workitem_id,
                name,
            )
        else:
            raise ApiError(
                f"{row_ref}: найдено >1 workitem для name={name!r} (sprintId={sprint_id or '<none>'}, parent={parent_id})"
            )

        if dry_run:
            log.info(
                "%s: Workitem PATCH: id=%s name=%r sprintId=%s assignee=%r",
                row_ref,
                workitem_id,
                name,
                sprint_id,
                username,
            )
            maybe_update_existing_workitem_custom_attributes(
                api,
                is_existing_workitem=is_existing_workitem,
                workspace_key=workspace_key,
                workitem_id=workitem_id,
                row=row,
                sync_context=sync_context,
                update_settings=update_settings,
                dry_run=True,
                log=log,
                warnings=warnings,
                errors=errors,
                counters=counters,
                non_fatal_select_tag_errors=non_fatal_select_tag_errors,
            )
            return workitem_id

        log.info(
            "%s: Workitem UPSERT action: patch id=%s sprintId=%s assignee=%r",
            row_ref,
            workitem_id,
            sprint_id,
            username,
        )
        api.workitems.patch(
            workspace_key,
            workitem_id=workitem_id,
            body=PatchWorkitemRequestBody(
                description=description or None,
                type=wi_type,
                startDate=start_iso,
                dueDate=end_iso,
                assignee=user_id,
                sprintId=sprint_id,
            ),
        )
        maybe_update_existing_workitem_custom_attributes(
            api,
            is_existing_workitem=is_existing_workitem,
            workspace_key=workspace_key,
            workitem_id=workitem_id,
            row=row,
            sync_context=sync_context,
            update_settings=update_settings,
            dry_run=False,
            log=log,
            warnings=warnings,
            errors=errors,
            counters=counters,
            non_fatal_select_tag_errors=non_fatal_select_tag_errors,
        )
        counters.workitems_patched += 1
        log.info("%s: Workitem UPSERT done: id=%s", row_ref, workitem_id)
        return workitem_id

    row_states: list[str] = ["pending"] * len(tasks_rows)

    def _process_row(row_index: int) -> bool:
        state = row_states[row_index]
        if state == "done":
            return True
        if state == "failed":
            return False
        if state == "processing":
            row_ref = tasks_rows[row_index]["row_ref"]
            message = f"{row_ref}: обнаружен циклический Parent dependency"
            log.error(message)
            errors.append(message)
            row_states[row_index] = "failed"
            return False

        row_states[row_index] = "processing"
        row = tasks_rows[row_index]
        row_ref = row["row_ref"]

        try:
            parent_id = folder_id
            effective_parent_name = effective_parent_name_by_row_index[row_index]

            if effective_parent_name:
                parent_task_row_index = parent_task_row_index_by_row_index.get(row_index)
                if parent_task_row_index is not None:
                    if parent_task_row_index == row_index:
                        raise ApiError(f"{row_ref}: Parent={effective_parent_name!r} указывает на эту же задачу")

                    if not _process_row(parent_task_row_index):
                        raise ApiError(
                            f"{row_ref}: parent task {effective_parent_name!r} не может быть использована из-за ошибки в родительской строке"
                        )

                    parent_workitem_id = workitem_id_by_row_index.get(parent_task_row_index)
                    if parent_workitem_id is None:
                        raise ApiError(f"{row_ref}: parent task {effective_parent_name!r} не имеет workitem id")
                    parent_id = parent_workitem_id
                else:
                    parent_id = _get_or_create_subfolder_id(
                        row_ref=row_ref,
                        folder_name=effective_parent_name,
                    )

            workitem_id = _upsert_single_row(
                row_index=row_index,
                row=row,
                parent_id=parent_id,
            )
            if workitem_id is not None:
                workitem_id_by_row_index[row_index] = workitem_id

            row_states[row_index] = "done"
            return True

        except ApiError as e:
            message = f"{row_ref}: {format_api_error(e)}"
            log.error(message)
            errors.append(message)
            row_states[row_index] = "failed"
            return False
        except Exception as e:
            message = f"{row_ref}: {e}"
            log.error(message)
            errors.append(message)
            row_states[row_index] = "failed"
            return False

    for row_index in range(len(tasks_rows)):
        _process_row(row_index)
