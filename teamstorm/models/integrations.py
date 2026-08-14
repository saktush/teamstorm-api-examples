# teamstorm/models/integrations.py
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from .base import TsBaseModel
from .common import UserModel
from .enums import SystemRoles, TokenType


class TokenModel(TsBaseModel):
    """
    Swagger: TokenModel
    required: author, createdAt, id, name, type, url

    A git integration token's metadata: name, target git host URL, who
    created/last changed it, and its TokenType (GitLab/GitFlic). Does NOT
    carry the secret token value -- that only ever appears on
    TokenSensitiveDataModel below, returned by create()/refresh(). See
    GitIntegrationTokensAPI's module docstring (teamstorm/api/integrations.py) for
    why.
    """

    id: UUID
    name: str
    url: str
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime | None = Field(default=None, alias="updatedAt")
    author: UserModel
    changed_by: UserModel | None = Field(default=None, alias="changedBy")
    type: TokenType


class TokenSensitiveDataModel(TokenModel):
    """
    Swagger: TokenSensitiveDataModel (allOf TokenModel + required "token")
    required: token (plus all TokenModel fields)

    SECURITY: `token` is the actual git integration secret. The server
    returns it ONLY on CreateToken and RefreshToken -- every other read
    (GetToken, ListTokens) and UpdateToken return the secret-less
    TokenModel instead. There is no endpoint that returns a previously
    issued token's secret again: if a response of this type is discarded
    without persisting `.token`, the value is permanently unrecoverable.
    Never log this model's dump or its `.token` field.
    """

    token: str


class TokensModelList(TsBaseModel):
    """
    Swagger: TokensModelList
    required: tokens

    Bare "tokens"-keyed envelope, not the usual "items" envelope, and not
    paginated (no fromToken/maxItemsCount/nextToken fields on this schema).
    GitIntegrationTokensAPI.list() therefore calls client.get() directly and
    unwraps `.tokens`, not client.get_all().
    """

    tokens: list[TokenModel]


class CreateTokenRequestBody(TsBaseModel):
    """
    Swagger: CreateTokenRequestBody
    required: name, type
    """

    name: str
    type: TokenType


class UpdateTokenRequestBody(TsBaseModel):
    """
    Swagger: UpdateTokenRequestBody
    required: name

    NOTE: UpdateToken is a PUT (full replace), confirmed as the "put" verb
    on .../git-integration-tokens/{tokenId} in swagger.json -- not a PATCH.
    Serialize with exclude_none=True (the TsBaseModel default), not
    exclude_unset; there is no partial-merge semantics here. `name` is the
    only field this schema defines, so "full replace" only ever means
    renaming the token -- it never touches the secret.
    """

    name: str


class OpenIdConnectionModel(TsBaseModel):
    """
    Swagger: OpenIdConnectionModel
    required: authority, id, isEnabled, name

    An OpenID Connect SSO connection configured on this CWM instance. This
    is a global, non-workspace-scoped resource -- no {workspace} path
    segment appears on any /open-id/... endpoint, confirmed directly
    against swagger.json.
    """

    id: UUID
    name: str
    authority: str
    is_enabled: bool = Field(alias="isEnabled")
    image_url: str | None = Field(default=None, alias="imageUrl")


class CreateOpenIdConnectionModel(TsBaseModel):
    """
    Swagger: CreateOpenIdConnectionModel
    required: authority, clientId, clientSecret, isEnabled, name, scope

    NOTE: this body itself carries the OIDC client secret (`clientSecret`)
    -- never log a serialized dump of this model.
    """

    name: str
    authority: str
    client_id: str = Field(alias="clientId")
    client_secret: str = Field(alias="clientSecret")
    metadata_address: str | None = Field(default=None, alias="metadataAddress")
    scope: list[str]
    is_enabled: bool = Field(alias="isEnabled")


class CreateOpenIdUserModel(TsBaseModel):
    """
    Swagger: CreateOpenIdUserModel
    required: displayName, email, externalId, userName

    Pre-provisions a local CWM user account for a specific OpenID
    connection, keyed by `externalId` (the subject/identifier the identity
    provider will present at login). Despite the bare operationId
    "CreateUser" on the endpoint this feeds
    (POST /open-id/connections/{connectionId}/users), this is NOT a generic
    "create any user" request body: its only OpenID-specific field,
    `roles`, accepts SystemRoles -- a fixed set of system-level roles
    (CoreAdmin/CwmAdmin/CwmUser/SecurityOfficer/CwmGuest) meaningful only at
    SSO pre-provisioning time. Confirmed against
    docs/api-analysis/upstream-semantics.md ("SystemRoles ... used only in
    OpenID pre-provisioning").
    """

    external_id: str = Field(alias="externalId")
    first_name: str | None = Field(default=None, alias="firstName")
    last_name: str | None = Field(default=None, alias="lastName")
    middle_name: str | None = Field(default=None, alias="middleName")
    user_name: str = Field(alias="userName")
    display_name: str = Field(alias="displayName")
    email: str
    roles: list[SystemRoles] | None = None
