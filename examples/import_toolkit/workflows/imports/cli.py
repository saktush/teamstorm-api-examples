from __future__ import annotations

import argparse
import logging
import os
from typing import Optional

from dotenv import load_dotenv


def build_arg_parser() -> argparse.ArgumentParser:
    load_dotenv()

    parser = argparse.ArgumentParser(
        "import_agile",
        description="Import sprints and tasks into CWM Public API from Excel/CSV",
    )
    parser.add_argument("--base-url", default=os.getenv("BASE_URL"))
    parser.add_argument("--token", default=os.getenv("API_TOKEN"))
    parser.add_argument("--workspace-key", required=True)
    parser.add_argument("--folder-name", required=True)
    parser.add_argument("--input-path")
    parser.add_argument("--excel-path")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--update-settings", action="store_true")
    parser.add_argument("--sync-members", action="store_true")
    parser.add_argument(
        "--allow-insecure",
        action="store_true",
        default=False,
        help="Allow non-HTTPS base_url (for local/staging use only).",
    )
    parser.add_argument("--log-file", default="./logs/import_agile.log")
    return parser


def resolve_input_path(
    args: argparse.Namespace,
    logger: Optional[logging.Logger] = None,
) -> Optional[str]:
    if args.input_path:
        if args.excel_path and logger:
            logger.warning("Указаны --input-path и --excel-path; используется --input-path, --excel-path игнорируется")
        return args.input_path

    if args.excel_path:
        if logger:
            logger.warning("Параметр --excel-path устарел и будет удален в следующем релизе; используйте --input-path")
        return args.excel_path

    return None


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = build_arg_parser()
    return parser.parse_args(argv)
