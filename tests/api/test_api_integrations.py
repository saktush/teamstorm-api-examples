import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from teamstorm.api.integrations import GitIntegrationTokensAPI, OpenIdAPI
from teamstorm.models.integrations import (
    CreateOpenIdConnectionModel,
    CreateOpenIdUserModel,
    CreateTokenRequestBody,
    UpdateTokenRequestBody,
)
from teamstorm.models.enums import TokenType
from teamstorm.api import TeamStormAPI


def _user_payload(**overrides) -> dict:
    payload = {
        "id": str(uuid4()),
        "displayName": "Ada Lovelace",
        "username": "ada",
        "email": "ada@example.com",
    }
    payload.update(overrides)
    return payload


def _token_payload(**overrides) -> dict:
    payload = {
        "id": str(uuid4()),
        "name": "CI token",
        "url": "https://gitlab.example.com/group/repo.git",
        "createdAt": "2026-01-15T12:00:00Z",
        "updatedAt": None,
        "author": _user_payload(),
        "changedBy": None,
        "type": "GitLab",
    }
    payload.update(overrides)
    return payload


def _connection_payload(**overrides) -> dict:
    payload = {
        "id": str(uuid4()),
        "name": "Corporate SSO",
        "authority": "https://login.example.com",
        "isEnabled": True,
        "imageUrl": None,
    }
    payload.update(overrides)
    return payload


class GitIntegrationTokensAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = GitIntegrationTokensAPI(self.client)
        self.workspace = "WS"
        self.token_id = uuid4()

    def test_list_uses_plain_get_not_get_all_and_unwraps_tokens_key(self) -> None:
        self.client.get.return_value = {"tokens": [_token_payload(), _token_payload(name="Deploy token")]}

        result = self.api.list(self.workspace)

        self.client.get.assert_called_once_with(f"/workspaces/{self.workspace}/git-integration-tokens")
        self.client.get_all.assert_not_called()
        self.assertEqual(2, len(result))
        self.assertEqual("Deploy token", result[1].name)

    def test_get(self) -> None:
        self.client.get.return_value = _token_payload(id=str(self.token_id))

        result = self.api.get(self.workspace, token_id=self.token_id)

        self.client.get.assert_called_once_with(f"/workspaces/{self.workspace}/git-integration-tokens/{self.token_id}")
        self.assertEqual(self.token_id, result.id)

    def test_create_posts_body_and_returns_sensitive_data_model_with_secret(self) -> None:
        self.client.post.return_value = _token_payload(token="glpat-supersecretvalue")

        result = self.api.create(self.workspace, CreateTokenRequestBody(name="CI token", type=TokenType.GitLab))

        self.client.post.assert_called_once_with(
            f"/workspaces/{self.workspace}/git-integration-tokens",
            {"name": "CI token", "type": "GitLab"},
        )
        # SECURITY: this is the one and only time the secret is available.
        self.assertEqual("glpat-supersecretvalue", result.token)
        self.assertEqual("CI token", result.name)

    def test_update_uses_put_full_replace(self) -> None:
        self.client.put.return_value = _token_payload(id=str(self.token_id), name="Renamed token")

        result = self.api.update(
            self.workspace,
            token_id=self.token_id,
            body=UpdateTokenRequestBody(name="Renamed token"),
        )

        self.client.put.assert_called_once_with(
            f"/workspaces/{self.workspace}/git-integration-tokens/{self.token_id}",
            {"name": "Renamed token"},
        )
        self.assertEqual("Renamed token", result.name)
        # update() must never return a model exposing a secret field.
        self.assertFalse(hasattr(result, "token"))

    def test_refresh_is_a_body_less_put_and_returns_new_secret(self) -> None:
        self.client.put.return_value = _token_payload(id=str(self.token_id), token="glpat-brandnewsecret")

        result = self.api.refresh(self.workspace, token_id=self.token_id)

        self.client.put.assert_called_once_with(
            f"/workspaces/{self.workspace}/git-integration-tokens/{self.token_id}/refresh"
        )
        # SECURITY: refresh() is the other (only other) place the secret is ever returned.
        self.assertEqual("glpat-brandnewsecret", result.token)

    def test_delete(self) -> None:
        self.client.delete.return_value = None

        result = self.api.delete(self.workspace, token_id=self.token_id)

        self.client.delete.assert_called_once_with(
            f"/workspaces/{self.workspace}/git-integration-tokens/{self.token_id}"
        )
        self.assertIsNone(result)


class OpenIdAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = OpenIdAPI(self.client)
        self.connection_id = uuid4()

    def test_list_uses_plain_get_for_bare_array_response(self) -> None:
        self.client.get.return_value = [_connection_payload(), _connection_payload(name="Legacy SSO")]

        result = self.api.list()

        self.client.get.assert_called_once_with("/open-id/connections")
        self.client.get_all.assert_not_called()
        self.assertEqual(2, len(result))
        self.assertEqual("Legacy SSO", result[1].name)

    def test_create_posts_no_workspace_segment_and_returns_bare_uuid(self) -> None:
        new_id = uuid4()
        self.client.post.return_value = str(new_id)

        body = CreateOpenIdConnectionModel(
            name="Corporate SSO",
            authority="https://login.example.com",
            client_id="client-123",
            client_secret="super-secret",
            scope=["openid", "profile"],
            is_enabled=True,
        )
        result = self.api.create(body)

        self.client.post.assert_called_once_with(
            "/open-id/connections",
            {
                "name": "Corporate SSO",
                "authority": "https://login.example.com",
                "clientId": "client-123",
                "clientSecret": "super-secret",
                "scope": ["openid", "profile"],
                "isEnabled": True,
            },
        )
        self.assertEqual(new_id, result)

    def test_delete_has_no_workspace_segment(self) -> None:
        self.client.delete.return_value = None

        result = self.api.delete(self.connection_id)

        self.client.delete.assert_called_once_with(f"/open-id/connections/{self.connection_id}")
        self.assertIsNone(result)

    def test_create_user_pre_provisions_user_under_connection(self) -> None:
        self.client.post.return_value = _user_payload(username="ada")

        body = CreateOpenIdUserModel(
            external_id="sso-subject-123",
            user_name="ada",
            display_name="Ada Lovelace",
            email="ada@example.com",
        )
        result = self.api.create_user(self.connection_id, body)

        self.client.post.assert_called_once_with(
            f"/open-id/connections/{self.connection_id}/users",
            {
                "externalId": "sso-subject-123",
                "userName": "ada",
                "displayName": "Ada Lovelace",
                "email": "ada@example.com",
            },
        )
        self.assertEqual("ada", result.username)


class IntegrationsApiWiringTestCase(unittest.TestCase):
    def test_grouped_api_exposes_git_integration_tokens_and_open_id(self) -> None:
        client = MagicMock()
        api = TeamStormAPI(client)

        git_tokens = api.git_integration_tokens
        open_id = api.open_id

        self.assertIsInstance(git_tokens, GitIntegrationTokensAPI)
        self.assertIs(client, git_tokens.client)
        self.assertIsInstance(open_id, OpenIdAPI)
        self.assertIs(client, open_id.client)


if __name__ == "__main__":
    unittest.main()
