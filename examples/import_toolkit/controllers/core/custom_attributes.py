import logging
from typing import Any, Callable, Optional
from uuid import UUID

from teamstorm.api import TeamStormAPI
from teamstorm.models.enums import AttributeType
from teamstorm.models.workitems_attributes_update import (
    UpdateWorkitemAttributeRequestBody,
)

from import_toolkit.controllers.core.attribute_value_mapper import (
    build_create_attribute_value,
    build_update_attribute_value,
)
from import_toolkit.controllers.core.attributes import (
    _make_option_resolver,
    _build_select_or_tag_update_payload_with_names,
    _expected_option_ids_from_raw,
    _extract_option_ids_from_attribute_value,
    _extract_option_ids_from_update_payload,
    _option_ids_match,
    _refresh_synced_attribute_options,
)
from import_toolkit.controllers.core.contracts import (
    PendingCustomAttributeUpdate,
    SyncedAttribute,
    SyncContext,
)
from import_toolkit.controllers.core.users import _make_user_resolver
from import_toolkit.controllers.core.utils import _warn


def build_create_custom_attributes_for_row(
    api: TeamStormAPI,
    *,
    workspace_key: str,
    row,
    sync_context: SyncContext,
    update_settings: bool,
    dry_run: bool,
    log: logging.Logger,
    warnings: list[str],
) -> list:
    payload_items: list = []
    user_resolver = _make_user_resolver(
        api,
        user_cache=sync_context.user_cache,
    )
    row_ref = row["row_ref"]

    for source_column, raw_value in row["custom_attributes_raw"].items():
        synced_attr = sync_context.attributes_by_column.get(source_column)
        if synced_attr is None:
            continue
        if synced_attr.attribute_id is None:
            _warn(
                log,
                warnings,
                (f"{row_ref}: attribute for column {source_column!r} " "is not available; value skipped"),
            )
            continue

        option_resolver: Optional[Callable[[str], Optional[str]]] = None
        if synced_attr.resolved_type in (AttributeType.Tag, AttributeType.UniSelect):
            option_resolver = _make_option_resolver(
                api,
                workspace_key=workspace_key,
                synced_attr=synced_attr,
                update_settings=update_settings,
                dry_run=dry_run,
                warnings=warnings,
                log=log,
            )

        payload_item = build_create_attribute_value(
            attribute_id=synced_attr.attribute_id,
            attribute_type=synced_attr.resolved_type,
            raw_value=raw_value,
            resolve_option_id=option_resolver,
            resolve_user=user_resolver,
            warn=lambda message, rr=row_ref: _warn(log, warnings, f"{rr}: {message}"),
        )
        if payload_item is not None:
            payload_items.append(payload_item)

    return payload_items


def build_update_custom_attributes_for_row(
    api: TeamStormAPI,
    *,
    workspace_key: str,
    row,
    sync_context: SyncContext,
    update_settings: bool,
    dry_run: bool,
    log: logging.Logger,
    warnings: list[str],
) -> list[PendingCustomAttributeUpdate]:
    payload_items: list[PendingCustomAttributeUpdate] = []
    user_resolver = _make_user_resolver(
        api,
        user_cache=sync_context.user_cache,
    )
    row_ref = row["row_ref"]

    for source_column, raw_value in row["custom_attributes_raw"].items():
        synced_attr = sync_context.attributes_by_column.get(source_column)
        if synced_attr is None:
            continue
        if synced_attr.attribute_id is None:
            _warn(
                log,
                warnings,
                (f"{row_ref}: attribute for column {source_column!r} " "is not available; value skipped"),
            )
            continue

        option_resolver: Optional[Callable[[str], Optional[str]]] = None
        if synced_attr.resolved_type in (AttributeType.Tag, AttributeType.UniSelect):
            option_resolver = _make_option_resolver(
                api,
                workspace_key=workspace_key,
                synced_attr=synced_attr,
                update_settings=update_settings,
                dry_run=dry_run,
                warnings=warnings,
                log=log,
            )

        payload_item = build_update_attribute_value(
            attribute_type=synced_attr.resolved_type,
            raw_value=raw_value,
            resolve_option_id=option_resolver,
            resolve_user=user_resolver,
            warn=lambda message, rr=row_ref: _warn(log, warnings, f"{rr}: {message}"),
        )
        if payload_item is not None:
            payload_items.append(
                PendingCustomAttributeUpdate(
                    source_column=source_column,
                    raw_value=raw_value,
                    synced_attr=synced_attr,
                    payload=payload_item,
                )
            )

    return payload_items


def _find_attribute_in_workitem(workitem_attributes: list, *, attribute_id: UUID) -> Optional[Any]:
    for attr in workitem_attributes:
        attr_id = getattr(attr, "id", None)
        if attr_id is None:
            continue
        if str(attr_id) == str(attribute_id):
            return attr
    return None


def update_workitem_custom_attributes(
    api: TeamStormAPI,
    *,
    workspace_key: str,
    workitem_id: UUID,
    row,
    sync_context: SyncContext,
    update_settings: bool,
    dry_run: bool,
    log: logging.Logger,
    warnings: list[str],
    errors: list[str],
    counters,
    non_fatal_select_tag_errors: Optional[list[str]] = None,
) -> None:
    row_ref = row["row_ref"]
    updates = build_update_custom_attributes_for_row(
        api,
        workspace_key=workspace_key,
        row=row,
        sync_context=sync_context,
        update_settings=update_settings,
        dry_run=dry_run,
        log=log,
        warnings=warnings,
    )
    log.debug(
        "%s: planned custom attribute upserts=%d for workitem=%s",
        row_ref,
        len(updates),
        workitem_id,
    )
    if not updates:
        return

    workitem_attributes = api.workitems.list_attributes(
        workspace_key,
        workitem_id=workitem_id,
    )
    available_ids = {attr.id for attr in workitem_attributes}

    for update_item in updates:
        synced_attr: SyncedAttribute = update_item.synced_attr
        attribute_id = synced_attr.attribute_id
        payload: UpdateWorkitemAttributeRequestBody = update_item.payload
        if attribute_id is None:
            _warn(
                log,
                warnings,
                (f"{row_ref}: attribute for column {update_item.source_column!r} " "is not available; value skipped"),
            )
            continue

        counters.custom_attr_updates_attempted += 1
        if attribute_id not in available_ids:
            log.info(
                (
                    "%s: attributeId=%s is not listed for workitem=%s "
                    "by list_attributes; "
                    "update attempt will still be sent"
                ),
                row_ref,
                attribute_id,
                workitem_id,
            )
        if dry_run:
            log.info(
                ("%s: Workitem ATTRIBUTE UPDATE: workitem=%s " "attribute=%s type=%s value=%r"),
                row_ref,
                workitem_id,
                attribute_id,
                payload.type,
                getattr(payload, "value", None),
            )
            counters.custom_attr_updates_skipped += 1
            continue

        def _record_failed_update(
            reason: str,
            *,
            non_fatal_select_tag: bool = False,
        ) -> None:
            counters.custom_attr_updates_failed += 1
            err = (
                f"{row_ref}: Workitem ATTRIBUTE UPDATE failed: workitem={workitem_id} "
                f"attribute={attribute_id} error={reason}"
            )
            if non_fatal_select_tag:
                if non_fatal_select_tag_errors is not None:
                    non_fatal_select_tag_errors.append(err)
                log.warning("%s [non-fatal-select-tag]", err)
                return
            errors.append(err)
            log.error(err)

        try:
            response_value = api.workitems.update_attribute(
                workspace_key,
                workitem_id=workitem_id,
                attribute_id=attribute_id,
                body=payload,
            )
        except Exception as exc:
            _record_failed_update(str(exc))
            continue

        if synced_attr.resolved_type not in (
            AttributeType.UniSelect,
            AttributeType.Tag,
        ):
            counters.custom_attr_updates_succeeded += 1
            continue

        requested_ids = _extract_option_ids_from_update_payload(payload)
        response_ids = _extract_option_ids_from_attribute_value(response_value)
        log.debug(
            (
                "%s: Select/Tag verify step1 attribute=%s column=%r type=%s raw=%r "
                "request_payload_value=%r requested_ids=%s response_ids=%s"
            ),
            row_ref,
            attribute_id,
            update_item.source_column,
            synced_attr.resolved_type.value,
            update_item.raw_value,
            getattr(payload, "value", None),
            requested_ids,
            response_ids,
        )
        if _option_ids_match(
            attribute_type=synced_attr.resolved_type,
            requested_ids=requested_ids,
            observed_ids=response_ids,
        ):
            counters.custom_attr_updates_succeeded += 1
            continue

        log.debug(
            ("%s: Select/Tag mismatch detected; refreshing options and " "retrying once (attribute=%s)"),
            row_ref,
            attribute_id,
        )
        try:
            _refresh_synced_attribute_options(
                api,
                workspace_key=workspace_key,
                synced_attr=synced_attr,
            )
        except Exception as exc:
            _record_failed_update(f"failed to refresh options before retry: {exc}")
            continue

        retry_payload = _build_select_or_tag_update_payload_with_names(
            synced_attr=synced_attr,
            raw_value=update_item.raw_value,
        )
        if retry_payload is None:
            _record_failed_update(
                (
                    "select/tag mismatch after retry: "
                    f"column={update_item.source_column!r} "
                    "name-payload rebuild returned empty value"
                ),
                non_fatal_select_tag=True,
            )
            continue

        expected_ids_after_refresh = _expected_option_ids_from_raw(
            synced_attr=synced_attr,
            raw_value=update_item.raw_value,
        )
        retry_requested_ids = expected_ids_after_refresh
        try:
            retry_response_value = api.workitems.update_attribute(
                workspace_key,
                workitem_id=workitem_id,
                attribute_id=attribute_id,
                body=retry_payload,
            )
        except Exception as exc:
            _record_failed_update(f"retry call failed: {exc}")
            continue

        retry_response_ids = _extract_option_ids_from_attribute_value(retry_response_value)
        log.debug(
            (
                "%s: Select/Tag verify retry response attribute=%s "
                "retry_payload_value=%r expected_ids=%s response_ids=%s"
            ),
            row_ref,
            attribute_id,
            getattr(retry_payload, "value", None),
            retry_requested_ids,
            retry_response_ids,
        )

        try:
            readback_attributes = api.workitems.list_attributes(
                workspace_key,
                workitem_id=workitem_id,
            )
        except Exception as exc:
            _record_failed_update(f"read-back after retry failed: {exc}")
            continue

        readback_value = _find_attribute_in_workitem(
            readback_attributes,
            attribute_id=attribute_id,
        )
        readback_ids = _extract_option_ids_from_attribute_value(readback_value)
        log.debug(
            ("%s: Select/Tag final read-back attribute=%s " "requested_ids=%s readback_ids=%s"),
            row_ref,
            attribute_id,
            retry_requested_ids,
            readback_ids,
        )
        if not _option_ids_match(
            attribute_type=synced_attr.resolved_type,
            requested_ids=retry_requested_ids,
            observed_ids=readback_ids,
        ):
            _record_failed_update(
                (
                    "select/tag mismatch after retry: "
                    f"column={update_item.source_column!r} "
                    f"requested={retry_requested_ids} "
                    f"response={retry_response_ids} readback={readback_ids}"
                ),
                non_fatal_select_tag=True,
            )
            continue

        counters.custom_attr_updates_succeeded += 1


def maybe_update_existing_workitem_custom_attributes(
    api: TeamStormAPI,
    *,
    is_existing_workitem: bool,
    workspace_key: str,
    workitem_id: UUID,
    row,
    sync_context: SyncContext,
    update_settings: bool,
    dry_run: bool,
    log: logging.Logger,
    warnings: list[str],
    errors: list[str],
    counters,
    non_fatal_select_tag_errors: Optional[list[str]] = None,
) -> None:
    update_workitem_custom_attributes(
        api,
        workspace_key=workspace_key,
        workitem_id=workitem_id,
        row=row,
        sync_context=sync_context,
        update_settings=update_settings,
        dry_run=dry_run,
        log=log,
        warnings=warnings,
        errors=errors,
        counters=counters,
        non_fatal_select_tag_errors=non_fatal_select_tag_errors,
    )
