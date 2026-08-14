from __future__ import annotations

from uuid import UUID

from pydantic import Field

from .workspaces import WorkspaceModel
from .attributes import AttributeFieldValue
from .base import TsBaseModel
from .common import DateTimeLike, UserModel
from .statuses import StatusModel
from .workitems_attributes_create import CreateWorkitemAttributeRequestBody
from .workitems_thumbs import (
    FolderThumbModel,
    SprintThumbModel,
    TreeNodeThumbModel,
    TypeThumbModel,
    WorkflowThumbModel,
    WorkitemPortfolioModel,
)


class CreateWorkitemRequestBody(TsBaseModel):
    """
    Request body for POST /workspaces/{workspace}/workitems.

    Swagger: CreateWorkitemRequestBody
    required: name, parentId, type
    NOTE: `parentId` is typed as a plain non-nullable GUID with no `required`
    keyword in the C# model, so an omitted value would silently become
    `Guid.Empty` in raw JSON -- and `Guid.Empty` does NOT mean "no parent" for
    workitems (a workitem is always a leaf of either a folder or another
    workitem; there is no root sentinel). This model keeps `parent_id`
    required with no default so the API wrapper itself can never construct that
    failure mode; pass a real folder GUID (e.g. the workspace's default
    folder from `FoldersAPI`). `type` is the target workitem type's key or
    name, resolved server-side.
    """

    name: str
    parent_id: UUID = Field(alias="parentId")
    type: str

    description: str | None = None
    workflow: str | None = None
    status: str | None = None
    start_date: DateTimeLike | None = Field(default=None, alias="startDate")
    due_date: DateTimeLike | None = Field(default=None, alias="dueDate")
    assignee: str | None = None
    sprint_id: UUID | None = Field(default=None, alias="sprintId")
    original_estimate: int | None = Field(default=None, alias="originalEstimate")
    attributes: list[CreateWorkitemAttributeRequestBody] | None = None
    portfolio_element_ids: list[UUID] | None = Field(default=None, alias="portfolioElementIds")


class PatchWorkitemRequestBody(TsBaseModel):
    """
    Request body for PATCH /workspaces/{workspace}/workitems/{workitem}.

    Swagger: PatchWorkitemRequestBody
    required: (none -- every field optional, partial-merge PATCH)
    """

    name: str | None = None
    description: str | None = None
    type: str | None = None
    workflow_id: UUID | None = Field(default=None, alias="workflowId")
    status: str | None = None
    start_date: DateTimeLike | None = Field(default=None, alias="startDate")
    due_date: DateTimeLike | None = Field(default=None, alias="dueDate")
    assignee: str | None = None
    sprint_id: UUID | None = Field(default=None, alias="sprintId")
    original_estimate: int | None = Field(default=None, alias="originalEstimate")
    story_points: int | None = Field(default=None, alias="storyPoints")
    parent_id: UUID | None = Field(default=None, alias="parentId")
    portfolio_element_ids: list[UUID] | None = Field(default=None, alias="portfolioElementIds")


class WorkitemsCountModel(TsBaseModel):
    """
    Swagger: WorkitemsCountModel
    required: count

    Response envelope for GET /workspaces/{workspace}/workitems/count.
    """

    count: int


class MissingWorkitemFieldError(AttributeError):
    """
    Raised by WorkitemModel.require.* when the underlying field is actually
    None on this workitem (e.g. a workitem with no status/workflow/sprint
    assigned). Use plain optional access (`wi.status`) when that's a real
    possibility for your data; use `wi.require.status` when you know it's
    always populated and want a non-Optional type with no defensive check.
    """

    def __init__(self, field: str, key: str) -> None:
        super().__init__(f"Workitem {key!r} has no {field!r} set")
        self.field = field
        self.key = key


class _RequiredWorkitemFields:
    """Non-Optional typed view over WorkitemModel's nullable reference fields."""

    __slots__ = ("_wi",)

    def __init__(self, wi: "WorkitemModel") -> None:
        self._wi = wi

    @property
    def status(self) -> StatusModel:
        """Return `wi.status`, or raise `MissingWorkitemFieldError` if it is `None`."""
        if self._wi.status is None:
            raise MissingWorkitemFieldError("status", self._wi.key)
        return self._wi.status

    @property
    def type(self) -> TypeThumbModel:
        """Return `wi.type`, or raise `MissingWorkitemFieldError` if it is `None`."""
        if self._wi.type is None:
            raise MissingWorkitemFieldError("type", self._wi.key)
        return self._wi.type

    @property
    def workflow(self) -> WorkflowThumbModel:
        """Return `wi.workflow`, or raise `MissingWorkitemFieldError` if it is `None`."""
        if self._wi.workflow is None:
            raise MissingWorkitemFieldError("workflow", self._wi.key)
        return self._wi.workflow

    @property
    def sprint(self) -> SprintThumbModel:
        """Return `wi.sprint`, or raise `MissingWorkitemFieldError` if it is `None`."""
        if self._wi.sprint is None:
            raise MissingWorkitemFieldError("sprint", self._wi.key)
        return self._wi.sprint

    @property
    def assignee(self) -> UserModel:
        """Return `wi.assignee`, or raise `MissingWorkitemFieldError` if it is `None`."""
        if self._wi.assignee is None:
            raise MissingWorkitemFieldError("assignee", self._wi.key)
        return self._wi.assignee

    @property
    def changed_by(self) -> UserModel:
        """Return `wi.changed_by`, or raise `MissingWorkitemFieldError` if it is `None`."""
        if self._wi.changed_by is None:
            raise MissingWorkitemFieldError("changedBy", self._wi.key)
        return self._wi.changed_by


class WorkitemModel(TsBaseModel):
    """
    A workitem (task/story/bug/etc.), returned by `WorkitemsAPI`.

    Swagger: WorkitemModel
    required: attributes, author, folder, id, key, name, parent, portfolios,
              workspace

    Several reference fields (`status`, `type`, `workflow`, `sprint`,
    `assignee`, `changed_by`) are `Optional` because a workitem can genuinely
    lack them (e.g. never assigned, no sprint). Use `wi.require.status` (see
    `.require` below) instead of `wi.status` when you know a field is always
    populated for your data and want a non-Optional value without writing a
    defensive `if wi.status is not None` check yourself -- it raises
    `MissingWorkitemFieldError` if the field actually is `None`, so you get a
    clear error instead of `AttributeError: NoneType has no attribute ...`
    two lines further down.
    """

    id: UUID
    key: str
    name: str

    description: str | None = None
    type: TypeThumbModel | None = None
    workflow: WorkflowThumbModel | None = None
    status: StatusModel | None = None

    start_date: DateTimeLike | None = Field(default=None, alias="startDate")
    end_date: DateTimeLike | None = Field(default=None, alias="endDate")
    created_date: DateTimeLike | None = Field(default=None, alias="createdDate")
    due_date: DateTimeLike | None = Field(default=None, alias="dueDate")

    assignee: UserModel | None = None
    author: UserModel
    sprint: SprintThumbModel | None = None
    folder: FolderThumbModel

    original_estimate: int | None = Field(default=None, alias="originalEstimate")
    time_spent: int | None = Field(default=None, alias="timeSpent")
    remaining_estimate: int | None = Field(default=None, alias="remainingEstimate")
    story_points: int | None = Field(default=None, alias="storyPoints")

    changed_by: UserModel | None = Field(default=None, alias="changedBy")
    change_date: DateTimeLike | None = Field(default=None, alias="changeDate")

    parent: TreeNodeThumbModel
    attributes: list[AttributeFieldValue]
    portfolios: list[WorkitemPortfolioModel]
    workspace: WorkspaceModel

    @property
    def require(self) -> _RequiredWorkitemFields:
        """
        Non-Optional typed access to status/type/workflow/sprint/assignee/changed_by.

        wi.status.category.name if wi.status else ""   # defensive, unchanged
        wi.require.status.category.name                # short, typed non-Optional;
                                                         # raises MissingWorkitemFieldError
                                                         # if actually absent
        """
        return _RequiredWorkitemFields(self)
