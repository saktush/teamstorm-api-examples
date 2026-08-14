#!/usr/bin/env python3
import argparse
from datetime import datetime
from pathlib import Path
from typing import List
from uuid import UUID

from teamstorm.client import TsClient
from teamstorm.models.workspaces import WorkspaceModel
from teamstorm.api import TeamStormAPI

from import_toolkit.logging_config import setup_logging
from import_toolkit.controllers.core.bootstrap import ensure_agile_extension, ensure_folder
from import_toolkit.controllers.core.contracts import Counters, SELECT_TAG_WRITE_STRATEGY
from import_toolkit.controllers.core.utils import pick_single
from import_toolkit.controllers.extensions.agile.sprints import upsert_sprints
from import_toolkit.controllers.extensions.agile.workitems import upsert_agile_workitems
from import_toolkit.io.readers import select_reader
from import_toolkit.io.readers.contracts import SprintImportRow, TaskImportRow
from import_toolkit.workflows.imports.cli import build_arg_parser, resolve_input_path
from import_toolkit.workflows.imports.settings_sync import run_settings_sync


def run_import_agile(args: argparse.Namespace) -> int:
    log = setup_logging(args.log_file)
    input_path = resolve_input_path(args, log)
    if not input_path:
        log.error(("Не указан путь для импорта: используйте --input-path " "или временно --excel-path"))
        return 2

    log.info(
        (
            "Start import (dry_run=%s, update_settings=%s, sync_members=%s), "
            "base_url=%s, workspace_key=%s, folder_name=%s, input=%s"
        ),
        args.dry_run,
        args.update_settings,
        args.sync_members,
        args.base_url,
        args.workspace_key,
        args.folder_name,
        input_path,
    )
    script_mtime = datetime.fromtimestamp(Path(__file__).stat().st_mtime)
    log.info(
        "Importer build marker: file_mtime=%s select_tag_strategy=%s",
        script_mtime.isoformat(timespec="seconds"),
        SELECT_TAG_WRITE_STRATEGY,
    )

    client = TsClient(args.base_url, args.token, logger=log, allow_insecure=args.allow_insecure)
    api = TeamStormAPI(client)

    counters = Counters()
    errors: list[str] = []
    non_fatal_select_tag_errors: list[str] = []
    warnings: list[str] = []
    sprints_by_name: dict[str, SprintImportRow] = {}
    tasks_rows: list[TaskImportRow] = []

    # Read and validate input first
    try:
        reader = select_reader(input_path)
    except ValueError as e:
        critical_errors = [str(e)]
        row_errors = []
    else:
        sprints_by_name, tasks_rows, critical_errors, row_errors = reader.load(input_path, log)
    if critical_errors:
        for e in critical_errors:
            log.error(e)
        log.error("Критические ошибки валидации: записи в API не будут выполнены")
        return 2
    errors.extend(row_errors)
    has_sprint_data = (
        bool(sprints_by_name)
        or any(row["use_backlog"] for row in tasks_rows)
        or any(bool(row["sprint_name"]) for row in tasks_rows)
    )

    # Workspace by key: GET /workspaces?key=...
    try:
        workspaces: List[WorkspaceModel] = api.workspaces.list(key=args.workspace_key)
        ws = pick_single(workspaces, f"Workspace key={args.workspace_key!r}")
        workspace_id = ws.id
        log.info("Workspace %s найден: id=%s", args.workspace_key, workspace_id)
    except Exception as e:
        log.error(str(e))
        return 2

    # Folder: only first level in workspace (parentId=workspaceId)
    try:
        folder_id = ensure_folder(
            api,
            workspace_key=args.workspace_key,
            folder_name=args.folder_name,
            workspace_id=workspace_id,
            log=log,
        )
    except Exception:
        return 2

    sprint_id_by_name: dict[str, UUID] = {}
    if has_sprint_data:
        # Agile extension in folder
        try:
            agile_id = ensure_agile_extension(
                api,
                workspace_key=args.workspace_key,
                folder_id=folder_id,
                dry_run=args.dry_run,
                log=log,
            )
        except Exception:
            return 2

        # Sprints upsert
        sprint_id_by_name = upsert_sprints(
            api,
            workspace_key=args.workspace_key,
            folder_id=folder_id,
            agile_id=agile_id,
            sprints_by_name=sprints_by_name,
            counters=counters,
            dry_run=args.dry_run,
            log=log,
            errors=errors,
        )
    else:
        log.info(("Sprint data отсутствуют: проверка/создание Agile extension " "и upsert спринтов пропущены"))

    # Optional metadata/settings sync
    sync_context = run_settings_sync(
        api,
        workspace_key=args.workspace_key,
        tasks_rows=tasks_rows,
        update_settings=args.update_settings,
        sync_members=args.sync_members,
        dry_run=args.dry_run,
        log=log,
        warnings=warnings,
    )

    # Workitems upsert
    upsert_agile_workitems(
        api,
        workspace_key=args.workspace_key,
        folder_id=folder_id,
        sprint_id_by_name=sprint_id_by_name,
        tasks_rows=tasks_rows,
        sync_context=sync_context,
        update_settings=args.update_settings,
        counters=counters,
        dry_run=args.dry_run,
        log=log,
        warnings=warnings,
        errors=errors,
        non_fatal_select_tag_errors=non_fatal_select_tag_errors,
    )

    # Final report
    log.info("=== Итог ===")
    log.info(
        "Sprints: created=%d, patched=%d",
        counters.sprints_created,
        counters.sprints_patched,
    )
    log.info(
        "Workitems: created=%d, patched=%d",
        counters.workitems_created,
        counters.workitems_patched,
    )
    log.info(
        "Custom attribute updates: attempted=%d, succeeded=%d, failed=%d, skipped=%d",
        counters.custom_attr_updates_attempted,
        counters.custom_attr_updates_succeeded,
        counters.custom_attr_updates_failed,
        counters.custom_attr_updates_skipped,
    )
    log.info("Rows skipped (dry-run/invalid)=%d", counters.rows_skipped)
    if non_fatal_select_tag_errors:
        log.info(
            "Non-fatal UniSelect/Tag row failures: %d",
            len(non_fatal_select_tag_errors),
        )
        for failure in non_fatal_select_tag_errors:
            log.warning(failure)
    if warnings:
        log.info("Предупреждений: %d", len(warnings))
        for warning in warnings:
            log.warning(warning)

    if errors:
        log.info("Ошибок: %d", len(errors))
        for e in errors:
            log.error(e)
        return 1

    if non_fatal_select_tag_errors:
        log.info("Завершено с non-fatal ошибками UniSelect/Tag")
        return 0

    log.info("Ошибок нет")
    return 0


def main() -> int:
    ap = build_arg_parser()
    args = ap.parse_args()
    return run_import_agile(args)


if __name__ == "__main__":
    raise SystemExit(main())
