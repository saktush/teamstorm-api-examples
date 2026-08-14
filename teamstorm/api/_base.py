from __future__ import annotations

from dataclasses import dataclass

from teamstorm.client import TsClient


@dataclass(frozen=True, slots=True)
class BaseAPI:
    """
    Common ancestor for every resource ``*API`` class (``WorkitemsAPI``,
    ``AttributesAPI``, ``WorkspacesAPI``, ...).

    A frozen (immutable), slotted dataclass holding a single field: the
    :class:`~teamstorm.client.TsClient` used to make requests. Subclassing is a
    one-liner -- no ``__init__`` override, no extra fields -- because every
    concrete ``*API`` class is stateless beyond the client reference; all
    per-call state (workspace, filters, ids) is passed as method arguments
    instead.

    Contract every subclass follows (see ``docs/api-analysis/conventions.md``
    §1): for a workspace-scoped resource, ``workspace_key: str`` is always the
    first positional parameter on every method, and every other filter/id is
    keyword-only after a bare ``*``. Global (non-workspace) resources simply
    omit ``workspace_key``.
    """

    client: TsClient
