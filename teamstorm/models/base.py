from __future__ import annotations
from typing import Any

from pydantic import BaseModel, ConfigDict


class TsBaseModel(BaseModel):
    """
    Canonical base class for every model in the API wrapper (`docs/api-analysis/conventions.md` §3).

    `populate_by_name=True` lets you construct a model from either its Python
    snake_case field name or its JSON camelCase alias. `extra="forbid"` is
    strict: an unknown field raises `ValidationError` instead of being
    silently accepted.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """
        Dump to a plain dict, defaulting to `by_alias=True, exclude_none=True,
        mode="json"` so the result is ready to hand to `requests`'s `json=`
        kwarg (UUIDs/datetimes/enums become plain `str`) without a caller
        having to remember these three flags.

        TRAP for PATCH bodies: these defaults make it impossible to send an
        intentional `null` for a field, and they cannot distinguish "field
        left unset" from "field explicitly set to None" -- both come out as
        "omit the key". A PATCH request body must instead be dumped with
        `exclude_unset=True, exclude_none=False` passed explicitly (which
        overrides these defaults via `kwargs.setdefault`), so that an
        unassigned field is dropped (server: leave unchanged) while an
        explicitly-assigned `None` is sent as JSON `null` (server: clear the
        field). The server really does distinguish the two -- see
        `docs/api-analysis/upstream-semantics.md` §7 -- and the
        `Patch*RequestBody` models across `teamstorm/models/`, together with
        the `patch()` methods in `teamstorm/api/`, are real examples.
        """
        kwargs.setdefault("by_alias", True)
        kwargs.setdefault("exclude_none", True)
        kwargs.setdefault("mode", "json")
        return super().model_dump(**kwargs)

    def model_dump_json(self, **kwargs: Any) -> str:
        """
        Same defaults and same PATCH trap as `model_dump` above, but returns
        a JSON string instead of a dict.
        """
        kwargs.setdefault("by_alias", True)
        kwargs.setdefault("exclude_none", True)
        return super().model_dump_json(**kwargs)


# Deprecated alias kept for pre-1.0 code that imported ``CwmBaseModel``; use ``TsBaseModel``.
CwmBaseModel = TsBaseModel
