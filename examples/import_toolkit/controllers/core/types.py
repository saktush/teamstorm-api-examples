from __future__ import annotations

import logging
from collections import Counter, defaultdict
from uuid import UUID

from teamstorm.models.types import CreateTypeRequestBody
from teamstorm.api import TeamStormAPI

from import_toolkit.controllers.core.contracts import SyncedAttribute
from import_toolkit.controllers.core.utils import _warn, normalize_str


def _pick_default_workflow_name(existing_types: list, workflows: list) -> str | None:
    existing_workflow_names = [
        normalize_str(t.workflow.name)
        for t in existing_types
        if getattr(t, "workflow", None) is not None and normalize_str(getattr(t.workflow, "name", ""))
    ]
    if existing_workflow_names:
        return Counter(existing_workflow_names).most_common(1)[0][0]

    for workflow in workflows:
        workflow_name = normalize_str(getattr(workflow, "name", ""))
        if not workflow_name:
            continue

        workflow_name_key = workflow_name.casefold()
        if workflow_name_key.startswith("default for ") and ": global:" in workflow_name_key:
            continue

        return workflow_name

    for workflow in workflows:
        workflow_name = normalize_str(getattr(workflow, "name", ""))
        if workflow_name:
            return workflow_name

    return None


def sync_types(
    api: TeamStormAPI,
    *,
    workspace_key: str,
    tasks_rows: list,
    attributes_by_column: dict[str, SyncedAttribute],
    update_settings: bool,
    dry_run: bool,
    log: logging.Logger,
    warnings: list[str],
) -> set[str]:
    type_usage: dict[str, set[UUID]] = defaultdict(set)
    for row in tasks_rows:
        wi_type = normalize_str(row["type"])
        for source_column in row["custom_attributes_raw"].keys():
            synced_attr = attributes_by_column.get(source_column)
            if synced_attr is None or synced_attr.attribute_id is None:
                continue
            type_usage[wi_type].add(synced_attr.attribute_id)

    existing_types = api.types.list(workspace_key)
    existing_by_name = {normalize_str(t.name): t for t in existing_types}
    known_types = set(existing_by_name.keys())
    used_types = {normalize_str(row["type"]) for row in tasks_rows}

    workflows = api.workflows.list(workspace_key)
    default_workflow_name = _pick_default_workflow_name(existing_types, workflows)

    for type_name in sorted(used_types):
        if type_name in existing_by_name:
            continue

        if not update_settings:
            _warn(
                log,
                warnings,
                (f"Missing workitem type {type_name!r}; " "skipped (enable --update-settings to create)"),
            )
            continue

        if default_workflow_name is None:
            _warn(
                log,
                warnings,
                f"Cannot create missing type {type_name!r}: workspace has no workflows",
            )
            continue

        if dry_run:
            log.info(
                "Settings sync dry-run: TYPE CREATE name=%r workflow=%r",
                type_name,
                default_workflow_name,
            )
            known_types.add(type_name)
            continue

        created = api.types.create(
            workspace_key,
            CreateTypeRequestBody(
                name=type_name,
                workflow=default_workflow_name,
            ),
        )
        existing_by_name[type_name] = created
        known_types.add(type_name)
        log.info(
            "Settings sync: TYPE created name=%r id=%s workflow=%s",
            created.name,
            created.id,
            created.workflow.name,
        )

    for type_name, attribute_ids in type_usage.items():
        current_type = existing_by_name.get(type_name)
        if current_type is None:
            continue
        current_ids = {attr.id for attr in current_type.attributes}
        missing_ids = sorted(attribute_ids - current_ids, key=str)
        for attribute_id in missing_ids:
            if not update_settings:
                continue
            if dry_run:
                log.info(
                    "Settings sync dry-run: TYPE LINK type=%r attribute=%s",
                    type_name,
                    attribute_id,
                )
                continue
            updated_type = api.types.add_attribute(
                workspace_key,
                type_key=type_name,
                attribute_id=attribute_id,
            )
            existing_by_name[type_name] = updated_type
            log.info(
                "Settings sync: TYPE LINKED type=%r attribute=%s",
                type_name,
                attribute_id,
            )

    return known_types
