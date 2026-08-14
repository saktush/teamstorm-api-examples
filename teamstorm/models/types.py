from __future__ import annotations

from uuid import UUID

from pydantic import Field

from .attributes import AttributeModel
from .base import TsBaseModel
from .enums import ProgressType, TypeColor, TypeIcon
from .workitems_thumbs import WorkflowThumbModel


class TypeModel(TsBaseModel):
    """
    A workitem type (e.g. "Bug", "Story"): its workflow, display appearance,
    attached custom attributes, and progress/estimation configuration.

    Swagger: TypeModel
    required: attributes, color, estimatesInStoryPoints, estimatesInTime,
              icon, id, name, showTimeTracking, workflow
    """

    id: UUID
    name: str
    color: TypeColor
    icon: TypeIcon
    workflow: WorkflowThumbModel
    attributes: list[AttributeModel]
    progress_type: ProgressType | None = Field(default=None, alias="progressType")
    estimates_in_time: bool = Field(alias="estimatesInTime")
    estimates_in_story_points: bool = Field(alias="estimatesInStoryPoints")
    show_time_tracking: bool = Field(alias="showTimeTracking")


class TypeModelList(TsBaseModel):
    """
    Response envelope for GET /workspaces/{workspace}/types.

    Swagger: TypeModelList
    required: items
    """

    items: list[TypeModel]


class CreateTypeRequestBody(TsBaseModel):
    """
    Request body for POST /workspaces/{workspace}/types -- `workflow` is the
    target `WorkflowModel`'s id/name (a plain string per swagger, not a
    nested object).

    Swagger: CreateTypeRequestBody
    required: name, workflow
    """

    name: str
    workflow: str
    icon: TypeIcon | None = None
    color: TypeColor | None = None
    attribute_ids: list[UUID] | None = Field(default=None, alias="attributeIds")
    progress_type: ProgressType | None = Field(default=None, alias="progressType")
    estimates_in_time: bool | None = Field(default=None, alias="estimatesInTime")
    estimates_in_story_points: bool | None = Field(default=None, alias="estimatesInStoryPoints")
    show_time_tracking: bool | None = Field(default=None, alias="showTimeTracking")


class PatchTypeRequestBody(TsBaseModel):
    """
    Request body for PATCH /workspaces/{workspace}/types/{type}.

    Swagger: PatchTypeRequestBody
    required: (none -- every field optional, partial-merge PATCH)
    """

    name: str | None = None
    workflow: str | None = None
    icon: TypeIcon | None = None
    color: TypeColor | None = None
    attribute_ids: list[UUID] | None = Field(default=None, alias="attributeIds")
    progress_type: ProgressType | None = Field(default=None, alias="progressType")
    estimates_in_time: bool | None = Field(default=None, alias="estimatesInTime")
    estimates_in_story_points: bool | None = Field(default=None, alias="estimatesInStoryPoints")
    show_time_tracking: bool | None = Field(default=None, alias="showTimeTracking")
