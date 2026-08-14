import importlib
import sys
import types
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from import_toolkit.controllers.core.contracts import (
    Counters,
    CustomAttributeSpec,
    SyncedAttribute,
    SyncContext,
)
from teamstorm.models.enums import AttributeType
from teamstorm.models.workitems_attributes_update import (
    UpdateUniSelectFieldRequestBody,
    UpdateUniStringFieldRequestBody,
)


def _load_module():
    module_name = "import_toolkit.controllers.core.custom_attributes"
    if module_name in sys.modules:
        module = importlib.reload(sys.modules[module_name])
    else:
        import import_toolkit.controllers.core.custom_attributes as module

    return module


class ImportAgileWorkitemAttributeUpdatesTestCase(unittest.TestCase):
    def _make_sync_context(self, module, *, column: str, attr_id, attr_type: AttributeType):
        synced = SyncedAttribute(
            spec=CustomAttributeSpec(
                source_column=column,
                attribute_name="Severity",
                requested_type=attr_type,
                unknown_marker=False,
            ),
            resolved_type=attr_type,
            attribute_id=attr_id,
            options_by_name={},
        )
        return SyncContext(
            attributes_by_column={column: synced},
            user_cache={},
            known_types=set(),
        )

    def _base_row(self, module):
        return {
            "row_ref": "Sheet2 row 2",
            "name": "Task",
            "description": "Desc",
            "assignee_username": "john",
            "sprint_name": "S1",
            "type": "Bug",
            "start_date": date(2026, 3, 18),
            "end_date": date(2026, 3, 19),
            "custom_attributes_raw": {"Severity[UniString]": "High"},
        }

    def test_upsert_runs_for_new_and_existing_workitems_after_patch(self) -> None:
        module = _load_module()
        api = MagicMock()
        workitem_id = uuid4()
        row = self._base_row(module)
        sync_context = self._make_sync_context(
            module,
            column="Severity[UniString]",
            attr_id=uuid4(),
            attr_type=AttributeType.UniString,
        )

        with unittest.mock.patch.object(module, "update_workitem_custom_attributes") as mocked_update:
            module.maybe_update_existing_workitem_custom_attributes(
                api,
                is_existing_workitem=False,
                workspace_key="WS",
                workitem_id=workitem_id,
                row=row,
                sync_context=sync_context,
                update_settings=True,
                dry_run=False,
                log=MagicMock(),
                warnings=[],
                errors=[],
                counters=Counters(),
            )
            mocked_update.assert_called_once()

            module.maybe_update_existing_workitem_custom_attributes(
                api,
                is_existing_workitem=True,
                workspace_key="WS",
                workitem_id=workitem_id,
                row=row,
                sync_context=sync_context,
                update_settings=True,
                dry_run=False,
                log=MagicMock(),
                warnings=[],
                errors=[],
                counters=Counters(),
            )
            self.assertEqual(2, mocked_update.call_count)

    def test_list_attributes_called_before_update_calls(self) -> None:
        module = _load_module()
        api = MagicMock()
        workitem_id = uuid4()
        attr_id = uuid4()
        row = self._base_row(module)
        sync_context = self._make_sync_context(
            module,
            column="Severity[UniString]",
            attr_id=attr_id,
            attr_type=AttributeType.UniString,
        )
        api.workitems.list_attributes.return_value = [types.SimpleNamespace(id=attr_id)]

        module.update_workitem_custom_attributes(
            api,
            workspace_key="WS",
            workitem_id=workitem_id,
            row=row,
            sync_context=sync_context,
            update_settings=True,
            dry_run=False,
            log=MagicMock(),
            warnings=[],
            errors=[],
            counters=Counters(),
        )

        self.assertEqual("list_attributes", api.workitems.method_calls[0][0])
        self.assertEqual("update_attribute", api.workitems.method_calls[1][0])

    def test_uses_synced_attribute_ids_only(self) -> None:
        module = _load_module()
        api = MagicMock()
        workitem_id = uuid4()
        attr_id = uuid4()
        row = self._base_row(module)
        row["custom_attributes_raw"]["Unmapped[UniString]"] = "X"
        sync_context = self._make_sync_context(
            module,
            column="Severity[UniString]",
            attr_id=attr_id,
            attr_type=AttributeType.UniString,
        )
        api.workitems.list_attributes.return_value = [types.SimpleNamespace(id=attr_id)]

        module.update_workitem_custom_attributes(
            api,
            workspace_key="WS",
            workitem_id=workitem_id,
            row=row,
            sync_context=sync_context,
            update_settings=True,
            dry_run=False,
            log=MagicMock(),
            warnings=[],
            errors=[],
            counters=Counters(),
        )

        self.assertEqual(1, api.workitems.update_attribute.call_count)
        called_kwargs = api.workitems.update_attribute.call_args.kwargs
        self.assertEqual(attr_id, called_kwargs["attribute_id"])

    def test_updates_even_if_attribute_not_listed_on_workitem(self) -> None:
        module = _load_module()
        api = MagicMock()
        workitem_id = uuid4()
        mapped_attr_id = uuid4()
        row = self._base_row(module)
        sync_context = self._make_sync_context(
            module,
            column="Severity[UniString]",
            attr_id=mapped_attr_id,
            attr_type=AttributeType.UniString,
        )
        api.workitems.list_attributes.return_value = [types.SimpleNamespace(id=uuid4())]
        warnings: list[str] = []
        log = MagicMock()

        module.update_workitem_custom_attributes(
            api,
            workspace_key="WS",
            workitem_id=workitem_id,
            row=row,
            sync_context=sync_context,
            update_settings=True,
            dry_run=False,
            log=log,
            warnings=warnings,
            errors=[],
            counters=Counters(),
        )

        self.assertEqual(1, api.workitems.update_attribute.call_count)
        self.assertTrue(any("is not listed for workitem" in str(call) for call in log.info.call_args_list))

    def test_dry_run_logs_each_planned_update_without_writes(self) -> None:
        module = _load_module()
        api = MagicMock()
        log = MagicMock()
        workitem_id = uuid4()
        attr_id = uuid4()
        row = self._base_row(module)
        sync_context = self._make_sync_context(
            module,
            column="Severity[UniString]",
            attr_id=attr_id,
            attr_type=AttributeType.UniString,
        )
        api.workitems.list_attributes.return_value = [types.SimpleNamespace(id=attr_id)]

        module.update_workitem_custom_attributes(
            api,
            workspace_key="WS",
            workitem_id=workitem_id,
            row=row,
            sync_context=sync_context,
            update_settings=True,
            dry_run=True,
            log=log,
            warnings=[],
            errors=[],
            counters=Counters(),
        )

        self.assertEqual(0, api.workitems.update_attribute.call_count)
        self.assertTrue(any("ATTRIBUTE UPDATE" in str(call) for call in log.info.call_args_list))

    def test_update_failure_becomes_row_error_and_next_row_continues(self) -> None:
        module = _load_module()
        api = MagicMock()
        workitem_id = uuid4()
        first_attr_id = uuid4()
        second_attr_id = uuid4()
        row = self._base_row(module)
        row["custom_attributes_raw"] = {
            "Severity[UniString]": "High",
            "Category[UniString]": "Backend",
        }
        sync_context = SyncContext(
            attributes_by_column={
                "Severity[UniString]": SyncedAttribute(
                    spec=CustomAttributeSpec(
                        source_column="Severity[UniString]",
                        attribute_name="Severity",
                        requested_type=AttributeType.UniString,
                        unknown_marker=False,
                    ),
                    resolved_type=AttributeType.UniString,
                    attribute_id=first_attr_id,
                    options_by_name={},
                ),
                "Category[UniString]": SyncedAttribute(
                    spec=CustomAttributeSpec(
                        source_column="Category[UniString]",
                        attribute_name="Category",
                        requested_type=AttributeType.UniString,
                        unknown_marker=False,
                    ),
                    resolved_type=AttributeType.UniString,
                    attribute_id=second_attr_id,
                    options_by_name={},
                ),
            },
            user_cache={},
            known_types=set(),
        )
        api.workitems.list_attributes.return_value = [
            types.SimpleNamespace(id=first_attr_id),
            types.SimpleNamespace(id=second_attr_id),
        ]
        api.workitems.update_attribute.side_effect = [RuntimeError("boom"), None]
        errors: list[str] = []
        counters = Counters()

        module.update_workitem_custom_attributes(
            api,
            workspace_key="WS",
            workitem_id=workitem_id,
            row=row,
            sync_context=sync_context,
            update_settings=True,
            dry_run=False,
            log=MagicMock(),
            warnings=[],
            errors=errors,
            counters=counters,
        )

        self.assertEqual(1, len(errors))
        self.assertEqual(2, api.workitems.update_attribute.call_count)
        self.assertEqual(2, counters.custom_attr_updates_attempted)
        self.assertEqual(1, counters.custom_attr_updates_failed)
        self.assertEqual(1, counters.custom_attr_updates_succeeded)

    def test_missing_custom_cell_does_not_clear_existing_value(self) -> None:
        module = _load_module()
        api = MagicMock()
        workitem_id = uuid4()
        attr_id = uuid4()
        row = self._base_row(module)
        row["custom_attributes_raw"] = {}
        sync_context = self._make_sync_context(
            module,
            column="Severity[UniString]",
            attr_id=attr_id,
            attr_type=AttributeType.UniString,
        )
        api.workitems.list_attributes.return_value = [types.SimpleNamespace(id=attr_id)]

        module.update_workitem_custom_attributes(
            api,
            workspace_key="WS",
            workitem_id=workitem_id,
            row=row,
            sync_context=sync_context,
            update_settings=True,
            dry_run=False,
            log=MagicMock(),
            warnings=[],
            errors=[],
            counters=Counters(),
        )

        self.assertEqual(0, api.workitems.update_attribute.call_count)

    def test_mapper_none_result_skips_update(self) -> None:
        module = _load_module()
        api = MagicMock()
        workitem_id = uuid4()
        attr_id = uuid4()
        row = self._base_row(module)
        row["custom_attributes_raw"] = {"Watcher[User]": "unknown-user"}
        sync_context = self._make_sync_context(
            module,
            column="Watcher[User]",
            attr_id=attr_id,
            attr_type=AttributeType.User,
        )
        api.workitems.list_attributes.return_value = [types.SimpleNamespace(id=attr_id)]
        api.users.list.return_value = []
        warnings: list[str] = []

        module.update_workitem_custom_attributes(
            api,
            workspace_key="WS",
            workitem_id=workitem_id,
            row=row,
            sync_context=sync_context,
            update_settings=True,
            dry_run=False,
            log=MagicMock(),
            warnings=warnings,
            errors=[],
            counters=Counters(),
        )

        self.assertEqual(0, api.workitems.update_attribute.call_count)
        self.assertTrue(any("Cannot resolve user" in warning for warning in warnings))

    def test_build_update_custom_attributes_returns_typed_payloads(self) -> None:
        module = _load_module()
        api = MagicMock()
        row = self._base_row(module)
        attr_id = uuid4()
        sync_context = self._make_sync_context(
            module,
            column="Severity[UniString]",
            attr_id=attr_id,
            attr_type=AttributeType.UniString,
        )

        updates = module.build_update_custom_attributes_for_row(
            api,
            workspace_key="WS",
            row=row,
            sync_context=sync_context,
            update_settings=True,
            dry_run=False,
            log=MagicMock(),
            warnings=[],
        )

        self.assertEqual(1, len(updates))
        self.assertEqual("Severity[UniString]", updates[0].source_column)
        self.assertEqual(attr_id, updates[0].synced_attr.attribute_id)
        self.assertIsInstance(updates[0].payload, UpdateUniStringFieldRequestBody)

    def test_uniselect_success_on_first_try_without_retry(self) -> None:
        module = _load_module()
        api = MagicMock()
        workitem_id = uuid4()
        attr_id = uuid4()
        option_id = uuid4()
        row = self._base_row(module)
        row["custom_attributes_raw"] = {"Severity[UniSelect]": "High"}
        synced_attr = SyncedAttribute(
            spec=CustomAttributeSpec(
                source_column="Severity[UniSelect]",
                attribute_name="Severity",
                requested_type=AttributeType.UniSelect,
                unknown_marker=False,
            ),
            resolved_type=AttributeType.UniSelect,
            attribute_id=attr_id,
            options_by_name={"high": option_id},
        )
        sync_context = SyncContext(
            attributes_by_column={"Severity[UniSelect]": synced_attr},
            user_cache={},
            known_types=set(),
        )
        api.workitems.list_attributes.return_value = [types.SimpleNamespace(id=attr_id)]
        api.workitems.update_attribute.return_value = types.SimpleNamespace(
            type=AttributeType.UniSelect,
            value=types.SimpleNamespace(id=option_id, name="High"),
        )
        errors: list[str] = []
        counters = Counters()

        module.update_workitem_custom_attributes(
            api,
            workspace_key="WS",
            workitem_id=workitem_id,
            row=row,
            sync_context=sync_context,
            update_settings=True,
            dry_run=False,
            log=MagicMock(),
            warnings=[],
            errors=errors,
            counters=counters,
        )

        self.assertEqual(1, api.workitems.update_attribute.call_count)
        self.assertEqual(0, api.attributes.get.call_count)
        self.assertEqual([], errors)
        self.assertEqual(1, counters.custom_attr_updates_succeeded)
        self.assertEqual(0, counters.custom_attr_updates_failed)

    def test_tag_success_on_first_try_without_retry(self) -> None:
        module = _load_module()
        api = MagicMock()
        workitem_id = uuid4()
        attr_id = uuid4()
        alpha_id = uuid4()
        beta_id = uuid4()
        row = self._base_row(module)
        row["custom_attributes_raw"] = {"Tags[Tag]": "alpha,beta"}
        synced_attr = SyncedAttribute(
            spec=CustomAttributeSpec(
                source_column="Tags[Tag]",
                attribute_name="Tags",
                requested_type=AttributeType.Tag,
                unknown_marker=False,
            ),
            resolved_type=AttributeType.Tag,
            attribute_id=attr_id,
            options_by_name={"alpha": alpha_id, "beta": beta_id},
        )
        sync_context = SyncContext(
            attributes_by_column={"Tags[Tag]": synced_attr},
            user_cache={},
            known_types=set(),
        )
        api.workitems.list_attributes.return_value = [types.SimpleNamespace(id=attr_id)]
        api.workitems.update_attribute.return_value = types.SimpleNamespace(
            type=AttributeType.Tag,
            value=[
                types.SimpleNamespace(id=alpha_id, name="alpha"),
                types.SimpleNamespace(id=beta_id, name="beta"),
            ],
        )
        errors: list[str] = []
        counters = Counters()

        module.update_workitem_custom_attributes(
            api,
            workspace_key="WS",
            workitem_id=workitem_id,
            row=row,
            sync_context=sync_context,
            update_settings=True,
            dry_run=False,
            log=MagicMock(),
            warnings=[],
            errors=errors,
            counters=counters,
        )

        self.assertEqual(1, api.workitems.update_attribute.call_count)
        self.assertEqual(0, api.attributes.get.call_count)
        self.assertEqual([], errors)
        self.assertEqual(1, counters.custom_attr_updates_succeeded)
        self.assertEqual(0, counters.custom_attr_updates_failed)

    def test_uniselect_retry_succeeds_after_options_refresh(self) -> None:
        module = _load_module()
        api = MagicMock()
        workitem_id = uuid4()
        attr_id = uuid4()
        stale_option_id = uuid4()
        fresh_option_id = uuid4()
        row = self._base_row(module)
        row["custom_attributes_raw"] = {"Severity[UniSelect]": "High"}
        synced_attr = SyncedAttribute(
            spec=CustomAttributeSpec(
                source_column="Severity[UniSelect]",
                attribute_name="Severity",
                requested_type=AttributeType.UniSelect,
                unknown_marker=False,
            ),
            resolved_type=AttributeType.UniSelect,
            attribute_id=attr_id,
            options_by_name={"high": stale_option_id},
        )
        sync_context = SyncContext(
            attributes_by_column={"Severity[UniSelect]": synced_attr},
            user_cache={},
            known_types=set(),
        )
        api.workitems.list_attributes.side_effect = [
            [types.SimpleNamespace(id=attr_id)],
            [
                types.SimpleNamespace(
                    id=attr_id,
                    type=AttributeType.UniSelect,
                    value=types.SimpleNamespace(id=fresh_option_id, name="High"),
                )
            ],
        ]
        api.workitems.update_attribute.side_effect = [
            types.SimpleNamespace(type=AttributeType.UniSelect, value=None),
            types.SimpleNamespace(
                type=AttributeType.UniSelect,
                value=types.SimpleNamespace(id=fresh_option_id, name="High"),
            ),
        ]
        api.attributes.get.return_value = types.SimpleNamespace(
            options=[types.SimpleNamespace(name="High", id=fresh_option_id)]
        )
        errors: list[str] = []
        counters = Counters()

        module.update_workitem_custom_attributes(
            api,
            workspace_key="WS",
            workitem_id=workitem_id,
            row=row,
            sync_context=sync_context,
            update_settings=True,
            dry_run=False,
            log=MagicMock(),
            warnings=[],
            errors=errors,
            counters=counters,
        )

        self.assertEqual(2, api.workitems.update_attribute.call_count)
        self.assertEqual(1, api.attributes.get.call_count)
        self.assertEqual([], errors)
        self.assertEqual(1, counters.custom_attr_updates_succeeded)
        self.assertEqual(0, counters.custom_attr_updates_failed)
        self.assertEqual(
            UpdateUniSelectFieldRequestBody,
            type(api.workitems.update_attribute.call_args_list[1].kwargs["body"]),
        )
        self.assertEqual(
            "High",
            api.workitems.update_attribute.call_args_list[1].kwargs["body"].value,
        )

    def test_uniselect_persistent_mismatch_becomes_non_fatal_row_error(self) -> None:
        module = _load_module()
        api = MagicMock()
        workitem_id = uuid4()
        attr_id = uuid4()
        option_id = uuid4()
        row = self._base_row(module)
        row["custom_attributes_raw"] = {"Severity[UniSelect]": "High"}
        synced_attr = SyncedAttribute(
            spec=CustomAttributeSpec(
                source_column="Severity[UniSelect]",
                attribute_name="Severity",
                requested_type=AttributeType.UniSelect,
                unknown_marker=False,
            ),
            resolved_type=AttributeType.UniSelect,
            attribute_id=attr_id,
            options_by_name={"high": option_id},
        )
        sync_context = SyncContext(
            attributes_by_column={"Severity[UniSelect]": synced_attr},
            user_cache={},
            known_types=set(),
        )
        api.workitems.list_attributes.side_effect = [
            [types.SimpleNamespace(id=attr_id)],
            [types.SimpleNamespace(id=attr_id, type=AttributeType.UniSelect, value=None)],
        ]
        api.workitems.update_attribute.side_effect = [
            types.SimpleNamespace(type=AttributeType.UniSelect, value=None),
            types.SimpleNamespace(type=AttributeType.UniSelect, value=None),
        ]
        api.attributes.get.return_value = types.SimpleNamespace(
            options=[types.SimpleNamespace(name="High", id=option_id)]
        )
        errors: list[str] = []
        non_fatal_select_tag_errors: list[str] = []
        counters = Counters()

        module.update_workitem_custom_attributes(
            api,
            workspace_key="WS",
            workitem_id=workitem_id,
            row=row,
            sync_context=sync_context,
            update_settings=True,
            dry_run=False,
            log=MagicMock(),
            warnings=[],
            errors=errors,
            counters=counters,
            non_fatal_select_tag_errors=non_fatal_select_tag_errors,
        )

        self.assertEqual(2, api.workitems.update_attribute.call_count)
        self.assertEqual(1, api.attributes.get.call_count)
        self.assertEqual(0, len(errors))
        self.assertEqual(1, len(non_fatal_select_tag_errors))
        self.assertEqual(1, counters.custom_attr_updates_failed)
        self.assertEqual(0, counters.custom_attr_updates_succeeded)
        self.assertTrue("mismatch after retry" in non_fatal_select_tag_errors[0])


if __name__ == "__main__":
    unittest.main()
