from __future__ import annotations

import logging
from typing import Any, Callable, Optional
from uuid import UUID

from teamstorm.models.attributes import (
    CreateAttributeOptionRequestBody,
    CreateAttributeRequestBody,
)
from teamstorm.models.enums import AttributeType
from teamstorm.models.workitems_attributes_update import (
    UpdateTagFieldRequestBody,
    UpdateUniSelectFieldRequestBody,
)
from teamstorm.api import TeamStormAPI

from import_toolkit.controllers.core.attribute_value_mapper import normalize_attribute_cell
from import_toolkit.controllers.core.contracts import (
    CustomAttributeSpec,
    SyncedAttribute,
    _TYPE_ALIASES,
    _TYPE_MARKER_RE,
)
from import_toolkit.controllers.core.utils import _warn, normalize_str


def parse_custom_attribute_header(header: str) -> CustomAttributeSpec:
    normalized = normalize_str(header)
    marker = _TYPE_MARKER_RE.fullmatch(normalized)
    if marker is None:
        return CustomAttributeSpec(
            source_column=header,
            attribute_name=normalized,
            requested_type=AttributeType.UniString,
            unknown_marker=False,
        )

    attr_name = normalize_str(marker.group("name"))
    marker_token = normalize_str(marker.group("type")).casefold()
    requested_type = _TYPE_ALIASES.get(marker_token, AttributeType.UniString)
    unknown_marker = marker_token not in _TYPE_ALIASES
    if not attr_name:
        attr_name = normalized
    return CustomAttributeSpec(
        source_column=header,
        attribute_name=attr_name,
        requested_type=requested_type,
        unknown_marker=unknown_marker,
    )


def _find_attribute_by_name(
    attributes: list,
    *,
    name: str,
) -> Optional[Any]:
    lowered = name.strip().casefold()
    for attr in attributes:
        if attr.name.strip().casefold() == lowered:
            return attr
    return None


def _make_option_resolver(
    api: TeamStormAPI,
    *,
    workspace_key: str,
    synced_attr: SyncedAttribute,
    update_settings: bool,
    dry_run: bool,
    warnings: list[str],
    log: logging.Logger,
) -> Callable[[str], Optional[str]]:
    def resolve(option_name: str) -> Optional[str]:
        option_key = normalize_str(option_name).casefold()
        if not option_key:
            return None
        existing_option_id = synced_attr.options_by_name.get(option_key)
        if existing_option_id is not None:
            return str(existing_option_id)

        if synced_attr.attribute_id is None or not update_settings:
            _warn(
                log,
                warnings,
                (f"Missing option {option_name!r} for attribute " f"{synced_attr.spec.attribute_name!r}; skipped"),
            )
            return None

        if dry_run:
            log.info(
                "Settings sync dry-run: OPTION CREATE attr=%r option=%r",
                synced_attr.spec.attribute_name,
                option_name,
            )
            return None

        updated_attr = api.attributes.add_option(
            workspace_key,
            attribute_id=synced_attr.attribute_id,
            body=CreateAttributeOptionRequestBody(
                id=None,
                name=option_name,
            ),
        )
        if updated_attr.options:
            synced_attr.options_by_name = {option.name.casefold(): option.id for option in updated_attr.options}
        created_option_id = synced_attr.options_by_name.get(option_key)
        if created_option_id is None:
            return None
        log.info(
            "Settings sync: OPTION CREATED attr=%r option=%r id=%s",
            synced_attr.spec.attribute_name,
            option_name,
            created_option_id,
        )
        return str(created_option_id)

    return resolve


def sync_attributes(
    api: TeamStormAPI,
    *,
    workspace_key: str,
    tasks_rows: list,
    update_settings: bool,
    dry_run: bool,
    log: logging.Logger,
    warnings: list[str],
) -> dict[str, SyncedAttribute]:
    existing_attributes = api.attributes.list(workspace_key)
    synced: dict[str, SyncedAttribute] = {}

    attribute_specs: dict[str, CustomAttributeSpec] = {}
    for row in tasks_rows:
        for source_column in row["custom_attributes_raw"].keys():
            if source_column in attribute_specs:
                continue
            spec = parse_custom_attribute_header(source_column)
            attribute_specs[source_column] = spec
            if spec.unknown_marker:
                _warn(
                    log,
                    warnings,
                    ("Unknown custom attribute marker for " f"{source_column!r}; fallback to UniString"),
                )

    for source_column, spec in attribute_specs.items():
        existing = _find_attribute_by_name(existing_attributes, name=spec.attribute_name)
        resolved_type = spec.requested_type
        attribute_id: Optional[UUID] = None
        options_by_name: dict[str, UUID] = {}

        if existing is not None:
            attribute_id = existing.id
            resolved_type = existing.type
            if existing.type != spec.requested_type:
                _warn(
                    log,
                    warnings,
                    (
                        f"Attribute type mismatch for {spec.attribute_name!r}: "
                        "existing="
                        f"{existing.type.value}, requested="
                        f"{spec.requested_type.value}; existing wins"
                    ),
                )
            if existing.options:
                options_by_name = {option.name.casefold(): option.id for option in existing.options}

        elif update_settings:
            if dry_run:
                log.info(
                    "Settings sync dry-run: ATTR CREATE name=%r type=%s",
                    spec.attribute_name,
                    spec.requested_type.value,
                )
            else:
                created = api.attributes.create(
                    workspace_key,
                    CreateAttributeRequestBody(
                        name=spec.attribute_name,
                        type=spec.requested_type,
                    ),
                )
                existing_attributes.append(created)
                attribute_id = created.id
                resolved_type = created.type
                if created.options:
                    options_by_name = {option.name.casefold(): option.id for option in created.options}
                log.info(
                    "Settings sync: ATTR created name=%r id=%s type=%s",
                    created.name,
                    created.id,
                    created.type.value,
                )
        else:
            _warn(
                log,
                warnings,
                (f"Missing custom attribute {spec.attribute_name!r}; " "skipped (enable --update-settings to create)"),
            )

        synced[source_column] = SyncedAttribute(
            spec=spec,
            resolved_type=resolved_type,
            attribute_id=attribute_id,
            options_by_name=options_by_name,
        )

    return synced


def _extract_option_id(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    option_id = getattr(value, "id", None)
    if option_id is not None:
        return str(option_id)
    if isinstance(value, dict):
        option_id = value.get("id")
        if option_id is None:
            return None
        return str(option_id)
    return None


def _extract_option_ids_from_update_payload(
    payload: Any,
) -> list[str]:
    if payload.type == AttributeType.UniSelect:
        option_id = _extract_option_id(getattr(payload, "value", None))
        return [option_id] if option_id else []

    if payload.type == AttributeType.Tag:
        raw_value = getattr(payload, "value", None)
        if not isinstance(raw_value, list):
            return []
        out: list[str] = []
        for item in raw_value:
            option_id = _extract_option_id(item)
            if option_id:
                out.append(option_id)
        return out

    return []


def _extract_option_ids_from_attribute_value(attribute_value: Any) -> list[str]:
    if attribute_value is None:
        return []

    value = getattr(attribute_value, "value", None)
    if value is None:
        return []

    field_type = getattr(attribute_value, "type", None)
    if field_type == AttributeType.UniSelect:
        option_id = _extract_option_id(value)
        return [option_id] if option_id else []

    if field_type == AttributeType.Tag:
        if not isinstance(value, list):
            return []
        out: list[str] = []
        for item in value:
            option_id = _extract_option_id(item)
            if option_id:
                out.append(option_id)
        return out

    return []


def _option_ids_match(
    *,
    attribute_type: AttributeType,
    requested_ids: list[str],
    observed_ids: list[str],
) -> bool:
    if attribute_type == AttributeType.UniSelect:
        return len(requested_ids) == 1 and len(observed_ids) == 1 and requested_ids[0] == observed_ids[0]

    if attribute_type == AttributeType.Tag:
        return len(requested_ids) == len(observed_ids) and set(requested_ids) == set(observed_ids)

    return True


def _refresh_synced_attribute_options(
    api: TeamStormAPI,
    *,
    workspace_key: str,
    synced_attr: SyncedAttribute,
) -> None:
    if synced_attr.attribute_id is None:
        return

    refreshed = api.attributes.get(workspace_key, attribute_id=synced_attr.attribute_id)
    options_by_name: dict[str, UUID] = {}
    if refreshed.options:
        options_by_name = {option.name.casefold(): option.id for option in refreshed.options}
    synced_attr.options_by_name = options_by_name


def _build_select_or_tag_update_payload_with_names(
    *,
    synced_attr: SyncedAttribute,
    raw_value: str,
) -> Optional[Any]:
    if synced_attr.resolved_type == AttributeType.UniSelect:
        normalized = normalize_attribute_cell(AttributeType.UniSelect, raw_value)
        if normalized is None:
            return None
        return UpdateUniSelectFieldRequestBody(
            type=AttributeType.UniSelect,
            value=str(normalized),
        )

    if synced_attr.resolved_type == AttributeType.Tag:
        normalized = normalize_attribute_cell(AttributeType.Tag, raw_value)
        if normalized is None:
            return None
        return UpdateTagFieldRequestBody(
            type=AttributeType.Tag,
            value=[str(tag_name) for tag_name in normalized],
        )

    return None


def _expected_option_ids_from_raw(
    *,
    synced_attr: SyncedAttribute,
    raw_value: str,
) -> list[str]:
    if synced_attr.resolved_type == AttributeType.UniSelect:
        normalized = normalize_attribute_cell(AttributeType.UniSelect, raw_value)
        if normalized is None:
            return []
        option_id = synced_attr.options_by_name.get(str(normalized).casefold())
        return [str(option_id)] if option_id is not None else []

    if synced_attr.resolved_type == AttributeType.Tag:
        normalized = normalize_attribute_cell(AttributeType.Tag, raw_value)
        if normalized is None:
            return []
        out: list[str] = []
        for tag_name in normalized:
            option_id = synced_attr.options_by_name.get(str(tag_name).casefold())
            if option_id is not None:
                out.append(str(option_id))
        return out

    return []
