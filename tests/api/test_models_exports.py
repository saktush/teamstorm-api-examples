import unittest

import teamstorm.models as models


class ModelsExportsTestCase(unittest.TestCase):
    def test_exports_include_new_symbols(self) -> None:
        expected = {
            # --- Tasks 1-5-ish: attributes/types/workflows/statuses/roles/groups ---
            "TypeColor",
            "TypeIcon",
            "ProgressType",
            "WorkflowType",
            "EstimatesType",
            "AttributeOptionModel",
            "AttributeModel",
            "AttributesModelList",
            "CreateAttributeOptionModel",
            "CreateAttributeOptionRequestBody",
            "PatchAttributeOptionModel",
            "PatchAttributeOptionRequestBody",
            "CreateAttributeRequestBody",
            "PatchAttributeRequestBody",
            "UpdateUserFieldValueModel",
            "UpdateUniStringFieldRequestBody",
            "UpdateNumberFieldRequestBody",
            "UpdateDateFieldRequestBody",
            "UpdateUniSelectFieldRequestBody",
            "UpdateTagFieldRequestBody",
            "UpdateUserFieldRequestBody",
            "UpdateTimeFieldRequestBody",
            "UpdateWorkitemAttributeRequestBody",
            "TypeModel",
            "TypeModelList",
            "CreateTypeRequestBody",
            "PatchTypeRequestBody",
            "TransitionModel",
            "CreateTransitionRequestBody",
            "PatchTransitionRequestBody",
            "WorkflowStatusModel",
            "WorkflowModel",
            "WorkflowModelList",
            "CreateWorkflowStatusRequestBody",
            "PatchWorkflowStatusRequestBody",
            "CreateWorkflowRequestBody",
            "PatchWorkflowRequestBody",
            "StatusCategoryModel",
            "StatusCategoryModelList",
            "StatusModel",
            "StatusModelList",
            "CreateStatusRequestBody",
            "Permission",
            "RoleModel",
            "RolesModelList",
            "SimpleRoleModel",
            "SimpleRoleModelList",
            "CreateRoleRequestBody",
            "PatchRoleRequestBody",
            "UsersModelList",
            "UserModelList",
            "GroupModel",
            "GroupModelList",
            # --- WorkitemLinks / LinkTypes ---
            "WorkitemLinkModel",
            "CreateWorkitemLinkRequestBody",
            "LinkTypeModel",
            "LinkTypeModelList",
            # --- Comments (Task 6): workitem + document ---
            "CommentModel",
            "CommentModelList",
            "CommentVisibilitySettingsModel",
            "CommentVisibilityType",
            "CreateCommentRequestBody",
            "UpdateCommentRequestBody",
            "UpdateCommentVisibilitySettingsRequestBody",
            "PrincipalModel",
            "PrincipalType",
            "UserPrincipalModel",
            "GroupPrincipalModel",
            "UpdateCommentPrincipalModel",
            # --- Documents core/versions/statuses ---
            "DocumentModel",
            "DocumentsModelList",
            "CreateDocumentRequestBody",
            "PatchDocumentRequestBody",
            "DocumentVersionModel",
            "DocumentVersionsModelList",
            "DocumentStatusModel",
            "DocumentsStatusModelList",
            # --- Document<->workitem links ---
            "CreateDocumentWorkitemLinkRequestBody",
            "DeleteDocumentWorkitemLinkRequestBody",
            # --- Sharing/permissions: workitem + document ---
            "SharedWorkitemPermission",
            "SharedWorkitemPermissionModel",
            "SharedWorkitemUserPermissionModel",
            "SharedWorkitemGroupPermissionModel",
            "CreateSharedWorkitemPermission",
            "CreateSharedWorkitemPermissionBody",
            "CreateSharedWorkitemUserPermissionBody",
            "CreateSharedWorkitemGroupPermissionBody",
            "PatchSharedWorkitemPermissionBody",
            "SharedDocumentPermission",
            "SharedDocumentPermissionModel",
            "SharedDocumentUserPermissionModel",
            "SharedDocumentGroupPermissionModel",
            "CreateSharedDocumentPermission",
            "CreateSharedDocumentPermissionBody",
            "CreateSharedDocumentUserPermissionBody",
            "CreateSharedDocumentGroupPermissionBody",
            "PatchSharedDocumentPermissionBody",
            "SharedItemAccessLevel",
            "SharedItemAccessType",
            # --- Portfolios & portfolio elements ---
            "PortfolioModel",
            "PortfolioModelList",
            "PortfolioThumbModel",
            "CreatePortfolioRequestBody",
            "PatchPortfolioRequestBody",
            "PortfolioElementModel",
            "PortfolioElementModelList",
            "PortfolioElementThumbModel",
            "CreatePortfolioElementRequestBody",
            "PatchPortfolioElementRequestBody",
            # --- Attachments: workitem + document ---
            "AttachmentModel",
            "AttachmentModelList",
            "AntivirusScanVerdict",
            # --- Time tracking & saved queries ---
            "TimeTrackingEntryModel",
            "TimeTrackingEntryTypeModel",
            "TimeTrackingModelList",
            "QueryVisibilitySettingsModel",
            "QueryVisibilityType",
            "UpdateQueryPrincipalModel",
            "UpdateQueryVisibilitySettingsRequestBody",
            # --- Git integration tokens & OpenID ---
            "TokenModel",
            "TokenSensitiveDataModel",
            "TokensModelList",
            "TokenType",
            "CreateTokenRequestBody",
            "UpdateTokenRequestBody",
            "OpenIdConnectionModel",
            "CreateOpenIdConnectionModel",
            "CreateOpenIdUserModel",
            # --- Providers ---
            "ProviderModel",
            "ProviderModelList",
            "ProviderType",
            # --- Folders / workitems misc ---
            "FolderModel",
            "CreateFolderRequestBody",
            "PatchFolderRequestBody",
            "WorkitemsCountModel",
            "WorkspaceModel",
            "ErrorModel",
            "OptionModel",
        }
        self.assertTrue(expected.issubset(set(models.__all__)))
        missing = expected - set(models.__all__)
        self.assertEqual(set(), missing, f"expected model symbols missing from teamstorm.models.__all__: {missing}")

    def test_exports_are_importable(self) -> None:
        for export_name in models.__all__:
            with self.subTest(export_name=export_name):
                self.assertTrue(hasattr(models, export_name))

    def test_update_attribute_value_request_body_is_attributes_one(self) -> None:
        self.assertEqual(
            "teamstorm.models.attributes",
            models.UpdateAttributeValueRequestBody.__module__,
        )

    def test_workitem_update_union_is_exported(self) -> None:
        self.assertIn("UpdateWorkitemAttributeRequestBody", models.__all__)
        self.assertTrue(hasattr(models, "UpdateWorkitemAttributeRequestBody"))

    def test_key_role_status_symbols_present(self) -> None:
        for name in (
            "Permission",
            "StatusCategoryModel",
            "RoleModel",
            "GroupModel",
            "TypeModel",
            "WorkflowModel",
        ):
            with self.subTest(name=name):
                self.assertIn(name, models.__all__)
                self.assertTrue(hasattr(models, name))

    def test_workitem_update_base_not_reexported(self) -> None:
        self.assertNotIn("UpdateAttributeValueRequestBodyWorkitem", models.__all__)


if __name__ == "__main__":
    unittest.main()
