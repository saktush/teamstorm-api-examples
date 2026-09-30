# CWM Python API wrapper — Operation Coverage

Full mapping of every CWM Public API spec operation (OpenAPI 3.0.4, `docs/openapi/swagger-v4.24.0.json`, 170 operations across 38 tags) to the concrete `teamstorm` API wrapper method that implements it.

**Status: 170/170 operations implemented (100%).** Verified by `tests/api/test_api_coverage.py`, which asserts the manifest in `tests/api/api_coverage_manifest.py` is both internally consistent and exactly equal, in both directions, to the operation set of the committed spec snapshot `docs/openapi/swagger-v4.24.0.json` -- no operation missing, no phantom entry.

This table is generated from that same manifest, so it cannot drift from what the coverage test actually checks.

How to read the "API wrapper method" column: `api_property.method(...)` -- `api_property` is the `TeamStormAPI` property (e.g. `api.workitems`), `method` is the method you call on the object it returns (e.g. `api.workitems.get(...)`).

## Summary by tag

| Tag | Ops | API wrapper class | Module |
|---|---|---|---|
| Agile | 4 | `AgileAPI` | `teamstorm/api/agile.py` |
| Attributes | 8 | `AttributesAPI` | `teamstorm/api/attributes.py` |
| DocumentAttachments | 9 | `DocumentAttachmentsAPI` | `teamstorm/api/attachments.py` |
| DocumentComments | 3 | `DocumentCommentsAPI` | `teamstorm/api/comments.py` |
| DocumentLinks | 4 | `DocumentWorkitemLinksAPI` | `teamstorm/api/documents.py` |
| DocumentVersions | 3 | `DocumentVersionsAPI` | `teamstorm/api/documents.py` |
| Documents | 7 | `DocumentsAPI` | `teamstorm/api/documents.py` |
| DocumentsSharing | 4 | `DocumentSharingAPI` | `teamstorm/api/sharing.py` |
| DocumentsStatuses | 2 | `DocumentStatusesAPI` | `teamstorm/api/documents.py` |
| Folders | 5 | `FoldersAPI` | `teamstorm/api/folders.py` |
| GitIntegrationTokens | 6 | `GitIntegrationTokensAPI` | `teamstorm/api/integrations.py` |
| LinkTypes | 1 | `LinksAPI` | `teamstorm/api/links.py` |
| OpenId | 4 | `OpenIdAPI` | `teamstorm/api/integrations.py` |
| PortfolioElements | 7 | `PortfolioElementsAPI` | `teamstorm/api/portfolios.py` |
| Portfolios | 5 | `PortfoliosAPI` | `teamstorm/api/portfolios.py` |
| Providers | 1 | `ProvidersAPI` | `teamstorm/api/providers.py` |
| Queries | 3 | `QueriesAPI` | `teamstorm/api/queries.py` |
| Roles | 5 | `RolesAPI` | `teamstorm/api/roles.py` |
| Sprints | 5 | `SprintsAPI` | `teamstorm/api/sprints.py` |
| StatusCategories | 1 | `StatusesAPI` | `teamstorm/api/statuses.py` |
| Statuses | 3 | `StatusesAPI` | `teamstorm/api/statuses.py` |
| TimeTracking | 2 | `TimeTrackingAPI` | `teamstorm/api/time_tracking.py` |
| Types | 7 | `TypesAPI` | `teamstorm/api/types.py` |
| UserGroups | 2 | `GroupsAPI` | `teamstorm/api/groups.py` |
| Users | 4 | `UsersAPI` | `teamstorm/api/users.py` |
| WorkCalendars | 1 | `WorkCalendarsAPI` | `teamstorm/api/work_calendars.py` |
| Workflows | 5 | `WorkflowsAPI` | `teamstorm/api/workflows.py` |
| WorkitemAttachments | 9 | `WorkitemAttachmentsAPI` | `teamstorm/api/attachments.py` |
| WorkitemAttributes | 2 | `WorkitemsAPI` | `teamstorm/api/workitems.py` |
| WorkitemComments | 6 | `WorkitemCommentsAPI` | `teamstorm/api/comments.py` |
| WorkitemLinks | 3 | `LinksAPI` | `teamstorm/api/links.py` |
| WorkitemTimeMetricTemplates | 1 | `WorkitemTimeMetricTemplatesAPI` | `teamstorm/api/time_metrics.py` |
| WorkitemTimeMetrics | 9 | `WorkitemTimeMetricsAPI` | `teamstorm/api/time_metrics.py` |
| Workitems | 8 | `WorkitemsAPI` | `teamstorm/api/workitems.py` |
| WorkitemsSharing | 4 | `WorkitemSharingAPI` | `teamstorm/api/sharing.py` |
| WorkspaceGroups | 6 | `WorkspaceGroupsAPI` | `teamstorm/api/workspace_groups.py` |
| WorkspaceUsers | 6 | `WorkspaceUsersAPI` | `teamstorm/api/workspace_users.py` |
| Workspaces | 5 | `WorkspacesAPI` | `teamstorm/api/workspaces.py` |
| **TOTAL** | **170** | | |

Tag count: 38. Operation count: 170 / 170.

## Full operation table

### Agile (4 ops)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| POST | `/workspaces/{workspace}/agile` | CreateAgile | `api.agile.create(...)` |
| GET | `/workspaces/{workspace}/agile/list` | GetAgileExtensions | `api.agile.list(...)` |
| DELETE | `/workspaces/{workspace}/agile/{agileId}` | DeleteAgile | `api.agile.delete(...)` |
| GET | `/workspaces/{workspace}/agile/{agileId}` | GetAgile | `api.agile.get(...)` |

### Attributes (8 ops)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| GET | `/workspaces/{workspace}/attributes` | ListAttributes | `api.attributes.list(...)` |
| POST | `/workspaces/{workspace}/attributes` | CreateAttribute | `api.attributes.create(...)` |
| DELETE | `/workspaces/{workspace}/attributes/{attributeId}` | DeleteAttribute | `api.attributes.delete(...)` |
| GET | `/workspaces/{workspace}/attributes/{attributeId}` | GetAttribute | `api.attributes.get(...)` |
| PATCH | `/workspaces/{workspace}/attributes/{attributeId}` | PatchAttribute | `api.attributes.patch(...)` |
| PATCH | `/workspaces/{workspace}/attributes/{attributeId}/options` | PatchAttributeOption | `api.attributes.patch_option(...)` |
| POST | `/workspaces/{workspace}/attributes/{attributeId}/options` | AddAttributeOption | `api.attributes.add_option(...)` |
| DELETE | `/workspaces/{workspace}/attributes/{attributeId}/options/{optionId}` | DeleteAttributeOption | `api.attributes.delete_option(...)` |

### DocumentAttachments (9 ops)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| DELETE | `/workspaces/{workspace}/documents/{document}/attachments` | DeleteDocumentAttachments | `api.document_attachments.delete_all(...)` |
| GET | `/workspaces/{workspace}/documents/{document}/attachments` | GetDocumentAttachments | `api.document_attachments.list(...)` |
| GET | `/workspaces/{workspace}/documents/{document}/attachments/versions` | GetDocumentAttachmentsWithVersions | `api.document_attachments.list_versions(...)` |
| DELETE | `/workspaces/{workspace}/documents/{document}/attachments/{attachmentId}` | DeleteDocumentAttachment | `api.document_attachments.delete(...)` |
| GET | `/workspaces/{workspace}/documents/{document}/attachments/{attachmentId}` | GetDocumentAttachment | `api.document_attachments.get(...)` |
| GET | `/workspaces/{workspace}/documents/{document}/attachments/{attachmentId}/download` | DownloadDocumentAttachments | `api.document_attachments.download(...)` |
| POST | `/workspaces/{workspace}/documents/{document}/attachments/{attachmentId}/upload` | UploadDocumentAttachments | `api.document_attachments.upload(...)` |
| DELETE | `/workspaces/{workspace}/documents/{document}/attachments/{attachmentId}/versions/{attachmentVersion}` | DeleteDocumentAttachmentVersion | `api.document_attachments.delete_version(...)` |
| GET | `/workspaces/{workspace}/documents/{document}/attachments/{attachmentId}/versions/{attachmentVersion}` | GetDocumentAttachmentWithVersions | `api.document_attachments.get_version(...)` |

### DocumentComments (3 ops)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| GET | `/workspaces/{workspace}/documents/{document}/comments` | ListDocumentComments | `api.document_comments.list(...)` |
| POST | `/workspaces/{workspace}/documents/{document}/comments` | CreateDocumentComment | `api.document_comments.create(...)` |
| DELETE | `/workspaces/{workspace}/documents/{document}/comments/{commentId}` | DeleteDocumentComment | `api.document_comments.delete(...)` |

### DocumentLinks (4 ops)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| DELETE | `/workspaces/{workspace}/documents/{document}/workitem-links` | DeleteDocumentWorkitemLink | `api.document_workitem_links.delete(...)` |
| GET | `/workspaces/{workspace}/documents/{document}/workitem-links` | GetDocumentWorkitemLinks | `api.document_workitem_links.list(...)` |
| POST | `/workspaces/{workspace}/documents/{document}/workitem-links` | CreateDocumentWorkitemLink | `api.document_workitem_links.create(...)` |
| GET | `/workspaces/{workspace}/workitems/{workitem}/document-links` | GetWorkitemDocumentLinks | `api.document_workitem_links.list_by_workitem(...)` |

### DocumentVersions (3 ops)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| GET | `/workspaces/{workspace}/documents/{document}/versions` | ListDocumentVersions | `api.document_versions.list(...)` |
| DELETE | `/workspaces/{workspace}/documents/{document}/versions/{documentVersion}` | DeleteDocumentVersion | `api.document_versions.delete(...)` |
| GET | `/workspaces/{workspace}/documents/{document}/versions/{documentVersion}` | GetDocumentByVersion | `api.document_versions.get(...)` |

### Documents (7 ops)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| GET | `/workspaces/{workspace}/documents` | ListDocuments | `api.documents.list(...)` |
| POST | `/workspaces/{workspace}/documents` | CreateDocument | `api.documents.create(...)` |
| DELETE | `/workspaces/{workspace}/documents/{document}` | DeleteDocument | `api.documents.delete(...)` |
| GET | `/workspaces/{workspace}/documents/{document}` | GetDocument | `api.documents.get(...)` |
| PATCH | `/workspaces/{workspace}/documents/{document}` | PatchDocument | `api.documents.patch(...)` |
| POST | `/workspaces/{workspace}/documents/{document}/block` | BlockDocument | `api.documents.block(...)` |
| POST | `/workspaces/{workspace}/documents/{document}/unblock` | UnblockDocument | `api.documents.unblock(...)` |

### DocumentsSharing (4 ops)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| GET | `/workspaces/{workspace}/documents/{document}/sharing` | ListSharedDocumentPermissions | `api.document_sharing.list(...)` |
| POST | `/workspaces/{workspace}/documents/{document}/sharing` | CreateSharedDocumentPermission | `api.document_sharing.create(...)` |
| DELETE | `/workspaces/{workspace}/documents/{document}/sharing/{permissionId}` | DeleteSharedDocumentPermission | `api.document_sharing.delete(...)` |
| PATCH | `/workspaces/{workspace}/documents/{document}/sharing/{permissionId}` | PatchSharedDocumentPermission | `api.document_sharing.patch(...)` |

### DocumentsStatuses (2 ops)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| GET | `/workspaces/{workspace}/documents-statuses` | ListDocumentStatuses | `api.document_statuses.list(...)` |
| GET | `/workspaces/{workspace}/documents-statuses/{status}` | GetDocumentsStatus | `api.document_statuses.get(...)` |

### Folders (5 ops)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| GET | `/workspaces/{workspace}/folders` | ListFolders | `api.folders.list(...)` |
| POST | `/workspaces/{workspace}/folders` | CreateFolder | `api.folders.create(...)` |
| DELETE | `/workspaces/{workspace}/folders/{folderId}` | DeleteFolder | `api.folders.delete(...)` |
| GET | `/workspaces/{workspace}/folders/{folderId}` | GetFolder | `api.folders.get(...)` |
| PATCH | `/workspaces/{workspace}/folders/{folderId}` | PatchFolder | `api.folders.patch(...)` |

### GitIntegrationTokens (6 ops)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| GET | `/workspaces/{workspace}/git-integration-tokens` | ListTokens | `api.git_integration_tokens.list(...)` |
| POST | `/workspaces/{workspace}/git-integration-tokens` | CreateToken | `api.git_integration_tokens.create(...)` |
| DELETE | `/workspaces/{workspace}/git-integration-tokens/{tokenId}` | DeleteTokenAsync | `api.git_integration_tokens.delete(...)` |
| GET | `/workspaces/{workspace}/git-integration-tokens/{tokenId}` | GetToken | `api.git_integration_tokens.get(...)` |
| PUT | `/workspaces/{workspace}/git-integration-tokens/{tokenId}` | UpdateToken | `api.git_integration_tokens.update(...)` |
| PUT | `/workspaces/{workspace}/git-integration-tokens/{tokenId}/refresh` | RefreshToken | `api.git_integration_tokens.refresh(...)` |

### LinkTypes (1 op)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| GET | `/workspaces/{workspace}/link-types` | ListLinkTypes | `api.links.list_types(...)` |

### OpenId (4 ops)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| GET | `/open-id/connections` | GetConnections | `api.open_id.list(...)` |
| POST | `/open-id/connections` | CreateConnection | `api.open_id.create(...)` |
| DELETE | `/open-id/connections/{connectionId}` | DeleteConnection | `api.open_id.delete(...)` |
| POST | `/open-id/connections/{connectionId}/users` | CreateUser | `api.open_id.create_user(...)` |

### PortfolioElements (7 ops)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| GET | `/workspaces/{workspace}/portfolio-elements` | ListPortfolioElements | `api.portfolio_elements.list(...)` |
| POST | `/workspaces/{workspace}/portfolio-elements` | *(none in spec)* | `api.portfolio_elements.create(...)` |
| DELETE | `/workspaces/{workspace}/portfolio-elements/{portfolioElementId}` | *(none in spec)* | `api.portfolio_elements.delete(...)` |
| GET | `/workspaces/{workspace}/portfolio-elements/{portfolioElementId}` | GetPortfolioElement | `api.portfolio_elements.get(...)` |
| PATCH | `/workspaces/{workspace}/portfolio-elements/{portfolioElementId}` | *(none in spec)* | `api.portfolio_elements.patch(...)` |
| DELETE | `/workspaces/{workspace}/portfolio-elements/{portfolioElementId}/workitems/{workitem}` | *(none in spec)* | `api.portfolio_elements.unlink_workitem(...)` |
| POST | `/workspaces/{workspace}/portfolio-elements/{portfolioElementId}/workitems/{workitem}` | *(none in spec)* | `api.portfolio_elements.link_workitem(...)` |

### Portfolios (5 ops)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| GET | `/workspaces/{workspace}/portfolios` | ListPortfolios | `api.portfolios.list(...)` |
| POST | `/workspaces/{workspace}/portfolios` | *(none in spec)* | `api.portfolios.create(...)` |
| DELETE | `/workspaces/{workspace}/portfolios/{portfolioId}` | *(none in spec)* | `api.portfolios.delete(...)` |
| GET | `/workspaces/{workspace}/portfolios/{portfolioId}` | GetPortfolio | `api.portfolios.get(...)` |
| PATCH | `/workspaces/{workspace}/portfolios/{portfolioId}` | *(none in spec)* | `api.portfolios.patch(...)` |

### Providers (1 op)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| GET | `/providers` | GetProviders | `api.providers.list(...)` |

### Queries (3 ops)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| GET | `/queries/{queryId}/workitems` | ListQueryWorkitems | `api.queries.list_workitems(...)` |
| GET | `/workspaces/{workspace}/queries/{queryId}/visibility` | GetQueryVisibilitySettings | `api.queries.get_visibility(...)` |
| PUT | `/workspaces/{workspace}/queries/{queryId}/visibility` | UpdateQueryVisibilitySettings | `api.queries.update_visibility(...)` |

### Roles (5 ops)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| GET | `/workspaces/{workspace}/roles` | ListRoles | `api.roles.list(...)` |
| POST | `/workspaces/{workspace}/roles` | CreateRole | `api.roles.create(...)` |
| DELETE | `/workspaces/{workspace}/roles/{roleId}` | DeleteRole | `api.roles.delete(...)` |
| GET | `/workspaces/{workspace}/roles/{roleId}` | GetRole | `api.roles.get(...)` |
| PATCH | `/workspaces/{workspace}/roles/{roleId}` | PatchRole | `api.roles.patch(...)` |

### Sprints (5 ops)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| GET | `/workspaces/{workspace}/sprints` | ListSprints | `api.sprints.list(...)` |
| POST | `/workspaces/{workspace}/sprints` | CreateSprint | `api.sprints.create(...)` |
| DELETE | `/workspaces/{workspace}/sprints/{sprintId}` | DeleteSprint | `api.sprints.delete(...)` |
| GET | `/workspaces/{workspace}/sprints/{sprintId}` | GetSprint | `api.sprints.get(...)` |
| PATCH | `/workspaces/{workspace}/sprints/{sprintId}` | PatchSprint | `api.sprints.patch(...)` |

### StatusCategories (1 op)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| GET | `/status-categories` | ListStatusCategories | `api.statuses.list_categories(...)` |

### Statuses (3 ops)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| GET | `/workspaces/{workspace}/statuses` | ListStatuses | `api.statuses.list(...)` |
| POST | `/workspaces/{workspace}/statuses` | CreateStatus | `api.statuses.create(...)` |
| GET | `/workspaces/{workspace}/statuses/{status}` | GetStatus | `api.statuses.get(...)` |

### TimeTracking (2 ops)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| GET | `/workspaces/time-tracking-entries` | GetTimeTrackingEntries | `api.time_tracking.list(...)` |
| GET | `/workspaces/time-tracking-entries/updates` | GetTimeTrackingEntriesUpdates | `api.time_tracking.list_updates(...)` |

### Types (7 ops)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| GET | `/workspaces/{workspace}/types` | ListTypes | `api.types.list(...)` |
| POST | `/workspaces/{workspace}/types` | CreateType | `api.types.create(...)` |
| DELETE | `/workspaces/{workspace}/types/{type}` | DeleteType | `api.types.delete(...)` |
| GET | `/workspaces/{workspace}/types/{type}` | GetType | `api.types.get(...)` |
| PATCH | `/workspaces/{workspace}/types/{type}` | PatchType | `api.types.patch(...)` |
| DELETE | `/workspaces/{workspace}/types/{type}/attributes/{attributeId}` | DeleteTypeAttribute | `api.types.remove_attribute(...)` |
| POST | `/workspaces/{workspace}/types/{type}/attributes/{attributeId}` | AddTypeAttribute | `api.types.add_attribute(...)` |

### UserGroups (2 ops)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| GET | `/user-groups` | ListUserGroups | `api.groups.list(...)` |
| GET | `/user-groups/{group}` | GetUserGroup | `api.groups.get(...)` |

### Users (4 ops)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| GET | `/users` | ListUsers | `api.users.list(...)` |
| POST | `/users/block/{userId}` | BlockUser | `api.users.block(...)` |
| POST | `/users/unblock/{userId}` | UnblockUser | `api.users.unblock(...)` |
| GET | `/users/{user}` | GetUser | `api.users.get(...)` |

### WorkCalendars (1 op)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| GET | `/work-calendars` | GetWorkCalendars | `api.work_calendars.list(...)` |

### Workflows (5 ops)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| GET | `/workspaces/{workspace}/workflows` | ListWorkflows | `api.workflows.list(...)` |
| POST | `/workspaces/{workspace}/workflows` | CreateWorkflow | `api.workflows.create(...)` |
| DELETE | `/workspaces/{workspace}/workflows/{workflow}` | DeleteWorkflow | `api.workflows.delete(...)` |
| GET | `/workspaces/{workspace}/workflows/{workflow}` | GetWorkflow | `api.workflows.get(...)` |
| PATCH | `/workspaces/{workspace}/workflows/{workflow}` | PatchWorkflow | `api.workflows.patch(...)` |

### WorkitemAttachments (9 ops)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| DELETE | `/workspaces/{workspace}/workitems/{workitem}/attachments` | DeleteWorkitemAttachments | `api.workitem_attachments.delete_all(...)` |
| GET | `/workspaces/{workspace}/workitems/{workitem}/attachments` | GetWorkitemAttachments | `api.workitem_attachments.list(...)` |
| GET | `/workspaces/{workspace}/workitems/{workitem}/attachments/versions` | GetWorkitemAttachmentsWithVersions | `api.workitem_attachments.list_versions(...)` |
| DELETE | `/workspaces/{workspace}/workitems/{workitem}/attachments/{attachmentId}` | DeleteWorkitemAttachment | `api.workitem_attachments.delete(...)` |
| GET | `/workspaces/{workspace}/workitems/{workitem}/attachments/{attachmentId}` | GetWorkitemAttachment | `api.workitem_attachments.get(...)` |
| GET | `/workspaces/{workspace}/workitems/{workitem}/attachments/{attachmentId}/download` | DownloadWorkitemAttachments | `api.workitem_attachments.download(...)` |
| POST | `/workspaces/{workspace}/workitems/{workitem}/attachments/{attachmentId}/upload` | UploadWorkitemAttachments | `api.workitem_attachments.upload(...)` |
| DELETE | `/workspaces/{workspace}/workitems/{workitem}/attachments/{attachmentId}/versions/{attachmentVersion}` | DeleteWorkitemAttachmentVersion | `api.workitem_attachments.delete_version(...)` |
| GET | `/workspaces/{workspace}/workitems/{workitem}/attachments/{attachmentId}/versions/{attachmentVersion}` | GetWorkitemAttachmentWithVersions | `api.workitem_attachments.get_version(...)` |

### WorkitemAttributes (2 ops)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| GET | `/workspaces/{workspace}/workitems/{workitem}/attributes` | ListWorkitemAttributes | `api.workitems.list_attributes(...)` |
| PUT | `/workspaces/{workspace}/workitems/{workitem}/attributes/{attributeId}` | UpdateWorkitemAttribute | `api.workitems.update_attribute(...)` |

### WorkitemComments (6 ops)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| GET | `/workspaces/{workspace}/workitems/{workitem}/comments` | ListWorkitemComments | `api.workitem_comments.list(...)` |
| POST | `/workspaces/{workspace}/workitems/{workitem}/comments` | CreateWorkitemComment | `api.workitem_comments.create(...)` |
| DELETE | `/workspaces/{workspace}/workitems/{workitem}/comments/{commentId}` | DeleteWorkitemComment | `api.workitem_comments.delete(...)` |
| PUT | `/workspaces/{workspace}/workitems/{workitem}/comments/{commentId}` | UpdateWorkitemComment | `api.workitem_comments.update(...)` |
| GET | `/workspaces/{workspace}/workitems/{workitem}/comments/{commentId}/visibility` | GetWorkitemCommentVisibilitySettings | `api.workitem_comments.get_visibility(...)` |
| PUT | `/workspaces/{workspace}/workitems/{workitem}/comments/{commentId}/visibility` | UpdateWorkitemCommentVisibilitySettings | `api.workitem_comments.update_visibility(...)` |

### WorkitemLinks (3 ops)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| DELETE | `/workspaces/{workspace}/links/{linkId}` | DeleteWorkitemLink | `api.links.delete(...)` |
| GET | `/workspaces/{workspace}/workitems/{workitem}/links` | ListWorkitemLinks | `api.links.list(...)` |
| POST | `/workspaces/{workspace}/workitems/{workitem}/links` | CreateWorkitemLink | `api.links.create(...)` |

### WorkitemTimeMetricTemplates (1 op)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| GET | `/workspaces/{workspace}/workitem-metric-templates` | GetWorkitemTimeMetricTemplates | `api.workitem_metric_templates.list(...)` |

### WorkitemTimeMetrics (9 ops)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| GET | `/workspaces/{workspace}/workitems/{workitem}/workitem-time-metrics` | GetWorkitemTimeMetrics | `api.workitem_time_metrics.list(...)` |
| POST | `/workspaces/{workspace}/workitems/{workitem}/workitem-time-metrics/enable` | EnableWorkitemTimeMetric | `api.workitem_time_metrics.enable(...)` |
| GET | `/workspaces/{workspace}/workitems/{workitem}/workitem-time-metrics/{metricId}` | GetWorkitemTimeMetric | `api.workitem_time_metrics.get(...)` |
| PATCH | `/workspaces/{workspace}/workitems/{workitem}/workitem-time-metrics/{metricId}` | UpdateWorkitemTimeMetricSettings | `api.workitem_time_metrics.update(...)` |
| POST | `/workspaces/{workspace}/workitems/{workitem}/workitem-time-metrics/{metricId}/disable` | DisableWorkitemTimeMetric | `api.workitem_time_metrics.disable(...)` |
| POST | `/workspaces/{workspace}/workitems/{workitem}/workitem-time-metrics/{metricId}/pause` | PauseWorkitemTimeMetric | `api.workitem_time_metrics.pause(...)` |
| POST | `/workspaces/{workspace}/workitems/{workitem}/workitem-time-metrics/{metricId}/resume` | ResumeWorkitemTimeMetric | `api.workitem_time_metrics.resume(...)` |
| POST | `/workspaces/{workspace}/workitems/{workitem}/workitem-time-metrics/{metricId}/start` | StartWorkitemTimeMetric | `api.workitem_time_metrics.start(...)` |
| POST | `/workspaces/{workspace}/workitems/{workitem}/workitem-time-metrics/{metricId}/stop` | StopWorkitemTimeMetric | `api.workitem_time_metrics.stop(...)` |

### Workitems (8 ops)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| GET | `/workspaces/{workspace}/workitems` | ListWorkitems | `api.workitems.list(...)` |
| POST | `/workspaces/{workspace}/workitems` | CreateWorkitem | `api.workitems.create(...)` |
| GET | `/workspaces/{workspace}/workitems/by-parent/{parent}` | ListWorkitemsByParent | `api.workitems.list_by_parent(...)` |
| GET | `/workspaces/{workspace}/workitems/count` | GetWorkitemsCount | `api.workitems.count(...)` |
| GET | `/workspaces/{workspace}/workitems/updates` | ListWorkitemsUpdates | `api.workitems.list_updates(...)` |
| DELETE | `/workspaces/{workspace}/workitems/{workitem}` | DeleteWorkitem | `api.workitems.delete(...)` |
| GET | `/workspaces/{workspace}/workitems/{workitem}` | GetWorkitemById | `api.workitems.get(...)` |
| PATCH | `/workspaces/{workspace}/workitems/{workitem}` | PatchWorkitem | `api.workitems.patch(...)` |

### WorkitemsSharing (4 ops)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| GET | `/workspaces/{workspace}/workitems/{workitem}/sharing` | ListSharedWorkitemPermissions | `api.workitem_sharing.list(...)` |
| POST | `/workspaces/{workspace}/workitems/{workitem}/sharing` | CreateSharedWorkitemPermission | `api.workitem_sharing.create(...)` |
| DELETE | `/workspaces/{workspace}/workitems/{workitem}/sharing/{permissionId}` | DeleteSharedWorkitemPermission | `api.workitem_sharing.delete(...)` |
| PATCH | `/workspaces/{workspace}/workitems/{workitem}/sharing/{permissionId}` | PatchSharedWorkitemPermission | `api.workitem_sharing.patch(...)` |

### WorkspaceGroups (6 ops)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| GET | `/workspaces/{workspace}/groups` | FilterWorkspaceUsers | `api.workspace_groups.list(...)` |
| DELETE | `/workspaces/{workspace}/groups/{groupId}` | RemoveWorkspaceGroup | `api.workspace_groups.remove(...)` |
| POST | `/workspaces/{workspace}/groups/{groupId}` | AddWorkspaceGroup | `api.workspace_groups.add(...)` |
| GET | `/workspaces/{workspace}/groups/{groupId}/roles` | GetGroupRoles | `api.workspace_groups.get_roles(...)` |
| DELETE | `/workspaces/{workspace}/groups/{groupId}/roles/{roleId}` | RemoveRoleForGroup | `api.workspace_groups.remove_role(...)` |
| POST | `/workspaces/{workspace}/groups/{groupId}/roles/{roleId}` | AddGroupRole | `api.workspace_groups.add_role(...)` |

### WorkspaceUsers (6 ops)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| GET | `/workspaces/{workspace}/users` | GetWorkspaceUsers | `api.workspace_users.list(...)` |
| DELETE | `/workspaces/{workspace}/users/{userId}` | RemoveWorkspaceUser | `api.workspace_users.remove(...)` |
| POST | `/workspaces/{workspace}/users/{userId}` | AddWorkspaceUser | `api.workspace_users.add(...)` |
| GET | `/workspaces/{workspace}/users/{userId}/roles` | GetUserRoles | `api.workspace_users.get_roles(...)` |
| DELETE | `/workspaces/{workspace}/users/{userId}/roles/{roleId}` | RemoveRoleForUser | `api.workspace_users.remove_role(...)` |
| POST | `/workspaces/{workspace}/users/{userId}/roles/{roleId}` | AddUserRole | `api.workspace_users.add_role(...)` |

### Workspaces (5 ops)

| HTTP | Path | operationId | API wrapper method |
|---|---|---|---|
| GET | `/workspaces` | ListWorkspaces | `api.workspaces.list(...)` |
| POST | `/workspaces` | CreateWorkspace | `api.workspaces.create(...)` |
| DELETE | `/workspaces/{workspace}` | DeleteWorkspace | `api.workspaces.delete(...)` |
| GET | `/workspaces/{workspace}` | GetWorkspace | `api.workspaces.get(...)` |
| PATCH | `/workspaces/{workspace}` | PatchWorkspace | `api.workspaces.patch(...)` |

