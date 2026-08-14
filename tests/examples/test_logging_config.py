import logging
import os
import tempfile
import unittest

from import_toolkit.logging_config import setup_logging


class SetupLoggingTestCase(unittest.TestCase):
    def tearDown(self):
        logger = logging.getLogger("import_agile")
        for h in logger.handlers[:]:
            h.close()
        logger.handlers.clear()

    def test_creates_missing_parent_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "nested", "deep", "app.log")
            setup_logging(log_path)
            self.assertTrue(os.path.isdir(os.path.dirname(log_path)))
            self.assertTrue(os.path.isfile(log_path))

    def test_existing_directory_raises_no_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "app.log")
            try:
                setup_logging(log_path)
            except Exception as exc:
                self.fail(f"setup_logging raised unexpectedly: {exc}")

    def test_logger_name_and_handler_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "app.log")
            logger = setup_logging(log_path)
            self.assertEqual(logger.name, "import_agile")
            self.assertEqual(len(logger.handlers), 3)
            handler_types = [type(h).__name__ for h in logger.handlers]
            self.assertEqual(handler_types.count("StreamHandler"), 2)
            self.assertEqual(handler_types.count("FileHandler"), 1)


if __name__ == "__main__":
    unittest.main()
