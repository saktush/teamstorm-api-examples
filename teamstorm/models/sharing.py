# teamstorm/models/sharing.py
from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field

from .base import TsBaseModel
from .common import GroupModel, UserModel
from .enums import SharedItemAccessLevel, SharedItemAccessType

# ---------------------------------------------------------------------------
# Workitem sharing
# ---------------------------------------------------------------------------


class SharedWorkitemPermissionModel(TsBaseModel):
    """
    Swagger: SharedWorkitemPermissionModel
    required: accessLevel, permissionId, type, workitemId, workspaceId
    Discriminator base for a workitem sharing permission's subject (a user or
    a group). Every real payload validates as one of the two concrete
    subclasses below, not this base -- see the SharedWorkitemPermission union.

    NOTE: this is deliberately NOT the same model as PrincipalModel/
    UserPrincipalModel/GroupPrincipalModel (teamstorm/models/comments.py, Task 6).
    Those model a comment-visibility access-list entry ({id, type} + an
    embedded user/group). This models a full sharing-permission record: its
    own permissionId, the workspace/workitem it applies to, and the
    accessLevel granted -- a genuinely different shape, not a redefinition.
    """

    type: SharedItemAccessType
    permission_id: UUID = Field(alias="permissionId")
    workspace_id: UUID = Field(alias="workspaceId")
    workitem_id: UUID = Field(alias="workitemId")
    access_level: SharedItemAccessLevel = Field(alias="accessLevel")


class SharedWorkitemUserPermissionModel(SharedWorkitemPermissionModel):
    """
    Swagger: SharedWorkitemUserPermissionModel (allOf SharedWorkitemPermissionModel + required "user")
    required: user (plus base fields)
    """

    type: Literal[SharedItemAccessType.User] = SharedItemAccessType.User
    user: UserModel


class SharedWorkitemGroupPermissionModel(SharedWorkitemPermissionModel):
    """
    Swagger: SharedWorkitemGroupPermissionModel (allOf SharedWorkitemPermissionModel + required "group")
    required: group (plus base fields)
    """

    type: Literal[SharedItemAccessType.Group] = SharedItemAccessType.Group
    group: GroupModel


SharedWorkitemPermission = Annotated[
    SharedWorkitemUserPermissionModel | SharedWorkitemGroupPermissionModel,
    Field(discriminator="type"),
]


class CreateSharedWorkitemPermissionBody(TsBaseModel):
    """
    Swagger: CreateSharedWorkitemPermissionBody
    required: accessLevel, type
    Discriminator base -- construct one of the two concrete subclasses below,
    not this class directly.
    """

    type: SharedItemAccessType
    access_level: SharedItemAccessLevel = Field(alias="accessLevel")


class CreateSharedWorkitemUserPermissionBody(CreateSharedWorkitemPermissionBody):
    """
    Swagger: CreateSharedWorkitemUserPermissionBody (allOf CreateSharedWorkitemPermissionBody + required "userId")
    Grants a single user direct access to a workitem at the given level.
    """

    type: Literal[SharedItemAccessType.User] = SharedItemAccessType.User
    user_id: UUID = Field(alias="userId")


class CreateSharedWorkitemGroupPermissionBody(CreateSharedWorkitemPermissionBody):
    """
    Swagger: CreateSharedWorkitemGroupPermissionBody (allOf CreateSharedWorkitemPermissionBody + required "groupId")
    Grants every member of a group direct access to a workitem at the given
    level.
    """

    type: Literal[SharedItemAccessType.Group] = SharedItemAccessType.Group
    group_id: UUID = Field(alias="groupId")


CreateSharedWorkitemPermission = Annotated[
    CreateSharedWorkitemUserPermissionBody | CreateSharedWorkitemGroupPermissionBody,
    Field(discriminator="type"),
]


class PatchSharedWorkitemPermissionBody(TsBaseModel):
    """
    Swagger: PatchSharedWorkitemPermissionBody
    required: none -- true partial update (per-field presence tracking per
    docs/api-analysis/upstream-semantics.md PATCH section).
    accessLevel is nullable per swagger. Serialize with
    model_dump(mode="json", exclude_unset=True, exclude_none=False):
    exclude_unset drops a never-assigned accessLevel from the body entirely
    (server: leave the current level unchanged); exclude_none=False still
    sends an explicitly-assigned accessLevel=None as JSON null (server:
    documented as a legal value, distinct from "absent").
    """

    access_level: SharedItemAccessLevel | None = Field(default=None, alias="accessLevel")


# ---------------------------------------------------------------------------
# Document sharing (structurally identical to workitem sharing above; see
# docs/api-analysis/upstream-semantics.md "Sharing / Permissions")
# ---------------------------------------------------------------------------


class SharedDocumentPermissionModel(TsBaseModel):
    """
    Swagger: SharedDocumentPermissionModel
    required: accessLevel, documentId, permissionId, type, workspaceId
    Discriminator base for a document sharing permission's subject (a user or
    a group). Every real payload validates as one of the two concrete
    subclasses below, not this base -- see the SharedDocumentPermission union.
    """

    type: SharedItemAccessType
    permission_id: UUID = Field(alias="permissionId")
    workspace_id: UUID = Field(alias="workspaceId")
    document_id: UUID = Field(alias="documentId")
    access_level: SharedItemAccessLevel = Field(alias="accessLevel")


class SharedDocumentUserPermissionModel(SharedDocumentPermissionModel):
    """
    Swagger: SharedDocumentUserPermissionModel (allOf SharedDocumentPermissionModel + required "user")
    required: user (plus base fields)
    """

    type: Literal[SharedItemAccessType.User] = SharedItemAccessType.User
    user: UserModel


class SharedDocumentGroupPermissionModel(SharedDocumentPermissionModel):
    """
    Swagger: SharedDocumentGroupPermissionModel (allOf SharedDocumentPermissionModel + required "group")
    required: group (plus base fields)
    """

    type: Literal[SharedItemAccessType.Group] = SharedItemAccessType.Group
    group: GroupModel


SharedDocumentPermission = Annotated[
    SharedDocumentUserPermissionModel | SharedDocumentGroupPermissionModel,
    Field(discriminator="type"),
]


class CreateSharedDocumentPermissionBody(TsBaseModel):
    """
    Swagger: CreateSharedDocumentPermissionBody
    required: accessLevel, type
    Discriminator base -- construct one of the two concrete subclasses below,
    not this class directly.
    """

    type: SharedItemAccessType
    access_level: SharedItemAccessLevel = Field(alias="accessLevel")


class CreateSharedDocumentUserPermissionBody(CreateSharedDocumentPermissionBody):
    """
    Swagger: CreateSharedDocumentUserPermissionBody (allOf CreateSharedDocumentPermissionBody + required "userId")
    Grants a single user direct access to a document at the given level.
    """

    type: Literal[SharedItemAccessType.User] = SharedItemAccessType.User
    user_id: UUID = Field(alias="userId")


class CreateSharedDocumentGroupPermissionBody(CreateSharedDocumentPermissionBody):
    """
    Swagger: CreateSharedDocumentGroupPermissionBody (allOf CreateSharedDocumentPermissionBody + required "groupId")
    Grants every member of a group direct access to a document at the given
    level.
    """

    type: Literal[SharedItemAccessType.Group] = SharedItemAccessType.Group
    group_id: UUID = Field(alias="groupId")


CreateSharedDocumentPermission = Annotated[
    CreateSharedDocumentUserPermissionBody | CreateSharedDocumentGroupPermissionBody,
    Field(discriminator="type"),
]


class PatchSharedDocumentPermissionBody(TsBaseModel):
    """
    Swagger: PatchSharedDocumentPermissionBody
    required: none -- true partial update, identical semantics to
    PatchSharedWorkitemPermissionBody above. Serialize with
    model_dump(mode="json", exclude_unset=True, exclude_none=False).
    """

    access_level: SharedItemAccessLevel | None = Field(default=None, alias="accessLevel")


__all__ = [
    "CreateSharedDocumentGroupPermissionBody",
    "CreateSharedDocumentPermission",
    "CreateSharedDocumentPermissionBody",
    "CreateSharedDocumentUserPermissionBody",
    "CreateSharedWorkitemGroupPermissionBody",
    "CreateSharedWorkitemPermission",
    "CreateSharedWorkitemPermissionBody",
    "CreateSharedWorkitemUserPermissionBody",
    "PatchSharedDocumentPermissionBody",
    "PatchSharedWorkitemPermissionBody",
    "SharedDocumentGroupPermissionModel",
    "SharedDocumentPermission",
    "SharedDocumentPermissionModel",
    "SharedDocumentUserPermissionModel",
    "SharedWorkitemGroupPermissionModel",
    "SharedWorkitemPermission",
    "SharedWorkitemPermissionModel",
    "SharedWorkitemUserPermissionModel",
]
