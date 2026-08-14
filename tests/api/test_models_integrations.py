import unittest
from uuid import uuid4

from pydantic import ValidationError

from teamstorm.models.enums import SystemRoles, TokenType
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


class TokenModelTestCase(unittest.TestCase):
    def test_round_trips_realistic_payload(self) -> None:
        payload = _token_payload()

        model = TokenModel.model_validate(payload)

        self.assertEqual(payload["id"], str(model.id))
        self.assertEqual("CI token", model.name)
        self.assertEqual("https://gitlab.example.com/group/repo.git", model.url)
        self.assertEqual("Ada Lovelace", model.author.display_name)
        self.assertIsNone(model.changed_by)
        self.assertIsNone(model.updated_at)
        self.assertEqual(TokenType.GitLab, model.type)

        dumped = model.model_dump()
        self.assertEqual("CI token", dumped["name"])
        self.assertEqual("GitLab", dumped["type"])
        self.assertNotIn("token", dumped)

    def test_updated_at_and_changed_by_can_be_populated(self) -> None:
        payload = _token_payload(
            updatedAt="2026-02-01T09:30:00Z",
            changedBy=_user_payload(username="bob"),
        )

        model = TokenModel.model_validate(payload)

        self.assertIsNotNone(model.updated_at)
        self.assertEqual("bob", model.changed_by.username)

    def test_extra_field_is_rejected(self) -> None:
        payload = _token_payload()
        payload["unexpectedField"] = "boom"
        with self.assertRaises(ValidationError):
            TokenModel.model_validate(payload)

    def test_missing_required_field_rejected(self) -> None:
        payload = _token_payload()
        del payload["url"]
        with self.assertRaises(ValidationError):
            TokenModel.model_validate(payload)

    def test_has_no_token_field(self) -> None:
        # The secret-less read model must never accept a "token" key --
        # that field only exists on TokenSensitiveDataModel.
        payload = _token_payload(token="should-not-be-accepted")
        with self.assertRaises(ValidationError):
            TokenModel.model_validate(payload)


class TokenSensitiveDataModelTestCase(unittest.TestCase):
    def test_round_trips_and_carries_secret(self) -> None:
        payload = _token_payload(token="glpat-supersecretvalue")

        model = TokenSensitiveDataModel.model_validate(payload)

        self.assertEqual("glpat-supersecretvalue", model.token)
        self.assertEqual("CI token", model.name)
        self.assertEqual(TokenType.GitLab, model.type)

        dumped = model.model_dump()
        self.assertEqual("glpat-supersecretvalue", dumped["token"])

    def test_missing_token_field_rejected(self) -> None:
        payload = _token_payload()
        with self.assertRaises(ValidationError):
            TokenSensitiveDataModel.model_validate(payload)


class TokensModelListTestCase(unittest.TestCase):
    def test_round_trips_tokens_envelope(self) -> None:
        payload = {"tokens": [_token_payload(), _token_payload(name="Deploy token")]}

        model = TokensModelList.model_validate(payload)

        self.assertEqual(2, len(model.tokens))
        self.assertEqual("Deploy token", model.tokens[1].name)

    def test_extra_field_is_rejected(self) -> None:
        payload = {"tokens": [], "unexpectedField": "boom"}
        with self.assertRaises(ValidationError):
            TokensModelList.model_validate(payload)


class CreateTokenRequestBodyTestCase(unittest.TestCase):
    def test_dump_contains_name_and_type(self) -> None:
        body = CreateTokenRequestBody(name="CI token", type=TokenType.GitFlic)

        dumped = body.model_dump(mode="json", exclude_none=True)

        self.assertEqual({"name": "CI token", "type": "GitFlic"}, dumped)


class UpdateTokenRequestBodyTestCase(unittest.TestCase):
    def test_dump_contains_only_name(self) -> None:
        body = UpdateTokenRequestBody(name="Renamed token")

        dumped = body.model_dump(mode="json", exclude_none=True)

        self.assertEqual({"name": "Renamed token"}, dumped)


class OpenIdConnectionModelTestCase(unittest.TestCase):
    def test_round_trips_realistic_payload(self) -> None:
        payload = {
            "id": str(uuid4()),
            "name": "Corporate SSO",
            "authority": "https://login.example.com",
            "isEnabled": True,
            "imageUrl": None,
        }

        model = OpenIdConnectionModel.model_validate(payload)

        self.assertEqual("Corporate SSO", model.name)
        self.assertTrue(model.is_enabled)
        self.assertIsNone(model.image_url)

    def test_extra_field_is_rejected(self) -> None:
        payload = {
            "id": str(uuid4()),
            "name": "Corporate SSO",
            "authority": "https://login.example.com",
            "isEnabled": True,
            "unexpectedField": "boom",
        }
        with self.assertRaises(ValidationError):
            OpenIdConnectionModel.model_validate(payload)


class CreateOpenIdConnectionModelTestCase(unittest.TestCase):
    def test_dump_uses_camel_case_aliases(self) -> None:
        body = CreateOpenIdConnectionModel(
            name="Corporate SSO",
            authority="https://login.example.com",
            client_id="client-123",
            client_secret="super-secret",
            scope=["openid", "profile", "email"],
            is_enabled=True,
        )

        dumped = body.model_dump(mode="json", exclude_none=True)

        self.assertEqual(
            {
                "name": "Corporate SSO",
                "authority": "https://login.example.com",
                "clientId": "client-123",
                "clientSecret": "super-secret",
                "scope": ["openid", "profile", "email"],
                "isEnabled": True,
            },
            dumped,
        )

    def test_metadata_address_is_optional_and_nullable(self) -> None:
        body = CreateOpenIdConnectionModel(
            name="Corporate SSO",
            authority="https://login.example.com",
            client_id="client-123",
            client_secret="super-secret",
            metadata_address="https://login.example.com/.well-known/openid-configuration",
            scope=["openid"],
            is_enabled=False,
        )

        dumped = body.model_dump(mode="json", exclude_none=True)

        self.assertEqual(
            "https://login.example.com/.well-known/openid-configuration",
            dumped["metadataAddress"],
        )


class CreateOpenIdUserModelTestCase(unittest.TestCase):
    def test_round_trips_with_roles(self) -> None:
        payload = {
            "externalId": "sso-subject-123",
            "firstName": "Ada",
            "lastName": "Lovelace",
            "middleName": None,
            "userName": "ada",
            "displayName": "Ada Lovelace",
            "email": "ada@example.com",
            "roles": ["CwmUser", "SecurityOfficer"],
        }

        model = CreateOpenIdUserModel.model_validate(payload)

        self.assertEqual("sso-subject-123", model.external_id)
        self.assertEqual([SystemRoles.CwmUser, SystemRoles.SecurityOfficer], model.roles)

        dumped = model.model_dump(mode="json", exclude_none=True)
        self.assertEqual("sso-subject-123", dumped["externalId"])
        self.assertEqual(["CwmUser", "SecurityOfficer"], dumped["roles"])

    def test_roles_and_optional_name_parts_are_optional(self) -> None:
        payload = {
            "externalId": "sso-subject-123",
            "userName": "ada",
            "displayName": "Ada Lovelace",
            "email": "ada@example.com",
        }

        model = CreateOpenIdUserModel.model_validate(payload)

        self.assertIsNone(model.roles)
        self.assertIsNone(model.first_name)

        dumped = model.model_dump(mode="json", exclude_none=True)
        self.assertNotIn("roles", dumped)
        self.assertNotIn("firstName", dumped)

    def test_extra_field_is_rejected(self) -> None:
        payload = {
            "externalId": "sso-subject-123",
            "userName": "ada",
            "displayName": "Ada Lovelace",
            "email": "ada@example.com",
            "unexpectedField": "boom",
        }
        with self.assertRaises(ValidationError):
            CreateOpenIdUserModel.model_validate(payload)


class TokenTypeEnumTestCase(unittest.TestCase):
    def test_enum_values_match_swagger(self) -> None:
        self.assertEqual(["GitLab", "GitFlic"], [member.value for member in TokenType])


class SystemRolesEnumTestCase(unittest.TestCase):
    def test_enum_values_match_swagger(self) -> None:
        self.assertEqual(
            ["CoreAdmin", "CwmAdmin", "CwmUser", "SecurityOfficer", "CwmGuest"],
            [member.value for member in SystemRoles],
        )


if __name__ == "__main__":
    unittest.main()
