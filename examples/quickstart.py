#!/usr/bin/env python3
"""
Runnable version of the Quickstart snippet in the top-level README.

Reads connection details from the environment (falling back to `.env` via
python-dotenv, same as the import_toolkit scripts), constructs a TsClient /
TeamStormAPI pair, fetches one workspace, and prints a couple more real calls on
top: the workitem types configured in that workspace, and how many
workitems it currently holds.

Usage:
    export BASE_URL="https://your-cwm-host"
    export API_TOKEN="YOUR_API_TOKEN"
    export WORKSPACE_KEY="YOUR_WORKSPACE_KEY"
    python examples/quickstart.py

Exits with a clear message (not a traceback) if any of the three required
environment variables is missing, or if the API call itself fails.
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

from teamstorm.client import ApiError, TsClient
from teamstorm.api import TeamStormAPI


def main() -> int:
    load_dotenv()

    base_url = os.getenv("BASE_URL")
    api_token = os.getenv("API_TOKEN")
    workspace_key = os.getenv("WORKSPACE_KEY")

    missing = [
        name
        for name, value in (
            ("BASE_URL", base_url),
            ("API_TOKEN", api_token),
            ("WORKSPACE_KEY", workspace_key),
        )
        if not value
    ]
    if missing:
        print(
            "Missing required environment variable(s): "
            + ", ".join(missing)
            + ".\nSet them directly, or copy .env.template to .env and fill it in.",
            file=sys.stderr,
        )
        return 1

    client = TsClient(base_url=base_url, token=api_token)
    ts = TeamStormAPI(client)

    try:
        workspace = ts.workspaces.get(workspace_key)
        print(workspace.name)

        types = ts.types.list(workspace_key)
        print(f"{len(types)} workitem type(s): {', '.join(t.name for t in types)}")

        workitem_count = ts.workitems.count(workspace_key)
        print(f"{workitem_count} workitem(s) in this workspace")
    except ApiError as e:
        print(f"CWM API call failed: {e}", file=sys.stderr)
        if e.details:
            print(e.details, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
