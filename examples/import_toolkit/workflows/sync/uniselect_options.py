#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from typing import Any, Iterable, Optional
from uuid import UUID

from dotenv import load_dotenv

from teamstorm.client import TsClient
from teamstorm.models.attributes import (
    CreateAttributeOptionRequestBody,
    CreateAttributeRequestBody,
    PatchAttributeOptionRequestBody,
)
from teamstorm.models.enums import AttributeType
from teamstorm.api import TeamStormAPI
from import_toolkit.logging_config import setup_logging


def normalize_name(value: str) -> str:
    return value.strip().casefold()


@dataclass(frozen=True)
class ReconciliationPlan:
    creates: list[str]
    renames: list[tuple[UUID, str]]
    deletes: list[UUID]
    errors: list[str]


@dataclass
class TargetReport:
    workspace_key: str
    creates: int = 0
    renames: int = 0
    deletes: int = 0
    failed_attributes: list[str] | None = None

    def __post_init__(self) -> None:
        if self.failed_attributes is None:
            self.failed_attributes = []

    @property
    def failed(self) -> bool:
        return bool(self.failed_attributes)


def _build_options_index(
    options: Iterable[Any],
    *,
    side_label: str,
    attribute_name: str,
) -> tuple[dict[str, Any], list[str]]:
    out: dict[str, Any] = {}
    errors: list[str] = []
    for option in options:
        option_name = str(getattr(option, "name", ""))
        key = normalize_name(option_name)
        if not key:
            errors.append(f"{side_label} attribute {attribute_name!r} has an option with empty name")
            continue
        if key in out:
            first = str(getattr(out[key], "name", ""))
            errors.append(
                (
                    f"Duplicate normalized option name in {side_label} attribute "
                    f"{attribute_name!r}: {first!r} and {option_name!r}"
                )
            )
            continue
        out[key] = option
    return out, errors


def plan_option_reconciliation(
    *,
    attribute_name: str,
    master_options: Iterable[Any],
    target_options: Iterable[Any],
) -> ReconciliationPlan:
    master_by_norm, master_errors = _build_options_index(
        master_options,
        side_label="master",
        attribute_name=attribute_name,
    )
    target_by_norm, target_errors = _build_options_index(
        target_options,
        side_label="target",
        attribute_name=attribute_name,
    )

    errors = [*master_errors, *target_errors]
    if errors:
        return ReconciliationPlan(creates=[], renames=[], deletes=[], errors=errors)

    creates: list[str] = []
    renames: list[tuple[UUID, str]] = []
    deletes: list[UUID] = []

    for norm_name, master_option in master_by_norm.items():
        target_option = target_by_norm.get(norm_name)
        if target_option is None:
            creates.append(str(getattr(master_option, "name")))
            continue

        target_option_name = str(getattr(target_option, "name"))
        master_option_name = str(getattr(master_option, "name"))
        if target_option_name != master_option_name:
            target_option_id = getattr(target_option, "id", None)
            if target_option_id is None:
                errors.append(
                    (f"Target option without id in attribute {attribute_name!r} " f"for normalized name {norm_name!r}")
                )
                continue
            renames.append((target_option_id, master_option_name))

    for norm_name, target_option in target_by_norm.items():
        if norm_name in master_by_norm:
            continue
        target_option_id = getattr(target_option, "id", None)
        if target_option_id is None:
            errors.append(
                (f"Target option without id in attribute {attribute_name!r} " f"for normalized name {norm_name!r}")
            )
            continue
        deletes.append(target_option_id)

    return ReconciliationPlan(
        creates=creates,
        renames=renames,
        deletes=deletes,
        errors=errors,
    )


def _find_attribute_by_name(attributes: Iterable[Any], *, name: str) -> Optional[Any]:
    wanted = normalize_name(name)
    for attr in attributes:
        if normalize_name(str(getattr(attr, "name", ""))) == wanted:
            return attr
    return None


def _ensure_unique_attribute_allowlist(
    attribute_names: list[str],
) -> tuple[list[str], list[str]]:
    deduped: list[str] = []
    seen: dict[str, str] = {}
    errors: list[str] = []
    for raw_name in attribute_names:
        trimmed = raw_name.strip()
        normalized = normalize_name(trimmed)
        if not normalized:
            errors.append("Attribute name cannot be empty")
            continue
        previous = seen.get(normalized)
        if previous is not None:
            errors.append(f"Duplicate attribute name in allowlist (normalized): {previous!r} and {trimmed!r}")
            continue
        seen[normalized] = trimmed
        deduped.append(trimmed)
    return deduped, errors


def _load_master_attributes(
    api: TeamStormAPI,
    *,
    master_workspace_key: str,
    attribute_names: list[str],
) -> tuple[list[Any], list[str]]:
    errors: list[str] = []
    allowlist, allowlist_errors = _ensure_unique_attribute_allowlist(attribute_names)
    errors.extend(allowlist_errors)
    if errors:
        return [], errors

    master_uniselect = api.attributes.list(
        master_workspace_key,
        type=AttributeType.UniSelect,
    )
    resolved: list[Any] = []

    for attribute_name in allowlist:
        found = _find_attribute_by_name(master_uniselect, name=attribute_name)
        if found is None:
            errors.append(("Master workspace is missing UniSelect attribute " f"{attribute_name!r}"))
            continue
        resolved.append(found)

    return resolved, errors


def _sync_single_attribute(
    api: TeamStormAPI,
    *,
    target_workspace_key: str,
    master_attribute: Any,
    target_attributes_by_name: dict[str, Any],
    apply: bool,
    log,
) -> tuple[int, int, int]:
    attribute_name = str(getattr(master_attribute, "name"))
    norm_name = normalize_name(attribute_name)

    target_attribute = target_attributes_by_name.get(norm_name)
    if target_attribute is None:
        if apply:
            target_attribute = api.attributes.create(
                target_workspace_key,
                CreateAttributeRequestBody(
                    name=attribute_name,
                    type=AttributeType.UniSelect,
                ),
            )
            log.info(
                "[%s] Attribute created in target: %r",
                target_workspace_key,
                attribute_name,
            )
        else:
            log.info(
                "[%s] Dry-run: attribute would be created in target: %r",
                target_workspace_key,
                attribute_name,
            )

            class _DryRunAttr:  # lightweight placeholder for planning options
                id = None
                options = []
                name = attribute_name

            target_attribute = _DryRunAttr()

    plan = plan_option_reconciliation(
        attribute_name=attribute_name,
        master_options=getattr(master_attribute, "options", None) or [],
        target_options=getattr(target_attribute, "options", None) or [],
    )

    if plan.errors:
        for error in plan.errors:
            log.warning("[%s] %s", target_workspace_key, error)
        raise ValueError(f"Cannot sync attribute {attribute_name!r}: normalization conflicts detected")

    if not apply:
        for option_name in plan.creates:
            log.info(
                "[%s] Dry-run: option create attr=%r option=%r",
                target_workspace_key,
                attribute_name,
                option_name,
            )
        for option_id, new_name in plan.renames:
            log.info(
                "[%s] Dry-run: option rename attr=%r option_id=%s -> %r",
                target_workspace_key,
                attribute_name,
                option_id,
                new_name,
            )
        for option_id in plan.deletes:
            log.info(
                "[%s] Dry-run: option delete attr=%r option_id=%s",
                target_workspace_key,
                attribute_name,
                option_id,
            )
        return len(plan.creates), len(plan.renames), len(plan.deletes)

    target_attribute_id = getattr(target_attribute, "id", None)
    if target_attribute_id is None:
        raise ValueError(f"Target attribute {attribute_name!r} does not have id")

    for option_name in plan.creates:
        api.attributes.add_option(
            target_workspace_key,
            attribute_id=target_attribute_id,
            body=CreateAttributeOptionRequestBody(
                id=None,
                name=option_name,
            ),
        )
        log.info(
            "[%s] Option created attr=%r option=%r",
            target_workspace_key,
            attribute_name,
            option_name,
        )

    for option_id, new_name in plan.renames:
        api.attributes.patch_option(
            target_workspace_key,
            attribute_id=target_attribute_id,
            body=PatchAttributeOptionRequestBody(
                id=option_id,
                name=new_name,
            ),
        )
        log.info(
            "[%s] Option renamed attr=%r option_id=%s -> %r",
            target_workspace_key,
            attribute_name,
            option_id,
            new_name,
        )

    for option_id in plan.deletes:
        api.attributes.delete_option(
            target_workspace_key,
            attribute_id=target_attribute_id,
            option_id=option_id,
        )
        log.info(
            "[%s] Option deleted attr=%r option_id=%s",
            target_workspace_key,
            attribute_name,
            option_id,
        )

    return len(plan.creates), len(plan.renames), len(plan.deletes)


def run_sync_uniselect_options(args: argparse.Namespace) -> int:
    log = setup_logging(args.log_file)

    if not args.base_url:
        log.error("Missing --base-url (or BASE_URL env)")
        return 2
    if not args.token:
        log.error("Missing --token (or API_TOKEN env)")
        return 2

    if not args.target_workspace_key:
        log.error("At least one --target-workspace-key is required")
        return 2

    if not args.attribute_name:
        log.error("At least one --attribute-name is required")
        return 2

    mode = "apply" if args.apply else "dry-run"
    log.info(
        ("UniSelect options sync started mode=%s master=%s targets=%s attrs=%s"),
        mode,
        args.master_workspace_key,
        ", ".join(args.target_workspace_key),
        ", ".join(args.attribute_name),
    )

    client = TsClient(args.base_url, args.token, logger=log, allow_insecure=args.allow_insecure)
    api = TeamStormAPI(client)

    try:
        master_attributes, master_errors = _load_master_attributes(
            api,
            master_workspace_key=args.master_workspace_key,
            attribute_names=args.attribute_name,
        )
    except Exception as exc:
        log.error("Failed to read master attributes: %s", exc)
        return 2

    if master_errors:
        for error in master_errors:
            log.error(error)
        return 2

    reports: list[TargetReport] = []

    for target_workspace_key in args.target_workspace_key:
        report = TargetReport(workspace_key=target_workspace_key)
        reports.append(report)

        if normalize_name(target_workspace_key) == normalize_name(args.master_workspace_key):
            log.info(
                "[%s] Target equals master workspace key, skipping",
                target_workspace_key,
            )
            continue

        try:
            target_attributes = api.attributes.list(
                target_workspace_key,
                type=AttributeType.UniSelect,
            )
        except Exception as exc:
            report.failed_attributes.append("<workspace>")
            log.error(
                "[%s] Failed to load target attributes: %s",
                target_workspace_key,
                exc,
            )
            continue

        target_by_name: dict[str, Any] = {}
        duplicate_target_attr_names: set[str] = set()
        for attr in target_attributes:
            key = normalize_name(str(getattr(attr, "name", "")))
            if key in target_by_name:
                duplicate_target_attr_names.add(str(getattr(attr, "name", "")))
            target_by_name[key] = attr

        if duplicate_target_attr_names:
            report.failed_attributes.append("<workspace>")
            log.error(
                "[%s] Duplicate normalized UniSelect attribute names in target: %s",
                target_workspace_key,
                ", ".join(sorted(duplicate_target_attr_names)),
            )
            continue

        for master_attribute in master_attributes:
            attribute_name = str(getattr(master_attribute, "name"))
            try:
                creates, renames, deletes = _sync_single_attribute(
                    api,
                    target_workspace_key=target_workspace_key,
                    master_attribute=master_attribute,
                    target_attributes_by_name=target_by_name,
                    apply=args.apply,
                    log=log,
                )
                report.creates += creates
                report.renames += renames
                report.deletes += deletes
            except Exception as exc:
                report.failed_attributes.append(attribute_name)
                log.error(
                    "[%s] Attribute sync failed attr=%r: %s",
                    target_workspace_key,
                    attribute_name,
                    exc,
                )

        log.info(
            "[%s] Summary: creates=%d renames=%d deletes=%d failed_attrs=%d",
            target_workspace_key,
            report.creates,
            report.renames,
            report.deletes,
            len(report.failed_attributes),
        )

    failed_targets = [r.workspace_key for r in reports if r.failed]
    if failed_targets:
        log.error(
            "Completed with failures in targets: %s",
            ", ".join(failed_targets),
        )
        return 1

    log.info("Completed successfully")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    load_dotenv()

    parser = argparse.ArgumentParser(
        "sync_uniselect_options",
        description="Sync UniSelect attribute options from master workspace to targets",
    )
    parser.add_argument("--base-url", default=os.getenv("BASE_URL"))
    parser.add_argument("--token", default=os.getenv("API_TOKEN"))
    parser.add_argument("--master-workspace-key", required=True)
    parser.add_argument(
        "--target-workspace-key",
        action="append",
        default=[],
        help="Repeat this argument for each target workspace",
    )
    parser.add_argument(
        "--attribute-name",
        action="append",
        default=[],
        help="Repeat this argument for each UniSelect attribute name to sync",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes (default is dry-run)",
    )
    parser.add_argument(
        "--allow-insecure",
        action="store_true",
        default=False,
        help="Allow non-HTTPS base_url (for local/staging use only).",
    )
    parser.add_argument(
        "--log-file",
        default="./logs/sync_uniselect_options.log",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    return run_sync_uniselect_options(args)


if __name__ == "__main__":
    raise SystemExit(main())
