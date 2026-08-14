from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from .base import TsBaseModel
from .common import UserModel, DateTimeLike
from .enums import SprintStates


class SprintMemberRequestBody(TsBaseModel):
    """
    One team member to assign to a sprint, embedded in
    `CreateSprintRequestBody.team` / `PatchSprintRequestBody.team`.

    Swagger: SprintMemberRequestBody
    required: userId
    """

    user_id: UUID = Field(alias="userId")
    days_off: int | None = Field(default=None, alias="daysOff")
    hours_per_day: int | None = Field(default=None, alias="hoursPerDay")


class CreateSprintRequestBody(TsBaseModel):
    """
    Swagger: CreateSprintRequestBody
    required (per swagger schema): agileId, endDate, estimatedStoryPoints, name,
    startDate, team, workdays

    NOTE: swagger's `required` list flags `estimatedStoryPoints` and `team` as
    required, but the server does not actually enforce that: both have real
    server-side defaults (`estimatedStoryPoints` defaults to 0, `team` to an
    empty list) -- the OpenAPI generator lists non-nullable properties as
    required regardless of business intent. Server-side validation only
    enforces `workdays > 0` unconditionally; it has no rule at all for
    estimatedStoryPoints/team. Omitting
    them round-trips safely (server substitutes 0 / empty list). Keeping them
    Optional here is intentional and matches docs/api-analysis/upstream-semantics.md
    ("Sprints"); do not widen to required.
    """

    agile_id: UUID = Field(alias="agileId")
    name: str
    start_date: DateTimeLike = Field(alias="startDate")
    end_date: DateTimeLike = Field(alias="endDate")
    workdays: int

    description: str | None = None
    copy_views_from_sprint: UUID | None = Field(default=None, alias="copyViewsFromSprint")
    estimated_story_points: int | None = Field(default=None, alias="estimatedStoryPoints")
    team: list[SprintMemberRequestBody] | None = None


class PatchSprintRequestBody(TsBaseModel):
    """
    Swagger: PatchSprintRequestBody
    required (per swagger schema): workdays

    NOTE: swagger flags `workdays` as required, but the server treats it like
    every other field on this partial-merge PATCH body: optional, and
    server-side validation only checks `workdays > 0` when the key is present
    in the request body -- i.e. it's validated like any other optional,
    conditionally-present PATCH field, not a mandatory one. This is the same
    "non-nullable type gets auto-marked required by the OpenAPI generator"
    artifact as CreateSprintRequestBody above. Keeping it Optional here is
    intentional; do not widen to required.
    """

    name: str | None = None
    description: str | None = None
    start_date: DateTimeLike | None = Field(default=None, alias="startDate")
    end_date: DateTimeLike | None = Field(default=None, alias="endDate")
    workdays: int | None = None
    estimated_story_points: int | None = Field(default=None, alias="estimatedStoryPoints")
    team: list[SprintMemberRequestBody] | None = None


class TeamMemberModel(TsBaseModel):
    """
    A resolved sprint team member, as returned in `SprintModel.team` (the
    response-side counterpart of `SprintMemberRequestBody`, with the user
    embedded as a full `UserModel` rather than just an id).

    Swagger: TeamMemberModel
    required: daysOff, hoursPerDay, user
    """

    days_off: int = Field(alias="daysOff")
    hours_per_day: int = Field(alias="hoursPerDay")
    user: UserModel


class SprintModel(TsBaseModel):
    """
    A sprint (iteration) on an agile board, returned by `SprintsAPI`.

    Swagger: SprintModel
    required: id, isBacklog, name
    """

    id: UUID
    name: str
    is_backlog: bool = Field(alias="isBacklog")

    description: str | None = None
    start_date: DateTimeLike | None = Field(default=None, alias="startDate")
    end_date: DateTimeLike | None = Field(default=None, alias="endDate")
    state: SprintStates | None = None
    workdays: int | None = None
    team: list[TeamMemberModel] | None = None
