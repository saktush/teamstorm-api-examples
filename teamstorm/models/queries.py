# teamstorm/models/queries.py
from __future__ import annotations

from uuid import UUID

from pydantic import Field

from .base import TsBaseModel
from .comments import AccessListPrincipal
from .enums import PrincipalType, QueryVisibilityType


class QueryVisibilitySettingsModel(TsBaseModel):
    """
    Swagger: QueryVisibilitySettingsModel
    required: accessList, visibilityType

    accessList reuses the exact same PrincipalModel/UserPrincipalModel/
    GroupPrincipalModel discriminated-union swagger schemas as
    CommentVisibilitySettingsModel (teamstorm/models/comments.py, Task 6) -- these
    are the identical components in swagger.json, not a look-alike
    redefinition, so AccessListPrincipal is imported and reused as-is rather
    than re-declared here.
    """

    visibility_type: QueryVisibilityType = Field(alias="visibilityType")
    access_list: list[AccessListPrincipal] = Field(alias="accessList")


class UpdateQueryPrincipalModel(TsBaseModel):
    """
    Swagger: UpdateQueryPrincipalModel
    required: id, type

    NOTE: a distinct swagger component from UpdateCommentPrincipalModel
    (teamstorm/models/comments.py) even though both are structurally {id, type} --
    modeled separately here to track the real, separately-named schema this
    operation actually declares.
    """

    id: UUID
    type: PrincipalType


class UpdateQueryVisibilitySettingsRequestBody(TsBaseModel):
    """
    Swagger: UpdateQueryVisibilitySettingsRequestBody
    required: accessList, visibilityType

    Full replace (PUT), not a partial patch -- serialize with
    model_dump(mode="json", exclude_none=True), not exclude_unset.
    """

    visibility_type: QueryVisibilityType = Field(alias="visibilityType")
    access_list: list[UpdateQueryPrincipalModel] = Field(alias="accessList")


__all__ = [
    "QueryVisibilitySettingsModel",
    "UpdateQueryPrincipalModel",
    "UpdateQueryVisibilitySettingsRequestBody",
]
