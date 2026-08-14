import importlib
import os
import sys
import types
import unittest
from argparse import Namespace
from dataclasses import dataclass
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

from teamstorm.models.enums import AttributeType
from teamstorm.models.workitems_attributes_create import (
    CreateDateFieldRequestBody,
    CreateNumberFieldRequestBody,
    CreateTagFieldRequestBody,
    CreateTimeFieldRequestBody,
    CreateUniSelectFieldRequestBody,
    CreateUniStringFieldRequestBody,
    CreateUserFieldRequestBody,
)


def _load_import_agile_module():
    os.environ.setdefault("API_TOKEN", "test-token")
    os.environ.setdefault("BASE_URL", "https://example.test")
    if "dotenv" not in sys.modules:
        fake_dotenv = types.ModuleType("dotenv")
        fake_dotenv.load_dotenv = lambda: None
        sys.modules["dotenv"] = fake_dotenv

    module_name = "import_toolkit.workflows.imports.agile"
    if module_name in sys.modules:
        return importlib.reload(sys.modules[module_name])

    import import_toolkit.workflows.imports.agile as import_agile

    return import_agile


@dataclass(frozen=True)
class FixtureIds:
    workspace_id: UUID
    folder_id: UUID
    agile_id: UUID
    sprint_id: UUID
    created_workitem_id: UUID
    existing_workitem_id: UUID
    user_id: UUID


def _make_ids() -> FixtureIds:
    return FixtureIds(
        workspace_id=uuid4(),
        folder_id=uuid4(),
        agile_id=uuid4(),
        sprint_id=uuid4(),
        created_workitem_id=uuid4(),
        existing_workitem_id=uuid4(),
        user_id=uuid4(),
    )


def _build_args(
    *,
    update_settings: bool = False,
    sync_members: bool = False,
    dry_run: bool = False,
) -> Namespace:
    return Namespace(
        base_url="https://example.test",
        token="test-token",
        workspace_key="WS",
        folder_name="Folder",
        input_path="./dummy.xlsx",
        excel_path=None,
        dry_run=dry_run,
        update_settings=update_settings,
        sync_members=sync_members,
        allow_insecure=False,
        log_file="./logs/import_agile.test.log",
    )


def _build_task_row(
    module,
    *,
    row_ref: str,
    name: str,
    custom_attributes_raw: dict[str, str],
    assignee_username: str = "john",
    sprint_name: str = "S1",
    use_backlog: bool = False,
    workitem_type: str = "Bug",
    parent_cell: str = "",
):
    return {
        "row_ref": row_ref,
        "name": name,
        "description": f"{name} description",
        "assignee_username": assignee_username,
        "sprint_name": sprint_name,
        "use_backlog": use_backlog,
        "type": workitem_type,
        "start_date": date(2026, 3, 1),
        "end_date": date(2026, 3, 2),
        "parent_cell": parent_cell,
        "custom_attributes_raw": custom_attributes_raw,
    }


def _build_validated_import(module, *, tasks_rows):
    sprints_by_name = {
        "S1": {
            "name": "S1",
            "start_date": date(2026, 3, 1),
            "end_date": date(2026, 3, 14),
        }
    }
    return sprints_by_name, tasks_rows, [], []


def _build_api_mock(ids: FixtureIds):
    user = SimpleNamespace(
        id=ids.user_id,
        username="john",
        email="john@example.com",
        display_name="John Doe",
    )
    bug_type = SimpleNamespace(name="Bug", attributes=[])
    workspace = SimpleNamespace(id=ids.workspace_id)
    folder = SimpleNamespace(id=ids.folder_id)
    agile = SimpleNamespace(id=ids.agile_id)
    sprint = SimpleNamespace(id=ids.sprint_id, name="S1")

    def users_lookup(**kwargs):
        if kwargs.get("username") == "john":
            return [user]
        if kwargs.get("email") == "john@example.com":
            return [user]
        if kwargs.get("display_name") == "John Doe":
            return [user]
        return []

    def update_attribute_ok(*args, **kwargs):
        body = kwargs.get("body")
        if body is None:
            return SimpleNamespace(id=uuid4())
        if body.type == AttributeType.UniSelect:
            return SimpleNamespace(
                type=AttributeType.UniSelect,
                value=SimpleNamespace(id=body.value, name="resolved"),
            )
        if body.type == AttributeType.Tag:
            return SimpleNamespace(
                type=AttributeType.Tag,
                value=[SimpleNamespace(id=value, name=str(value)) for value in (body.value or [])],
            )
        return SimpleNamespace(
            id=uuid4(),
            type=body.type,
            value=getattr(body, "value", None),
        )

    api = SimpleNamespace(
        workspaces=SimpleNamespace(
            list=MagicMock(return_value=[workspace]),
        ),
        folders=SimpleNamespace(
            list=MagicMock(return_value=[folder]),
            create=MagicMock(return_value=folder),
        ),
        agile=SimpleNamespace(
            list=MagicMock(return_value=[agile]),
            create=MagicMock(return_value=agile),
        ),
        sprints=SimpleNamespace(
            list=MagicMock(return_value=[sprint]),
            create=MagicMock(return_value=sprint),
            patch=MagicMock(return_value=sprint),
        ),
        workitems=SimpleNamespace(
            list=MagicMock(return_value=[]),
            create=MagicMock(return_value=SimpleNamespace(id=ids.created_workitem_id)),
            patch=MagicMock(return_value=SimpleNamespace(id=ids.created_workitem_id)),
            list_attributes=MagicMock(return_value=[]),
            update_attribute=MagicMock(side_effect=update_attribute_ok),
        ),
        users=SimpleNamespace(
            list=MagicMock(side_effect=users_lookup),
        ),
        types=SimpleNamespace(
            list=MagicMock(return_value=[bug_type]),
            create=MagicMock(return_value=bug_type),
            add_attribute=MagicMock(return_value=bug_type),
            get=MagicMock(return_value=bug_type),
        ),
        attributes=SimpleNamespace(
            list=MagicMock(return_value=[]),
            get=MagicMock(return_value=SimpleNamespace(options=[])),
            create=MagicMock(),
            add_option=MagicMock(),
        ),
        workflows=SimpleNamespace(
            list=MagicMock(return_value=[SimpleNamespace(name="Default Workflow")]),
        ),
        roles=SimpleNamespace(
            list=MagicMock(return_value=[]),
        ),
        workspace_users=SimpleNamespace(
            list=MagicMock(return_value=[]),
            add=MagicMock(),
            add_role=MagicMock(),
        ),
    )
    return api, SimpleNamespace(user=user, bug_type=bug_type)


def _run_main(module, *, args: Namespace, validated_import, api):
    logger = MagicMock()
    reader = SimpleNamespace(load=MagicMock(return_value=validated_import))

    with (
        patch.object(module.argparse.ArgumentParser, "parse_args", return_value=args),
        patch.object(module, "setup_logging", return_value=logger),
        patch.object(module, "select_reader", return_value=reader),
        patch.object(module, "TsClient", return_value=MagicMock(name="client")),
        patch.object(module, "TeamStormAPI", return_value=api),
    ):
        exit_code = module.main()

    return exit_code, logger


class ImportAgileEndToEndMockedTestCase(unittest.TestCase):
    def test_create_new_workitem_with_attributes(self) -> None:
        module = _load_import_agile_module()
        ids = _make_ids()
        api, state = _build_api_mock(ids)
        severity_attr_id = uuid4()
        severity_attr = SimpleNamespace(
            id=severity_attr_id,
            name="Severity",
            type=AttributeType.UniString,
            options=None,
        )
        api.attributes.list.return_value = [severity_attr]
        state.bug_type.attributes = [severity_attr]

        task = _build_task_row(
            module,
            row_ref="Sheet2 row 2",
            name="Task-Create",
            custom_attributes_raw={"Severity[UniString]": "High"},
        )
        validated = _build_validated_import(module, tasks_rows=[task])
        args = _build_args(update_settings=False)

        code, _ = _run_main(module, args=args, validated_import=validated, api=api)

        self.assertEqual(0, code)
        api.workitems.create.assert_called_once()
        create_body = api.workitems.create.call_args.args[1]
        self.assertIsNotNone(create_body.attributes)
        self.assertEqual(1, len(create_body.attributes))
        payload = create_body.attributes[0]
        self.assertIsInstance(payload, CreateUniStringFieldRequestBody)
        self.assertEqual(AttributeType.UniString, payload.type)
        self.assertEqual(severity_attr_id, payload.id)
        self.assertEqual("High", payload.value)
        api.workitems.patch.assert_called_once()
        api.workitems.update_attribute.assert_called_once()
        update_kwargs = api.workitems.update_attribute.call_args.kwargs
        self.assertEqual(severity_attr_id, update_kwargs["attribute_id"])

    def test_create_new_workitem_upserts_all_custom_attribute_types(self) -> None:
        module = _load_import_agile_module()
        ids = _make_ids()
        api, state = _build_api_mock(ids)

        comment_attr_id = uuid4()
        estimate_attr_id = uuid4()
        target_attr_id = uuid4()
        severity_attr_id = uuid4()
        tags_attr_id = uuid4()
        reviewer_attr_id = uuid4()
        spent_attr_id = uuid4()
        high_id = uuid4()
        alpha_id = uuid4()
        beta_id = uuid4()

        attributes = [
            SimpleNamespace(
                id=comment_attr_id,
                name="comment",
                type=AttributeType.UniString,
                options=None,
            ),
            SimpleNamespace(
                id=estimate_attr_id,
                name="estimate",
                type=AttributeType.Number,
                options=None,
            ),
            SimpleNamespace(
                id=target_attr_id,
                name="target_date",
                type=AttributeType.Date,
                options=None,
            ),
            SimpleNamespace(
                id=severity_attr_id,
                name="severity",
                type=AttributeType.UniSelect,
                options=[SimpleNamespace(name="High", id=high_id)],
            ),
            SimpleNamespace(
                id=tags_attr_id,
                name="tags",
                type=AttributeType.Tag,
                options=[
                    SimpleNamespace(name="alpha", id=alpha_id),
                    SimpleNamespace(name="beta", id=beta_id),
                ],
            ),
            SimpleNamespace(
                id=reviewer_attr_id,
                name="reviewer",
                type=AttributeType.User,
                options=None,
            ),
            SimpleNamespace(
                id=spent_attr_id,
                name="spent",
                type=AttributeType.TimeDuration,
                options=None,
            ),
        ]
        api.attributes.list.return_value = attributes
        state.bug_type.attributes = attributes
        api.workitems.list_attributes.return_value = [SimpleNamespace(id=a.id) for a in attributes]

        task = _build_task_row(
            module,
            row_ref="Sheet2 row 2",
            name="Task-All-Types",
            custom_attributes_raw={
                "comment[UniString]": "TXT-01",
                "estimate[Number]": "2.5",
                "target_date[Date]": "2026-03-08",
                "severity[UniSelect]": "High",
                "tags[Tag]": "alpha,beta",
                "reviewer[User]": "john@example.com",
                "spent[TimeDuration]": "30m",
            },
        )
        validated = _build_validated_import(module, tasks_rows=[task])
        args = _build_args(update_settings=False)

        code, _ = _run_main(module, args=args, validated_import=validated, api=api)

        self.assertEqual(0, code)
        api.workitems.create.assert_called_once()
        create_body = api.workitems.create.call_args.args[1]
        self.assertIsNotNone(create_body.attributes)
        self.assertEqual(7, len(create_body.attributes))
        create_types = {type(item) for item in create_body.attributes}
        self.assertEqual(
            {
                CreateUniStringFieldRequestBody,
                CreateNumberFieldRequestBody,
                CreateDateFieldRequestBody,
                CreateUniSelectFieldRequestBody,
                CreateTagFieldRequestBody,
                CreateUserFieldRequestBody,
                CreateTimeFieldRequestBody,
            },
            create_types,
        )
        api.workitems.patch.assert_called_once()
        self.assertEqual(7, api.workitems.update_attribute.call_count)
        updated_ids = {call.kwargs["attribute_id"] for call in api.workitems.update_attribute.call_args_list}
        self.assertEqual(
            {
                comment_attr_id,
                estimate_attr_id,
                target_attr_id,
                severity_attr_id,
                tags_attr_id,
                reviewer_attr_id,
                spent_attr_id,
            },
            updated_ids,
        )

    def test_patch_existing_then_update_attributes(self) -> None:
        module = _load_import_agile_module()
        ids = _make_ids()
        api, state = _build_api_mock(ids)
        events: list[str] = []
        severity_attr_id = uuid4()
        severity_attr = SimpleNamespace(
            id=severity_attr_id,
            name="Severity",
            type=AttributeType.UniString,
            options=None,
        )
        api.attributes.list.return_value = [severity_attr]
        state.bug_type.attributes = [severity_attr]
        api.workitems.list.side_effect = lambda *args, **kwargs: events.append("workitems_list") or [
            SimpleNamespace(id=ids.existing_workitem_id)
        ]
        api.workitems.patch.side_effect = lambda *args, **kwargs: events.append("workitems_patch") or SimpleNamespace(
            id=ids.existing_workitem_id
        )
        api.workitems.list_attributes.side_effect = lambda *args, **kwargs: events.append("list_attributes") or [
            SimpleNamespace(id=uuid4())
        ]
        api.workitems.update_attribute.side_effect = lambda *args, **kwargs: events.append(
            "update_attribute"
        ) or SimpleNamespace(id=uuid4())

        task = _build_task_row(
            module,
            row_ref="Sheet2 row 2",
            name="Task-Existing",
            custom_attributes_raw={"Severity[UniString]": "High"},
        )
        validated = _build_validated_import(module, tasks_rows=[task])
        args = _build_args(update_settings=False)

        code, _ = _run_main(module, args=args, validated_import=validated, api=api)

        self.assertEqual(0, code)
        api.workitems.create.assert_not_called()
        api.workitems.patch.assert_called_once()
        api.workitems.update_attribute.assert_called_once()
        update_kwargs = api.workitems.update_attribute.call_args.kwargs
        self.assertEqual(severity_attr_id, update_kwargs["attribute_id"])
        self.assertLess(events.index("workitems_patch"), events.index("update_attribute"))

    def test_uniselect_persistent_mismatch_is_non_fatal_for_exit_code(self) -> None:
        module = _load_import_agile_module()
        ids = _make_ids()
        api, state = _build_api_mock(ids)
        severity_attr_id = uuid4()
        high_id = uuid4()
        severity_attr = SimpleNamespace(
            id=severity_attr_id,
            name="Severity",
            type=AttributeType.UniSelect,
            options=[SimpleNamespace(name="High", id=high_id)],
        )
        api.attributes.list.return_value = [severity_attr]
        api.attributes.get.return_value = severity_attr
        state.bug_type.attributes = [severity_attr]
        api.workitems.list.return_value = []
        api.workitems.list_attributes.side_effect = [
            [SimpleNamespace(id=severity_attr_id)],
            [
                SimpleNamespace(
                    id=severity_attr_id,
                    type=AttributeType.UniSelect,
                    value=None,
                )
            ],
        ]
        api.workitems.update_attribute.side_effect = [
            SimpleNamespace(type=AttributeType.UniSelect, value=None),
            SimpleNamespace(type=AttributeType.UniSelect, value=None),
        ]

        task = _build_task_row(
            module,
            row_ref="Sheet2 row 2",
            name="Task-Select-Mismatch",
            custom_attributes_raw={"Severity[UniSelect]": "High"},
        )
        validated = _build_validated_import(module, tasks_rows=[task])
        args = _build_args(update_settings=False)

        code, logger = _run_main(module, args=args, validated_import=validated, api=api)

        self.assertEqual(0, code)
        self.assertEqual(2, api.workitems.update_attribute.call_count)
        retry_body = api.workitems.update_attribute.call_args_list[1].kwargs["body"]
        self.assertEqual("High", retry_body.value)
        self.assertTrue(any("Non-fatal UniSelect/Tag row failures" in str(call) for call in logger.info.call_args_list))
        self.assertTrue(any("mismatch after retry" in str(call) for call in logger.warning.call_args_list))

    def test_non_select_update_failure_still_fails_run(self) -> None:
        module = _load_import_agile_module()
        ids = _make_ids()
        api, state = _build_api_mock(ids)
        comment_attr_id = uuid4()
        comment_attr = SimpleNamespace(
            id=comment_attr_id,
            name="comment",
            type=AttributeType.UniString,
            options=None,
        )
        api.attributes.list.return_value = [comment_attr]
        state.bug_type.attributes = [comment_attr]
        api.workitems.list.return_value = []
        api.workitems.list_attributes.return_value = [SimpleNamespace(id=comment_attr_id)]
        api.workitems.update_attribute.side_effect = RuntimeError("boom")

        task = _build_task_row(
            module,
            row_ref="Sheet2 row 2",
            name="Task-String-Failure",
            custom_attributes_raw={"comment[UniString]": "TXT-01"},
        )
        validated = _build_validated_import(module, tasks_rows=[task])
        args = _build_args(update_settings=False)

        code, logger = _run_main(module, args=args, validated_import=validated, api=api)

        self.assertEqual(1, code)
        self.assertTrue(any("Workitem ATTRIBUTE UPDATE failed" in str(call) for call in logger.error.call_args_list))

    def test_sync_settings_then_import_tasks(self) -> None:
        module = _load_import_agile_module()
        ids = _make_ids()
        api, state = _build_api_mock(ids)
        events: list[str] = []
        created_attr_id = uuid4()
        created_attr = SimpleNamespace(
            id=created_attr_id,
            name="Severity",
            type=AttributeType.UniString,
            options=None,
        )

        api.attributes.list.side_effect = lambda *args, **kwargs: events.append("sync_attributes_list") or []
        api.attributes.create.side_effect = (
            lambda *args, **kwargs: events.append("sync_attributes_create") or created_attr
        )
        api.types.list.side_effect = lambda *args, **kwargs: events.append("sync_types_list") or [state.bug_type]
        api.workflows.list.side_effect = lambda *args, **kwargs: events.append("sync_workflows_list") or [
            SimpleNamespace(name="WF")
        ]

        def add_attribute(*args, **kwargs):
            events.append("sync_types_link")
            state.bug_type.attributes = [created_attr]
            return state.bug_type

        api.types.add_attribute.side_effect = add_attribute
        api.workitems.list.side_effect = lambda *args, **kwargs: events.append("workitems_list") or []

        task = _build_task_row(
            module,
            row_ref="Sheet2 row 2",
            name="Task-With-Sync",
            custom_attributes_raw={"Severity[UniString]": "High"},
        )
        validated = _build_validated_import(module, tasks_rows=[task])
        args = _build_args(update_settings=True)

        code, _ = _run_main(module, args=args, validated_import=validated, api=api)

        self.assertEqual(0, code)
        self.assertTrue(api.attributes.create.called)
        self.assertTrue(api.types.add_attribute.called)
        self.assertLess(events.index("sync_attributes_list"), events.index("workitems_list"))
        create_body = api.workitems.create.call_args.args[1]
        self.assertEqual(created_attr_id, create_body.attributes[0].id)

    def test_tag_option_create_and_reuse(self) -> None:
        module = _load_import_agile_module()
        ids = _make_ids()
        api, state = _build_api_mock(ids)
        tags_attr_id = uuid4()
        tags_attr = SimpleNamespace(
            id=tags_attr_id,
            name="Tags",
            type=AttributeType.Tag,
            options=None,
        )
        api.attributes.list.return_value = [tags_attr]
        state.bug_type.attributes = [tags_attr]

        option_store: dict[str, tuple[str, UUID]] = {}

        def add_option(workspace_key, *, attribute_id, body):
            key = body.name.casefold()
            if key not in option_store:
                option_store[key] = (body.name, uuid4())
            return SimpleNamespace(
                options=[SimpleNamespace(name=name, id=option_id) for name, option_id in option_store.values()]
            )

        api.attributes.add_option.side_effect = add_option
        api.workitems.create.side_effect = [
            SimpleNamespace(id=uuid4()),
            SimpleNamespace(id=uuid4()),
        ]

        task_1 = _build_task_row(
            module,
            row_ref="Sheet2 row 2",
            name="Task-Tag-1",
            custom_attributes_raw={"Tags[Tag]": "alpha,beta"},
        )
        task_2 = _build_task_row(
            module,
            row_ref="Sheet2 row 3",
            name="Task-Tag-2",
            custom_attributes_raw={"Tags[Tag]": "beta;gamma"},
        )
        validated = _build_validated_import(module, tasks_rows=[task_1, task_2])
        args = _build_args(update_settings=True)

        code, _ = _run_main(module, args=args, validated_import=validated, api=api)

        self.assertEqual(0, code)
        self.assertEqual(3, api.attributes.add_option.call_count)
        self.assertEqual(2, api.workitems.create.call_count)

        create_body_1 = api.workitems.create.call_args_list[0].args[1]
        create_body_2 = api.workitems.create.call_args_list[1].args[1]
        payload_1 = create_body_1.attributes[0]
        payload_2 = create_body_2.attributes[0]
        self.assertIsInstance(payload_1, CreateTagFieldRequestBody)
        self.assertIsInstance(payload_2, CreateTagFieldRequestBody)

        alpha_id = str(option_store["alpha"][1])
        beta_id = str(option_store["beta"][1])
        gamma_id = str(option_store["gamma"][1])
        self.assertEqual([alpha_id, beta_id], payload_1.value)
        self.assertEqual([beta_id, gamma_id], payload_2.value)

    def test_user_attribute_resolution(self) -> None:
        module = _load_import_agile_module()
        ids = _make_ids()
        api, state = _build_api_mock(ids)
        watcher_attr_id = uuid4()
        watcher_attr = SimpleNamespace(
            id=watcher_attr_id,
            name="Watcher",
            type=AttributeType.User,
            options=None,
        )
        api.attributes.list.return_value = [watcher_attr]
        state.bug_type.attributes = [watcher_attr]

        task_1 = _build_task_row(
            module,
            row_ref="Sheet2 row 2",
            name="Task-User-Resolved",
            custom_attributes_raw={"Watcher[User]": "john@example.com"},
        )
        task_2 = _build_task_row(
            module,
            row_ref="Sheet2 row 3",
            name="Task-User-Unresolved",
            custom_attributes_raw={"Watcher[User]": "ghost@example.com"},
        )
        validated = _build_validated_import(module, tasks_rows=[task_1, task_2])
        args = _build_args(update_settings=False)

        code, logger = _run_main(module, args=args, validated_import=validated, api=api)

        self.assertEqual(0, code)
        self.assertEqual(2, api.workitems.create.call_count)

        create_body_1 = api.workitems.create.call_args_list[0].args[1]
        create_body_2 = api.workitems.create.call_args_list[1].args[1]
        self.assertIsNotNone(create_body_1.attributes)
        self.assertIsNone(create_body_2.attributes)

        payload = create_body_1.attributes[0]
        self.assertIsInstance(payload, CreateUserFieldRequestBody)
        self.assertEqual(state.user.id, payload.value.id)
        self.assertEqual("john", payload.value.user_name)
        self.assertTrue(any("ghost@example.com" in str(call) for call in logger.warning.call_args_list))

    def test_multilevel_parent_task_and_blank_parent_reset(self) -> None:
        module = _load_import_agile_module()
        ids = _make_ids()
        api, _ = _build_api_mock(ids)

        parent_id = uuid4()
        child_id = uuid4()
        reset_id = uuid4()
        api.workitems.create.side_effect = [
            SimpleNamespace(id=parent_id),
            SimpleNamespace(id=child_id),
            SimpleNamespace(id=reset_id),
        ]

        parent = _build_task_row(
            module,
            row_ref="Sheet2 row 2",
            name="Parent-Task",
            custom_attributes_raw={},
            parent_cell="",
        )
        child = _build_task_row(
            module,
            row_ref="Sheet2 row 3",
            name="Child-Task",
            custom_attributes_raw={},
            parent_cell="Parent-Task",
        )
        root_again = _build_task_row(
            module,
            row_ref="Sheet2 row 4",
            name="Root-Again",
            custom_attributes_raw={},
            parent_cell="",
        )
        validated = _build_validated_import(module, tasks_rows=[parent, child, root_again])

        code, _ = _run_main(module, args=_build_args(), validated_import=validated, api=api)

        self.assertEqual(0, code)
        self.assertEqual(3, api.workitems.create.call_count)
        create_parent = api.workitems.create.call_args_list[0].args[1]
        create_child = api.workitems.create.call_args_list[1].args[1]
        create_reset = api.workitems.create.call_args_list[2].args[1]
        self.assertEqual(ids.folder_id, create_parent.parent_id)
        self.assertEqual(parent_id, create_child.parent_id)
        self.assertEqual(ids.folder_id, create_reset.parent_id)

    def test_forward_reference_parent_task_is_resolved(self) -> None:
        module = _load_import_agile_module()
        ids = _make_ids()
        api, _ = _build_api_mock(ids)

        parent_id = uuid4()
        child_id = uuid4()
        api.workitems.create.side_effect = [
            SimpleNamespace(id=parent_id),
            SimpleNamespace(id=child_id),
        ]

        child = _build_task_row(
            module,
            row_ref="Sheet2 row 2",
            name="Child-Task",
            custom_attributes_raw={},
            parent_cell="Parent-Task",
        )
        parent = _build_task_row(
            module,
            row_ref="Sheet2 row 3",
            name="Parent-Task",
            custom_attributes_raw={},
            parent_cell="",
        )
        validated = _build_validated_import(module, tasks_rows=[child, parent])

        code, _ = _run_main(module, args=_build_args(), validated_import=validated, api=api)

        self.assertEqual(0, code)
        self.assertEqual(2, api.workitems.create.call_count)
        create_parent = api.workitems.create.call_args_list[0].args[1]
        create_child = api.workitems.create.call_args_list[1].args[1]
        self.assertEqual("Parent-Task", create_parent.name)
        self.assertEqual("Child-Task", create_child.name)
        self.assertEqual(ids.folder_id, create_parent.parent_id)
        self.assertEqual(parent_id, create_child.parent_id)

    def test_parent_folder_fallback_creates_and_reuses_subfolder(self) -> None:
        module = _load_import_agile_module()
        ids = _make_ids()
        api, _ = _build_api_mock(ids)

        subfolder_id = uuid4()
        root_folder = SimpleNamespace(id=ids.folder_id)
        subfolder = SimpleNamespace(id=subfolder_id)

        def folders_list(workspace_key, *, name=None, parent_id=None):
            if name == "Folder" and parent_id == ids.workspace_id:
                return [root_folder]
            if name == "Platform" and parent_id == ids.folder_id:
                return []
            return []

        api.folders.list.side_effect = folders_list
        api.folders.create.return_value = subfolder

        task_1 = _build_task_row(
            module,
            row_ref="Sheet2 row 2",
            name="Task-1",
            custom_attributes_raw={},
            parent_cell="Platform",
        )
        task_2 = _build_task_row(
            module,
            row_ref="Sheet2 row 3",
            name="Task-2",
            custom_attributes_raw={},
            parent_cell="Platform",
        )
        validated = _build_validated_import(module, tasks_rows=[task_1, task_2])

        code, _ = _run_main(module, args=_build_args(), validated_import=validated, api=api)

        self.assertEqual(0, code)
        self.assertEqual(1, api.folders.create.call_count)
        self.assertEqual(2, api.workitems.create.call_count)
        create_1 = api.workitems.create.call_args_list[0].args[1]
        create_2 = api.workitems.create.call_args_list[1].args[1]
        self.assertEqual(subfolder_id, create_1.parent_id)
        self.assertEqual(subfolder_id, create_2.parent_id)

    def test_duplicate_parent_name_uses_first_and_logs_warning(self) -> None:
        module = _load_import_agile_module()
        ids = _make_ids()
        api, _ = _build_api_mock(ids)

        first_parent_id = uuid4()
        second_parent_id = uuid4()
        child_id = uuid4()
        api.workitems.create.side_effect = [
            SimpleNamespace(id=first_parent_id),
            SimpleNamespace(id=second_parent_id),
            SimpleNamespace(id=child_id),
        ]

        parent_1 = _build_task_row(
            module,
            row_ref="Sheet2 row 2",
            name="Parent",
            custom_attributes_raw={},
        )
        parent_2 = _build_task_row(
            module,
            row_ref="Sheet2 row 3",
            name="Parent",
            custom_attributes_raw={},
        )
        child = _build_task_row(
            module,
            row_ref="Sheet2 row 4",
            name="Child",
            custom_attributes_raw={},
            parent_cell="Parent",
        )
        validated = _build_validated_import(module, tasks_rows=[parent_1, parent_2, child])

        code, logger = _run_main(module, args=_build_args(), validated_import=validated, api=api)

        self.assertEqual(0, code)
        self.assertEqual(3, api.workitems.create.call_count)
        child_body = api.workitems.create.call_args_list[2].args[1]
        self.assertEqual(first_parent_id, child_body.parent_id)
        self.assertTrue(any("неоднозначен" in str(call) for call in logger.warning.call_args_list))

    def test_task_without_sprint_is_created_without_sprint_id(self) -> None:
        module = _load_import_agile_module()
        ids = _make_ids()
        api, _ = _build_api_mock(ids)

        task = _build_task_row(
            module,
            row_ref="Sheet2 row 2",
            name="Task-No-Sprint",
            sprint_name="",
            custom_attributes_raw={},
        )
        validated = ({}, [task], [], [])

        code, _ = _run_main(module, args=_build_args(), validated_import=validated, api=api)

        self.assertEqual(0, code)
        api.agile.list.assert_not_called()
        api.agile.create.assert_not_called()
        create_body = api.workitems.create.call_args.args[1]
        self.assertIsNone(create_body.sprint_id)
        list_kwargs = api.workitems.list.call_args.kwargs
        self.assertNotIn("sprint_id", list_kwargs)

    def test_mixed_tasks_with_and_without_sprint(self) -> None:
        module = _load_import_agile_module()
        ids = _make_ids()
        api, _ = _build_api_mock(ids)

        task_no_sprint = _build_task_row(
            module,
            row_ref="Sheet2 row 2",
            name="Task-No-Sprint",
            sprint_name="",
            custom_attributes_raw={},
        )
        task_with_sprint = _build_task_row(
            module,
            row_ref="Sheet2 row 3",
            name="Task-With-Sprint",
            sprint_name="S1",
            custom_attributes_raw={},
        )
        validated = _build_validated_import(module, tasks_rows=[task_no_sprint, task_with_sprint])

        code, _ = _run_main(module, args=_build_args(), validated_import=validated, api=api)

        self.assertEqual(0, code)
        self.assertEqual(2, api.workitems.create.call_count)
        create_no_sprint = api.workitems.create.call_args_list[0].args[1]
        create_with_sprint = api.workitems.create.call_args_list[1].args[1]
        self.assertIsNone(create_no_sprint.sprint_id)
        self.assertEqual(ids.sprint_id, create_with_sprint.sprint_id)

    def test_auto_inferred_sprint_is_created_and_assigned(self) -> None:
        module = _load_import_agile_module()
        ids = _make_ids()
        api, _ = _build_api_mock(ids)
        api.sprints.list.return_value = []

        inferred_sprint_name = "Sprint-Inferred"
        task = _build_task_row(
            module,
            row_ref="Sheet2 row 2",
            name="Task-Inferred-Sprint",
            sprint_name=inferred_sprint_name,
            custom_attributes_raw={},
        )
        validated = (
            {
                inferred_sprint_name: {
                    "name": inferred_sprint_name,
                    "start_date": date(2026, 3, 1),
                    "end_date": date(2026, 3, 14),
                }
            },
            [task],
            [],
            [],
        )

        code, _ = _run_main(module, args=_build_args(), validated_import=validated, api=api)

        self.assertEqual(0, code)
        api.sprints.create.assert_called_once()
        api.agile.list.assert_called_once()
        create_sprint_body = api.sprints.create.call_args.args[1]
        self.assertEqual(inferred_sprint_name, create_sprint_body.name)

        create_task_body = api.workitems.create.call_args.args[1]
        self.assertEqual(ids.sprint_id, create_task_body.sprint_id)

    def test_backlog_marker_row_uses_backlog_sprint_id(self) -> None:
        module = _load_import_agile_module()
        ids = _make_ids()
        api, _ = _build_api_mock(ids)
        backlog_id = uuid4()

        def sprints_list(workspace_key, *, folder_id=None, name=None):
            if folder_id == ids.folder_id and name is None:
                return [SimpleNamespace(id=backlog_id, name="Backlog", is_backlog=True)]
            return []

        api.sprints.list.side_effect = sprints_list

        backlog_task = _build_task_row(
            module,
            row_ref="tasks row 2",
            name="Task-Backlog",
            sprint_name="backlog",
            use_backlog=True,
            custom_attributes_raw={},
        )
        validated = ({}, [backlog_task], [], [])

        code, _ = _run_main(module, args=_build_args(), validated_import=validated, api=api)

        self.assertEqual(0, code)
        api.agile.list.assert_called_once()
        create_task_body = api.workitems.create.call_args.args[1]
        self.assertEqual(backlog_id, create_task_body.sprint_id)

    def test_mixed_backlog_named_and_unsprinted_rows(self) -> None:
        module = _load_import_agile_module()
        ids = _make_ids()
        api, _ = _build_api_mock(ids)
        backlog_id = uuid4()

        def sprints_list(workspace_key, *, folder_id=None, name=None):
            if folder_id == ids.folder_id and name == "S1":
                return [SimpleNamespace(id=ids.sprint_id, name="S1", is_backlog=False)]
            if folder_id == ids.folder_id and name is None:
                return [SimpleNamespace(id=backlog_id, name="Backlog", is_backlog=True)]
            return []

        api.sprints.list.side_effect = sprints_list

        backlog_task = _build_task_row(
            module,
            row_ref="tasks row 2",
            name="Task-Backlog",
            sprint_name="Backlog data",
            use_backlog=True,
            custom_attributes_raw={},
        )
        named_task = _build_task_row(
            module,
            row_ref="tasks row 3",
            name="Task-S1",
            sprint_name="S1",
            use_backlog=False,
            custom_attributes_raw={},
        )
        unsprinted_task = _build_task_row(
            module,
            row_ref="tasks row 4",
            name="Task-No-Sprint",
            sprint_name="",
            use_backlog=False,
            custom_attributes_raw={},
        )
        validated = _build_validated_import(module, tasks_rows=[backlog_task, named_task, unsprinted_task])

        code, _ = _run_main(module, args=_build_args(), validated_import=validated, api=api)

        self.assertEqual(0, code)
        self.assertEqual(3, api.workitems.create.call_count)
        create_backlog = api.workitems.create.call_args_list[0].args[1]
        create_named = api.workitems.create.call_args_list[1].args[1]
        create_unsprinted = api.workitems.create.call_args_list[2].args[1]
        self.assertEqual(backlog_id, create_backlog.sprint_id)
        self.assertEqual(ids.sprint_id, create_named.sprint_id)
        self.assertIsNone(create_unsprinted.sprint_id)

    def test_missing_backlog_sprint_produces_row_error(self) -> None:
        module = _load_import_agile_module()
        ids = _make_ids()
        api, _ = _build_api_mock(ids)
        api.sprints.list.side_effect = lambda *args, **kwargs: []

        backlog_task = _build_task_row(
            module,
            row_ref="tasks row 2",
            name="Task-Backlog",
            sprint_name="backlog",
            use_backlog=True,
            custom_attributes_raw={},
        )
        validated = ({}, [backlog_task], [], [])

        code, logger = _run_main(module, args=_build_args(), validated_import=validated, api=api)

        self.assertEqual(1, code)
        self.assertTrue(any("backlog sprint" in str(call) for call in logger.error.call_args_list))

    def test_ambiguous_backlog_sprints_produce_row_error(self) -> None:
        module = _load_import_agile_module()
        ids = _make_ids()
        api, _ = _build_api_mock(ids)
        backlog_1 = SimpleNamespace(id=uuid4(), name="Backlog A", is_backlog=True)
        backlog_2 = SimpleNamespace(id=uuid4(), name="Backlog B", is_backlog=True)
        api.sprints.list.side_effect = lambda *args, **kwargs: (
            [backlog_1, backlog_2] if kwargs.get("name") is None else []
        )

        backlog_task = _build_task_row(
            module,
            row_ref="tasks row 2",
            name="Task-Backlog",
            sprint_name="backlog",
            use_backlog=True,
            custom_attributes_raw={},
        )
        validated = ({}, [backlog_task], [], [])

        code, logger = _run_main(module, args=_build_args(), validated_import=validated, api=api)

        self.assertEqual(1, code)
        self.assertTrue(any("найдено >1 backlog sprint" in str(call) for call in logger.error.call_args_list))


if __name__ == "__main__":
    unittest.main()
