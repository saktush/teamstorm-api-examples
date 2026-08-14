import json
import logging
from datetime import date, datetime, time
from typing import Any, List, TypeVar

from dateutil.parser import isoparse

from import_toolkit.controllers.core.contracts import TZ_MSK

T = TypeVar("T")


def _warn(log: logging.Logger, warnings: list[str], message: str) -> None:
    warnings.append(message)
    log.warning(message)


def _date_to_iso_datetime(d: date) -> str:
    dt = datetime.combine(d, time(0, 0, 0), tzinfo=TZ_MSK)
    return dt.isoformat(timespec="seconds")


def pick_single(items: List[T], what: str) -> T:
    from teamstorm.client import ApiError

    if len(items) == 0:
        raise ApiError(f"{what}: не найдено")
    if len(items) > 1:
        raise ApiError(f"{what}: найдено >1 (неоднозначно)")
    return items[0]


def calc_workdays(start_iso: str, end_iso: str) -> int:
    from teamstorm.client import ApiError

    s = isoparse(start_iso).date()
    e = isoparse(end_iso).date()
    if e < s:
        raise ApiError(f"Sprint dates invalid: startDate={start_iso} endDate={end_iso}")

    days = (e - s).days  # end не включаем
    if days <= 0:
        return 1

    full_weeks, rem = divmod(days, 7)
    wd = full_weeks * 5

    for i in range(rem):
        if (s.weekday() + i) % 7 < 5:
            wd += 1

    return max(wd, 1)


def normalize_str(value: str) -> str:
    from import_toolkit.io.readers.common import normalize_str as reader_normalize_str

    return reader_normalize_str(value)


def format_api_error(
    err: Exception,
    *,
    max_details_len: int = 1000,
) -> str:
    from teamstorm.client import ApiError

    if not isinstance(err, ApiError):
        return str(err)

    parts: list[str] = [str(err)]
    if err.status is not None:
        parts.append(f"status={err.status}")
    if err.method or err.path:
        parts.append(f"request={err.method or '?'} {err.path or '?'}")
    if err.details:
        details = err.details
        if len(details) > max_details_len:
            details = f"{details[:max_details_len]}...[truncated]"
        parts.append(f"details={details}")
        hint = _hint_from_api_error_details(err.details)
        if hint:
            parts.append(f"hint={hint}")

    return " | ".join(parts)


def _hint_from_api_error_details(details: str) -> str:
    try:
        payload = json.loads(details)
    except Exception:
        return ""

    if not isinstance(payload, dict):
        return ""

    err_type = payload.get("type")
    if err_type == "AssigneeHasNoAccessException":
        return "Assignee has no access to workspace; add users to workspace or rerun with --sync-members"
    if err_type == "WorkitemTypeNotFoundException":
        return "Workitem type missing in workspace; rerun with --update-settings to create types/attributes from XLSX"

    return ""
