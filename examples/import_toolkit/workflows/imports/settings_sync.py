from __future__ import annotations

from teamstorm.api import TeamStormAPI

from import_toolkit.controllers.core.attributes import sync_attributes
from import_toolkit.controllers.core.membership import sync_workspace_members
from import_toolkit.controllers.core.contracts import SyncContext
from import_toolkit.controllers.core.types import sync_types
from import_toolkit.workflows.imports.metadata_sync import (
    sync_roles,
    sync_statuses,
    sync_workflows,
)


def run_settings_sync(
    api: TeamStormAPI,
    *,
    workspace_key: str,
    tasks_rows: list,
    update_settings: bool,
    sync_members: bool,
    dry_run: bool,
    log,
    warnings: list[str],
) -> SyncContext:
    if update_settings:
        sync_statuses(log, workspace_key=workspace_key)
        sync_workflows(log, workspace_key=workspace_key)
        sync_roles(log, workspace_key=workspace_key)
    else:
        log.info("Settings sync: metadata sync disabled (flag --update-settings is off)")

    attributes_by_column = sync_attributes(
        api,
        workspace_key=workspace_key,
        tasks_rows=tasks_rows,
        update_settings=update_settings,
        dry_run=dry_run,
        log=log,
        warnings=warnings,
    )
    known_types = sync_types(
        api,
        workspace_key=workspace_key,
        tasks_rows=tasks_rows,
        attributes_by_column=attributes_by_column,
        update_settings=update_settings,
        dry_run=dry_run,
        log=log,
        warnings=warnings,
    )
    user_cache = sync_workspace_members(
        api,
        workspace_key=workspace_key,
        tasks_rows=tasks_rows,
        attributes_by_column=attributes_by_column,
        sync_members=sync_members,
        dry_run=dry_run,
        log=log,
        warnings=warnings,
    )

    return SyncContext(
        attributes_by_column=attributes_by_column,
        user_cache=user_cache,
        known_types=known_types,
    )
