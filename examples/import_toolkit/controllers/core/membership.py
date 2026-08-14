from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from teamstorm.models.enums import AttributeType
from teamstorm.api import TeamStormAPI

from import_toolkit.controllers.core.contracts import SyncedAttribute
from import_toolkit.controllers.core.users import _find_system_user_role, _resolve_user_identifier
from import_toolkit.controllers.core.utils import _warn, normalize_str


def sync_workspace_members(
    api: TeamStormAPI,
    *,
    workspace_key: str,
    tasks_rows: list,
    attributes_by_column: dict[str, SyncedAttribute],
    sync_members: bool,
    dry_run: bool,
    log: logging.Logger,
    warnings: list[str],
) -> dict[str, Optional[tuple[UUID, str]]]:
    user_cache: dict[str, Optional[tuple[UUID, str]]] = {}

    candidate_identifiers: set[str] = set()
    for row in tasks_rows:
        assignee = normalize_str(row["assignee_username"])
        if assignee:
            candidate_identifiers.add(assignee)
        for source_column, raw_value in row["custom_attributes_raw"].items():
            synced_attr = attributes_by_column.get(source_column)
            if synced_attr is None or synced_attr.resolved_type != AttributeType.User:
                continue
            candidate_identifiers.add(normalize_str(raw_value))

    for identifier in sorted(candidate_identifiers):
        if not identifier:
            continue
        resolved = _resolve_user_identifier(api, identifier, cache=user_cache)
        if resolved is None:
            _warn(
                log,
                warnings,
                f"Cannot resolve user identifier {identifier!r}",
            )

    if not sync_members:
        log.info("Settings sync: workspace membership skipped (flag --sync-members is off)")
        return user_cache

    resolved_users: set[UUID] = set()
    for resolved in user_cache.values():
        if resolved is None:
            continue
        resolved_users.add(resolved[0])
    if not resolved_users:
        return user_cache

    workspace_users = api.workspace_users.list(workspace_key)
    workspace_user_ids = {user.id for user in workspace_users}
    roles = api.roles.list(workspace_key, is_system_role=True)
    user_role = _find_system_user_role(roles)
    if user_role is None:
        _warn(
            log,
            warnings,
            ("Cannot find system role 'User'; users will be added " "without explicit role assignment"),
        )

    for user_id in sorted(resolved_users, key=str):
        if user_id not in workspace_user_ids:
            if dry_run:
                log.info("Settings sync dry-run: WORKSPACE USER ADD userId=%s", user_id)
            else:
                api.workspace_users.add(workspace_key, user_id=user_id)
                log.info("Settings sync: WORKSPACE USER ADDED userId=%s", user_id)
                workspace_user_ids.add(user_id)

        if user_role is None:
            continue
        if dry_run:
            log.info(
                "Settings sync dry-run: WORKSPACE USER ROLE ADD userId=%s roleId=%s",
                user_id,
                user_role.id,
            )
            continue
        api.workspace_users.add_role(
            workspace_key,
            user_id=user_id,
            role_id=user_role.id,
        )
        log.info(
            "Settings sync: WORKSPACE USER ROLE ADDED userId=%s roleId=%s",
            user_id,
            user_role.id,
        )

    return user_cache
