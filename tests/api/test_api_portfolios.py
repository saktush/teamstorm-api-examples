import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from pydantic import ValidationError

from teamstorm.api.portfolios import PortfolioElementsAPI, PortfoliosAPI
from teamstorm.api import TeamStormAPI
from teamstorm.models.portfolios import (
    CreatePortfolioElementRequestBody,
    CreatePortfolioRequestBody,
    PatchPortfolioElementRequestBody,
    PatchPortfolioRequestBody,
    PortfolioElementModel,
    PortfolioModel,
)


def _folder_thumb() -> dict:
    return {"id": str(uuid4()), "name": "Roadmap"}


def _portfolio_element_thumb() -> dict:
    return {"id": str(uuid4()), "name": "Q3 Rollup"}


def _portfolio_payload(**overrides) -> dict:
    payload = {
        "id": str(uuid4()),
        "name": "Product Portfolio",
        "description": "All product initiatives",
        "folder": _folder_thumb(),
        "elements": [_portfolio_element_thumb()],
        "workflow": None,
    }
    payload.update(overrides)
    return payload


def _status_payload() -> dict:
    return {
        "id": str(uuid4()),
        "name": "In Progress",
        "category": {"id": str(uuid4()), "name": "Active"},
    }


def _user_payload() -> dict:
    return {
        "id": str(uuid4()),
        "displayName": "Jane Doe",
        "username": "jane",
        "email": "jane@example.com",
    }


def _portfolio_thumb() -> dict:
    return {"id": str(uuid4()), "name": "Product Portfolio"}


def _portfolio_element_payload(**overrides) -> dict:
    payload = {
        "id": str(uuid4()),
        "name": "Q3 Rollup",
        "description": "Q3 initiatives",
        "startDate": "2026-07-01T00:00:00Z",
        "endDate": "2026-09-30T00:00:00Z",
        "status": _status_payload(),
        "responsibles": [_user_payload()],
        "portfolio": _portfolio_thumb(),
    }
    payload.update(overrides)
    return payload


class PortfoliosAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = PortfoliosAPI(self.client)
        self.workspace = "WS"
        self.portfolio_id = uuid4()
        self.folder_id = uuid4()

    def test_list_uses_plain_get_and_unwraps_items(self) -> None:
        self.client.get.return_value = {"items": [_portfolio_payload()]}

        result = self.api.list(self.workspace, name="Product", folder_id=self.folder_id)

        self.client.get.assert_called_once_with(
            f"/workspaces/{self.workspace}/portfolios",
            params={"name": "Product", "folderId": str(self.folder_id)},
        )
        self.client.get_all.assert_not_called()
        self.assertEqual(1, len(result))
        self.assertIsInstance(result[0], PortfolioModel)
        self.assertEqual("Product Portfolio", result[0].name)

    def test_list_no_filters_passes_none_params(self) -> None:
        self.client.get.return_value = {"items": []}

        result = self.api.list(self.workspace)

        self.client.get.assert_called_once_with(
            f"/workspaces/{self.workspace}/portfolios",
            params=None,
        )
        self.assertEqual([], result)

    def test_list_validation_error_on_bad_payload(self) -> None:
        self.client.get.return_value = {"items": [{"id": str(uuid4())}]}
        with self.assertRaises(ValidationError):
            self.api.list(self.workspace)

    def test_get_exact_path(self) -> None:
        self.client.get.return_value = _portfolio_payload()

        result = self.api.get(self.workspace, portfolio_id=self.portfolio_id)

        self.client.get.assert_called_once_with(f"/workspaces/{self.workspace}/portfolios/{self.portfolio_id}")
        self.assertIsInstance(result, PortfolioModel)

    def test_create_posts_exact_path_and_body(self) -> None:
        self.client.post.return_value = _portfolio_payload()
        body = CreatePortfolioRequestBody(name="Product Portfolio", folder_id=self.folder_id)

        result = self.api.create(self.workspace, body)

        self.client.post.assert_called_once_with(
            f"/workspaces/{self.workspace}/portfolios",
            {"name": "Product Portfolio", "folderId": str(self.folder_id)},
        )
        self.assertEqual("Product Portfolio", result.name)

    def test_patch_is_rename_only_uses_exclude_unset(self) -> None:
        self.client.patch.return_value = _portfolio_payload(name="Renamed Portfolio")
        body = PatchPortfolioRequestBody(name="Renamed Portfolio")

        result = self.api.patch(self.workspace, portfolio_id=self.portfolio_id, body=body)

        self.client.patch.assert_called_once_with(
            f"/workspaces/{self.workspace}/portfolios/{self.portfolio_id}",
            {"name": "Renamed Portfolio"},
        )
        self.assertEqual("Renamed Portfolio", result.name)

    def test_patch_body_has_no_other_patchable_fields(self) -> None:
        # PatchPortfolioRequestBody only models `name` -- this is a rename,
        # not a general partial update. extra="forbid" means passing any
        # other field raises immediately.
        with self.assertRaises(ValidationError):
            PatchPortfolioRequestBody(name="X", description="not patchable")

    def test_delete_exact_path(self) -> None:
        self.client.delete.return_value = None

        result = self.api.delete(self.workspace, portfolio_id=self.portfolio_id)

        self.client.delete.assert_called_once_with(f"/workspaces/{self.workspace}/portfolios/{self.portfolio_id}")
        self.assertIsNone(result)


class PortfolioElementsAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.api = PortfolioElementsAPI(self.client)
        self.workspace = "WS"
        self.portfolio_element_id = uuid4()
        self.portfolio_id = uuid4()
        self.folder_id = uuid4()

    def test_list_uses_plain_get_and_unwraps_items(self) -> None:
        self.client.get.return_value = {"items": [_portfolio_element_payload()]}

        result = self.api.list(
            self.workspace,
            name="Rollup",
            folder_id=self.folder_id,
            portfolio_id=self.portfolio_id,
            status="InProgress",
        )

        self.client.get.assert_called_once_with(
            f"/workspaces/{self.workspace}/portfolio-elements",
            params={
                "name": "Rollup",
                "folderId": str(self.folder_id),
                "portfolioId": str(self.portfolio_id),
                "status": "InProgress",
            },
        )
        self.client.get_all.assert_not_called()
        self.assertEqual(1, len(result))
        self.assertIsInstance(result[0], PortfolioElementModel)
        self.assertEqual("Q3 Rollup", result[0].name)

    def test_list_validation_error_on_bad_payload(self) -> None:
        self.client.get.return_value = {"items": [{"id": str(uuid4())}]}
        with self.assertRaises(ValidationError):
            self.api.list(self.workspace)

    def test_get_exact_path(self) -> None:
        self.client.get.return_value = _portfolio_element_payload()

        result = self.api.get(self.workspace, portfolio_element_id=self.portfolio_element_id)

        self.client.get.assert_called_once_with(
            f"/workspaces/{self.workspace}/portfolio-elements/{self.portfolio_element_id}"
        )
        self.assertIsInstance(result, PortfolioElementModel)

    def test_create_posts_exact_path_and_body(self) -> None:
        self.client.post.return_value = _portfolio_element_payload()
        body = CreatePortfolioElementRequestBody(portfolio_id=self.portfolio_id, name="Q3 Rollup")

        result = self.api.create(self.workspace, body)

        self.client.post.assert_called_once_with(
            f"/workspaces/{self.workspace}/portfolio-elements",
            {"portfolioId": str(self.portfolio_id), "name": "Q3 Rollup"},
        )
        self.assertEqual("Q3 Rollup", result.name)

    def test_patch_is_genuine_partial_update_uses_exclude_unset(self) -> None:
        self.client.patch.return_value = _portfolio_element_payload(description=None)
        body = PatchPortfolioElementRequestBody(description=None)

        result = self.api.patch(
            self.workspace,
            portfolio_element_id=self.portfolio_element_id,
            body=body,
        )

        self.client.patch.assert_called_once_with(
            f"/workspaces/{self.workspace}/portfolio-elements/{self.portfolio_element_id}",
            {"description": None},
        )
        self.assertIsInstance(result, PortfolioElementModel)

    def test_patch_omits_unset_fields_entirely(self) -> None:
        self.client.patch.return_value = _portfolio_element_payload(name="Renamed")
        body = PatchPortfolioElementRequestBody(name="Renamed")

        self.api.patch(self.workspace, portfolio_element_id=self.portfolio_element_id, body=body)

        self.client.patch.assert_called_once_with(
            f"/workspaces/{self.workspace}/portfolio-elements/{self.portfolio_element_id}",
            {"name": "Renamed"},
        )

    def test_delete_exact_path(self) -> None:
        self.client.delete.return_value = None

        result = self.api.delete(self.workspace, portfolio_element_id=self.portfolio_element_id)

        self.client.delete.assert_called_once_with(
            f"/workspaces/{self.workspace}/portfolio-elements/{self.portfolio_element_id}"
        )
        self.assertIsNone(result)

    def test_link_workitem_posts_bodyless(self) -> None:
        self.client.post.return_value = _portfolio_element_payload()

        result = self.api.link_workitem(
            self.workspace,
            portfolio_element_id=self.portfolio_element_id,
            workitem_id="WS-42",
        )

        self.client.post.assert_called_once_with(
            f"/workspaces/{self.workspace}/portfolio-elements/{self.portfolio_element_id}/workitems/WS-42"
        )
        self.assertIsInstance(result, PortfolioElementModel)

    def test_unlink_workitem_exact_path(self) -> None:
        self.client.delete.return_value = None

        result = self.api.unlink_workitem(
            self.workspace,
            portfolio_element_id=self.portfolio_element_id,
            workitem_id="WS-42",
        )

        self.client.delete.assert_called_once_with(
            f"/workspaces/{self.workspace}/portfolio-elements/{self.portfolio_element_id}/workitems/WS-42"
        )
        self.assertIsNone(result)


class PortfolioModelsTestCase(unittest.TestCase):
    def test_portfolio_model_round_trips_realistic_payload(self) -> None:
        payload = _portfolio_payload()

        portfolio = PortfolioModel.model_validate(payload)

        self.assertEqual(payload["name"], portfolio.name)
        self.assertEqual(1, len(portfolio.elements))
        self.assertIsNone(portfolio.workflow)

    def test_portfolio_element_model_round_trips_realistic_payload(self) -> None:
        payload = _portfolio_element_payload()

        element = PortfolioElementModel.model_validate(payload)

        self.assertEqual(payload["name"], element.name)
        self.assertEqual("In Progress", element.status.name)
        self.assertEqual(1, len(element.responsibles))
        self.assertEqual("jane", element.responsibles[0].username)
        self.assertEqual("Product Portfolio", element.portfolio.name)

    def test_portfolio_extra_field_rejected(self) -> None:
        payload = _portfolio_payload()
        payload["unexpectedField"] = "boom"
        with self.assertRaises(ValidationError):
            PortfolioModel.model_validate(payload)

    def test_portfolio_element_extra_field_rejected(self) -> None:
        payload = _portfolio_element_payload()
        payload["unexpectedField"] = "boom"
        with self.assertRaises(ValidationError):
            PortfolioElementModel.model_validate(payload)


class PortfoliosApiWiringTestCase(unittest.TestCase):
    def test_grouped_api_exposes_portfolios_and_portfolio_elements(self) -> None:
        client = MagicMock()
        api = TeamStormAPI(client)

        portfolios = api.portfolios
        portfolio_elements = api.portfolio_elements

        self.assertIsInstance(portfolios, PortfoliosAPI)
        self.assertIs(client, portfolios.client)
        self.assertIsInstance(portfolio_elements, PortfolioElementsAPI)
        self.assertIs(client, portfolio_elements.client)


if __name__ == "__main__":
    unittest.main()
