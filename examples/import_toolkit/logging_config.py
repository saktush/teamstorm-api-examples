import logging
import sys
from pathlib import Path


class MaxLevelFilter(logging.Filter):
    def __init__(self, max_level: int):
        super().__init__()
        self.max_level = max_level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno <= self.max_level


def setup_logging(log_file: str) -> logging.Logger:
    logger = logging.getLogger("import_agile")
    logger.setLevel(logging.DEBUG)

    fmt_simple = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    fmt_verbose = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(filename)s:%(lineno)d %(funcName)s() %(message)s"
    )

    h_info = logging.StreamHandler(sys.stdout)
    h_info.setLevel(logging.INFO)
    h_info.addFilter(MaxLevelFilter(logging.INFO))  # пропускаем только INFO (без WARNING/ERROR)
    h_info.setFormatter(fmt_simple)

    h_err = logging.StreamHandler(sys.stdout)
    h_err.setLevel(logging.WARNING)
    h_err.setFormatter(fmt_verbose)

    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    h_file = logging.FileHandler(log_file, encoding="utf-8")
    h_file.setLevel(logging.DEBUG)
    h_file.setFormatter(fmt_verbose)

    logger.handlers = []
    logger.addHandler(h_info)
    logger.addHandler(h_err)
    logger.addHandler(h_file)
    return logger
