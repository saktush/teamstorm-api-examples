# teamstorm/api/types.py
from __future__ import annotations

from uuid import UUID

from pydantic import TypeAdapter

from ._base import BaseAPI
from teamstorm.models.types import CreateTypeRequestBody, PatchTypeRequestBody, TypeModel


class TypesAPI(BaseAPI):
    """
    Workitem types (e.g. "Bug", "Story"), each bound to a workflow and a set
    of assignable attributes.

    7 ops (Types tag): list, get, create, patch, delete, plus
    add_attribute/remove_attribute for managing which AttributesAPI
    definitions a type exposes on its workitems.
    """

    def list(self, workspace_key: str) -> list[TypeModel]:
        """
        List every workitem type defined in a workspace.

        :param workspace_key: workspace key or id.
        :return: every TypeModel in the workspace.
        HTTP: GET /workspaces/{workspace}/types
        NOTE: this endpoint does not paginate (no fromToken/maxItemsCount on
        the wire) -- a bare array is returned; get_all() is used only as the
        client's generic list-fetch helper.
        """
        data = self.client.get_all(f"/workspaces/{workspace_key}/types")
        return TypeAdapter(list[TypeModel]).validate_python(data)

    def get(self, workspace_key: str, type_key: str) -> TypeModel:
        """
        Fetch a single workitem type by id or name.

        :param workspace_key: workspace key or id.
        :param type_key: type UUID or name (path segment).
        :return: the matching TypeModel.
        HTTP: GET /workspaces/{workspace}/types/{type}
        """
        data = self.client.get(f"/workspaces/{workspace_key}/types/{type_key}")
        return TypeModel.model_validate(data)

    def create(self, workspace_key: str, body: CreateTypeRequestBody) -> TypeModel:
        """
        Create a new workitem type.

        :param workspace_key: workspace key or id.
        :param body: CreateTypeRequestBody -- required name and workflow
            (key or name), plus optional icon/color/attributeIds.
        :return: the created TypeModel.
        HTTP: POST /workspaces/{workspace}/types
        """
        payload = body.model_dump(mode="json", exclude_none=True)
        data = self.client.post(f"/workspaces/{workspace_key}/types", payload)
        return TypeModel.model_validate(data)

    def patch(self, workspace_key: str, *, type_key: str, body: PatchTypeRequestBody) -> TypeModel:
        """
        Partially update a workitem type.

        :param workspace_key: workspace key or id.
        :param type_key: type UUID or name (path segment).
        :param body: partial type fields to update.
        :return: the updated TypeModel.
        HTTP: PATCH /workspaces/{workspace}/types/{type}
        NOTE: only fields explicitly set on *body* are sent
        (exclude_unset=True): the server distinguishes a field absent from
        the request body (leave unchanged)
        from one present with value null (clear it). exclude_none is
        explicitly disabled here because TsBaseModel.model_dump() otherwise
        defaults exclude_none=True, which would silently drop an intentional
        "clear this field" null.
        """
        payload = body.model_dump(mode="json", exclude_unset=True, exclude_none=False)
        data = self.client.patch(f"/workspaces/{workspace_key}/types/{type_key}", payload)
        return TypeModel.model_validate(data)

    def delete(self, workspace_key: str, *, type_key: str) -> None:
        """
        Delete a workitem type.

        :param workspace_key: workspace key or id.
        :param type_key: type UUID or name (path segment).
        :return: None.
        HTTP: DELETE /workspaces/{workspace}/types/{type}
        """
        self.client.delete(f"/workspaces/{workspace_key}/types/{type_key}")
        return None

    def add_attribute(self, workspace_key: str, *, type_key: str, attribute_id: UUID) -> TypeModel:
        """
        Assign an existing attribute definition to a workitem type.

        :param workspace_key: workspace key or id.
        :param type_key: type UUID or name (path segment).
        :param attribute_id: UUID of an existing AttributesAPI attribute to
            attach to this type.
        :return: the updated TypeModel.
        HTTP: POST /workspaces/{workspace}/types/{type}/attributes/{attributeId}
        NOTE: body-less POST -- an empty JSON object is sent as the payload,
        no fields to set (the attribute id is entirely in the path).
        """
        data = self.client.post(
            f"/workspaces/{workspace_key}/types/{type_key}/attributes/{attribute_id}",
            body={},
        )
        return TypeModel.model_validate(data)

    def remove_attribute(self, workspace_key: str, *, type_key: str, attribute_id: UUID) -> None:
        """
        Unassign an attribute from a workitem type (the attribute definition
        itself is untouched; only the type<->attribute link is removed).

        :param workspace_key: workspace key or id.
        :param type_key: type UUID or name (path segment).
        :param attribute_id: UUID of the attribute to detach from this type.
        :return: None.
        HTTP: DELETE /workspaces/{workspace}/types/{type}/attributes/{attributeId}
        """
        self.client.delete(f"/workspaces/{workspace_key}/types/{type_key}/attributes/{attribute_id}")
        return None
