# teamstorm/models/time_tracking.py
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from .base import TsBaseModel
from .common import UserModel
from .workitems import WorkitemModel


class TimeTrackingEntryTypeModel(TsBaseModel):
    """
    Swagger: TimeTrackingEntryTypeModel
    required: id, name
    """

    id: UUID
    name: str


class TimeTrackingEntryModel(TsBaseModel):
    """
    Swagger: TimeTrackingEntryModel
    required: author, createdAt, date, deletedAt, deleteUser, deleteUserId,
    description, id, spentTime, updatedAt, workitem

    NOTE: deletedAt/deleteUser/deleteUserId/description are all listed as
    *required* by swagger but are also *nullable* -- following existing repo
    precedent for this exact required-but-nullable shape (e.g. UserModel.email,
    teamstorm/models/common.py:38) they are modeled as Optional[...] = None rather
    than a required-no-default field, so a payload that sends an explicit
    null round-trips the same as one that (against spec) omits the key.
    """

    id: UUID
    date: datetime
    spent_time: int = Field(alias="spentTime")
    description: str | None = None
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    deleted_at: datetime | None = Field(default=None, alias="deletedAt")
    delete_user_id: UUID | None = Field(default=None, alias="deleteUserId")
    delete_user: UserModel | None = Field(default=None, alias="deleteUser")
    workitem: WorkitemModel
    author: UserModel
    type: TimeTrackingEntryTypeModel | None = None


class TimeTrackingModelList(TsBaseModel):
    """
    Swagger: TimeTrackingModelList
    required: items
    Cursor-paginated envelope (see docs/api-analysis/upstream-semantics.md
    "Pagination" 2a) -- the actual API methods consume this shape via
    client.get_all() + TypeAdapter(List[TimeTrackingEntryModel]) rather than
    validating this envelope class directly, matching the dominant pattern
    used by every other *API list() method in this repo.
    """

    from_token: str | None = Field(default=None, alias="fromToken")
    max_items_count: int | None = Field(default=None, alias="maxItemsCount")
    next_token: str | None = Field(default=None, alias="nextToken")
    items: list[TimeTrackingEntryModel]


__all__ = [
    "TimeTrackingEntryModel",
    "TimeTrackingEntryTypeModel",
    "TimeTrackingModelList",
]
