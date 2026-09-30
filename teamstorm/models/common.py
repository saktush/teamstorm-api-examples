from __future__ import annotations
from datetime import datetime
from uuid import UUID

from pydantic import Field

from .base import TsBaseModel

UUIDStr = UUID | str
# NOTE: the API is inconsistent about whether date-shaped fields come back as a
# real ISO-8601 datetime or an opaque string, so this alias documents that
# ambiguity rather than resolving it. This is a deliberate, tested trade-off,
# not an oversight -- known consequences: (1) the `str` arm accepts any
# non-empty string, including one that isn't a date at all, with no format
# validation; (2) a naive (tz-unaware) `datetime` passed in serializes back out
# without a UTC offset. Do not "fix" either behavior here without updating the
# tests that pin it.
DateTimeLike = datetime | str


class ErrorModel(TsBaseModel):
    """
    The shape of an error response body from the TeamStorm API (surfaced to
    callers via `ApiError`).

    Swagger: ErrorModel
    required: key, messages, type
    """

    type: str
    key: str
    messages: list[str]
    payload: dict[str, str] | None = None


class OptionModel(TsBaseModel):
    """
    A generic id/name pair. Used, among other places, as the `value` shape
    of `UniSelectFieldValueModel`/`TagFieldValueModel` (a chosen attribute
    option).

    Swagger: OptionModel
    required: id, name
    """

    id: UUID
    name: str


class UserModel(TsBaseModel):
    """
    A TeamStorm user account, as embedded in responses (author, assignee,
    changed_by, comment principal, etc.) and returned by `UsersAPI`.

    NOTE: `username` is the user's real login. Per the TS-15580 fix, the
    author/updatedBy/createdBy users in workspace, role, document and
    sprint-related responses now carry the login there instead of the display
    name; other embedded users are not covered by that report.

    Swagger: UserModel
    required: displayName, email, id, username
    """

    id: UUID
    display_name: str = Field(alias="displayName")
    username: str
    email: str | None = None
    provider_id: UUID | None = Field(default=None, alias="providerId")


class UsersModelList(TsBaseModel):
    """
    Response envelope for GET /users -- the global (non-workspace-scoped,
    non-paginated) user listing; unlike `UserModelList` below, it carries no
    from/next-token fields.

    Swagger: UsersModelList
    required: items
    """

    items: list[UserModel]


class UserModelList(TsBaseModel):
    """
    Paginated response envelope for GET /workspaces/{workspace}/users.

    Swagger: UserModelList
    required: items
    """

    from_token: str | None = Field(default=None, alias="fromToken")
    max_items_count: int | None = Field(default=None, alias="maxItemsCount")
    next_token: str | None = Field(default=None, alias="nextToken")
    items: list[UserModel]


class GroupModel(TsBaseModel):
    """
    A TeamStorm user group, as returned by `GroupsAPI` and embedded wherever
    a group can be the subject of a permission (sharing, roles).

    Swagger: GroupModel
    required: id, name
    """

    id: UUID
    name: str
    provider_id: UUID | None = Field(default=None, alias="providerId")


class GroupModelList(TsBaseModel):
    """
    Paginated response envelope for GET /groups.

    Swagger: GroupModelList
    required: items
    """

    from_token: str | None = Field(default=None, alias="fromToken")
    max_items_count: int | None = Field(default=None, alias="maxItemsCount")
    next_token: str | None = Field(default=None, alias="nextToken")
    items: list[GroupModel]
