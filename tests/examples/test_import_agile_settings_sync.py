import importlib
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from datetime import date

from import_toolkit.controllers.core.attributes import sync_attributes
from import_toolkit.controllers.core.contracts import CustomAttributeSpec, SyncedAttribute
from import_toolkit.controllers.core.membership import sync_workspace_members
from import_toolkit.controllers.core.types import sync_types
from teamstorm.models.enums import AttributeType


def _load_attributes_module():
    if "import_toolkit.workflows.imports.settings_sync" in sys.modules:
        return importlib.reload(sys.modules["import_toolkit.workflows.imports.settings_sync"])
    import import_toolkit.workflows.imports.settings_sync as settings_sync

    return settings_sync


def _build_api() -> SimpleNamespace:
    return SimpleNamespace(
        attributes=SimpleNamespace(
            list=MagicMock(return_value=[]),
            create=MagicMock(),
            add_option=MagicMock(),
        ),
        types=SimpleNamespace(
            list=MagicMock(return_value=[]),
            create=MagicMock(),
            add_attribute=MagicMock(),
        ),
        workflows=SimpleNamespace(list=MagicMock(return_value=[])),
        users=SimpleNamespace(list=MagicMock(return_value=[])),
        roles=SimpleNamespace(list=MagicMock(return_value=[])),
        workspace_users=SimpleNamespace(
            list=MagicMock(return_value=[]),
            add=MagicMock(),
            add_role=MagicMock(),
        ),
    )


class ImportAgileSettingsSyncTestCase(unittest.TestCase):
    def test_run_settings_sync_order_when_enabled(self) -> None:
        module = _load_attributes_module()
        api = _build_api()
        log = MagicMock()
        warnings: list[str] = []
        calls: list[str] = []

        with (
            patch.object(
                module,
                "sync_statuses",
                side_effect=lambda *args, **kwargs: calls.append("statuses"),
            ),
            patch.object(
                module,
                "sync_workflows",
                side_effect=lambda *args, **kwargs: calls.append("workflows"),
            ),
            patch.object(
                module,
                "sync_roles",
                side_effect=lambda *args, **kwargs: calls.append("roles"),
            ),
            patch.object(
                module,
                "sync_attributes",
                side_effect=lambda *args, **kwargs: calls.append("attributes") or {},
            ),
            patch.object(
                module,
                "sync_types",
                side_effect=lambda *args, **kwargs: calls.append("types") or set(),
            ),
            patch.object(
                module,
                "sync_workspace_members",
                side_effect=lambda *args, **kwargs: calls.append("members") or {},
            ),
        ):
            module.run_settings_sync(
                api,
                workspace_key="WS",
                tasks_rows=[],
                update_settings=True,
                sync_members=False,
                dry_run=False,
                log=log,
                warnings=warnings,
            )

        self.assertEqual(
            ["statuses", "workflows", "roles", "attributes", "types", "members"],
            calls,
        )

    def test_sync_attributes_marker_parse_and_unknown_fallback(self) -> None:
        api = _build_api()
        log = MagicMock()
        warnings: list[str] = []

        created_severity = SimpleNamespace(
            id=uuid4(),
            name="Severity",
            type=AttributeType.UniSelect,
            options=None,
        )
        created_watcher = SimpleNamespace(
            id=uuid4(),
            name="Watcher",
            type=AttributeType.User,
            options=None,
        )
        created_unknown = SimpleNamespace(
            id=uuid4(),
            name="Unknown",
            type=AttributeType.UniString,
            options=None,
        )
        api.attributes.create.side_effect = [
            created_severity,
            created_watcher,
            created_unknown,
        ]

        tasks_rows = [
            {
                "row_ref": "r1",
                "name": "Task",
                "description": "d",
                "assignee_username": "john",
                "sprint_name": "S1",
                "type": "Bug",
                "start_date": date(2026, 3, 18),
                "end_date": date(2026, 3, 19),
                "custom_attributes_raw": {
                    "Severity[UniSelect]": "High",
                    "Watcher[User]": "john",
                    "Unknown[MagicType]": "abc",
                },
            }
        ]

        synced = sync_attributes(
            api,
            workspace_key="WS",
            tasks_rows=tasks_rows,
            update_settings=True,
            dry_run=False,
            log=log,
            warnings=warnings,
        )

        self.assertEqual(3, api.attributes.create.call_count)
        self.assertEqual(AttributeType.UniSelect, synced["Severity[UniSelect]"].resolved_type)
        self.assertEqual(AttributeType.User, synced["Watcher[User]"].resolved_type)
        self.assertEqual(AttributeType.UniString, synced["Unknown[MagicType]"].resolved_type)
        self.assertTrue(any("fallback to UniString" in warning for warning in warnings))

    def test_sync_attributes_existing_type_wins_on_mismatch(self) -> None:
        api = _build_api()
        log = MagicMock()
        warnings: list[str] = []

        existing = SimpleNamespace(
            id=uuid4(),
            name="Estimate",
            type=AttributeType.UniString,
            options=None,
        )
        api.attributes.list.return_value = [existing]

        tasks_rows = [
            {
                "row_ref": "r1",
                "name": "Task",
                "description": "d",
                "assignee_username": "john",
                "sprint_name": "S1",
                "type": "Bug",
                "start_date": date(2026, 3, 18),
                "end_date": date(2026, 3, 19),
                "custom_attributes_raw": {"Estimate[Number]": "12"},
            }
        ]

        synced = sync_attributes(
            api,
            workspace_key="WS",
            tasks_rows=tasks_rows,
            update_settings=True,
            dry_run=False,
            log=log,
            warnings=warnings,
        )
        self.assertEqual(AttributeType.UniString, synced["Estimate[Number]"].resolved_type)
        self.assertEqual(0, api.attributes.create.call_count)
        self.assertTrue(any("type mismatch" in warning for warning in warnings))

    def test_sync_types_create_and_link_per_usage(self) -> None:
        api = _build_api()
        log = MagicMock()
        warnings: list[str] = []

        workflow = SimpleNamespace(name="Default WF")
        api.workflows.list.return_value = [workflow]
        created_type = SimpleNamespace(
            id=uuid4(),
            name="Bug",
            workflow=workflow,
            attributes=[],
        )
        api.types.create.return_value = created_type
        api.types.add_attribute.return_value = created_type

        attribute_id = uuid4()
        synced_attr = SyncedAttribute(
            spec=CustomAttributeSpec(
                source_column="Severity[UniSelect]",
                attribute_name="Severity",
                requested_type=AttributeType.UniSelect,
                unknown_marker=False,
            ),
            resolved_type=AttributeType.UniSelect,
            attribute_id=attribute_id,
            options_by_name={},
        )

        tasks_rows = [
            {
                "row_ref": "r1",
                "name": "Task",
                "description": "d",
                "assignee_username": "john",
                "sprint_name": "S1",
                "type": "Bug",
                "start_date": date(2026, 3, 18),
                "end_date": date(2026, 3, 19),
                "custom_attributes_raw": {"Severity[UniSelect]": "High"},
            }
        ]

        known_types = sync_types(
            api,
            workspace_key="WS",
            tasks_rows=tasks_rows,
            attributes_by_column={"Severity[UniSelect]": synced_attr},
            update_settings=True,
            dry_run=False,
            log=log,
            warnings=warnings,
        )

        self.assertIn("Bug", known_types)
        self.assertEqual(1, api.types.create.call_count)
        self.assertEqual(1, api.types.add_attribute.call_count)

    def test_sync_types_prefers_existing_types_workflow_over_first_listed_workflow(
        self,
    ) -> None:
        api = _build_api()
        log = MagicMock()
        warnings: list[str] = []

        technical_workflow = SimpleNamespace(name="Default for portfolio extension: Global:123")
        default_workflow = SimpleNamespace(name="Процесс по умолчанию")
        api.workflows.list.return_value = [technical_workflow, default_workflow]
        api.types.list.return_value = [
            SimpleNamespace(
                id=uuid4(),
                name="Задача",
                workflow=default_workflow,
                attributes=[],
            )
        ]
        api.types.create.return_value = SimpleNamespace(
            id=uuid4(),
            name="Проект",
            workflow=default_workflow,
            attributes=[],
        )

        known_types = sync_types(
            api,
            workspace_key="WS",
            tasks_rows=[
                {
                    "row_ref": "r1",
                    "name": "Task",
                    "description": "d",
                    "assignee_username": "john",
                    "sprint_name": "S1",
                    "type": "Проект",
                    "start_date": date(2026, 3, 18),
                    "end_date": date(2026, 3, 19),
                    "custom_attributes_raw": {},
                }
            ],
            attributes_by_column={},
            update_settings=True,
            dry_run=False,
            log=log,
            warnings=warnings,
        )

        self.assertIn("Проект", known_types)
        _, create_body = api.types.create.call_args.args
        self.assertEqual("Процесс по умолчанию", create_body.workflow)

    def test_sync_workspace_members_flag_controls_writes(self) -> None:
        api = _build_api()
        log = MagicMock()
        warnings: list[str] = []

        user_id = uuid4()
        api.users.list.side_effect = lambda **kwargs: (
            [
                SimpleNamespace(
                    id=user_id,
                    username="john",
                    email="john@example.com",
                    display_name="John Doe",
                )
            ]
            if kwargs.get("username") == "john"
            else []
        )
        role_id = uuid4()
        api.roles.list.return_value = [SimpleNamespace(id=role_id, name="User", is_system=True)]
        api.workspace_users.list.return_value = []

        tasks_rows = [
            {
                "row_ref": "r1",
                "name": "Task",
                "description": "d",
                "assignee_username": "john",
                "sprint_name": "S1",
                "type": "Bug",
                "start_date": date(2026, 3, 18),
                "end_date": date(2026, 3, 19),
                "custom_attributes_raw": {},
            }
        ]

        sync_workspace_members(
            api,
            workspace_key="WS",
            tasks_rows=tasks_rows,
            attributes_by_column={},
            sync_members=False,
            dry_run=False,
            log=log,
            warnings=warnings,
        )
        self.assertEqual(0, api.workspace_users.add.call_count)
        self.assertEqual(0, api.workspace_users.add_role.call_count)

        sync_workspace_members(
            api,
            workspace_key="WS",
            tasks_rows=tasks_rows,
            attributes_by_column={},
            sync_members=True,
            dry_run=False,
            log=log,
            warnings=warnings,
        )
        self.assertEqual(1, api.workspace_users.add.call_count)
        self.assertEqual(1, api.workspace_users.add_role.call_count)

    def test_dry_run_sync_does_not_write(self) -> None:
        module = _load_attributes_module()
        api = _build_api()
        log = MagicMock()
        warnings: list[str] = []

        api.workflows.list.return_value = [SimpleNamespace(name="WF")]
        api.roles.list.return_value = [SimpleNamespace(id=uuid4(), name="User", is_system=True)]
        api.users.list.side_effect = lambda **kwargs: []

        tasks_rows = [
            {
                "row_ref": "r1",
                "name": "Task",
                "description": "d",
                "assignee_username": "john",
                "sprint_name": "S1",
                "type": "Bug",
                "start_date": date(2026, 3, 18),
                "end_date": date(2026, 3, 19),
                "custom_attributes_raw": {"Severity[UniSelect]": "High"},
            }
        ]

        module.run_settings_sync(
            api,
            workspace_key="WS",
            tasks_rows=tasks_rows,
            update_settings=True,
            sync_members=True,
            dry_run=True,
            log=log,
            warnings=warnings,
        )

        self.assertEqual(0, api.attributes.create.call_count)
        self.assertEqual(0, api.types.create.call_count)
        self.assertEqual(0, api.types.add_attribute.call_count)
        self.assertEqual(0, api.workspace_users.add.call_count)

    def test_missing_attribute_without_update_settings_warns_and_continues(
        self,
    ) -> None:
        api = _build_api()
        log = MagicMock()
        warnings: list[str] = []

        tasks_rows = [
            {
                "row_ref": "r1",
                "name": "Task",
                "description": "d",
                "assignee_username": "john",
                "sprint_name": "S1",
                "type": "Bug",
                "start_date": date(2026, 3, 18),
                "end_date": date(2026, 3, 19),
                "custom_attributes_raw": {"Severity[UniSelect]": "High"},
            }
        ]

        synced = sync_attributes(
            api,
            workspace_key="WS",
            tasks_rows=tasks_rows,
            update_settings=False,
            dry_run=False,
            log=log,
            warnings=warnings,
        )

        self.assertIn("Severity[UniSelect]", synced)
        self.assertIsNone(synced["Severity[UniSelect]"].attribute_id)
        self.assertTrue(any("Missing custom attribute" in warning for warning in warnings))
        self.assertEqual(0, api.attributes.create.call_count)

    def test_update_settings_on_syncs_attribute_ids_for_mapping(self) -> None:
        api = _build_api()
        log = MagicMock()
        warnings: list[str] = []
        created = SimpleNamespace(
            id=uuid4(),
            name="Severity",
            type=AttributeType.UniSelect,
            options=None,
        )
        api.attributes.create.return_value = created

        tasks_rows = [
            {
                "row_ref": "r1",
                "name": "Task",
                "description": "d",
                "assignee_username": "john",
                "sprint_name": "S1",
                "type": "Bug",
                "start_date": date(2026, 3, 18),
                "end_date": date(2026, 3, 19),
                "custom_attributes_raw": {"Severity[UniSelect]": "High"},
            }
        ]

        synced = sync_attributes(
            api,
            workspace_key="WS",
            tasks_rows=tasks_rows,
            update_settings=True,
            dry_run=False,
            log=log,
            warnings=warnings,
        )

        self.assertEqual(1, api.attributes.create.call_count)
        self.assertEqual(created.id, synced["Severity[UniSelect]"].attribute_id)
        self.assertEqual(AttributeType.UniSelect, synced["Severity[UniSelect]"].resolved_type)


if __name__ == "__main__":
    unittest.main()
