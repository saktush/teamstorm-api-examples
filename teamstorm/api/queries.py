# teamstorm/api/queries.py
from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import TypeAdapter

from teamstorm.api._base import BaseAPI
from teamstorm.models.queries import QueryVisibilitySettingsModel, UpdateQueryVisibilitySettingsRequestBody
from teamstorm.models.workitems import WorkitemModel


class QueriesAPI(BaseAPI):
    """
    Saved-query visibility settings, plus listing the workitems a saved query
    currently matches.

    3 ops (Queries tag) -- much narrower than the tag name suggests: there is
    no create/list/delete for saved queries via the public API. A saved query
    must already exist (created via the TeamStorm UI or another channel)
    before any of these operations can touch it. See
    docs/api-analysis/upstream-semantics.md "Gotchas" #7.
    """

    def list_workitems(
        self,
        query_id: UUID,
        *,
        from_token: str | None = None,
        max_items_count: int | None = None,
    ) -> list[WorkitemModel]:
        """
        List every workitem currently matching an existing saved query's
        filter.

        query_id: the saved query's UUID (path segment). NOT workspace-scoped
        -- unlike get_visibility()/update_visibility() below, this path has
        no {workspace} segment.
        from_token / max_items_count: cursor pagination.
        Returns: every WorkitemModel the query currently matches.
        GET /queries/{queryId}/workitems.
        """
        params: dict[str, Any] = {}
        if from_token is not None:
            params["fromToken"] = from_token
        if max_items_count is not None:
            params["maxItemsCount"] = max_items_count

        data = self.client.get_all(f"/queries/{query_id}/workitems", params=params or None)
        return TypeAdapter(list[WorkitemModel]).validate_python(data)

    def get_visibility(self, workspace_key: str, *, query_id: UUID) -> QueryVisibilitySettingsModel:
        """
        Get a saved query's visibility settings.

        workspace_key: workspace key or id.
        query_id: the saved query's UUID (path segment).
        Returns: the QueryVisibilitySettingsModel (visibility type + access list).
        GET /workspaces/{workspace}/queries/{queryId}/visibility.
        """
        data = self.client.get(f"/workspaces/{workspace_key}/queries/{query_id}/visibility")
        return QueryVisibilitySettingsModel.model_validate(data)

    def update_visibility(
        self,
        workspace_key: str,
        *,
        query_id: UUID,
        body: UpdateQueryVisibilitySettingsRequestBody,
    ) -> QueryVisibilitySettingsModel:
        """
        Replace a saved query's visibility settings.

        workspace_key: workspace key or id.
        query_id: the saved query's UUID (path segment).
        body: new visibility type + access list (full replace, not a patch).
        Returns: the updated QueryVisibilitySettingsModel.
        PUT /workspaces/{workspace}/queries/{queryId}/visibility.
        """
        payload = body.model_dump(mode="json", exclude_none=True)
        data = self.client.put(
            f"/workspaces/{workspace_key}/queries/{query_id}/visibility",
            payload,
        )
        return QueryVisibilitySettingsModel.model_validate(data)
