from __future__ import annotations

from uuid import UUID

from pydantic import Field

from .base import TsBaseModel
from .enums import WorkflowType
from .statuses import StatusCategoryModel, StatusModel


class TransitionModel(TsBaseModel):
    """
    A single allowed status transition inside a `WorkflowModel`: either from
    one specific status (`from_status`) or from any status
    (`from_all_statuses`) to `next_status`.

    Swagger: TransitionModel
    required: fromAllStatuses, isInitial, nextStatus, transitionId
    """

    transition_id: UUID = Field(alias="transitionId")
    from_status: StatusModel | None = Field(default=None, alias="fromStatus")
    next_status: StatusModel = Field(alias="nextStatus")
    from_all_statuses: bool = Field(alias="fromAllStatuses")
    is_initial: bool = Field(alias="isInitial")


class CreateTransitionRequestBody(TsBaseModel):
    """
    A transition to include when creating a workflow, embedded in
    `CreateWorkflowRequestBody.transitions`. Omitting `from_status_id` means
    "from any status" (mirrors `TransitionModel.from_all_statuses`).

    Swagger: CreateTransitionRequestBody
    required: isInitial, nextStatusId
    """

    from_status_id: UUID | None = Field(default=None, alias="fromStatusId")
    next_status_id: UUID = Field(alias="nextStatusId")
    is_initial: bool = Field(alias="isInitial")


class PatchTransitionRequestBody(TsBaseModel):
    """
    A transition to include when patching a workflow's transition list,
    embedded in `PatchWorkflowRequestBody.transitions`. Include
    `transition_id` to update an existing transition, or omit it to add a
    new one.

    Swagger: PatchTransitionRequestBody
    required: isInitial, nextStatusId
    """

    transition_id: UUID | None = Field(default=None, alias="transitionId")
    from_status_id: UUID | None = Field(default=None, alias="fromStatusId")
    next_status_id: UUID = Field(alias="nextStatusId")
    is_initial: bool = Field(alias="isInitial")


class WorkflowStatusModel(TsBaseModel):
    """
    A status placed on a workflow's diagram, with its canvas position.

    Swagger: WorkflowStatusModel
    required: category, id, name, positionX, positionY
    """

    id: UUID
    name: str
    category: StatusCategoryModel
    position_x: int = Field(alias="positionX")
    position_y: int = Field(alias="positionY")


class WorkflowModel(TsBaseModel):
    """
    A workflow: the set of statuses and allowed transitions between them for
    either workitems or portfolio elements (see `WorkflowType`).

    Swagger: WorkflowModel
    required: id, name, statuses, transitions, type
    """

    id: UUID
    name: str
    type: WorkflowType
    description: str | None = None
    transitions: list[TransitionModel]
    statuses: list[WorkflowStatusModel]


class WorkflowModelList(TsBaseModel):
    """
    Response envelope for GET /workspaces/{workspace}/workflows.

    Swagger: WorkflowModelList
    required: items
    """

    items: list[WorkflowModel]


class CreateWorkflowStatusRequestBody(TsBaseModel):
    """
    A status to place on the diagram when creating a workflow, embedded in
    `CreateWorkflowRequestBody.statuses`.

    Swagger: CreateWorkflowStatusRequestBody
    required: positionX, positionY, statusId
    """

    status_id: UUID = Field(alias="statusId")
    position_x: int = Field(alias="positionX")
    position_y: int = Field(alias="positionY")


class PatchWorkflowStatusRequestBody(TsBaseModel):
    """
    A status to place/reposition on the diagram when patching a workflow,
    embedded in `PatchWorkflowRequestBody.statuses`.

    Swagger: PatchWorkflowStatusRequestBody
    required: positionX, positionY, statusId
    """

    status_id: UUID = Field(alias="statusId")
    position_x: int = Field(alias="positionX")
    position_y: int = Field(alias="positionY")


class CreateWorkflowRequestBody(TsBaseModel):
    """
    Request body for POST /workspaces/{workspace}/workflows.

    Swagger: CreateWorkflowRequestBody
    required: name, statuses, transitions
    """

    name: str
    transitions: list[CreateTransitionRequestBody]
    statuses: list[CreateWorkflowStatusRequestBody]


class PatchWorkflowRequestBody(TsBaseModel):
    """
    Request body for PATCH /workspaces/{workspace}/workflows/{workflow}.

    Swagger: PatchWorkflowRequestBody
    required: (none -- every field optional, partial-merge PATCH)
    """

    name: str | None = None
    transitions: list[PatchTransitionRequestBody] | None = None
    statuses: list[PatchWorkflowStatusRequestBody] | None = None
