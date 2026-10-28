"""The live e2e scenario: ordered steps from workspace creation to deletion (see the design doc in docs/superpowers).

Each step declares the operations it is there to call (``ops``) and the registry entries it needs (``needs``).
Steps put what they create into ``ctx.reg``; cleanup steps delete it and pop the entry.
"""

from __future__ import annotations

import datetime as dt
from typing import Any
from uuid import UUID

from e2e.runner import Ctx, RecordedFailure, Step, is_stale_e2e_workspace, run_marker
from teamstorm.client import ApiError
from teamstorm.models import (
    AttributeType,
    CreateAttributeOptionModel,
    CreateAttributeOptionRequestBody,
    CreateAttributeRequestBody,
    CreateCommentRequestBody,
    CreateDocumentRequestBody,
    CreateDocumentWorkitemLinkRequestBody,
    CreateFolderRequestBody,
    CreatePortfolioElementRequestBody,
    CreatePortfolioRequestBody,
    CreateRoleRequestBody,
    CreateStatusRequestBody,
    CreateTokenRequestBody,
    CreateTransitionRequestBody,
    CreateTypeRequestBody,
    CreateWorkflowRequestBody,
    CreateWorkflowStatusRequestBody,
    CreateWorkitemLinkRequestBody,
    DeleteDocumentWorkitemLinkRequestBody,
    EnableWorkitemTimeMetricRequestBody,
    EstimatesType,
    PatchAttributeOptionRequestBody,
    PatchAttributeRequestBody,
    PatchDocumentRequestBody,
    PatchFolderRequestBody,
    PatchPortfolioElementRequestBody,
    PatchPortfolioRequestBody,
    PatchRoleRequestBody,
    PatchTypeRequestBody,
    PatchWorkflowRequestBody,
    Permission,
    PrincipalType,
    SprintMemberRequestBody,
    TokenType,
    UpdateCommentPrincipalModel,
    UpdateCommentRequestBody,
    UpdateCommentVisibilitySettingsRequestBody,
    UpdateDateFieldRequestBody,
    UpdateNumberFieldRequestBody,
    UpdateTagFieldRequestBody,
    UpdateTimeFieldRequestBody,
    UpdateTokenRequestBody,
    UpdateUniSelectFieldRequestBody,
    UpdateUniStringFieldRequestBody,
    UpdateUserFieldRequestBody,
    UpdateUserFieldValueModel,
    UpdateWorkitemTimeMetricSettingsRequestBody,
)
from teamstorm.models.workitems_attributes_update import UpdateWorkitemAttributeRequestBody
from teamstorm.models.agile import CreateAgileRequestBody
from teamstorm.models.comments import CommentVisibilityType
from teamstorm.models.sharing import (
    CreateSharedDocumentUserPermissionBody,
    CreateSharedWorkitemUserPermissionBody,
    PatchSharedDocumentPermissionBody,
    PatchSharedWorkitemPermissionBody,
    SharedItemAccessLevel,
)
from teamstorm.models.sprints import CreateSprintRequestBody, PatchSprintRequestBody
from teamstorm.models.workitems import CreateWorkitemRequestBody, PatchWorkitemRequestBody
from teamstorm.models.workspaces import CreateWorkspaceRequestBody, PatchWorkspaceRequestBody
from teamstorm.models.workitems_attributes_create import (
    CreateDateFieldRequestBody,
    CreateNumberFieldRequestBody,
    CreateTagFieldRequestBody,
    CreateTimeFieldRequestBody,
    CreateUniSelectFieldRequestBody,
    CreateUniStringFieldRequestBody,
    CreateUserFieldRequestBody,
    CreateUserFieldValueModel,
)

DEMO_USERS = ("demo.user1", "demo.user2", "demo.user3", "demo.user4")
FILE_V1, FILE_V2 = b"teamstorm e2e attachment v1\n", b"teamstorm e2e attachment v2\n"

# Portfolio operations have no operationId in the spec; the manifest keys them by "METHOD path".
PORTFOLIO_CREATE = "POST /workspaces/{workspace}/portfolios"
PORTFOLIO_PATCH = "PATCH /workspaces/{workspace}/portfolios/{portfolioId}"
PORTFOLIO_DELETE = "DELETE /workspaces/{workspace}/portfolios/{portfolioId}"
ELEMENT_CREATE = "POST /workspaces/{workspace}/portfolio-elements"
ELEMENT_PATCH = "PATCH /workspaces/{workspace}/portfolio-elements/{portfolioElementId}"
ELEMENT_DELETE = "DELETE /workspaces/{workspace}/portfolio-elements/{portfolioElementId}"
ELEMENT_LINK = "POST /workspaces/{workspace}/portfolio-elements/{portfolioElementId}/workitems/{workitem}"
ELEMENT_UNLINK = "DELETE /workspaces/{workspace}/portfolio-elements/{portfolioElementId}/workitems/{workitem}"


def _a(ctx: Ctx) -> str:
    return str(ctx.reg["ws_a"].key)


def _b(ctx: Ctx) -> str:
    return str(ctx.reg["ws_b"].key)


def _user(ctx: Ctx, n: int) -> Any:
    return ctx.reg["users"][n - 1]


def _check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


# --- 0. preflight (read only) -------------------------------------------------------------------------------------


def preflight(ctx: Ctx) -> None:
    api = ctx.api
    api.workspaces.list(key=ctx.prefix + "A")  # also proves the token works before any write
    users = []
    for name in DEMO_USERS:
        # GET /users/{username} matched "demo.user1" to "demo.user12" on a live stand: resolve by exact username.
        found = [u for u in api.users.list(username=name) if u.username.lower() == name]
        _check(len(found) == 1, f"expected exactly one user {name}, found {len(found)}")
        _check(api.users.get(str(found[0].id)).id == found[0].id, f"users.get by id returned another user for {name}")
        users.append(found[0])
    ctx.reg["users"] = users
    api.providers.list()
    ctx.reg["categories"] = api.statuses.list_categories()
    ctx.reg["calendars"] = api.work_calendars.list()


def global_groups(ctx: Ctx) -> None:
    wanted = ctx.env.get("E2E_GROUP")
    groups = ctx.api.groups.list(name=wanted) if wanted else ctx.api.groups.list()
    if not groups:
        ctx.skip("no user group on the instance" + (f" named {wanted}" if wanted else ""))
    ctx.reg["group"] = ctx.api.groups.get(str(groups[0].id))


# --- 1. workspaces -------------------------------------------------------------------------------------------------


def create_workspaces(ctx: Ctx) -> None:
    for suffix in ("A", "B"):
        key = ctx.prefix + suffix
        body = CreateWorkspaceRequestBody(
            key=key, name=f"{key} live e2e {ctx.started:%Y-%m-%d %H:%M:%S} UTC", description=run_marker(ctx.prefix)
        )
        ctx.reg["ws_" + suffix.lower()] = ctx.api.workspaces.create(body)


def sweep_earlier_runs(ctx: Ctx) -> None:
    owner = ctx.reg["ws_a"].author
    if owner is None:
        ctx.skip("the server did not return the workspace author")
    sweep(ctx, owner.id, delete=True)


def sweep(ctx: Ctx, owner_id: UUID, *, delete: bool) -> None:
    log = ctx.reg.setdefault("sweep_log", [])
    now = dt.datetime.now(dt.timezone.utc)
    for ws in ctx.api.workspaces.list():  # no key filter: its matching rules are not documented
        if not is_stale_e2e_workspace(ws, owner_id=owner_id, now=now, current_prefix=ctx.prefix):
            continue
        if not delete:
            log.append({"key": ws.key, "result": "candidate (dry run)"})
            continue
        try:
            ctx.api.workspaces.delete(workspace_key=ws.key)
            log.append({"key": ws.key, "result": "deleted"})
        except Exception as e:  # noqa: BLE001 -- a stale workspace that will not go is a warning, not a FAIL
            log.append({"key": ws.key, "result": f"warning: {e}"})


def read_workspaces(ctx: Ctx) -> None:
    ws = ctx.api.workspaces.get(_a(ctx))
    _check(ws.id == ctx.reg["ws_a"].id, "workspaces.get returned another workspace")
    description = run_marker(ctx.prefix) + " (patched)"
    patched = ctx.api.workspaces.patch(workspace_key=_a(ctx), body=PatchWorkspaceRequestBody(description=description))
    _check(run_marker(ctx.prefix) in (patched.description or ""), "the sweep marker did not survive the patch")
    found = ctx.api.workspaces.list(key=_a(ctx))
    _check(_a(ctx) in {w.key for w in found}, "workspaces.list(key=...) misses the run workspace")


# --- 2. members and roles ------------------------------------------------------------------------------------------


def roles_and_members(ctx: Ctx) -> None:
    api, ws = ctx.api, _a(ctx)
    api.roles.list(ws)
    role = api.roles.create(ws, CreateRoleRequestBody(name="e2e role", permissions=[Permission.WorkspaceContentRead]))
    ctx.reg["role"] = role
    api.roles.get(ws, role_id=role.id)
    api.roles.patch(
        ws,
        role_id=role.id,
        body=PatchRoleRequestBody(
            name="e2e role patched", permissions=[Permission.WorkspaceContentRead, Permission.WorkitemCreate]
        ),
    )
    for user in ctx.reg["users"]:
        api.workspace_users.add(ws, user_id=user.id)
    api.workspace_users.add(_b(ctx), user_id=_user(ctx, 1).id)
    ctx.reg["members"] = True
    listed = {u.id for u in api.workspace_users.list(ws)}
    _check({u.id for u in ctx.reg["users"]} <= listed, "workspace_users.list misses added demo users")
    uid = _user(ctx, 4).id
    api.workspace_users.add_role(ws, user_id=uid, role_id=role.id)
    _check(role.id in {r.id for r in api.workspace_users.get_roles(ws, user_id=uid)}, "user role not granted")
    api.workspace_users.remove_role(ws, user_id=uid, role_id=role.id)


def workspace_group(ctx: Ctx) -> None:
    api, ws, gid, rid = ctx.api, _a(ctx), ctx.reg["group"].id, ctx.reg["role"].id
    api.workspace_groups.add(ws, group_id=gid)
    try:
        api.workspace_groups.list(ws)
        api.workspace_groups.add_role(ws, group_id=gid, role_id=rid)
        _check(rid in {r.id for r in api.workspace_groups.get_roles(ws, group_id=gid)}, "group role not granted")
        api.workspace_groups.remove_role(ws, group_id=gid, role_id=rid)
    finally:
        api.workspace_groups.remove(ws, group_id=gid)


# --- 3. folders ----------------------------------------------------------------------------------------------------


def folders(ctx: Ctx) -> None:
    api, ws = ctx.api, _a(ctx)
    root = api.folders.create(ws, CreateFolderRequestBody(name="e2e root", parent_id=ctx.reg["ws_a"].id))
    ctx.reg["root"] = root
    ctx.reg["sub"] = api.folders.create(ws, CreateFolderRequestBody(name="e2e sub", parent_id=root.id))
    api.folders.get(ws, folder_id=root.id)
    api.folders.list(ws, parent_id=root.id)
    api.folders.patch(ws, folder_id=ctx.reg["sub"].id, body=PatchFolderRequestBody(description="patched"))
    ctx.reg["root_b"] = api.folders.create(
        _b(ctx), CreateFolderRequestBody(name="e2e root B", parent_id=ctx.reg["ws_b"].id)
    )


# --- 4. statuses and workflow --------------------------------------------------------------------------------------


def statuses_and_workflow(ctx: Ctx) -> None:
    api, ws = ctx.api, _a(ctx)
    api.statuses.list(ws)
    categories = ctx.reg["categories"]
    first, last = categories[0], categories[-1]
    todo = api.statuses.create(ws, CreateStatusRequestBody(name=f"e2e todo {ctx.prefix}", category=str(first.id)))
    done = api.statuses.create(ws, CreateStatusRequestBody(name=f"e2e done {ctx.prefix}", category=str(last.id)))
    api.statuses.get(ws, status_key=str(todo.id))
    ctx.reg["statuses"] = (todo, done)
    workflow = api.workflows.create(
        ws,
        CreateWorkflowRequestBody(
            name="e2e workflow",
            statuses=[
                CreateWorkflowStatusRequestBody(status_id=todo.id, position_x=0, position_y=0),
                CreateWorkflowStatusRequestBody(status_id=done.id, position_x=200, position_y=0),
            ],
            transitions=[
                CreateTransitionRequestBody(next_status_id=todo.id, is_initial=True),
                CreateTransitionRequestBody(from_status_id=todo.id, next_status_id=done.id, is_initial=False),
            ],
        ),
    )
    ctx.reg["workflow"] = workflow
    api.workflows.get(ws, str(workflow.id))
    api.workflows.list(ws)
    api.workflows.patch(ws, workflow_key=str(workflow.id), body=PatchWorkflowRequestBody(name="e2e workflow patched"))


# --- 5. attributes -------------------------------------------------------------------------------------------------


def attributes(ctx: Ctx) -> None:
    api, ws = ctx.api, _a(ctx)
    created = {}
    for kind in AttributeType:
        options = None
        if kind in (AttributeType.UniSelect, AttributeType.Tag):
            options = [CreateAttributeOptionModel(name="one"), CreateAttributeOptionModel(name="two")]
        created[kind] = api.attributes.create(
            ws, CreateAttributeRequestBody(name=f"e2e {kind.value}", type=kind, options=options)
        )
    ctx.reg["attrs"] = created
    select = created[AttributeType.UniSelect]
    api.attributes.get(ws, attribute_id=select.id)
    api.attributes.list(ws)
    api.attributes.patch(ws, attribute_id=select.id, body=PatchAttributeRequestBody(description="patched"))
    added = api.attributes.add_option(
        ws, attribute_id=select.id, body=CreateAttributeOptionRequestBody(id=None, name="three")
    )
    option = next(o for o in added.options or [] if o.name == "three")
    api.attributes.patch_option(
        ws, attribute_id=select.id, body=PatchAttributeOptionRequestBody(id=option.id, name="three renamed")
    )
    api.attributes.delete_option(ws, attribute_id=select.id, option_id=option.id)


# --- 6. types ------------------------------------------------------------------------------------------------------


def types(ctx: Ctx) -> None:
    api, ws = ctx.api, _a(ctx)
    api.types.list(ws)
    created = api.types.create(
        ws, CreateTypeRequestBody(name=f"e2e type {ctx.prefix}", workflow=str(ctx.reg["workflow"].id))
    )
    ctx.reg["type"] = created
    key = str(created.id)
    for attribute in ctx.reg["attrs"].values():
        api.types.add_attribute(ws, type_key=key, attribute_id=attribute.id)
    api.types.get(ws, key)
    api.types.patch(ws, type_key=key, body=PatchTypeRequestBody(estimates_in_story_points=True))
    number = ctx.reg["attrs"][AttributeType.Number].id
    api.types.remove_attribute(ws, type_key=key, attribute_id=number)
    api.types.add_attribute(ws, type_key=key, attribute_id=number)


# --- 7. agile and sprints ------------------------------------------------------------------------------------------


def agile_and_sprint(ctx: Ctx) -> None:
    api, ws, root = ctx.api, _a(ctx), ctx.reg["root"].id
    agile = api.agile.create(
        ws, body=CreateAgileRequestBody(folder_id=root, estimates_type=EstimatesType.EstimatesInStoryPoints)
    )
    ctx.reg["agile"] = agile
    api.agile.get(ws, agile_id=agile.id)
    api.agile.list(ws, folder_id=root)
    start = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    sprint = api.sprints.create(
        ws,
        CreateSprintRequestBody(
            agile_id=agile.id,
            name="e2e sprint",
            start_date=start,
            end_date=start + dt.timedelta(days=14),
            workdays=10,
            estimated_story_points=20,  # required when the agile estimates in story points
            team=[SprintMemberRequestBody(user_id=_user(ctx, n).id) for n in (1, 2)],
        ),
    )
    ctx.reg["sprint"] = sprint
    api.sprints.get(ws, sprint_id=sprint.id)
    api.sprints.list(ws, folder_id=root)
    api.sprints.patch(ws, sprint_id=sprint.id, body=PatchSprintRequestBody(description="patched"))


# --- 8. portfolios -------------------------------------------------------------------------------------------------


def portfolios(ctx: Ctx) -> None:
    api, ws = ctx.api, _a(ctx)
    portfolio = api.portfolios.create(
        ws, CreatePortfolioRequestBody(name="e2e portfolio", folder_id=ctx.reg["root"].id)
    )
    ctx.reg["portfolio"] = portfolio
    api.portfolios.get(ws, portfolio_id=portfolio.id)
    api.portfolios.list(ws)
    api.portfolios.patch(ws, portfolio_id=portfolio.id, body=PatchPortfolioRequestBody(name="e2e portfolio patched"))
    element = api.portfolio_elements.create(
        ws,
        CreatePortfolioElementRequestBody(
            portfolio_id=portfolio.id, name="e2e element", responsibles=[str(_user(ctx, 1).id)]
        ),
    )
    ctx.reg["element"] = element
    api.portfolio_elements.get(ws, portfolio_element_id=element.id)
    api.portfolio_elements.list(ws, portfolio_id=portfolio.id)
    api.portfolio_elements.patch(
        ws, portfolio_element_id=element.id, body=PatchPortfolioElementRequestBody(description="patched")
    )


# --- 9. workitems --------------------------------------------------------------------------------------------------


def _create_values(ctx: Ctx) -> list[Any]:
    attrs = ctx.reg["attrs"]
    return [
        CreateUniStringFieldRequestBody(id=attrs[AttributeType.UniString].id, value="text"),
        CreateNumberFieldRequestBody(id=attrs[AttributeType.Number].id, value=42),
        CreateDateFieldRequestBody(id=attrs[AttributeType.Date].id, value=ctx.started),
        CreateUniSelectFieldRequestBody(id=attrs[AttributeType.UniSelect].id, value="one"),
        CreateTagFieldRequestBody(id=attrs[AttributeType.Tag].id, value=["one", "two"]),
        CreateUserFieldRequestBody(
            id=attrs[AttributeType.User].id, value=CreateUserFieldValueModel(id=_user(ctx, 2).id)
        ),
        CreateTimeFieldRequestBody(id=attrs[AttributeType.TimeDuration].id, value=3600),
    ]


def workitems(ctx: Ctx) -> None:
    api, ws = ctx.api, _a(ctx)
    type_key = str(ctx.reg["type"].id)
    parent = api.workitems.create(
        ws,
        CreateWorkitemRequestBody(
            name="e2e parent",
            parent_id=ctx.reg["sub"].id,
            type=type_key,
            description="e2e parent workitem",
            assignee=_user(ctx, 1).username,
            sprint_id=ctx.reg["sprint"].id,
            attributes=_create_values(ctx),
        ),
    )
    ctx.reg["parent"] = parent
    ctx.reg["child"] = api.workitems.create(
        ws,
        CreateWorkitemRequestBody(name="e2e child", parent_id=parent.id, type=type_key, description="e2e child"),
    )
    b_type = api.types.list(_b(ctx))[0]
    ctx.reg["item_b"] = api.workitems.create(
        _b(ctx),
        CreateWorkitemRequestBody(
            name="e2e item B", parent_id=ctx.reg["root_b"].id, type=str(b_type.id), description="e2e item in B"
        ),
    )


def read_workitems(ctx: Ctx) -> None:
    api, ws, parent = ctx.api, _a(ctx), ctx.reg["parent"]
    todo, done = ctx.reg["statuses"]
    api.workitems.get(ws, workitem_id=parent.id)
    api.workitems.list(ws)
    api.workitems.list(ws, type=str(ctx.reg["type"].id))
    api.workitems.list(ws, sprint_id=ctx.reg["sprint"].id)
    api.workitems.list(ws, parent=parent.id)
    api.workitems.list(ws, assignee=_user(ctx, 1).username)
    api.workitems.list(ws, status=str(todo.id))
    _check(api.workitems.count(ws) >= 2, "workitems.count is below the two created workitems")
    api.workitems.list_updates(ws, changed_from_date=ctx.started - dt.timedelta(minutes=5))
    children = api.workitems.list_by_parent(ws, parent_id=parent.id)
    _check(ctx.reg["child"].id in {w.id for w in children}, "list_by_parent misses the child")
    patched = api.workitems.patch(
        ws, workitem_id=parent.id, body=PatchWorkitemRequestBody(status=str(done.id), story_points=3)
    )
    _check(patched.status is not None and patched.status.id == done.id, "status transition did not apply")


def workitem_attributes(ctx: Ctx) -> None:
    api, ws, wid, attrs = ctx.api, _a(ctx), ctx.reg["parent"].id, ctx.reg["attrs"]
    api.workitems.list_attributes(ws, workitem_id=wid)
    bodies: list[UpdateWorkitemAttributeRequestBody] = [
        UpdateUniStringFieldRequestBody(type=AttributeType.UniString, value="text 2"),
        UpdateNumberFieldRequestBody(type=AttributeType.Number, value=43),
        UpdateDateFieldRequestBody(type=AttributeType.Date, value=ctx.started + dt.timedelta(days=1)),
        UpdateUniSelectFieldRequestBody(type=AttributeType.UniSelect, value="two"),
        UpdateTagFieldRequestBody(type=AttributeType.Tag, value=["two"]),
        UpdateUserFieldRequestBody(type=AttributeType.User, value=UpdateUserFieldValueModel(id=_user(ctx, 3).id)),
        UpdateTimeFieldRequestBody(type=AttributeType.TimeDuration, value=7200),
    ]
    for body in bodies:
        api.workitems.update_attribute(ws, workitem_id=wid, attribute_id=attrs[AttributeType(body.type)].id, body=body)


def portfolio_link(ctx: Ctx) -> None:
    api, ws, element, wid = ctx.api, _a(ctx), ctx.reg["element"].id, ctx.reg["parent"].id
    link_call = len(ctx.client.calls)
    failure: Exception | None = None
    try:
        api.portfolio_elements.link_workitem(ws, portfolio_element_id=element, workitem_id=wid)
    except Exception as e:  # noqa: BLE001 -- reported below, after the read-back
        failure = e
        ctx.client.calls[link_call].error = (
            ctx.client.calls[link_call].error or " ".join(f"{type(e).__name__}: {e}".split())[:300]
        )
    # The link may commit and still fail response validation: read back instead of retrying.
    if wid in {w.id for w in api.workitems.list(ws, portfolio_element_id=element)}:
        ctx.reg["element_link"] = True
    if failure is not None:
        raise RecordedFailure(f"link_workitem: {type(failure).__name__}") from failure


# --- 10. workitem collaboration ------------------------------------------------------------------------------------


def workitem_comments(ctx: Ctx) -> None:
    api, ws, wid = ctx.api, _a(ctx), ctx.reg["parent"].id
    comment = api.workitem_comments.create(ws, workitem_id=wid, body=CreateCommentRequestBody(text="e2e comment"))
    ctx.reg["comment"] = comment
    api.workitem_comments.list(ws, workitem_id=wid)
    api.workitem_comments.update(
        ws, workitem_id=wid, comment_id=comment.id, body=UpdateCommentRequestBody(text="e2e comment edited")
    )
    api.workitem_comments.get_visibility(ws, workitem_id=wid, comment_id=comment.id)
    api.workitem_comments.update_visibility(
        ws,
        workitem_id=wid,
        comment_id=comment.id,
        body=UpdateCommentVisibilitySettingsRequestBody(
            visibility_type=CommentVisibilityType.OnlySelected,
            access_list=[UpdateCommentPrincipalModel(id=_user(ctx, 2).id, type=PrincipalType.User)],
        ),
    )


def workitem_links(ctx: Ctx) -> None:
    api, ws, wid = ctx.api, _a(ctx), ctx.reg["parent"].id
    link_type = api.links.list_types(ws)[0]
    ctx.reg["link"] = api.links.create(
        ws,
        workitem_id=wid,
        body=CreateWorkitemLinkRequestBody(
            type=str(link_type.id),  # the key answered LinkType.NotFound on a live stand
            linked_workitem=str(ctx.reg["item_b"].id),
            linked_workspace=_b(ctx),
        ),
    )
    api.links.list(ws, workitem_id=wid)


def workitem_sharing(ctx: Ctx) -> None:
    api, ws, wid = ctx.api, _a(ctx), ctx.reg["parent"].id
    share = api.workitem_sharing.create(
        ws,
        workitem_id=wid,
        body=CreateSharedWorkitemUserPermissionBody(access_level=SharedItemAccessLevel.Read, user_id=_user(ctx, 3).id),
    )
    ctx.reg["wi_share"] = share
    api.workitem_sharing.list(ws, workitem_id=wid)
    api.workitem_sharing.patch(
        ws,
        workitem_id=wid,
        permission_id=share.permission_id,
        body=PatchSharedWorkitemPermissionBody(access_level=SharedItemAccessLevel.Comment),
    )


def _attachments_roundtrip(ctx: Ctx, attachments: Any, ws: str, owner: dict[str, Any], reg_key: str) -> None:
    # The API cannot add a version to an existing attachment (re-upload answers File.Conflict), so each of the
    # three delete flavours gets an attachment of its own: delete, delete_version (of the only version), delete_all.
    first = attachments.upload(ws, file_name="e2e.txt", content=FILE_V1, content_type="text/plain", **owner)
    ctx.reg[reg_key] = first
    ctx.reg[reg_key + "_second"] = attachments.upload(
        ws, file_name="e2e-2.txt", content=FILE_V2, content_type="text/plain", **owner
    )
    attachments.upload(ws, file_name="e2e-3.txt", content=FILE_V1, content_type="text/plain", **owner)
    _check(len(attachments.list(ws, **owner)) == 3, "attachments.list does not show the three uploads")
    current = attachments.get(ws, attachment_id=first, **owner)
    ctx.soft(attachments.get_version, ws, attachment_id=first, version=current.version, **owner)
    _check(attachments.download(ws, attachment_id=first, **owner) == FILE_V1, "downloaded bytes differ")
    ctx.soft(attachments.list_versions, ws, **owner)


def workitem_attachments(ctx: Ctx) -> None:
    owner = {"workitem_id": ctx.reg["parent"].id}
    _attachments_roundtrip(ctx, ctx.api.workitem_attachments, _a(ctx), owner, "wi_att")


def time_metrics(ctx: Ctx) -> None:
    api, ws, wid = ctx.api, _a(ctx), ctx.reg["child"].id
    templates = api.workitem_metric_templates.list(ws)
    if not templates:
        ctx.skip("the new workspace has no time-metric template (templates cannot be created via the API)")
    metrics = api.workitem_time_metrics
    calendars = ctx.reg["calendars"]
    metric_id = metrics.enable(
        ws,
        workitem_id=wid,
        body=EnableWorkitemTimeMetricRequestBody(
            template_id=templates[0].id, limit_seconds=3600, work_calendar_id=calendars[0].id if calendars else None
        ),
    ).id
    metrics.list(ws, workitem_id=wid)
    metrics.get(ws, workitem_id=wid, metric_id=metric_id)
    metrics.update(
        ws, workitem_id=wid, metric_id=metric_id, body=UpdateWorkitemTimeMetricSettingsRequestBody(limit_seconds=7200)
    )
    for operation in ("start", "pause", "resume", "stop", "disable"):
        getattr(metrics, operation)(ws, workitem_id=wid, metric_id=metric_id)


# --- 11. documents -------------------------------------------------------------------------------------------------


def documents(ctx: Ctx) -> None:
    api, ws = ctx.api, _a(ctx)
    statuses = api.document_statuses.list(ws)
    doc = api.documents.create(
        ws,
        CreateDocumentRequestBody(
            name="e2e document",
            content="<p>e2e</p>",
            parent_id=ctx.reg["ws_a"].id,  # a folder parent answered 404 "Node not found" on a live stand
            labels=["e2e"],
        ),
    )
    ctx.reg["doc"] = doc
    api.documents.get(ws, document_id=doc.id)
    api.documents.list(ws)
    if statuses:
        api.document_statuses.get(ws, status_key=str(statuses[0].id))
        try:
            api.documents.patch(ws, document_id=doc.id, body=PatchDocumentRequestBody(status=str(statuses[0].id)))
        except ApiError as e:
            if "DocumentStatuses.Disabled" not in (e.details or ""):
                raise
            # A new workspace lists document statuses but keeps them disabled; the API cannot enable them.
            ctx.client.calls[-1].counts = False
            ctx.skip_op("PatchDocument", "document statuses are disabled in a new workspace")
    else:
        ctx.skip_op("GetDocumentsStatus", "the workspace has no document statuses")
        ctx.skip_op("PatchDocument", "the workspace has no document statuses")
    _check(api.documents.block(ws, document_id=doc.id).is_blocked, "document is not blocked")
    _check(not api.documents.unblock(ws, document_id=doc.id).is_blocked, "document is still blocked")
    versions = api.document_versions.list(ws, document_id=doc.id)
    api.document_versions.get(ws, document_id=doc.id, version=versions[-1].version_number)
    ctx.reg["doc_versions"] = sorted(v.version_number for v in versions)


def document_collaboration(ctx: Ctx) -> None:
    api, ws, did, item_b = ctx.api, _a(ctx), ctx.reg["doc"].id, ctx.reg["item_b"]
    ctx.reg["doc_comment"] = api.document_comments.create(
        ws, document_id=did, body=CreateCommentRequestBody(text="e2e doc comment")
    )
    api.document_comments.list(ws, document_id=did)
    api.document_workitem_links.create(
        ws,
        document_id=did,
        body=CreateDocumentWorkitemLinkRequestBody(workitem=str(item_b.id), workitem_workspace=_b(ctx)),
    )
    ctx.reg["doc_link"] = True
    api.document_workitem_links.list(ws, document_id=did)
    api.document_workitem_links.list_by_workitem(_b(ctx), workitem_id=item_b.id)
    share = api.document_sharing.create(
        ws,
        document_id=did,
        body=CreateSharedDocumentUserPermissionBody(access_level=SharedItemAccessLevel.Read, user_id=_user(ctx, 4).id),
    )
    ctx.reg["doc_share"] = share
    api.document_sharing.list(ws, document_id=did)
    api.document_sharing.patch(
        ws,
        document_id=did,
        permission_id=share.permission_id,
        body=PatchSharedDocumentPermissionBody(access_level=SharedItemAccessLevel.Comment),
    )


def document_attachments(ctx: Ctx) -> None:
    owner = {"document_id": ctx.reg["doc"].id}
    _attachments_roundtrip(ctx, ctx.api.document_attachments, _a(ctx), owner, "doc_att")


# --- 12. integrations, 13. global reads ----------------------------------------------------------------------------


def git_tokens(ctx: Ctx) -> None:
    api, ws = ctx.api, _a(ctx)
    token = api.git_integration_tokens.create(ws, CreateTokenRequestBody(name="e2e token", type=TokenType.GitLab))
    ctx.reg["token"] = token.id  # never keep the secret itself
    api.git_integration_tokens.get(ws, token_id=token.id)
    api.git_integration_tokens.list(ws)
    api.git_integration_tokens.update(ws, token_id=token.id, body=UpdateTokenRequestBody(name="e2e token renamed"))
    api.git_integration_tokens.refresh(ws, token_id=token.id)


def time_tracking(ctx: Ctx) -> None:
    start = ctx.started - dt.timedelta(days=7)
    ctx.api.time_tracking.list(start_date=start)
    ctx.api.time_tracking.list_updates(start_date=start)


def queries(ctx: Ctx) -> None:
    query_id, query_ws = ctx.env.get("E2E_QUERY_ID"), ctx.env.get("E2E_QUERY_WORKSPACE")
    if not query_id or not query_ws:
        ctx.skip("set E2E_QUERY_ID and E2E_QUERY_WORKSPACE to read an existing saved query")
    ctx.api.queries.list_workitems(UUID(query_id), max_items_count=10)
    ctx.api.queries.get_visibility(query_ws, query_id=UUID(query_id))


# --- 14. cleanup ---------------------------------------------------------------------------------------------------


def _cleanup(key: str, ops: tuple[str, ...], fn: Any, needs: tuple[str, ...] = ()) -> Step:
    def run(ctx: Ctx) -> None:
        fn(ctx)
        ctx.reg.pop(key, None)

    return Step(f"delete {key}", ops, run, needs=(key, *needs), cleanup=True)


def _delete_attachments(attachments: Any, owner_key: str, att_key: str) -> Any:
    def run(ctx: Ctx) -> None:
        owner = {owner_key: ctx.reg[att_key + "_owner"]}
        attachments_api = getattr(ctx.api, attachments)
        second = ctx.reg[att_key + "_second"]
        version = attachments_api.get(_a(ctx), attachment_id=second, **owner).version
        attachments_api.delete_version(_a(ctx), attachment_id=second, version=version, **owner)
        attachments_api.delete(_a(ctx), attachment_id=ctx.reg[att_key], **owner)
        attachments_api.delete_all(_a(ctx), **owner)

    return run


def _delete_doc_version(ctx: Ctx) -> None:
    versions = ctx.reg.get("doc_versions") or []
    if len(versions) < 2:
        ctx.skip_op("DeleteDocumentVersion", f"the document has {len(versions)} version(s); the API cannot add one")
        return
    ctx.api.document_versions.delete(_a(ctx), document_id=ctx.reg["doc"].id, version=versions[0])


def _remove_members(ctx: Ctx) -> None:
    for user in ctx.reg["users"]:
        ctx.api.workspace_users.remove(_a(ctx), user_id=user.id)
    ctx.api.workspace_users.remove(_b(ctx), user_id=_user(ctx, 1).id)


def _delete_role(ctx: Ctx) -> None:
    system = ctx.api.roles.list(_a(ctx), is_system_role=True)
    replacement = system[0].id if system else None
    ctx.api.roles.delete(_a(ctx), role_id=ctx.reg["role"].id, replacement_role_id=replacement)


def _remember_attachment_owners(ctx: Ctx) -> None:
    if "parent" in ctx.reg:
        ctx.reg["wi_att_owner"] = ctx.reg["parent"].id
    if "doc" in ctx.reg:
        ctx.reg["doc_att_owner"] = ctx.reg["doc"].id


def build_steps() -> list[Step]:
    a = ("ws_a", "ws_b")
    return [
        Step(
            "preflight",
            ("ListWorkspaces", "ListUsers", "GetUser", "GetProviders", "ListStatusCategories", "GetWorkCalendars"),
            preflight,
        ),
        Step("global groups", ("ListUserGroups", "GetUserGroup"), global_groups, needs=("users",)),
        Step("create workspaces", ("CreateWorkspace",), create_workspaces, needs=("users",)),
        Step("sweep earlier runs", (), sweep_earlier_runs, needs=("ws_a",), counts=False),
        Step("read workspaces", ("GetWorkspace", "PatchWorkspace"), read_workspaces, needs=a),
        Step(
            "roles and members",
            ("ListRoles", "CreateRole", "GetRole", "PatchRole", "AddWorkspaceUser", "GetWorkspaceUsers")
            + ("AddUserRole", "GetUserRoles", "RemoveRoleForUser"),
            roles_and_members,
            needs=a,
        ),
        Step(
            "workspace group",
            ("AddWorkspaceGroup", "FilterWorkspaceUsers", "AddGroupRole", "GetGroupRoles", "RemoveRoleForGroup")
            + ("RemoveWorkspaceGroup",),
            workspace_group,
            needs=("ws_a", "group", "role"),
        ),
        Step("folders", ("CreateFolder", "GetFolder", "ListFolders", "PatchFolder"), folders, needs=a),
        Step(
            "statuses and workflow",
            ("ListStatuses", "CreateStatus", "GetStatus", "CreateWorkflow", "GetWorkflow", "ListWorkflows")
            + ("PatchWorkflow",),
            statuses_and_workflow,
            needs=("ws_a", "categories"),
        ),
        Step(
            "attributes",
            ("CreateAttribute", "GetAttribute", "ListAttributes", "PatchAttribute", "AddAttributeOption")
            + ("PatchAttributeOption", "DeleteAttributeOption"),
            attributes,
            needs=("ws_a",),
        ),
        Step(
            "types",
            ("ListTypes", "CreateType", "AddTypeAttribute", "GetType", "PatchType", "DeleteTypeAttribute"),
            types,
            needs=("ws_a", "workflow", "attrs"),
        ),
        Step(
            "agile and sprint",
            ("CreateAgile", "GetAgile", "GetAgileExtensions", "CreateSprint", "GetSprint", "ListSprints")
            + ("PatchSprint",),
            agile_and_sprint,
            needs=("ws_a", "root", "members"),
        ),
        Step(
            "portfolios",
            (PORTFOLIO_CREATE, "GetPortfolio", "ListPortfolios", PORTFOLIO_PATCH, ELEMENT_CREATE)
            + ("GetPortfolioElement", "ListPortfolioElements", ELEMENT_PATCH),
            portfolios,
            needs=("ws_a", "root", "members"),
        ),
        Step("workitems", ("CreateWorkitem",), workitems, needs=(*a, "type", "sub", "sprint", "root_b", "members")),
        Step(
            "read workitems",
            ("GetWorkitemById", "ListWorkitems", "GetWorkitemsCount", "ListWorkitemsUpdates", "ListWorkitemsByParent")
            + ("PatchWorkitem",),
            read_workitems,
            needs=("parent", "child"),
        ),
        Step(
            "workitem attributes",
            ("ListWorkitemAttributes", "UpdateWorkitemAttribute"),
            workitem_attributes,
            needs=("parent",),
        ),
        Step("portfolio link", (ELEMENT_LINK,), portfolio_link, needs=("parent", "element")),
        Step(
            "workitem comments",
            ("CreateWorkitemComment", "ListWorkitemComments", "UpdateWorkitemComment")
            + ("GetWorkitemCommentVisibilitySettings", "UpdateWorkitemCommentVisibilitySettings"),
            workitem_comments,
            needs=("parent",),
        ),
        Step(
            "workitem links",
            ("ListLinkTypes", "CreateWorkitemLink", "ListWorkitemLinks"),
            workitem_links,
            needs=("parent", "item_b"),
        ),
        Step(
            "workitem sharing",
            ("CreateSharedWorkitemPermission", "ListSharedWorkitemPermissions", "PatchSharedWorkitemPermission"),
            workitem_sharing,
            needs=("parent",),
        ),
        Step(
            "workitem attachments",
            ("UploadWorkitemAttachments", "GetWorkitemAttachments", "GetWorkitemAttachmentsWithVersions")
            + ("GetWorkitemAttachment", "GetWorkitemAttachmentWithVersions", "DownloadWorkitemAttachments"),
            workitem_attachments,
            needs=("parent",),
        ),
        Step(
            "time metrics",
            ("GetWorkitemTimeMetricTemplates", "EnableWorkitemTimeMetric", "GetWorkitemTimeMetrics")
            + ("GetWorkitemTimeMetric", "UpdateWorkitemTimeMetricSettings", "StartWorkitemTimeMetric")
            + ("PauseWorkitemTimeMetric", "ResumeWorkitemTimeMetric", "StopWorkitemTimeMetric")
            + ("DisableWorkitemTimeMetric",),
            time_metrics,
            needs=("child", "calendars"),
        ),
        Step(
            "documents",
            ("ListDocumentStatuses", "GetDocumentsStatus", "CreateDocument", "GetDocument", "ListDocuments")
            + ("PatchDocument", "BlockDocument", "UnblockDocument", "ListDocumentVersions", "GetDocumentByVersion"),
            documents,
            needs=("ws_a", "root"),
        ),
        Step(
            "document collaboration",
            ("CreateDocumentComment", "ListDocumentComments", "CreateDocumentWorkitemLink")
            + ("GetDocumentWorkitemLinks", "GetWorkitemDocumentLinks", "CreateSharedDocumentPermission")
            + ("ListSharedDocumentPermissions", "PatchSharedDocumentPermission"),
            document_collaboration,
            needs=("doc", "item_b", "members"),
        ),
        Step(
            "document attachments",
            ("UploadDocumentAttachments", "GetDocumentAttachments", "GetDocumentAttachmentsWithVersions")
            + ("GetDocumentAttachment", "GetDocumentAttachmentWithVersions", "DownloadDocumentAttachments"),
            document_attachments,
            needs=("doc",),
        ),
        Step(
            "git tokens",
            ("CreateToken", "GetToken", "ListTokens", "UpdateToken", "RefreshToken"),
            git_tokens,
            needs=("ws_a",),
        ),
        Step("time tracking", ("GetTimeTrackingEntries", "GetTimeTrackingEntriesUpdates"), time_tracking),
        Step("queries", ("ListQueryWorkitems", "GetQueryVisibilitySettings"), queries),
        # --- cleanup, reverse order; every step runs whenever its object is still registered ---
        Step("remember attachment owners", (), _remember_attachment_owners, cleanup=True),
        _cleanup(
            "token",
            ("DeleteTokenAsync",),
            lambda c: c.api.git_integration_tokens.delete(_a(c), token_id=c.reg["token"]),
        ),
        _cleanup(
            "doc_att",
            ("DeleteDocumentAttachmentVersion", "DeleteDocumentAttachment", "DeleteDocumentAttachments"),
            _delete_attachments("document_attachments", "document_id", "doc_att"),
            needs=("doc_att_owner",),
        ),
        _cleanup(
            "doc_share",
            ("DeleteSharedDocumentPermission",),
            lambda c: c.api.document_sharing.delete(
                _a(c), document_id=c.reg["doc"].id, permission_id=c.reg["doc_share"].permission_id
            ),
        ),
        _cleanup(
            "doc_link",
            ("DeleteDocumentWorkitemLink",),
            lambda c: c.api.document_workitem_links.delete(
                _a(c),
                document_id=c.reg["doc"].id,
                body=DeleteDocumentWorkitemLinkRequestBody(workitem=str(c.reg["item_b"].id), workitem_workspace=_b(c)),
            ),
        ),
        _cleanup(
            "doc_comment",
            ("DeleteDocumentComment",),
            lambda c: c.api.document_comments.delete(
                _a(c), document_id=c.reg["doc"].id, comment_id=c.reg["doc_comment"].id
            ),
        ),
        _cleanup("doc_versions", ("DeleteDocumentVersion",), _delete_doc_version, needs=("doc",)),
        _cleanup("doc", ("DeleteDocument",), lambda c: c.api.documents.delete(_a(c), document_id=c.reg["doc"].id)),
        _cleanup(
            "wi_att",
            ("DeleteWorkitemAttachmentVersion", "DeleteWorkitemAttachment", "DeleteWorkitemAttachments"),
            _delete_attachments("workitem_attachments", "workitem_id", "wi_att"),
            needs=("wi_att_owner",),
        ),
        _cleanup(
            "wi_share",
            ("DeleteSharedWorkitemPermission",),
            lambda c: c.api.workitem_sharing.delete(
                _a(c), workitem_id=c.reg["parent"].id, permission_id=c.reg["wi_share"].permission_id
            ),
        ),
        _cleanup("link", ("DeleteWorkitemLink",), lambda c: c.api.links.delete(_a(c), link_id=c.reg["link"].id)),
        _cleanup(
            "comment",
            ("DeleteWorkitemComment",),
            lambda c: c.api.workitem_comments.delete(
                _a(c), workitem_id=c.reg["parent"].id, comment_id=c.reg["comment"].id
            ),
        ),
        _cleanup(
            "element_link",
            (ELEMENT_UNLINK,),
            lambda c: c.api.portfolio_elements.unlink_workitem(
                _a(c), portfolio_element_id=c.reg["element"].id, workitem_id=c.reg["parent"].id
            ),
        ),
        _cleanup("child", ("DeleteWorkitem",), lambda c: c.api.workitems.delete(_a(c), workitem_id=c.reg["child"].id)),
        _cleanup(
            "parent", ("DeleteWorkitem",), lambda c: c.api.workitems.delete(_a(c), workitem_id=c.reg["parent"].id)
        ),
        _cleanup(
            "item_b", ("DeleteWorkitem",), lambda c: c.api.workitems.delete(_b(c), workitem_id=c.reg["item_b"].id)
        ),
        _cleanup(
            "element",
            (ELEMENT_DELETE,),
            lambda c: c.api.portfolio_elements.delete(_a(c), portfolio_element_id=c.reg["element"].id),
        ),
        _cleanup(
            "portfolio",
            (PORTFOLIO_DELETE,),
            lambda c: c.api.portfolios.delete(_a(c), portfolio_id=c.reg["portfolio"].id),
        ),
        _cleanup("sprint", ("DeleteSprint",), lambda c: c.api.sprints.delete(_a(c), sprint_id=c.reg["sprint"].id)),
        _cleanup("agile", ("DeleteAgile",), lambda c: c.api.agile.delete(_a(c), agile_id=c.reg["agile"].id)),
        _cleanup("type", ("DeleteType",), lambda c: c.api.types.delete(_a(c), type_key=str(c.reg["type"].id))),
        _cleanup(
            "attrs",
            ("DeleteAttribute",),
            lambda c: [c.api.attributes.delete(_a(c), attribute_id=x.id) for x in c.reg["attrs"].values()],
        ),
        _cleanup(
            "workflow",
            ("DeleteWorkflow",),
            lambda c: c.api.workflows.delete(_a(c), workflow_key=str(c.reg["workflow"].id)),
        ),
        _cleanup("role", ("DeleteRole",), _delete_role),
        _cleanup("members", ("RemoveWorkspaceUser",), _remove_members),
        _cleanup("sub", ("DeleteFolder",), lambda c: c.api.folders.delete(_a(c), folder_id=c.reg["sub"].id)),
        _cleanup("root", ("DeleteFolder",), lambda c: c.api.folders.delete(_a(c), folder_id=c.reg["root"].id)),
        _cleanup("ws_b", ("DeleteWorkspace",), lambda c: c.api.workspaces.delete(workspace_key=_b(c))),
        _cleanup("ws_a", ("DeleteWorkspace",), lambda c: c.api.workspaces.delete(workspace_key=_a(c))),
    ]
