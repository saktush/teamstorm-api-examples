# teamstorm/models/workitems_attributes_create.py
from __future__ import annotations
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field

from .base import TsBaseModel
from .enums import AttributeType


class CreateAttributeValueRequestBody(TsBaseModel):
    """
    Base contract for create-attribute values (used via allOf in swagger).
    Swagger: required = ["id", "type"].
    """

    type: AttributeType
    id: UUID


class CreateUniStringFieldRequestBody(CreateAttributeValueRequestBody):
    """
    Variant selected when `type == "UniString"`: sets a free-text attribute
    value. `value` is a required (non-nullable) string.

    Swagger: CreateUniStringFieldRequestBody (allOf CreateAttributeValueRequestBody + value)
    """

    type: Literal[AttributeType.UniString] = AttributeType.UniString
    value: str


class CreateNumberFieldRequestBody(CreateAttributeValueRequestBody):
    """
    Variant selected when `type == "Number"`: `value` is a required float.

    Swagger: CreateNumberFieldRequestBody (allOf CreateAttributeValueRequestBody + value)
    """

    type: Literal[AttributeType.Number] = AttributeType.Number
    value: float


class CreateDateFieldRequestBody(CreateAttributeValueRequestBody):
    """
    Variant selected when `type == "Date"`: `value` is a required datetime.

    Swagger: CreateDateFieldRequestBody (allOf CreateAttributeValueRequestBody + value)
    """

    type: Literal[AttributeType.Date] = AttributeType.Date
    # swagger: string (date-time)
    value: datetime


class CreateUniSelectFieldRequestBody(CreateAttributeValueRequestBody):
    """
    Variant selected when `type == "UniSelect"`: `value` is the chosen
    option's name or id as a plain string (unlike the response-side
    `UniSelectFieldValueModel`, which embeds a full `OptionModel`).

    Swagger: CreateUniSelectFieldRequestBody (allOf CreateAttributeValueRequestBody + value)
    """

    type: Literal[AttributeType.UniSelect] = AttributeType.UniSelect
    # swagger: string
    value: str


class CreateTagFieldRequestBody(CreateAttributeValueRequestBody):
    """
    Variant selected when `type == "Tag"`: `value` is a list of option
    names/ids as plain strings -- the multi-select counterpart of
    `CreateUniSelectFieldRequestBody`.

    Swagger: CreateTagFieldRequestBody (allOf CreateAttributeValueRequestBody + value)
    """

    type: Literal[AttributeType.Tag] = AttributeType.Tag
    value: list[str]


class CreateUserFieldValueModel(TsBaseModel):
    """
    Value payload for a `User`-type attribute on create: identify the target
    user by `id` or by `user_name` (both nullable/optional in the spec, but
    the server needs at least one to resolve the user).

    Swagger: CreateUserFieldValueModel
    """

    # swagger: id is string(uuid), nullable true; userName string nullable true
    id: UUID | None = None
    user_name: str | None = Field(default=None, alias="userName")


class CreateUserFieldRequestBody(CreateAttributeValueRequestBody):
    """
    Variant selected when `type == "User"`: `value` is a
    `CreateUserFieldValueModel` identifying the user to assign.

    Swagger: CreateUserFieldRequestBody (allOf CreateAttributeValueRequestBody + value)
    """

    type: Literal[AttributeType.User] = AttributeType.User
    value: CreateUserFieldValueModel


class CreateTimeFieldRequestBody(CreateAttributeValueRequestBody):
    """
    Variant selected when `type == "TimeDuration"`: `value` is a required
    int32 duration in the server's own unit (see `TimeFieldValueModel` for
    the same caveat on the response side).

    Swagger: CreateTimeFieldRequestBody (allOf CreateAttributeValueRequestBody + value)
    """

    type: Literal[AttributeType.TimeDuration] = AttributeType.TimeDuration
    value: int  # int32


# Discriminated union of all seven create-attribute-value request shapes,
# tagged by `type`. Pass one of the concrete `Create*FieldRequestBody`
# instances (never `CreateAttributeValueRequestBody` itself) wherever a
# workitem-creation attribute value is required.
CreateWorkitemAttributeRequestBody = Annotated[
    CreateUniStringFieldRequestBody
    | CreateNumberFieldRequestBody
    | CreateDateFieldRequestBody
    | CreateUniSelectFieldRequestBody
    | CreateTagFieldRequestBody
    | CreateUserFieldRequestBody
    | CreateTimeFieldRequestBody,
    Field(discriminator="type"),
]
