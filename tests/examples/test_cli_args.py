import importlib
import logging
import sys
import unittest
from argparse import Namespace


def _load_cli_module():
    module_name = "import_toolkit.workflows.imports.cli"
    if module_name in sys.modules:
        return importlib.reload(sys.modules[module_name])
    import import_toolkit.workflows.imports.cli as cli

    return cli


class CliArgsTestCase(unittest.TestCase):
    def test_excel_path_alias_still_supported(self) -> None:
        module = _load_cli_module()
        args = Namespace(input_path=None, excel_path="./agile.xlsx")

        resolved = module.resolve_input_path(args)
        self.assertEqual("./agile.xlsx", resolved)

    def test_input_path_wins_when_both_are_set(self) -> None:
        module = _load_cli_module()
        args = Namespace(input_path="./csv_dir", excel_path="./agile.xlsx")
        logger = logging.getLogger("test.cli")

        with self.assertLogs("test.cli", level="WARNING") as cm:
            resolved = module.resolve_input_path(args, logger=logger)

        self.assertEqual("./csv_dir", resolved)
        self.assertTrue(any("--input-path" in line for line in cm.output))


if __name__ == "__main__":
    unittest.main()
