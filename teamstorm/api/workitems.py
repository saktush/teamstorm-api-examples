from __future__ import annotations

import builtins
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import TypeAdapter

from teamstorm.api._base import BaseAPI
from teamstorm.client import ApiError
from teamstorm.models.attributes import AttributeFieldValue
from teamstorm.models.common import DateTimeLike, UUIDStr
from teamstorm.models.enums import AttributeType
from teamstorm.models.workitems import (
    CreateWorkitemRequestBody,
    PatchWorkitemRequestBody,
    WorkitemModel,
    WorkitemsCountModel,
)
from teamstorm.models.workitems_attributes_update import UpdateWorkitemAttributeRequestBody


def _query_date(value: DateTimeLike) -> str:
    """Convert a datetime or already-formatted string into a query-string-safe value."""
    return value.isoformat() if isinstance(value, datetime) else value


class WorkitemsAPI(BaseAPI):
    """
    Workitems (tasks/stories/bugs/etc.): the central resource everything else
    in the API wrapper either belongs to (attachments, comments, links, sharing,
    time tracking) or references (folders, sprints, portfolios, attributes).

    14 ops across 3 swagger tags (Workitems, WorkitemAttributes): list,
    create, list_by_parent, count, list_updates, delete, get, patch, plus
    list_attributes/update_attribute for the attribute *values* assigned to
    one workitem (attribute *definitions* live in AttributesAPI).
    """

    def list(
        self,
        workspace_key: str,
        *,
        type: str | None = None,
        sprint_id: UUID | None = None,
        portfolio_element_id: UUID | None = None,
        parent: UUID | None = None,
        name: str | None = None,
        assignee: str | None = None,
        author: str | None = None,
        status: str | None = None,
        status_category: str | None = None,
        from_token: str | None = None,
        max_items_count: int | None = None,
    ) -> list[WorkitemModel]:
        """
        List workitems in a workspace, filtered by any combination of type,
        sprint, portfolio element, parent, name, assignee, author, status or
        status category.

        :param workspace_key: workspace key or id.
        :param type: optional workitem type key/name filter.
        :param sprint_id: optional filter to one sprint.
        :param portfolio_element_id: optional filter to one portfolio
            element.
        :param parent: optional filter to direct children of one workitem.
        :param name: optional name filter.
        :param assignee: optional assignee username/id filter.
        :param author: optional author username/id filter.
        :param status: optional status key/name filter.
        :param status_category: optional status category filter.
        :param from_token: pagination cursor from a previous page's
            nextToken.
        :param max_items_count: page size (API wrapper default 500 when omitted).
        :return: every matching WorkitemModel across all pages.
        HTTP: GET /workspaces/{workspace}/workitems
        NOTE: this endpoint IS paginated (fromToken/maxItemsCount query
        params) -- fetches every page via get_all().
        """
        params: dict[str, Any] = {}
        if type is not None:
            params["type"] = type
        if sprint_id is not None:
            params["sprintId"] = str(sprint_id)
        if portfolio_element_id is not None:
            params["portfolioElementId"] = str(portfolio_element_id)
        if parent is not None:
            params["parent"] = str(parent)
        if name is not None:
            params["name"] = name
        if assignee is not None:
            params["assignee"] = assignee
        if author is not None:
            params["author"] = author
        if status is not None:
            params["status"] = status
        if status_category is not None:
            params["statusCategory"] = status_category
        if from_token is not None:
            params["fromToken"] = from_token
        if max_items_count is not None:
            params["maxItemsCount"] = max_items_count

        data = self.client.get_all(
            f"/workspaces/{workspace_key}/workitems",
            params=params or None,
        )
        return TypeAdapter(list[WorkitemModel]).validate_python(data)

    def get(self, workspace_key: str, *, workitem_id: UUIDStr) -> WorkitemModel:
        """
        Fetch a single workitem by id.

        workspace_key: workspace key.
        workitem_id: workitem UUID or human-readable key (e.g. "WS-42") -- the
            server resolves either (docs/api-analysis/upstream-semantics.md §9).
        Returns: the WorkitemModel.
        GET /workspaces/{workspace}/workitems/{workitem}.
        """
        data = self.client.get(f"/workspaces/{workspace_key}/workitems/{workitem_id}")
        return WorkitemModel.model_validate(data)

    def create(self, workspace_key: str, body: CreateWorkitemRequestBody) -> WorkitemModel:
        """
        Create a new workitem.

        :param workspace_key: workspace key or id.
        :param body: CreateWorkitemRequestBody -- required name, parentId
            (either a folder or another workitem; there is no root
            sentinel), and type. See the model's own docstring for a
            `Guid.Empty` gotcha around an omitted parentId.
        :return: the created WorkitemModel.
        HTTP: POST /workspaces/{workspace}/workitems
        """
        payload = body.model_dump(mode="json", exclude_none=True)
        data = self.client.post(f"/workspaces/{workspace_key}/workitems", payload)
        return WorkitemModel.model_validate(data)

    def patch(
        self,
        workspace_key: str,
        *,
        workitem_id: UUIDStr,
        body: PatchWorkitemRequestBody,
    ) -> WorkitemModel:
        """
        Partially update a workitem's name/description/type/status/etc.

        :param workspace_key: workspace key.
        :param workitem_id: workitem UUID or key to patch.
        :param body: partial workitem fields to update.
        :return: the updated WorkitemModel.
        HTTP: PATCH /workspaces/{workspace}/workitems/{workitem}
        NOTE: only fields explicitly set on *body* are sent
        (exclude_unset=True): the server distinguishes a field absent from
        the request body (leave unchanged)
        from one present with value null (clear it). exclude_none is
        explicitly disabled here because TsBaseModel.model_dump() otherwise
        defaults exclude_none=True, which would silently drop an intentional
        "clear this field" null. To change a single attribute *value*
        (including clearing it to null), use update_attribute() below
        instead -- it is a dedicated PUT endpoint with real null-clearing
        semantics.
        NOTE: an explicit `assignee=None` now really clears the assignee
        (TS-17874); previously it could not be cleared. Leave
        `assignee` unset to keep the current assignee.
        """
        payload = body.model_dump(mode="json", exclude_unset=True, exclude_none=False)
        data = self.client.patch(
            f"/workspaces/{workspace_key}/workitems/{workitem_id}",
            payload,
        )
        return WorkitemModel.model_validate(data)

    def delete(self, workspace_key: str, *, workitem_id: UUIDStr) -> None:
        """
        Delete a workitem.

        WARNING: this is a genuine cascading HARD DELETE on the server, not a
        soft/trash delete. The workitem and everything hanging off it (child
        workitems, attachments, comments, links, etc.) is removed immediately
        and irreversibly.

        workspace_key: workspace key.
        workitem_id: workitem UUID or key to delete.
        Returns: None.
        DELETE /workspaces/{workspace}/workitems/{workitem}.
        """
        self.client.delete(f"/workspaces/{workspace_key}/workitems/{workitem_id}")
        return None

    def list_by_parent(
        self,
        workspace_key: str,
        *,
        parent_id: UUIDStr,
        with_sub_items: bool | None = None,
    ) -> builtins.list[WorkitemModel]:
        """
        List the workitems whose parent is the given workitem.

        workspace_key: workspace key.
        parent_id: parent workitem UUID or key (path segment).
        with_sub_items: when True, include the full descendant sub-tree
            instead of only direct children.
        Returns: list[WorkitemModel].
        GET /workspaces/{workspace}/workitems/by-parent/{parent} with query param withSubItems.
        """
        params: dict[str, Any] = {}
        if with_sub_items is not None:
            params["withSubItems"] = with_sub_items

        data = self.client.get_all(
            f"/workspaces/{workspace_key}/workitems/by-parent/{parent_id}",
            params=params or None,
        )
        return TypeAdapter(list[WorkitemModel]).validate_python(data)

    def count(self, workspace_key: str) -> int:
        """
        Count workitems in a workspace.

        workspace_key: workspace key.
        Returns: the total workitem count as an int (unwrapped from WorkitemsCountModel).
        GET /workspaces/{workspace}/workitems/count.
        """
        data = self.client.get(f"/workspaces/{workspace_key}/workitems/count")
        return WorkitemsCountModel.model_validate(data).count

    def list_updates(
        self,
        workspace_key: str,
        *,
        changed_from_date: DateTimeLike,
        changed_to_date: DateTimeLike | None = None,
        from_token: str | None = None,
        max_items_count: int | None = None,
    ) -> builtins.list[WorkitemModel]:
        """
        List workitems changed within a date range, most recent server-side changes first.

        workspace_key: workspace key.
        changed_from_date: required lower bound (inclusive) on change timestamp;
            a datetime or an already-formatted ISO-8601 string.
        changed_to_date: optional upper bound (inclusive) on change timestamp.
        from_token: opaque pagination cursor from a previous page.
        max_items_count: page size (server default 50, max 1000).
        Returns: list[WorkitemModel].
        GET /workspaces/{workspace}/workitems/updates with query params
        changedFromDate/changedToDate/fromToken/maxItemsCount.
        NOTE: the upper-bound query parameter is spelled `changedToDate` on the wire
        (it was `ChangedToDate` before spec v4.24.0); the Python argument name
        `changed_to_date` is unchanged.
        """
        params: dict[str, Any] = {"changedFromDate": _query_date(changed_from_date)}
        if changed_to_date is not None:
            params["changedToDate"] = _query_date(changed_to_date)
        if from_token is not None:
            params["fromToken"] = from_token
        if max_items_count is not None:
            params["maxItemsCount"] = max_items_count

        data = self.client.get_all(
            f"/workspaces/{workspace_key}/workitems/updates",
            params=params,
        )
        return TypeAdapter(list[WorkitemModel]).validate_python(data)

    def list_attributes(self, workspace_key: str, *, workitem_id: UUIDStr) -> builtins.list[AttributeFieldValue]:
        """
        List every attribute value currently set on a workitem.

        :param workspace_key: workspace key.
        :param workitem_id: workitem UUID or key (path segment).
        :return: one AttributeFieldValue per attribute assigned to the
            workitem's type (the discriminated union tagged by `type` -- see
            teamstorm.models.attributes.AttributeFieldValue).
        HTTP: GET /workspaces/{workspace}/workitems/{workitem}/attributes
        NOTE: this endpoint does not paginate (no fromToken/maxItemsCount on
        the wire) -- a bare array is returned; get_all() is used only as the
        client's generic list-fetch helper.
        """
        data = self.client.get_all(f"/workspaces/{workspace_key}/workitems/{workitem_id}/attributes")
        return TypeAdapter(list[AttributeFieldValue]).validate_python(data)

    def update_attribute(
        self,
        workspace_key: str,
        *,
        workitem_id: UUIDStr,
        attribute_id: UUID,
        body: UpdateWorkitemAttributeRequestBody,
    ) -> AttributeFieldValue:
        """
        Set or clear one attribute value on a workitem.

        Unlike patch() above, this is a full replace (PUT, not PATCH) of a
        single attribute value, and `value` is nullable and required: pass
        `None` inside the concrete `Update*FieldRequestBody` variant to
        clear the attribute (there is no separate delete-attribute-value
        endpoint). Construct one of the concrete `Update*FieldRequestBody`
        classes from teamstorm.models.workitems_attributes_update -- picking
        the one matching the attribute's own type -- not the discriminator
        base class.

        This method PUTs first and, only on a 404/405 ApiError, transparently
        falls back to PATCH on the same path -- a narrow, endpoint-specific
        workaround for UniSelect/Tag attributes on some server versions (see
        docs/api-analysis/conventions.md §10 item 7). Extra debug logging is
        emitted for UniSelect/Tag values specifically.

        :param workspace_key: workspace key.
        :param workitem_id: workitem UUID or key (path segment).
        :param attribute_id: UUID of the attribute definition whose value to
            set (path segment).
        :param body: the concrete Update*FieldRequestBody variant matching
            the attribute's type; its nested `value` may be None to clear it.
        :return: the AttributeFieldValue reflecting the new state.
        :raises ApiError: propagated as-is for any status other than 404/405
            on the initial PUT (those two trigger the PATCH fallback
            instead).
        HTTP: PUT /workspaces/{workspace}/workitems/{workitem}/attributes/{attributeId}
        (falls back to PATCH on the same path if the PUT itself 404s/405s).
        """
        # `value` is required-and-nullable in the spec, so an explicit None is
        # the documented way to clear an attribute. TsBaseModel.model_dump()
        # defaults to exclude_none=True, which would drop the key entirely and
        # turn the clear into a silent no-op -- hence exclude_none=False.
        # exclude_unset=True still trims the untouched optional keys of a
        # nested value object (e.g. UpdateUserFieldValueModel.id vs userName).
        payload = body.model_dump(mode="json", exclude_unset=True, exclude_none=False)
        path = f"/workspaces/{workspace_key}/workitems/{workitem_id}/attributes/{attribute_id}"
        is_select_or_tag = body.type in (AttributeType.UniSelect, AttributeType.Tag)
        if is_select_or_tag:
            self.client.log.debug(
                "Workitem ATTRIBUTE UPDATE request method=PUT path=%s type=%s value=%r",
                path,
                body.type.value,
                payload.get("value"),
            )
        try:
            data = self.client.put(path, payload)
            method_used = "PUT"
        except ApiError as exc:
            if exc.status not in (404, 405):
                raise
            if is_select_or_tag:
                self.client.log.debug(
                    "Workitem ATTRIBUTE UPDATE fallback PUT->PATCH path=%s status=%s details=%s",
                    path,
                    exc.status,
                    exc.details,
                )
            data = self.client.patch(path, payload)
            method_used = "PATCH"
        if is_select_or_tag:
            self.client.log.debug(
                "Workitem ATTRIBUTE UPDATE response method=%s path=%s raw=%r",
                method_used,
                path,
                data,
            )
        return TypeAdapter(AttributeFieldValue).validate_python(data)
