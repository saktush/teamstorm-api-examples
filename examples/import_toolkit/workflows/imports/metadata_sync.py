from __future__ import annotations

import logging


def sync_statuses(log: logging.Logger, *, workspace_key: str) -> None:
    log.info(
        "Settings sync: statuses skipped (workspace=%s, no source metadata yet)",
        workspace_key,
    )


def sync_workflows(log: logging.Logger, *, workspace_key: str) -> None:
    log.info(
        "Settings sync: workflows skipped (workspace=%s, no source metadata yet)",
        workspace_key,
    )


def sync_roles(log: logging.Logger, *, workspace_key: str) -> None:
    log.info(
        "Settings sync: roles skipped (workspace=%s, no source metadata yet)",
        workspace_key,
    )
