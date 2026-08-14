# teamstorm/api/time_tracking.py
from __future__ import annotations

import builtins
from datetime import datetime
from typing import Any

from pydantic import TypeAdapter

from teamstorm.api._base import BaseAPI
from teamstorm.models.common import DateTimeLike
from teamstorm.models.time_tracking import TimeTrackingEntryModel


def _query_date(value: DateTimeLike) -> str:
    """Convert a datetime or already-formatted string into a query-string-safe value."""
    return value.isoformat() if isinstance(value, datetime) else value


_ENTRY_LIST_ADAPTER: TypeAdapter = TypeAdapter(list[TimeTrackingEntryModel])


class TimeTrackingAPI(BaseAPI):
    """
    Read-only time-tracking entries, aggregated across every workspace the
    caller has permission to see -- not a single-workspace resource.

    2 ops (TimeTracking tag): list entries in a date range, and list entries
    changed (created/updated/soft-deleted) in a date range for incremental
    sync. There is no create/update/delete for time entries via the public
    API -- see docs/api-analysis/upstream-semantics.md "Gotchas" #8.

    NOTE: both paths are literally "/workspaces/time-tracking-entries[...]"
    -- "time-tracking-entries" sits where a {workspace} segment would
    normally go. There is no {workspace} path segment and no workspace query
    parameter either (verified against swagger.json): these endpoints
    aggregate across every workspace the caller has the
    WorkspaceTimeTrackReport permission in. Do not pass a workspace_key.
    """

    def list(
        self,
        *,
        start_date: DateTimeLike,
        end_date: DateTimeLike | None = None,
        users: str | None = None,
        from_token: str | None = None,
        max_items_count: int | None = None,
    ) -> list[TimeTrackingEntryModel]:
        """
        List time-tracking entries across every workspace the caller can see.

        start_date: required lower bound (inclusive) on entry date.
        end_date: optional upper bound on entry date.
        users: optional comma-separated list of usernames (logins) to filter
        by -- NOT full names, GUIDs, or emails; the server resolves each
        entry by login and 400s if one doesn't resolve (see
        docs/api-analysis/upstream-semantics.md "Filtering & sorting" ->
        TimeTracking).
        from_token / max_items_count: cursor pagination.
        Returns: every matching TimeTrackingEntryModel.
        GET /workspaces/time-tracking-entries.
        """
        params: dict[str, Any] = {"startDate": _query_date(start_date)}
        if end_date is not None:
            params["endDate"] = _query_date(end_date)
        if users is not None:
            params["users"] = users
        if from_token is not None:
            params["fromToken"] = from_token
        if max_items_count is not None:
            params["maxItemsCount"] = max_items_count

        data = self.client.get_all("/workspaces/time-tracking-entries", params=params)
        return _ENTRY_LIST_ADAPTER.validate_python(data)

    def list_updates(
        self,
        *,
        start_date: DateTimeLike,
        end_date: DateTimeLike | None = None,
        users: str | None = None,
        with_deleted: bool | None = None,
        from_token: str | None = None,
        max_items_count: int | None = None,
    ) -> builtins.list[TimeTrackingEntryModel]:
        """
        List time-tracking entries created/updated (and optionally
        soft-deleted) in a date range, across every workspace the caller can
        see -- for incremental sync.

        start_date: required lower bound (inclusive) on the change date.
        end_date: optional upper bound on the change date.
        users: optional comma-separated list of usernames (logins) to filter
        by (same resolution rule as list()).
        with_deleted: when true, include entries that were soft-deleted in
        the window (their deletedAt/deleteUser/deleteUserId become non-null).
        from_token / max_items_count: cursor pagination.
        Returns: every matching TimeTrackingEntryModel.
        GET /workspaces/time-tracking-entries/updates.
        """
        params: dict[str, Any] = {"startDate": _query_date(start_date)}
        if end_date is not None:
            params["endDate"] = _query_date(end_date)
        if users is not None:
            params["users"] = users
        if with_deleted is not None:
            params["withDeleted"] = with_deleted
        if from_token is not None:
            params["fromToken"] = from_token
        if max_items_count is not None:
            params["maxItemsCount"] = max_items_count

        data = self.client.get_all("/workspaces/time-tracking-entries/updates", params=params)
        return _ENTRY_LIST_ADAPTER.validate_python(data)
