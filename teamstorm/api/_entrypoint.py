from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from teamstorm.client import TsClient

if TYPE_CHECKING:
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
    from teamstorm.api.time_metrics import WorkitemTimeMetricsAPI, WorkitemTimeMetricTemplatesAPI
    from teamstorm.api.time_tracking import TimeTrackingAPI
    from teamstorm.api.types import TypesAPI
    from teamstorm.api.users import UsersAPI
    from teamstorm.api.work_calendars import WorkCalendarsAPI
    from teamstorm.api.workflows import WorkflowsAPI
    from teamstorm.api.workitems import WorkitemsAPI
    from teamstorm.api.workspace_groups import WorkspaceGroupsAPI
    from teamstorm.api.workspace_users import WorkspaceUsersAPI
    from teamstorm.api.workspaces import WorkspacesAPI


@dataclass(frozen=True, slots=True)
class TeamStormAPI:
    """
    Single entrypoint that groups the typed resource API wrappers.

    Usage::

        from teamstorm.client import TsClient
        from teamstorm.api import TeamStormAPI

        ts = TeamStormAPI(TsClient(base_url=..., token=...))
        ts.workspaces.get("KEY")

    Every property below returns a freshly constructed `*API` instance backed
    by ``self.client`` -- there is no per-property caching (``ts.workspaces is
    ts.workspaces`` is ``False``). `*API` classes are frozen dataclasses that
    hold nothing but the client reference, so constructing one is cheap
    (attribute assignment, no I/O); caching would only save that, at the cost
    of making TeamStormAPI's own dataclass identity/equality semantics more
    subtle and of one more place object identity could accidentally start
    being relied upon. Kept simple on purpose.

    The runtime import inside each property is function-local, not
    module-level -- measured with ``python -X importtime -c "import
    teamstorm"``: lazy imports keep `import teamstorm` at ~100ms, while
    eagerly importing every `*API` module (which pulls in `teamstorm.models`
    and `pydantic`) pushed the same import to ~230ms, a ~130ms tax paid by
    every caller regardless of which resource(s) they actually use. That is
    not "a few ms", so laziness stays. The concrete return type on every
    property below is what actually fixes the original defect (every
    property was untyped, so `ts.workspaces` type-checked as `Any`) --
    getting the annotation right does not require eagerly importing anything;
    `TYPE_CHECKING`-only imports above supply it at zero runtime cost.
    """

    client: TsClient

    @property
    def workspaces(self) -> WorkspacesAPI:
        """Workspaces: the top-level container for folders, workitems and documents. Returns WorkspacesAPI."""
        from teamstorm.api.workspaces import WorkspacesAPI

        return WorkspacesAPI(self.client)

    @property
    def folders(self) -> FoldersAPI:
        """Folders: the tree that organizes agile boards, sprints and workitems in a workspace. Returns FoldersAPI."""
        from teamstorm.api.folders import FoldersAPI

        return FoldersAPI(self.client)

    @property
    def agile(self) -> AgileAPI:
        """Agile board configuration attached to a folder (estimation type, board metadata). Returns AgileAPI."""
        from teamstorm.api.agile import AgileAPI

        return AgileAPI(self.client)

    @property
    def sprints(self) -> SprintsAPI:
        """Sprints (iterations): dates, team membership, and the backlog sprint. Returns SprintsAPI."""
        from teamstorm.api.sprints import SprintsAPI

        return SprintsAPI(self.client)

    @property
    def workitems(self) -> WorkitemsAPI:
        """Workitems (tasks/stories/bugs): CRUD, filtering, counts, and attribute values. Returns WorkitemsAPI."""
        from teamstorm.api.workitems import WorkitemsAPI

        return WorkitemsAPI(self.client)

    @property
    def users(self) -> UsersAPI:
        """Tenant-wide user accounts: lookup and block/unblock. Returns UsersAPI."""
        from teamstorm.api.users import UsersAPI

        return UsersAPI(self.client)

    @property
    def types(self) -> TypesAPI:
        """Workitem types (e.g. "Bug", "Story") and their assignable attributes. Returns TypesAPI."""
        from teamstorm.api.types import TypesAPI

        return TypesAPI(self.client)

    @property
    def attributes(self) -> AttributesAPI:
        """Custom attribute definitions and their UniSelect/Tag options. Returns AttributesAPI."""
        from teamstorm.api.attributes import AttributesAPI

        return AttributesAPI(self.client)

    @property
    def statuses(self) -> StatusesAPI:
        """Workflow statuses and the global status categories they roll up to. Returns StatusesAPI."""
        from teamstorm.api.statuses import StatusesAPI

        return StatusesAPI(self.client)

    @property
    def workflows(self) -> WorkflowsAPI:
        """Workflows: the named graph of statuses and transitions a type is bound to. Returns WorkflowsAPI."""
        from teamstorm.api.workflows import WorkflowsAPI

        return WorkflowsAPI(self.client)

    @property
    def roles(self) -> RolesAPI:
        """Permission roles (name + Permission set) assignable to users and groups. Returns RolesAPI."""
        from teamstorm.api.roles import RolesAPI

        return RolesAPI(self.client)

    @property
    def workspace_users(self) -> WorkspaceUsersAPI:
        """Workspace-scoped user membership and per-workspace role assignments. Returns WorkspaceUsersAPI."""
        from teamstorm.api.workspace_users import WorkspaceUsersAPI

        return WorkspaceUsersAPI(self.client)

    @property
    def workspace_groups(self) -> WorkspaceGroupsAPI:
        """Workspace-scoped group membership and per-workspace role assignments. Returns WorkspaceGroupsAPI."""
        from teamstorm.api.workspace_groups import WorkspaceGroupsAPI

        return WorkspaceGroupsAPI(self.client)

    @property
    def groups(self) -> GroupsAPI:
        """Tenant-wide user groups (identity groups), independent of any workspace. Returns GroupsAPI."""
        from teamstorm.api.groups import GroupsAPI

        return GroupsAPI(self.client)

    @property
    def providers(self) -> ProvidersAPI:
        """Identity providers (SSO/OpenID connections) configured on this instance. Returns ProvidersAPI."""
        from teamstorm.api.providers import ProvidersAPI

        return ProvidersAPI(self.client)

    @property
    def links(self) -> LinksAPI:
        """Typed workitem-to-workitem links (blocks, relates-to, ...) and their types. Returns LinksAPI."""
        from teamstorm.api.links import LinksAPI

        return LinksAPI(self.client)

    @property
    def workitem_comments(self) -> WorkitemCommentsAPI:
        """Comments on a workitem, including per-comment visibility settings. Returns WorkitemCommentsAPI."""
        from teamstorm.api.comments import WorkitemCommentsAPI

        return WorkitemCommentsAPI(self.client)

    @property
    def document_comments(self) -> DocumentCommentsAPI:
        """Comments on a document. Returns DocumentCommentsAPI."""
        from teamstorm.api.comments import DocumentCommentsAPI

        return DocumentCommentsAPI(self.client)

    @property
    def documents(self) -> DocumentsAPI:
        """Documents core CRUD, plus block/unblock. Returns DocumentsAPI."""
        from teamstorm.api.documents import DocumentsAPI

        return DocumentsAPI(self.client)

    @property
    def document_versions(self) -> DocumentVersionsAPI:
        """Read-only version history for a document. Returns DocumentVersionsAPI."""
        from teamstorm.api.documents import DocumentVersionsAPI

        return DocumentVersionsAPI(self.client)

    @property
    def document_statuses(self) -> DocumentStatusesAPI:
        """Workspace-configurable named statuses documents can be tagged with. Returns DocumentStatusesAPI."""
        from teamstorm.api.documents import DocumentStatusesAPI

        return DocumentStatusesAPI(self.client)

    @property
    def document_workitem_links(self) -> DocumentWorkitemLinksAPI:
        """Untyped links between a document and one or more workitems, both directions. Returns DocumentWorkitemLinksAPI."""
        from teamstorm.api.documents import DocumentWorkitemLinksAPI

        return DocumentWorkitemLinksAPI(self.client)

    @property
    def workitem_sharing(self) -> WorkitemSharingAPI:
        """Per-user/per-group sharing permissions granted on a workitem. Returns WorkitemSharingAPI."""
        from teamstorm.api.sharing import WorkitemSharingAPI

        return WorkitemSharingAPI(self.client)

    @property
    def document_sharing(self) -> DocumentSharingAPI:
        """Per-user/per-group sharing permissions granted on a document. Returns DocumentSharingAPI."""
        from teamstorm.api.sharing import DocumentSharingAPI

        return DocumentSharingAPI(self.client)

    @property
    def portfolios(self) -> PortfoliosAPI:
        """Portfolios: named groupings of portfolio elements above the workitem level. Returns PortfoliosAPI."""
        from teamstorm.api.portfolios import PortfoliosAPI

        return PortfoliosAPI(self.client)

    @property
    def portfolio_elements(self) -> PortfolioElementsAPI:
        """Portfolio elements and their links to the workitems they group. Returns PortfolioElementsAPI."""
        from teamstorm.api.portfolios import PortfolioElementsAPI

        return PortfolioElementsAPI(self.client)

    @property
    def workitem_attachments(self) -> WorkitemAttachmentsAPI:
        """File attachments on a workitem, including all stored versions. Returns WorkitemAttachmentsAPI."""
        from teamstorm.api.attachments import WorkitemAttachmentsAPI

        return WorkitemAttachmentsAPI(self.client)

    @property
    def document_attachments(self) -> DocumentAttachmentsAPI:
        """File attachments on a document, including all stored versions. Returns DocumentAttachmentsAPI."""
        from teamstorm.api.attachments import DocumentAttachmentsAPI

        return DocumentAttachmentsAPI(self.client)

    @property
    def time_tracking(self) -> TimeTrackingAPI:
        """Time tracking entries logged against workitems, tenant-wide. Returns TimeTrackingAPI."""
        from teamstorm.api.time_tracking import TimeTrackingAPI

        return TimeTrackingAPI(self.client)

    @property
    def queries(self) -> QueriesAPI:
        """Saved queries: their workitem results and visibility settings. Returns QueriesAPI."""
        from teamstorm.api.queries import QueriesAPI

        return QueriesAPI(self.client)

    @property
    def git_integration_tokens(self) -> GitIntegrationTokensAPI:
        """Git integration tokens (GitLab/GitFlic) for a workspace. Returns GitIntegrationTokensAPI."""
        from teamstorm.api.integrations import GitIntegrationTokensAPI

        return GitIntegrationTokensAPI(self.client)

    @property
    def open_id(self) -> OpenIdAPI:
        """OpenID connections and pre-provisioned users for SSO login. Returns OpenIdAPI."""
        from teamstorm.api.integrations import OpenIdAPI

        return OpenIdAPI(self.client)

    @property
    def workitem_time_metrics(self) -> WorkitemTimeMetricsAPI:
        """SLA/OLA-style time metrics on a workitem: enable from a template, start/pause/resume/stop. Returns WorkitemTimeMetricsAPI."""
        from teamstorm.api.time_metrics import WorkitemTimeMetricsAPI

        return WorkitemTimeMetricsAPI(self.client)

    @property
    def workitem_metric_templates(self) -> WorkitemTimeMetricTemplatesAPI:
        """Workspace time-metric templates that can be enabled on workitems. Returns WorkitemTimeMetricTemplatesAPI."""
        from teamstorm.api.time_metrics import WorkitemTimeMetricTemplatesAPI

        return WorkitemTimeMetricTemplatesAPI(self.client)

    @property
    def work_calendars(self) -> WorkCalendarsAPI:
        """Work calendars used by time metrics (tenant-wide, system administrators only). Returns WorkCalendarsAPI."""
        from teamstorm.api.work_calendars import WorkCalendarsAPI

        return WorkCalendarsAPI(self.client)
