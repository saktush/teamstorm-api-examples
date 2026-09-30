"""TeamStorm CWM Public API: typed client, resource API wrappers, and pydantic models."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from teamstorm.client import ApiError, RetryConfig, TimeoutConfig, TsClient
from teamstorm.api import TeamStormAPI

try:
    __version__ = version("teamstorm-api-examples")
except PackageNotFoundError:
    # Running from a source checkout that was never `pip install`-ed (editable
    # or otherwise) -- there is no installed distribution metadata to read.
    # This project is not published to a package index; keep the source-tree
    # fallback aligned with the release version declared in pyproject.toml.
    __version__ = "1.1.0"

__all__ = [
    "__version__",
    "ApiError",
    "RetryConfig",
    "TimeoutConfig",
    "TsClient",
    "TeamStormAPI",
]
