# teamstorm/api/integrations.py
"""
Administrative integration surfaces: git integration tokens (workspace-
scoped) and OpenID Connect SSO connections (global).

10 ops total, split 6/4 across GitIntegrationTokensAPI (GitIntegrationTokens
tag, workspace-scoped -- every path carries a {workspace} segment) and
OpenIdAPI (OpenId tag, global -- no {workspace} segment on any /open-id/...
endpoint). Both scopings are confirmed directly against swagger.json; do not
assume otherwise from the tag name alone.

SECURITY -- git integration token secrets are returned ONLY ONCE, by
GitIntegrationTokensAPI.create() and .refresh() (see both methods'
docstrings). A caller who discards that response cannot recover the secret
through any other endpoint. Never log a response body or a `.token` field
from this module, and never log a CreateOpenIdConnectionModel dump (it
carries an OIDC client secret).
"""

from __future__ import annotations

from uuid import UUID

from pydantic import TypeAdapter

from teamstorm.api._base import BaseAPI
from teamstorm.models.common import UserModel
from teamstorm.models.integrations import (
    CreateOpenIdConnectionModel,
    CreateOpenIdUserModel,
    CreateTokenRequestBody,
    OpenIdConnectionModel,
    TokenModel,
    TokenSensitiveDataModel,
    TokensModelList,
    UpdateTokenRequestBody,
)


class GitIntegrationTokensAPI(BaseAPI):
    """
    Git integration tokens for a workspace: credentials CWM uses to talk to
    an external git host (GitLab/GitFlic) on the workspace's behalf.

    6 ops (GitIntegrationTokens tag): list, get, create, update, refresh,
    delete. Every path is workspace-scoped
    (/workspaces/{workspace}/git-integration-tokens...), confirmed directly
    against swagger.json.

    SECURITY: the actual secret token value is returned ONLY by create() and
    refresh() (as TokenSensitiveDataModel.token) -- every other read here
    (list, get) and update() return the secret-less TokenModel. There is no
    endpoint that returns a previously issued token's secret again. See
    create() and refresh() docstrings before building anything that might
    discard their response.
    """

    def list(self, workspace_key: str) -> list[TokenModel]:
        """
        List every git integration token configured for a workspace.

        workspace_key: workspace key or id.
        Returns: every TokenModel for the workspace (secret-less -- use
        create()/refresh() to obtain a token's actual secret value).
        GET /workspaces/{workspace}/git-integration-tokens.
        NOTE: response wraps items under a "tokens" key, not "items", and is
        not paginated (no fromToken/maxItemsCount/nextToken on this schema)
        -- uses a plain get(), not get_all().
        """
        data = self.client.get(f"/workspaces/{workspace_key}/git-integration-tokens")
        return TokensModelList.model_validate(data).tokens

    def get(self, workspace_key: str, *, token_id: UUID) -> TokenModel:
        """
        Get one git integration token's metadata.

        workspace_key: workspace key or id.
        token_id: token UUID (path segment).
        Returns: the TokenModel (secret-less).
        GET /workspaces/{workspace}/git-integration-tokens/{tokenId}.
        """
        data = self.client.get(f"/workspaces/{workspace_key}/git-integration-tokens/{token_id}")
        return TokenModel.model_validate(data)

    def create(self, workspace_key: str, body: CreateTokenRequestBody) -> TokenSensitiveDataModel:
        """
        Create a new git integration token for a workspace.

        SECURITY -- the response's `.token` field is the ONLY time this
        secret is ever returned by the server. GetToken/ListTokens/
        UpdateToken all return the secret-less TokenModel afterward, and
        there is no "reveal secret" endpoint. If the caller discards this
        response without persisting `.token` (e.g. into a secret store), the
        value is permanently unrecoverable -- the only remedies at that
        point are refresh() (which issues a brand-new secret, invalidating
        the old one) or delete-and-recreate. Never log this response body or
        the `.token` field.

        workspace_key: workspace key or id.
        body: token name and TokenType (GitLab/GitFlic).
        Returns: the created TokenSensitiveDataModel, including `.token`.
        POST /workspaces/{workspace}/git-integration-tokens.
        """
        payload = body.model_dump(mode="json", exclude_none=True)
        data = self.client.post(f"/workspaces/{workspace_key}/git-integration-tokens", payload)
        return TokenSensitiveDataModel.model_validate(data)

    def update(self, workspace_key: str, *, token_id: UUID, body: UpdateTokenRequestBody) -> TokenModel:
        """
        Rename an existing git integration token.

        This is a PUT (full replace, confirmed as the "put" verb in
        swagger.json), not a PATCH -- serialized with exclude_none=True, not
        exclude_unset. `name` is the only field UpdateTokenRequestBody
        defines, so "full replace" only ever means renaming the token; it
        never touches the secret.

        workspace_key: workspace key or id.
        token_id: token UUID (path segment).
        body: the new name.
        Returns: the updated TokenModel (secret-less).
        PUT /workspaces/{workspace}/git-integration-tokens/{tokenId}.
        """
        payload = body.model_dump(mode="json", exclude_none=True)
        data = self.client.put(f"/workspaces/{workspace_key}/git-integration-tokens/{token_id}", payload)
        return TokenModel.model_validate(data)

    def refresh(self, workspace_key: str, *, token_id: UUID) -> TokenSensitiveDataModel:
        """
        Issue a brand-new secret for an existing token (same token_id/name;
        the previous secret stops working immediately).

        SECURITY -- exactly like create(), the response's `.token` field is
        the ONLY time this new secret is ever returned. It cannot be
        fetched again afterward through GetToken/ListTokens (both return
        the secret-less TokenModel). Persist `.token` immediately, or the
        new secret is unrecoverable and the only remedy is to refresh again.
        Never log this response body or the `.token` field.

        workspace_key: workspace key or id.
        token_id: token UUID (path segment).
        Returns: the TokenSensitiveDataModel with the new `.token` value.
        PUT /workspaces/{workspace}/git-integration-tokens/{tokenId}/refresh.
        NOTE: body-less PUT -- no request payload is sent.
        """
        data = self.client.put(f"/workspaces/{workspace_key}/git-integration-tokens/{token_id}/refresh")
        return TokenSensitiveDataModel.model_validate(data)

    def delete(self, workspace_key: str, *, token_id: UUID) -> None:
        """
        Delete a git integration token, revoking its access immediately.

        workspace_key: workspace key or id.
        token_id: token UUID (path segment).
        Returns: None.
        DELETE /workspaces/{workspace}/git-integration-tokens/{tokenId}.
        """
        self.client.delete(f"/workspaces/{workspace_key}/git-integration-tokens/{token_id}")
        return None


class OpenIdAPI(BaseAPI):
    """
    OpenID Connect SSO connection administration.

    4 ops (OpenId tag): list, create, delete, create_user. GLOBAL resource
    -- no {workspace} path segment on any /open-id/... endpoint, confirmed
    directly against swagger.json (unlike GitIntegrationTokensAPI above,
    which IS workspace-scoped). Do not pass a workspace_key to any method
    here.
    """

    def list(self) -> list[OpenIdConnectionModel]:
        """
        List every OpenID Connect SSO connection configured on this CWM
        instance.

        Returns: every OpenIdConnectionModel. The response is a bare JSON
        array (no envelope, no pagination) -- uses a plain get(), not
        get_all().
        GET /open-id/connections.
        """
        data = self.client.get("/open-id/connections")
        return TypeAdapter(list[OpenIdConnectionModel]).validate_python(data)

    def create(self, body: CreateOpenIdConnectionModel) -> UUID:
        """
        Create a new OpenID Connect SSO connection.

        The request body carries the OIDC client secret (`clientSecret`) --
        never log this call's payload.

        body: connection name, authority, clientId/clientSecret, scope,
        isEnabled, and optional metadataAddress.
        Returns: the new connection's UUID. NOTE: unlike every other
        create() in this API wrapper, the response here is a bare JSON string (the
        id itself), not a model object -- confirmed in swagger.json, whose
        200 response schema for this operation is
        `{"type": "string", "format": "uuid"}`, not a $ref to a model.
        POST /open-id/connections.
        """
        payload = body.model_dump(mode="json", exclude_none=True)
        data = self.client.post("/open-id/connections", payload)
        return UUID(data)

    def delete(self, connection_id: UUID) -> None:
        """
        Delete an OpenID Connect SSO connection.

        connection_id: connection UUID (path segment).
        Returns: None.
        DELETE /open-id/connections/{connectionId}.
        """
        self.client.delete(f"/open-id/connections/{connection_id}")
        return None

    def create_user(self, connection_id: UUID, body: CreateOpenIdUserModel) -> UserModel:
        """
        Pre-provision a local CWM user account for this OpenID connection.

        Despite the bare operationId "CreateUser", this is NOT a generic
        user-creation endpoint: it registers a user record keyed by
        `body.external_id` (the subject the identity provider will present
        at login) ahead of that user's first SSO sign-in, optionally
        granting one or more SystemRoles up front. See
        CreateOpenIdUserModel's docstring (teamstorm/models/integrations.py) and
        docs/api-analysis/upstream-semantics.md ("SystemRoles ... used only
        in OpenID pre-provisioning").

        connection_id: the OpenID connection this user is pre-provisioned
        against (path segment).
        body: externalId/userName/displayName/email and optional
        firstName/lastName/middleName/roles.
        Returns: the created UserModel.
        POST /open-id/connections/{connectionId}/users.
        """
        payload = body.model_dump(mode="json", exclude_none=True)
        data = self.client.post(f"/open-id/connections/{connection_id}/users", payload)
        return UserModel.model_validate(data)
