# teamstorm/api/portfolios.py
from __future__ import annotations

from typing import Any
from uuid import UUID

from teamstorm.api._base import BaseAPI
from teamstorm.models.common import UUIDStr
from teamstorm.models.portfolios import (
    CreatePortfolioElementRequestBody,
    CreatePortfolioRequestBody,
    PatchPortfolioElementRequestBody,
    PatchPortfolioRequestBody,
    PortfolioElementModel,
    PortfolioElementModelList,
    PortfolioModel,
    PortfolioModelList,
)


class PortfoliosAPI(BaseAPI):
    """
    Portfolios: OKR-style rollups of portfolio elements, each scoped to a folder.

    5 ops (Portfolios tag): list/get/create/patch/delete. `patch` is NOT a
    general partial update -- see its docstring below.
    """

    def list(
        self,
        workspace_key: str,
        *,
        name: str | None = None,
        folder_id: UUID | None = None,
    ) -> list[PortfolioModel]:
        """
        List portfolios in a workspace, optionally filtered by name/folder.

        workspace_key: workspace key.
        name: optional name filter.
        folder_id: optional owning-folder UUID filter.
        Returns: every matching PortfolioModel.
        GET /workspaces/{workspace}/portfolios.
        NOTE: this endpoint does not paginate (no fromToken/maxItemsCount
        query params, no token field on PortfolioModelList) -- uses a plain
        get(), not get_all(); do not add from_token/max_items_count
        parameters here.
        """
        params: dict[str, Any] = {}
        if name is not None:
            params["name"] = name
        if folder_id is not None:
            params["folderId"] = str(folder_id)

        data = self.client.get(f"/workspaces/{workspace_key}/portfolios", params=params or None)
        return PortfolioModelList.model_validate(data).items

    def get(self, workspace_key: str, *, portfolio_id: UUID) -> PortfolioModel:
        """
        Fetch a single portfolio by id.

        workspace_key: workspace key.
        portfolio_id: UUID of the portfolio to fetch.
        Returns: the matching PortfolioModel.
        GET /workspaces/{workspace}/portfolios/{portfolioId}.
        """
        data = self.client.get(f"/workspaces/{workspace_key}/portfolios/{portfolio_id}")
        return PortfolioModel.model_validate(data)

    def create(self, workspace_key: str, body: CreatePortfolioRequestBody) -> PortfolioModel:
        """
        Create a portfolio inside a folder.

        workspace_key: workspace key.
        body: name + owning folder id (both required).
        Returns: the created PortfolioModel.
        POST /workspaces/{workspace}/portfolios.
        """
        payload = body.model_dump(mode="json", exclude_none=True)
        data = self.client.post(f"/workspaces/{workspace_key}/portfolios", payload)
        return PortfolioModel.model_validate(data)

    def patch(
        self,
        workspace_key: str,
        *,
        portfolio_id: UUID,
        body: PatchPortfolioRequestBody,
    ) -> PortfolioModel:
        """
        Rename a portfolio.

        NOTE: despite the PATCH verb, this is NOT a general partial update.
        The server's PatchPortfolioRequestBody has exactly one field, a
        required `name` -- there is nothing else patchable through this
        endpoint (verified against docs/api-analysis/upstream-semantics.md,
        Section 7, item 2: no per-field presence tracking, unlike
        PortfolioElementsAPI.patch below). The body is still serialized with
        exclude_unset=True, exclude_none=False for consistency with every
        other PATCH call site in this API wrapper, but in practice `name` is always
        present since the model requires it.

        workspace_key: workspace key.
        portfolio_id: UUID of the portfolio to rename.
        body: the new name.
        Returns: the updated PortfolioModel.
        PATCH /workspaces/{workspace}/portfolios/{portfolioId}.
        """
        payload = body.model_dump(mode="json", exclude_unset=True, exclude_none=False)
        data = self.client.patch(f"/workspaces/{workspace_key}/portfolios/{portfolio_id}", payload)
        return PortfolioModel.model_validate(data)

    def delete(self, workspace_key: str, *, portfolio_id: UUID) -> None:
        """
        Delete a portfolio.

        workspace_key: workspace key.
        portfolio_id: UUID of the portfolio to delete.
        Returns: None.
        DELETE /workspaces/{workspace}/portfolios/{portfolioId}.
        """
        self.client.delete(f"/workspaces/{workspace_key}/portfolios/{portfolio_id}")
        return None


class PortfolioElementsAPI(BaseAPI):
    """
    Portfolio elements: individual rollup items that belong to a portfolio
    and can be linked to workitems.

    7 ops (PortfolioElements tag): list/get/create/patch/delete on the
    element itself, plus link_workitem/unlink_workitem to attach/detach a
    workitem. Unlike PortfoliosAPI.patch, `patch` here IS a genuine
    partial-merge update.
    """

    def list(
        self,
        workspace_key: str,
        *,
        name: str | None = None,
        folder_id: UUID | None = None,
        portfolio_id: UUID | None = None,
        status: str | None = None,
    ) -> list[PortfolioElementModel]:
        """
        List portfolio elements in a workspace, optionally filtered.

        workspace_key: workspace key.
        name: optional name filter.
        folder_id: optional folder UUID filter.
        portfolio_id: optional owning-portfolio UUID filter.
        status: optional status id/name filter.
        Returns: every matching PortfolioElementModel.
        GET /workspaces/{workspace}/portfolio-elements.
        NOTE: this endpoint does not paginate (no fromToken/maxItemsCount
        query params, no token field on PortfolioElementModelList) -- uses a
        plain get(), not get_all().
        """
        params: dict[str, Any] = {}
        if name is not None:
            params["name"] = name
        if folder_id is not None:
            params["folderId"] = str(folder_id)
        if portfolio_id is not None:
            params["portfolioId"] = str(portfolio_id)
        if status is not None:
            params["status"] = status

        data = self.client.get(f"/workspaces/{workspace_key}/portfolio-elements", params=params or None)
        return PortfolioElementModelList.model_validate(data).items

    def get(self, workspace_key: str, *, portfolio_element_id: UUID) -> PortfolioElementModel:
        """
        Fetch a single portfolio element by id.

        workspace_key: workspace key.
        portfolio_element_id: UUID of the portfolio element to fetch.
        Returns: the matching PortfolioElementModel.
        GET /workspaces/{workspace}/portfolio-elements/{portfolioElementId}.
        """
        data = self.client.get(f"/workspaces/{workspace_key}/portfolio-elements/{portfolio_element_id}")
        return PortfolioElementModel.model_validate(data)

    def create(self, workspace_key: str, body: CreatePortfolioElementRequestBody) -> PortfolioElementModel:
        """
        Create a portfolio element inside a portfolio.

        workspace_key: workspace key.
        body: owning portfolio id + name (both required), plus optional
        description/startDate/endDate/responsibles.
        Returns: the created PortfolioElementModel.
        POST /workspaces/{workspace}/portfolio-elements.
        """
        payload = body.model_dump(mode="json", exclude_none=True)
        data = self.client.post(f"/workspaces/{workspace_key}/portfolio-elements", payload)
        return PortfolioElementModel.model_validate(data)

    def patch(
        self,
        workspace_key: str,
        *,
        portfolio_element_id: UUID,
        body: PatchPortfolioElementRequestBody,
    ) -> PortfolioElementModel:
        """
        Partially update a portfolio element.

        Unlike PortfoliosAPI.patch, this IS a genuine partial-merge PATCH:
        every field on PatchPortfolioElementRequestBody is optional, and the
        server distinguishes a field absent from the request (leave
        unchanged) from one present with value null (clear it). Only fields
        explicitly set on *body* are sent (exclude_unset=True); exclude_none
        is disabled because TsBaseModel.model_dump() otherwise defaults to
        exclude_none=True, which would silently drop an intentional
        "clear this field" null.

        workspace_key: workspace key.
        portfolio_element_id: UUID of the portfolio element to patch.
        body: partial fields to update.
        Returns: the updated PortfolioElementModel.
        PATCH /workspaces/{workspace}/portfolio-elements/{portfolioElementId}.
        """
        payload = body.model_dump(mode="json", exclude_unset=True, exclude_none=False)
        data = self.client.patch(
            f"/workspaces/{workspace_key}/portfolio-elements/{portfolio_element_id}",
            payload,
        )
        return PortfolioElementModel.model_validate(data)

    def delete(self, workspace_key: str, *, portfolio_element_id: UUID) -> None:
        """
        Delete a portfolio element.

        workspace_key: workspace key.
        portfolio_element_id: UUID of the portfolio element to delete.
        Returns: None.
        DELETE /workspaces/{workspace}/portfolio-elements/{portfolioElementId}.
        """
        self.client.delete(f"/workspaces/{workspace_key}/portfolio-elements/{portfolio_element_id}")
        return None

    def link_workitem(
        self,
        workspace_key: str,
        *,
        portfolio_element_id: UUID,
        workitem_id: UUIDStr,
    ) -> PortfolioElementModel:
        """
        Attach a workitem to a portfolio element.

        Body-less POST (teamstorm.client.TsClient.post's `body` parameter is
        optional and omitted here entirely).

        GOTCHA (verified server behavior): creating a subtask already
        auto-copies the parent workitem's portfolio-element links onto the
        child -- the server hardcodes copy-portfolio-links behavior to
        always-on for subtask creation (see
        docs/api-analysis/upstream-semantics.md, "Gotchas" item 2). Calling
        this method again right after creating a subtask that already
        inherited the same link is redundant, not harmful, but a caller who
        does NOT want the inherited link must explicitly call
        unlink_workitem() after create -- there is no way to opt out of the
        copy at creation time via the public API.

        workspace_key: workspace key.
        portfolio_element_id: UUID of the portfolio element.
        workitem_id: workitem UUID or key (path segment; swagger types this as
        a plain string, not a uuid format, matching the key-or-id resolution
        used for workitem path/query segments elsewhere in this API).
        Returns: the updated PortfolioElementModel.
        POST /workspaces/{workspace}/portfolio-elements/{portfolioElementId}/workitems/{workitem}.
        """
        data = self.client.post(
            f"/workspaces/{workspace_key}/portfolio-elements/{portfolio_element_id}/workitems/{workitem_id}"
        )
        return PortfolioElementModel.model_validate(data)

    def unlink_workitem(
        self,
        workspace_key: str,
        *,
        portfolio_element_id: UUID,
        workitem_id: UUIDStr,
    ) -> None:
        """
        Detach a workitem from a portfolio element.

        workspace_key: workspace key.
        portfolio_element_id: UUID of the portfolio element.
        workitem_id: workitem UUID or key (path segment).
        Returns: None.
        DELETE /workspaces/{workspace}/portfolio-elements/{portfolioElementId}/workitems/{workitem}.
        """
        self.client.delete(
            f"/workspaces/{workspace_key}/portfolio-elements/{portfolio_element_id}/workitems/{workitem_id}"
        )
        return None
