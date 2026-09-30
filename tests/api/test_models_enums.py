import enum
import inspect
import json
import unittest
from pathlib import Path

import teamstorm.models.enums as enums_module
import teamstorm.models.roles as roles_module
from teamstorm.models.enums import (
    AttributeType,
    EstimatesType,
    ProgressType,
    SprintStates,
    TypeColor,
    TypeIcon,
    WorkflowType,
    WorkitemTimeMetricStatus,
    WorkitemTimeMetricTemplateType,
)


class EnumsModelTestCase(unittest.TestCase):
    def test_enum_values_match_swagger(self) -> None:
        cases = [
            (
                "AttributeType",
                AttributeType,
                [
                    "UniString",
                    "Number",
                    "Date",
                    "UniSelect",
                    "Tag",
                    "User",
                    "TimeDuration",
                ],
            ),
            (
                "SprintStates",
                SprintStates,
                [
                    "New",
                    "Active",
                    "Completed",
                ],
            ),
            (
                "TypeColor",
                TypeColor,
                [
                    "Sky",
                    "Mint",
                    "Yellow",
                    "Amber",
                    "Slate",
                    "Tomato",
                    "Red",
                    "Crimson",
                    "Pink",
                    "Plum",
                    "Purple",
                    "Violet",
                    "Indigo",
                    "Blue",
                    "Cyan",
                    "Teal",
                    "Green",
                    "Grass",
                    "Orange",
                    "Brown",
                    "Gold",
                    "Bronze",
                    "Gray",
                ],
            ),
            (
                "TypeIcon",
                TypeIcon,
                [
                    "BugSolid",
                    "BookmarkSolid",
                    "LightningSolid",
                    "LayersSolid",
                    "CrownSolid",
                    "DocSolid",
                    "FireSolid",
                    "EyeSolid",
                    "LampSolid",
                    "StarSolid",
                    "CheckmarkCircleSolid",
                    "FlagSolid",
                    "ChartPieSolid",
                    "UmbrellaSolid",
                    "WaveformEcgSolid",
                    "KeySolid",
                    "FavoritesSolid",
                    "CheckboxSolid",
                    "AlertTriangleSolid",
                    "TraySolid",
                    "BoxSolid",
                    "BracketsSolid",
                    "MessageBubbleSolid",
                    "SettingsSolid",
                    "GiftboxSolid",
                    "PenSolid",
                    "ShieldSolid",
                    "LockSolid",
                    "Square4GridSolid",
                    "BookOpenSolid",
                    "QuestionCircleSolid",
                    "MinusCircleSolid",
                    "PlusCircleSolid",
                    "InfoCircleSolid",
                    "ArrowCircleUpSolid",
                    "ArrowCircleDownSolid",
                    "AlertCircleSolid",
                    "CompassSolid",
                    "EmojiFrownSolid",
                    "EmojiSmileSolid",
                    "ArrowTurnRightSolid",
                    "ArrowTurnLeftSolid",
                    "ArrowDownSolid",
                    "ArrowUpSolid",
                    "CheckmarkSolid",
                    "HouseSolid",
                    "ClockSolid",
                    "ArchiveboxSolid",
                    "HeadphonesSolid",
                    "TgSolid",
                    "ShapeRhombusSolid",
                    "Poop",
                    "ShapeTriangleSolid",
                    "ShapeCircleSolid",
                    "ShapeSquareSolid",
                    "TrashSolid",
                    "BrushSolid",
                    "AsteriskSolid",
                    "RocketSolid",
                    "LeafSolid",
                    "TriangleCircleSolid",
                    "Sparkle",
                ],
            ),
            (
                "ProgressType",
                ProgressType,
                [
                    "ByStatus",
                    "ByChildren",
                    "ByMetric",
                ],
            ),
            (
                "WorkflowType",
                WorkflowType,
                [
                    "Workitem",
                    "Portfolio",
                ],
            ),
            (
                "EstimatesType",
                EstimatesType,
                [
                    "EstimatesInTime",
                    "EstimatesInStoryPoints",
                ],
            ),
            (
                "WorkitemTimeMetricStatus",
                WorkitemTimeMetricStatus,
                [
                    "NotStarted",
                    "InProgress",
                    "Approaching",
                    "Paused",
                    "Breached",
                    "CompletedInTime",
                    "CompletedBreached",
                    "Disabled",
                ],
            ),
            (
                "WorkitemTimeMetricTemplateType",
                WorkitemTimeMetricTemplateType,
                [
                    "Sla",
                    "Ola",
                    "Custom",
                ],
            ),
        ]

        for enum_name, enum_cls, expected_values in cases:
            with self.subTest(enum_name=enum_name):
                self.assertEqual(expected_values, [member.value for member in enum_cls])

    def test_every_spec_enum_is_mirrored_exactly(self) -> None:
        """
        Every enum schema in the committed v4.24.0 snapshot must exist in the
        wrapper with exactly the spec's values (no missing value, no extra
        one, same order), and every wrapper enum must exist in the spec.
        """
        spec_path = Path(__file__).resolve().parent.parent.parent / "docs" / "openapi" / "swagger-v4.24.0.json"
        schemas = json.loads(spec_path.read_text(encoding="utf-8"))["components"]["schemas"]
        spec_enums = {name: schema["enum"] for name, schema in schemas.items() if "enum" in schema}

        wrapper_enums: dict[str, list[str]] = {}
        for module in (enums_module, roles_module):
            for name, cls in inspect.getmembers(module, inspect.isclass):
                if issubclass(cls, enum.Enum) and cls.__module__ == module.__name__:
                    wrapper_enums[name] = [member.value for member in cls]

        self.assertEqual(sorted(spec_enums), sorted(wrapper_enums))
        for name, values in spec_enums.items():
            with self.subTest(enum_name=name):
                self.assertEqual(values, wrapper_enums[name])

    def test_permission_has_workspace_tree_move_and_time_metrics(self) -> None:
        self.assertEqual("WorkspaceTreeMove", roles_module.Permission.WorkspaceTreeMove.value)
        self.assertEqual("WorkspaceTimeMetrics", roles_module.Permission.WorkspaceTimeMetrics.value)


if __name__ == "__main__":
    unittest.main()
