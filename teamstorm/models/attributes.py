# teamstorm/models/attributes.py
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field

from .base import TsBaseModel
from .common import OptionModel, UserModel
from .enums import AttributeType
from .workitems_thumbs import TypeThumbModel


class AttributeOptionModel(TsBaseModel):
    """
    One selectable value of a UniSelect/Tag attribute (e.g. "High" for a
    "Severity" attribute).

    Swagger: AttributeOptionModel
    required: id, name
    """

    id: UUID
    name: str


class AttributeModel(TsBaseModel):
    """
    A custom attribute definition: a workspace-configurable field (of a given
    `AttributeType`) that can be attached to one or more workitem types.

    Swagger: AttributeModel
    required: id, name, type, workitemTypes
    """

    id: UUID
    name: str
    description: str | None = None
    type: AttributeType
    options: list[AttributeOptionModel] | None = None
    workitem_types: list[TypeThumbModel] = Field(alias="workitemTypes")


class AttributesModelList(TsBaseModel):
    """
    Paginated response envelope for GET /workspaces/{workspace}/attributes.

    Swagger: AttributesModelList
    required: items
    """

    from_token: str | None = Field(default=None, alias="fromToken")
    max_items_count: int | None = Field(default=None, alias="maxItemsCount")
    next_token: str | None = Field(default=None, alias="nextToken")
    items: list[AttributeModel]


class CreateAttributeOptionModel(TsBaseModel):
    """
    A single option to seed when creating a UniSelect/Tag attribute; embedded
    in `CreateAttributeRequestBody.options`, not posted on its own.

    Swagger: CreateAttributeOptionModel
    required: name
    """

    name: str


class CreateAttributeOptionRequestBody(TsBaseModel):
    """
    Request body for POST /workspaces/{workspace}/attributes/{attribute}/options
    -- adds a new option to an existing UniSelect/Tag attribute.

    Swagger: CreateAttributeOptionRequestBody
    required: id, name
    NOTE: `id` is nullable in the spec despite being required -- pass `None`
    to let the server generate one, or a client-chosen UUID to set it
    explicitly.
    """

    id: UUID | None
    name: str


class PatchAttributeOptionModel(TsBaseModel):
    """
    A single option update embedded in `PatchAttributeRequestBody.options`
    (rename an existing option by id, or add a new one by omitting id).

    Swagger: PatchAttributeOptionModel
    required: id, name
    """

    id: UUID | None
    name: str


class PatchAttributeOptionRequestBody(TsBaseModel):
    """
    Request body for PATCH /workspaces/{workspace}/attributes/{attributeId}/options
    -- renames an existing attribute option. The option is identified by `id`
    in the body, not by a path segment.

    Swagger: PatchAttributeOptionRequestBody
    required: id, name
    """

    id: UUID
    name: str


class CreateAttributeRequestBody(TsBaseModel):
    """
    Request body for POST /workspaces/{workspace}/attributes -- defines a new
    custom attribute. `options` is only meaningful (and typically required by
    the server) when `type` is `UniSelect` or `Tag`.

    Swagger: CreateAttributeRequestBody
    required: name, type
    """

    name: str
    description: str | None = None
    type: AttributeType
    options: list[CreateAttributeOptionModel] | None = None


class PatchAttributeRequestBody(TsBaseModel):
    """
    Request body for PATCH /workspaces/{workspace}/attributes/{attribute} --
    partial update of an attribute's name/description/options. `type` cannot
    be changed after creation (absent from this body).

    Swagger: PatchAttributeRequestBody
    required: (none -- every field optional, partial-merge PATCH)
    """

    name: str | None = None
    description: str | None = None
    options: list[PatchAttributeOptionModel] | None = None


class AttributeValueModel(TsBaseModel):
    """
    Discriminator base for a workitem's attribute value: `id`/`name`/
    `description` identify *which* attribute this is, and `type` selects
    which concrete `*FieldValueModel` subclass (below) actually carries the
    value. Every real payload validates as one of those subclasses, not this
    base -- see the `AttributeFieldValue` union.

    Swagger: AttributeValueModel
    required: id, name, type
    """

    type: AttributeType
    id: UUID
    name: str
    description: str | None = None


class UpdateAttributeValueRequestBody(TsBaseModel):
    """
    Spec-faithful model of the bare discriminator base for updating a single
    workitem attribute value via
    PATCH /workspaces/{workspace}/workitems/{workitem}/attributes/{attribute}.

    You almost certainly do not want this class. It carries nothing but
    `type`, and nothing inherits from it -- the variants you actually send
    live in `teamstorm.models.workitems_attributes_update` and descend from
    that module's own same-named base. Construct the concrete
    `Update*FieldRequestBody` for your attribute's type, or accept the
    `UpdateWorkitemAttributeRequestBody` discriminated union, which is what
    `WorkitemsAPI.update_attribute` takes.

    Swagger: UpdateAttributeValueRequestBody
    required: type
    """

    type: AttributeType


class UniStringFieldValueModel(AttributeValueModel):
    """
    Value variant selected when `type == "UniString"`: a free-text attribute
    value. `value` is a plain string (or `None` if unset).

    Swagger: UniStringFieldValueModel (allOf AttributeValueModel + value)
    """

    type: Literal[AttributeType.UniString] = AttributeType.UniString
    value: str | None = None


class NumberFieldValueModel(AttributeValueModel):
    """
    Value variant selected when `type == "Number"`: `value` is a float (or
    `None` if unset).

    Swagger: NumberFieldValueModel (allOf AttributeValueModel + value)
    """

    type: Literal[AttributeType.Number] = AttributeType.Number
    value: float | None = None


class DateFieldValueModel(AttributeValueModel):
    """
    Value variant selected when `type == "Date"`: `value` is a `datetime` (or
    `None` if unset).

    Swagger: DateFieldValueModel (allOf AttributeValueModel + value)
    """

    type: Literal[AttributeType.Date] = AttributeType.Date
    value: datetime | None = None


class UniSelectFieldValueModel(AttributeValueModel):
    """
    Value variant selected when `type == "UniSelect"`: `value` is the single
    chosen `OptionModel` (or `None` if unset), drawn from the attribute's
    configured `options`.

    Swagger: UniSelectFieldValueModel (allOf AttributeValueModel + value)
    """

    type: Literal[AttributeType.UniSelect] = AttributeType.UniSelect
    value: OptionModel | None = None


class TagFieldValueModel(AttributeValueModel):
    """
    Value variant selected when `type == "Tag"`: `value` is a list of zero or
    more chosen `OptionModel`s (or `None` if unset) -- the multi-select
    counterpart of `UniSelectFieldValueModel`.

    Swagger: TagFieldValueModel (allOf AttributeValueModel + value)
    """

    type: Literal[AttributeType.Tag] = AttributeType.Tag
    value: list[OptionModel] | None = None


class UserFieldValueModel(AttributeValueModel):
    """
    Value variant selected when `type == "User"`: `value` is the assigned
    `UserModel` (or `None` if unset).

    Swagger: UserFieldValueModel (allOf AttributeValueModel + value)
    """

    type: Literal[AttributeType.User] = AttributeType.User
    value: UserModel | None = None


class TimeFieldValueModel(AttributeValueModel):
    """
    Value variant selected when `type == "TimeDuration"`: `value` is an
    integer duration (or `None` if unset). Units are not specified in the
    spec beyond "integer"; treat as an opaque server-defined unit rather than
    assuming seconds or minutes.

    Swagger: TimeFieldValueModel (allOf AttributeValueModel + value)
    """

    type: Literal[AttributeType.TimeDuration] = AttributeType.TimeDuration
    value: int | None = None


# Discriminated union of all seven workitem attribute value shapes, tagged by
# `type`. Used wherever a response embeds a workitem's live attribute values
# (see `WorkitemModel`); pydantic picks the concrete subclass from the `type`
# field automatically on validation.
AttributeFieldValue = Annotated[
    UniStringFieldValueModel
    | NumberFieldValueModel
    | DateFieldValueModel
    | UniSelectFieldValueModel
    | TagFieldValueModel
    | UserFieldValueModel
    | TimeFieldValueModel,
    Field(discriminator="type"),
]
