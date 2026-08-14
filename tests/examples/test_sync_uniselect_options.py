import importlib
import sys
import unittest
from argparse import Namespace
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4


def _load_module():
    mod_name = "import_toolkit.workflows.sync.uniselect_options"
    if mod_name in sys.modules:
        return importlib.reload(sys.modules[mod_name])
    return importlib.import_module(mod_name)


def _option(name: str):
    return SimpleNamespace(id=uuid4(), name=name)


def _attribute(name: str, options: list):
    return SimpleNamespace(
        id=uuid4(),
        name=name,
        type="UniSelect",
        options=options,
    )


class UniSelectPlanTestCase(unittest.TestCase):
    def test_plan_create_only(self) -> None:
        module = _load_module()
        plan = module.plan_option_reconciliation(
            attribute_name="Severity",
            master_options=[_option("High"), _option("Low")],
            target_options=[],
        )

        self.assertEqual(["High", "Low"], plan.creates)
        self.assertEqual([], plan.renames)
        self.assertEqual([], plan.deletes)
        self.assertEqual([], plan.errors)

    def test_plan_rename_only_normalized_match(self) -> None:
        module = _load_module()
        target = _option("high")
        plan = module.plan_option_reconciliation(
            attribute_name="Severity",
            master_options=[_option("High")],
            target_options=[target],
        )

        self.assertEqual([], plan.creates)
        self.assertEqual([(target.id, "High")], plan.renames)
        self.assertEqual([], plan.deletes)
        self.assertEqual([], plan.errors)

    def test_plan_delete_only(self) -> None:
        module = _load_module()
        extra = _option("obsolete")
        plan = module.plan_option_reconciliation(
            attribute_name="Severity",
            master_options=[],
            target_options=[extra],
        )

        self.assertEqual([], plan.creates)
        self.assertEqual([], plan.renames)
        self.assertEqual([extra.id], plan.deletes)
        self.assertEqual([], plan.errors)

    def test_plan_mixed_create_rename_delete(self) -> None:
        module = _load_module()
        keep_but_rename = _option("medium")
        delete_me = _option("extra")
        plan = module.plan_option_reconciliation(
            attribute_name="Severity",
            master_options=[_option("Medium"), _option("High")],
            target_options=[keep_but_rename, delete_me],
        )

        self.assertEqual(["High"], plan.creates)
        self.assertEqual([(keep_but_rename.id, "Medium")], plan.renames)
        self.assertEqual([delete_me.id], plan.deletes)
        self.assertEqual([], plan.errors)

    def test_plan_duplicate_normalized_name_conflict(self) -> None:
        module = _load_module()
        plan = module.plan_option_reconciliation(
            attribute_name="Severity",
            master_options=[_option("High"), _option(" high ")],
            target_options=[],
        )

        self.assertEqual([], plan.creates)
        self.assertEqual([], plan.renames)
        self.assertEqual([], plan.deletes)
        self.assertTrue(any("Duplicate normalized option name" in e for e in plan.errors))


class UniSelectWorkflowTestCase(unittest.TestCase):
    def test_missing_target_attribute_is_created_and_options_synced(self) -> None:
        module = _load_module()
        log = MagicMock()

        master_attr = _attribute("Severity", [_option("High"), _option("Low")])
        created_target_attr = _attribute("Severity", [])

        api = SimpleNamespace(
            attributes=SimpleNamespace(
                list=MagicMock(side_effect=[[master_attr], []]),
                create=MagicMock(return_value=created_target_attr),
                add_option=MagicMock(),
                patch_option=MagicMock(),
                delete_option=MagicMock(),
            )
        )

        args = Namespace(
            base_url="https://cwm.example",
            token="token",
            master_workspace_key="MASTER",
            target_workspace_key=["TARGET1"],
            attribute_name=["Severity"],
            apply=True,
            allow_insecure=False,
            log_file="./logs/test.log",
        )

        with (
            patch.object(module, "setup_logging", return_value=log),
            patch.object(module, "TsClient", return_value=MagicMock()),
            patch.object(module, "TeamStormAPI", return_value=api),
        ):
            code = module.run_sync_uniselect_options(args)

        self.assertEqual(0, code)
        self.assertEqual(1, api.attributes.create.call_count)
        self.assertEqual(2, api.attributes.add_option.call_count)
        self.assertEqual(0, api.attributes.patch_option.call_count)
        self.assertEqual(0, api.attributes.delete_option.call_count)

    def test_dry_run_makes_no_write_calls(self) -> None:
        module = _load_module()
        log = MagicMock()

        master_attr = _attribute("Severity", [_option("High")])
        target_attr = _attribute("Severity", [])

        api = SimpleNamespace(
            attributes=SimpleNamespace(
                list=MagicMock(side_effect=[[master_attr], [target_attr]]),
                create=MagicMock(),
                add_option=MagicMock(),
                patch_option=MagicMock(),
                delete_option=MagicMock(),
            )
        )

        args = Namespace(
            base_url="https://cwm.example",
            token="token",
            master_workspace_key="MASTER",
            target_workspace_key=["TARGET1"],
            attribute_name=["Severity"],
            apply=False,
            allow_insecure=False,
            log_file="./logs/test.log",
        )

        with (
            patch.object(module, "setup_logging", return_value=log),
            patch.object(module, "TsClient", return_value=MagicMock()),
            patch.object(module, "TeamStormAPI", return_value=api),
        ):
            code = module.run_sync_uniselect_options(args)

        self.assertEqual(0, code)
        self.assertEqual(0, api.attributes.create.call_count)
        self.assertEqual(0, api.attributes.add_option.call_count)
        self.assertEqual(0, api.attributes.patch_option.call_count)
        self.assertEqual(0, api.attributes.delete_option.call_count)

    def test_continue_on_target_failure_and_return_non_zero(self) -> None:
        module = _load_module()
        log = MagicMock()

        master_attr = _attribute("Severity", [_option("High")])
        target_attr = _attribute("Severity", [])

        def list_side_effect(workspace_key, **kwargs):
            if workspace_key == "MASTER":
                return [master_attr]
            if workspace_key == "BAD":
                raise RuntimeError("boom")
            return [target_attr]

        api = SimpleNamespace(
            attributes=SimpleNamespace(
                list=MagicMock(side_effect=list_side_effect),
                create=MagicMock(),
                add_option=MagicMock(),
                patch_option=MagicMock(),
                delete_option=MagicMock(),
            )
        )

        args = Namespace(
            base_url="https://cwm.example",
            token="token",
            master_workspace_key="MASTER",
            target_workspace_key=["BAD", "GOOD"],
            attribute_name=["Severity"],
            apply=True,
            allow_insecure=False,
            log_file="./logs/test.log",
        )

        with (
            patch.object(module, "setup_logging", return_value=log),
            patch.object(module, "TsClient", return_value=MagicMock()),
            patch.object(module, "TeamStormAPI", return_value=api),
        ):
            code = module.run_sync_uniselect_options(args)

        self.assertEqual(1, code)
        self.assertEqual(1, api.attributes.add_option.call_count)


class UniSelectCliArgsTestCase(unittest.TestCase):
    def test_parser_supports_repeated_target_and_attribute_args(self) -> None:
        module = _load_module()
        parser = module.build_arg_parser()

        args = parser.parse_args(
            [
                "--master-workspace-key",
                "MASTER",
                "--target-workspace-key",
                "A",
                "--target-workspace-key",
                "B",
                "--attribute-name",
                "Severity",
                "--attribute-name",
                "Priority",
            ]
        )

        self.assertEqual("MASTER", args.master_workspace_key)
        self.assertEqual(["A", "B"], args.target_workspace_key)
        self.assertEqual(["Severity", "Priority"], args.attribute_name)
        self.assertFalse(args.apply)


if __name__ == "__main__":
    unittest.main()
