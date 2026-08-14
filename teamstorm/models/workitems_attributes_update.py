from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field

from .base import TsBaseModel
from .enums import AttributeType


class UpdateAttributeValueRequestBody(TsBaseModel):
    """
    Local discriminator base for the Update*FieldRequestBody variants below.

    NOTE: this class deliberately shares its name with, but is a DIFFERENT
    class from, `teamstorm.models.attributes.UpdateAttributeValueRequestBody`
    -- that is the one actually exported from `teamstorm.models`
    (`tests/api/test_models_exports.py::test_update_attribute_value_request_body_is_attributes_one`
    pins `models.UpdateAttributeValueRequestBody.__module__` to
    `teamstorm.models.attributes`). This module-local class is never imported
    by `teamstorm/models/__init__.py`; it exists purely so the
    `Update*FieldRequestBody` subclasses below have a common parent to
    inherit `type` from. Always import the concrete `Update*FieldRequestBody`
    variant you need, or the `UpdateWorkitemAttributeRequestBody` union --
    never this class by name from this module.

    Swagger: UpdateAttributeValueRequestBody
    required: type
    """

    type: AttributeType


class UpdateUserFieldValueModel(TsBaseModel):
    """
    Value payload for a `User`-type attribute on update: identify the target
    user by `id` or by `user_name`.

    Swagger: UpdateUserFieldValueModel
    """

    id: UUID | None = None
    user_name: str | None = Field(default=None, alias="userName")


class UpdateUniStringFieldRequestBody(UpdateAttributeValueRequestBody):
    """
    Variant selected when `type == "UniString"`: `value` is a nullable
    string -- pass `None` to clear the attribute.

    Swagger: UpdateUniStringFieldRequestBody (allOf UpdateAttributeValueRequestBody + value)
    """

    type: Literal[AttributeType.UniString]
    value: str | None


class UpdateNumberFieldRequestBody(UpdateAttributeValueRequestBody):
    """
    Variant selected when `type == "Number"`: `value` is a nullable float --
    pass `None` to clear the attribute.

    Swagger: UpdateNumberFieldRequestBody (allOf UpdateAttributeValueRequestBody + value)
    """

    type: Literal[AttributeType.Number]
    value: float | None


class UpdateDateFieldRequestBody(UpdateAttributeValueRequestBody):
    """
    Variant selected when `type == "Date"`: `value` is a nullable datetime --
    pass `None` to clear the attribute.

    Swagger: UpdateDateFieldRequestBody (allOf UpdateAttributeValueRequestBody + value)
    """

    type: Literal[AttributeType.Date]
    value: datetime | None


class UpdateUniSelectFieldRequestBody(UpdateAttributeValueRequestBody):
    """
    Variant selected when `type == "UniSelect"`: `value` is the chosen
    option's name or id as a nullable plain string -- pass `None` to clear
    the selection.

    Swagger: UpdateUniSelectFieldRequestBody (allOf UpdateAttributeValueRequestBody + value)
    """

    type: Literal[AttributeType.UniSelect]
    value: str | None


class UpdateTagFieldRequestBody(UpdateAttributeValueRequestBody):
    """
    Variant selected when `type == "Tag"`: `value` is a nullable list of
    option names/ids -- the multi-select counterpart of
    `UpdateUniSelectFieldRequestBody`.

    Swagger: UpdateTagFieldRequestBody (allOf UpdateAttributeValueRequestBody + value)
    """

    type: Literal[AttributeType.Tag]
    value: list[str] | None


class UpdateUserFieldRequestBody(UpdateAttributeValueRequestBody):
    """
    Variant selected when `type == "User"`: `value` is a nullable
    `UpdateUserFieldValueModel` identifying the user to assign, or `None` to
    unassign.

    Swagger: UpdateUserFieldRequestBody (allOf UpdateAttributeValueRequestBody + value)
    """

    type: Literal[AttributeType.User]
    value: UpdateUserFieldValueModel | None


class UpdateTimeFieldRequestBody(UpdateAttributeValueRequestBody):
    """
    Variant selected when `type == "TimeDuration"`: `value` is a nullable
    int duration -- pass `None` to clear the attribute.

    Swagger: UpdateTimeFieldRequestBody (allOf UpdateAttributeValueRequestBody + value)
    """

    type: Literal[AttributeType.TimeDuration]
    value: int | None


# Discriminated union of all seven update-attribute-value request shapes,
# tagged by `type`. Construct one of the concrete `Update*FieldRequestBody`
# instances (never `UpdateAttributeValueRequestBody` itself) and pass it to
# WorkitemsAPI.update_attribute.
UpdateWorkitemAttributeRequestBody = Annotated[
    UpdateUniStringFieldRequestBody
    | UpdateNumberFieldRequestBody
    | UpdateDateFieldRequestBody
    | UpdateUniSelectFieldRequestBody
    | UpdateTagFieldRequestBody
    | UpdateUserFieldRequestBody
    | UpdateTimeFieldRequestBody,
    Field(discriminator="type"),
]
