import unittest
from unittest.mock import MagicMock

import teamstorm.api as api_pkg
from teamstorm.api.agile import AgileAPI
from teamstorm.api.attachments import DocumentAttachmentsAPI, WorkitemAttachmentsAPI
from teamstorm.api.attributes import AttributesAPI
from teamstorm.api.comments import DocumentCommentsAPI, WorkitemCommentsAPI
from teamstorm.api.documents import (
    DocumentsAPI,
    DocumentStatusesAPI,
    DocumentVersionsAPI,
    DocumentWorkitemLinksAPI,
)
from teamstorm.api.folders import FoldersAPI
from teamstorm.api.groups import GroupsAPI
from teamstorm.api.integrations import GitIntegrationTokensAPI, OpenIdAPI
from teamstorm.api.links import LinksAPI
from teamstorm.api.portfolios import PortfolioElementsAPI, PortfoliosAPI
from teamstorm.api.providers import ProvidersAPI
from teamstorm.api.queries import QueriesAPI
from teamstorm.api.roles import RolesAPI
from teamstorm.api.sharing import DocumentSharingAPI, WorkitemSharingAPI
from teamstorm.api.sprints import SprintsAPI
from teamstorm.api.statuses import StatusesAPI
from teamstorm.api.time_tracking import TimeTrackingAPI
from teamstorm.api.types import TypesAPI
from teamstorm.api.users import UsersAPI
from teamstorm.api.workflows import WorkflowsAPI
from teamstorm.api.workitems import WorkitemsAPI
from teamstorm.api.workspace_groups import WorkspaceGroupsAPI
from teamstorm.api.workspace_users import WorkspaceUsersAPI
from teamstorm.api.workspaces import WorkspacesAPI
from teamstorm.api import TeamStormAPI

# Every (TeamStormAPI property name, expected concrete *API class) pair. This
# is the full 32-property surface exported by teamstorm.api. This table pins
# every grouped resource, not just the ones added most recently.
ALL_API_PROPERTIES = (
    ("workspaces", WorkspacesAPI),
    ("folders", FoldersAPI),
    ("agile", AgileAPI),
    ("sprints", SprintsAPI),
    ("workitems", WorkitemsAPI),
    ("users", UsersAPI),
    ("types", TypesAPI),
    ("attributes", AttributesAPI),
    ("statuses", StatusesAPI),
    ("workflows", WorkflowsAPI),
    ("roles", RolesAPI),
    ("workspace_users", WorkspaceUsersAPI),
    ("workspace_groups", WorkspaceGroupsAPI),
    ("groups", GroupsAPI),
    ("providers", ProvidersAPI),
    ("links", LinksAPI),
    ("workitem_comments", WorkitemCommentsAPI),
    ("document_comments", DocumentCommentsAPI),
    ("documents", DocumentsAPI),
    ("document_versions", DocumentVersionsAPI),
    ("document_statuses", DocumentStatusesAPI),
    ("document_workitem_links", DocumentWorkitemLinksAPI),
    ("workitem_sharing", WorkitemSharingAPI),
    ("document_sharing", DocumentSharingAPI),
    ("portfolios", PortfoliosAPI),
    ("portfolio_elements", PortfolioElementsAPI),
    ("workitem_attachments", WorkitemAttachmentsAPI),
    ("document_attachments", DocumentAttachmentsAPI),
    ("time_tracking", TimeTrackingAPI),
    ("queries", QueriesAPI),
    ("git_integration_tokens", GitIntegrationTokensAPI),
    ("open_id", OpenIdAPI),
)

# Every concrete *API class name that must be re-exported from teamstorm.api.__all__.
ALL_API_CLASS_NAMES = {cls.__name__ for _, cls in ALL_API_PROPERTIES}


class ApiSurfaceTestCase(unittest.TestCase):
    def test_grouped_api_exposes_all_api_properties(self) -> None:
        """
        Every resource added across Tasks 1-13 must be reachable as a lazy
        TeamStormAPI property, returning an instance of the correct concrete
        *API class wrapping the exact same client used to construct TeamStormAPI.
        """
        client = MagicMock()
        api = TeamStormAPI(client)

        for property_name, expected_cls in ALL_API_PROPERTIES:
            with self.subTest(property_name=property_name):
                api_instance = getattr(api, property_name)
                self.assertIsInstance(api_instance, expected_cls)
                self.assertIs(client, api_instance.client)

    def test_api_package_exports_include_all_symbols(self) -> None:
        """
        Every concrete *API class registered on TeamStormAPI must also be a
        real, importable member of teamstorm.api.__all__ -- the two
        grouped entrypoint and package-export contracts must stay in lockstep.
        """
        self.assertTrue(ALL_API_CLASS_NAMES.issubset(set(api_pkg.__all__)))
        missing = ALL_API_CLASS_NAMES - set(api_pkg.__all__)
        self.assertEqual(set(), missing, f"expected API classes missing from teamstorm.api.__all__: {missing}")

        for export_name in ALL_API_CLASS_NAMES:
            with self.subTest(export_name=export_name):
                self.assertTrue(hasattr(api_pkg, export_name))


if __name__ == "__main__":
    unittest.main()
