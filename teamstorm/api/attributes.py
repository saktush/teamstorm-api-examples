from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import TypeAdapter

from ._base import BaseAPI
from teamstorm.models.attributes import (
    AttributeModel,
    CreateAttributeOptionRequestBody,
    CreateAttributeRequestBody,
    PatchAttributeOptionRequestBody,
    PatchAttributeRequestBody,
)
from teamstorm.models.enums import AttributeType


class AttributesAPI(BaseAPI):
    """
    Custom attribute definitions (workspace-configurable fields attached to
    workitem types) and their UniSelect/Tag options.

    9 ops (Attributes tag): list, get, create, patch, delete, plus
    add_option/patch_option/delete_option for managing UniSelect/Tag options
    on an existing attribute. Values assigned to a specific workitem are a
    different resource -- see WorkitemsAPI.list_attributes/update_attribute.
    """

    def list(
        self,
        workspace_key: str,
        *,
        name: str | None = None,
        is_full_name_matching: bool | None = None,
        type: AttributeType | None = None,
    ) -> list[AttributeModel]:
        """
        List the custom attributes defined in a workspace.

        :param workspace_key: workspace key or id.
        :param name: optional name filter.
        :param is_full_name_matching: when True, `name` must match exactly
            rather than as a substring/prefix.
        :param type: optional AttributeType filter (e.g. UniSelect, Number).
        :return: every AttributeModel across all pages.
        HTTP: GET /workspaces/{workspace}/attributes
        NOTE: the endpoint is paginated on the wire (fromToken/maxItemsCount),
        but this method does not expose a from_token/max_items_count
        parameter -- get_all() still walks every page regardless, using the
        client's default page size of 500.
        """
        params: dict[str, Any] = {}
        if name is not None:
            params["name"] = name
        if is_full_name_matching is not None:
            params["isFullNameMatching"] = is_full_name_matching
        if type is not None:
            params["type"] = type.value

        data = self.client.get_all(
            f"/workspaces/{workspace_key}/attributes",
            params=params or None,
        )
        return TypeAdapter(list[AttributeModel]).validate_python(data)

    def get(self, workspace_key: str, *, attribute_id: UUID) -> AttributeModel:
        """
        Fetch a single attribute definition by id.

        :param workspace_key: workspace key or id.
        :param attribute_id: UUID of the attribute to fetch.
        :return: the matching AttributeModel.
        HTTP: GET /workspaces/{workspace}/attributes/{attributeId}
        """
        data = self.client.get(f"/workspaces/{workspace_key}/attributes/{attribute_id}")
        return AttributeModel.model_validate(data)

    def create(self, workspace_key: str, body: CreateAttributeRequestBody) -> AttributeModel:
        """
        Create a new custom attribute definition.

        :param workspace_key: workspace key or id.
        :param body: CreateAttributeRequestBody -- name, type, and (for
            UniSelect/Tag) the seed options list.
        :return: the created AttributeModel.
        HTTP: POST /workspaces/{workspace}/attributes
        """
        payload = body.model_dump(mode="json", exclude_none=True)
        data = self.client.post(f"/workspaces/{workspace_key}/attributes", payload)
        return AttributeModel.model_validate(data)

    def patch(
        self,
        workspace_key: str,
        *,
        attribute_id: UUID,
        body: PatchAttributeRequestBody,
    ) -> AttributeModel:
        """
        Partially update an attribute's name/description/options. `type`
        cannot be changed after creation.

        :param workspace_key: workspace key or id.
        :param attribute_id: UUID of the attribute to patch.
        :param body: partial attribute fields to update.
        :return: the updated AttributeModel.
        HTTP: PATCH /workspaces/{workspace}/attributes/{attributeId}
        NOTE: only fields explicitly set on *body* are sent
        (exclude_unset=True): the server distinguishes a field absent from
        the request body (leave unchanged)
        from one present with value null (clear it). exclude_none is
        explicitly disabled here because TsBaseModel.model_dump() otherwise
        defaults exclude_none=True, which would silently drop an intentional
        "clear this field" null.
        """
        payload = body.model_dump(mode="json", exclude_unset=True, exclude_none=False)
        data = self.client.patch(
            f"/workspaces/{workspace_key}/attributes/{attribute_id}",
            payload,
        )
        return AttributeModel.model_validate(data)

    def delete(self, workspace_key: str, *, attribute_id: UUID) -> None:
        """
        Delete an attribute definition (and its options).

        :param workspace_key: workspace key or id.
        :param attribute_id: UUID of the attribute to delete.
        :return: None.
        HTTP: DELETE /workspaces/{workspace}/attributes/{attributeId}
        """
        self.client.delete(f"/workspaces/{workspace_key}/attributes/{attribute_id}")
        return None

    def add_option(
        self,
        workspace_key: str,
        *,
        attribute_id: UUID,
        body: CreateAttributeOptionRequestBody,
    ) -> AttributeModel:
        """
        Add a new selectable option to an existing UniSelect/Tag attribute.

        :param workspace_key: workspace key or id.
        :param attribute_id: UUID of the attribute to add an option to.
        :param body: CreateAttributeOptionRequestBody -- option name, and an
            optional client-chosen id (server generates one when omitted).
        :return: the updated AttributeModel, including the new option.
        HTTP: POST /workspaces/{workspace}/attributes/{attributeId}/options
        """
        payload = body.model_dump(mode="json", exclude_none=True)
        data = self.client.post(
            f"/workspaces/{workspace_key}/attributes/{attribute_id}/options",
            payload,
        )
        return AttributeModel.model_validate(data)

    def patch_option(
        self,
        workspace_key: str,
        *,
        attribute_id: UUID,
        body: PatchAttributeOptionRequestBody,
    ) -> AttributeModel:
        """
        Rename an existing UniSelect/Tag option.

        :param workspace_key: workspace key or id.
        :param attribute_id: UUID of the attribute the option belongs to.
        :param body: PatchAttributeOptionRequestBody -- identifies the option
            by `id` and carries its new `name`. NOTE: the option id travels in
            the request body, not the path -- there is no `{optionId}` path
            segment on this route.
        :return: the updated AttributeModel.
        HTTP: PATCH /workspaces/{workspace}/attributes/{attributeId}/options
        """
        payload = body.model_dump(mode="json", exclude_none=True)
        data = self.client.patch(
            f"/workspaces/{workspace_key}/attributes/{attribute_id}/options",
            payload,
        )
        return AttributeModel.model_validate(data)

    def delete_option(
        self,
        workspace_key: str,
        *,
        attribute_id: UUID,
        option_id: UUID,
    ) -> None:
        """
        Delete one selectable option from a UniSelect/Tag attribute.

        :param workspace_key: workspace key or id.
        :param attribute_id: UUID of the attribute the option belongs to.
        :param option_id: UUID of the option to delete (path segment here,
            unlike patch_option()).
        :return: None.
        HTTP: DELETE /workspaces/{workspace}/attributes/{attributeId}/options/{optionId}
        """
        self.client.delete(f"/workspaces/{workspace_key}/attributes/{attribute_id}/options/{option_id}")
        return None
