# teamstorm/models/comments.py
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field

from .base import TsBaseModel
from .common import GroupModel, UserModel
from .enums import CommentVisibilityType, PrincipalType


class CommentModel(TsBaseModel):
    """
    Swagger: CommentModel
    required: author, createdAt, id, text, updatedAt, visibilityType
    """

    id: UUID
    text: str
    author: UserModel
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    visibility_type: CommentVisibilityType = Field(alias="visibilityType")


class CommentModelList(TsBaseModel):
    """
    Swagger: CommentModelList
    required: items
    NOTE: unlike most *ModelList schemas in this repo, this one carries no
    fromToken/nextToken/maxItemsCount fields -- the List*Comments endpoints do
    not paginate (no such query params on the GET operations either).
    """

    items: list[CommentModel]


class CreateCommentRequestBody(TsBaseModel):
    """
    Swagger: CreateCommentRequestBody
    required: text
    """

    text: str


class UpdateCommentRequestBody(TsBaseModel):
    """
    Swagger: UpdateCommentRequestBody
    required: text
    NOTE: UpdateWorkitemComment is a PUT (full replace), not a PATCH -- serialize
    with model_dump(mode="json", exclude_none=True), not exclude_unset.
    """

    text: str


class PrincipalModel(TsBaseModel):
    """
    Swagger: PrincipalModel
    required: id, type
    Discriminator base for CommentVisibilitySettingsModel.accessList entries.
    PrincipalType has exactly two members (User/Group), so every real payload
    validates as one of the two concrete subclasses below, not this base.
    """

    id: UUID
    type: PrincipalType


class UserPrincipalModel(PrincipalModel):
    """
    Swagger: UserPrincipalModel (allOf PrincipalModel + required "user")
    required: id, type, user
    """

    type: Literal[PrincipalType.User] = PrincipalType.User
    user: UserModel


class GroupPrincipalModel(PrincipalModel):
    """
    Swagger: GroupPrincipalModel (allOf PrincipalModel + required "group")
    required: id, type, group
    """

    type: Literal[PrincipalType.Group] = PrincipalType.Group
    group: GroupModel


AccessListPrincipal = Annotated[
    UserPrincipalModel | GroupPrincipalModel,
    Field(discriminator="type"),
]


class CommentVisibilitySettingsModel(TsBaseModel):
    """
    Swagger: CommentVisibilitySettingsModel
    required: accessList, visibilityType
    """

    visibility_type: CommentVisibilityType = Field(alias="visibilityType")
    access_list: list[AccessListPrincipal] = Field(alias="accessList")


class UpdateCommentPrincipalModel(TsBaseModel):
    """
    Swagger: UpdateCommentPrincipalModel
    required: id, type
    """

    id: UUID
    type: PrincipalType


class UpdateCommentVisibilitySettingsRequestBody(TsBaseModel):
    """
    Swagger: UpdateCommentVisibilitySettingsRequestBody
    required: accessList, visibilityType
    """

    visibility_type: CommentVisibilityType = Field(alias="visibilityType")
    access_list: list[UpdateCommentPrincipalModel] = Field(alias="accessList")
